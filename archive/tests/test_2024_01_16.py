"""
Tests for voting 16/01/2023

"""

from typing import List
from archive.scripts.vote_2024_01_16 import start_vote, TokenLimit, amount_limits
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import Permission
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, LIDO, network_name
from utils.test.helpers import almostEqWithDiff
from configs.config_mainnet import (
    LIDO,
    FINANCE,
    DAI_TOKEN,
    LDO_TOKEN,
    USDC_TOKEN,
    USDT_TOKEN,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
)
from utils.test.easy_track_helpers import create_and_enact_payment_motion, check_add_and_remove_recipient_with_voting
from utils.test.event_validators.permission import (
    Permission,
    validate_grant_role_event,
    validate_permission_revoke_event,
    validate_permission_grantp_event,
)
from utils.test.event_validators.hash_consensus import (
    validate_hash_consensus_member_removed,
    validate_hash_consensus_member_added,
)
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_deactivated,
    validate_node_operator_name_set_event,
    NodeOperatorNameSetItem,
)
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event,
    validate_update_spent_amount_event,
)
from utils.easy_track import create_permissions
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

eth_limit = TokenLimit(address=ZERO_ADDRESS, limit=1_000 * 10**18)
steth_limit = TokenLimit(address=LIDO, limit=1_000 * 10**18)
ldo_limit = TokenLimit(address=LDO_TOKEN, limit=5_000_000 * (10**18))
dai_limit = TokenLimit(address=DAI_TOKEN, limit=2_000_000 * (10**18))
usdc_limit = TokenLimit(address=USDC_TOKEN, limit=2_000_000 * (10**6))
usdt_limit = TokenLimit(address=USDT_TOKEN, limit=2_000_000 * (10**6))


STETH_TRANSFER_MAX_DELTA = 2
MANAGE_MEMBERS_AND_QUORUM_ROLE = "0x66a484cf1a3c6ef8dfd59d24824943d2853a29d96f34a01271efc55774452a51"

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5

permission = Permission(
    entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
    app=FINANCE,
    role="0x5de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc",
)  # keccak256('CREATE_PAYMENTS_ROLE')

node_operator_name_set = NodeOperatorNameSetItem(nodeOperatorId=20, name="HashKey Cloud")


def test_vote(helpers, accounts, vote_ids_from_env, stranger, bypass_events_decoding, ldo_holder):
    steth = contracts.lido
    agent = contracts.agent
    easy_track = contracts.easy_track
    node_operators_registry = contracts.node_operators_registry
    accounting_hash_consensus = contracts.hash_consensus_for_accounting_oracle
    validators_exit_bus_hash_consensus = contracts.hash_consensus_for_validators_exit_bus_oracle

    assert not contracts.hash_consensus_for_accounting_oracle.hasRole(MANAGE_MEMBERS_AND_QUORUM_ROLE, agent)
    assert not contracts.hash_consensus_for_validators_exit_bus_oracle.hasRole(MANAGE_MEMBERS_AND_QUORUM_ROLE, agent)

    jump_crypto_node_operator_id = 1
    anyblock_analytics_node_operator_id = 12

    jump_crypto_oracle_member = "0x1d0813bf088be3047d827d98524fbf779bc25f00"
    chain_layer_oracle_member = "0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf"

    assert accounting_hash_consensus.getIsMember(jump_crypto_oracle_member)
    assert validators_exit_bus_hash_consensus.getIsMember(jump_crypto_oracle_member)

    assert not accounting_hash_consensus.getIsMember(chain_layer_oracle_member)
    assert not validators_exit_bus_hash_consensus.getIsMember(chain_layer_oracle_member)

    assert accounting_hash_consensus.getQuorum() == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
    assert validators_exit_bus_hash_consensus.getQuorum() == HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM

    rcc_multisig_acc = accounts.at("0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437", force=True)
    pml_multisig_acc = accounts.at("0x17F6b2C738a63a8D3A113a228cfd0b373244633D", force=True)
    atc_multisig_acc = accounts.at("0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956", force=True)
    lego_multisig_acc = accounts.at("0x12a43b049A7D330cB8aEAB5113032D18AE9a9030", force=True)

    active_node_operators_before = node_operators_registry.getActiveNodeOperatorsCount()

    evm_script_factories_before = easy_track.getEVMScriptFactories()

    rcc_dai_top_up_evm_script_factory_old = "0x84f74733ede9bFD53c1B3Ea96338867C94EC313e"
    pml_dai_top_up_evm_script_factory_old = "0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD"
    atc_dai_top_up_evm_script_factory_old = "0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07"

    assert rcc_dai_top_up_evm_script_factory_old in evm_script_factories_before
    assert pml_dai_top_up_evm_script_factory_old in evm_script_factories_before
    assert atc_dai_top_up_evm_script_factory_old in evm_script_factories_before

    rcc_stables_top_up_evm_script_factory_new = "0x75bDecbb6453a901EBBB945215416561547dfDD4"
    pml_stables_top_up_evm_script_factory_new = "0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D"
    atc_stables_top_up_evm_script_factory_new = "0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab"

    assert rcc_stables_top_up_evm_script_factory_new not in evm_script_factories_before
    assert pml_stables_top_up_evm_script_factory_new not in evm_script_factories_before
    assert atc_stables_top_up_evm_script_factory_new not in evm_script_factories_before

    rcc_steth_top_up_evm_script_factory_new = "0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35"
    pml_steth_top_up_evm_script_factory_new = "0xc5527396DDC353BD05bBA578aDAa1f5b6c721136"
    atc_steth_top_up_evm_script_factory_new = "0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9"

    assert rcc_steth_top_up_evm_script_factory_new not in evm_script_factories_before
    assert pml_steth_top_up_evm_script_factory_new not in evm_script_factories_before
    assert atc_steth_top_up_evm_script_factory_new not in evm_script_factories_before

    lego_dai_top_up_evm_script_factory_old = "0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC"
    assert lego_dai_top_up_evm_script_factory_old in evm_script_factories_before

    lego_stables_top_up_evm_script_factory_new = "0x6AB39a8Be67D9305799c3F8FdFc95Caf3150d17c"
    assert lego_stables_top_up_evm_script_factory_new not in evm_script_factories_before

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # I. Replace Jump Crypto with ChainLayer in Lido on Ethereum Oracle set

    # 1. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for AccountingOracle on Lido on Ethereum to Agent
    assert contracts.hash_consensus_for_accounting_oracle.hasRole(MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address)

    # 2. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum to Agent
    assert contracts.hash_consensus_for_validators_exit_bus_oracle.hasRole(
        MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address
    )

    # 3. Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from
    #    HashConsensus for AccountingOracle on Lido on Ethereum
    assert not accounting_hash_consensus.getIsMember(jump_crypto_oracle_member)

    # 4. Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from
    #    HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum
    assert not validators_exit_bus_hash_consensus.getIsMember(jump_crypto_oracle_member)

    # 5. Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to
    #    HashConsensus for AccountingOracle on Lido on Ethereum Oracle set
    assert accounting_hash_consensus.getIsMember(chain_layer_oracle_member)

    # 6. Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to
    #    HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set
    assert validators_exit_bus_hash_consensus.getIsMember(chain_layer_oracle_member)

    assert accounting_hash_consensus.getQuorum() == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
    assert validators_exit_bus_hash_consensus.getQuorum() == HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM

    # II. Deactivate Jump Crypto and Anyblock Analytics node operators
    assert node_operators_registry.getActiveNodeOperatorsCount() == active_node_operators_before - 2

    # 7. Deactivate the node operator named 'Jump Crypto' with id 1 in Curated Node Operators Registry
    assert not node_operators_registry.getNodeOperatorIsActive(jump_crypto_node_operator_id)

    # 8. Deactivate the node operator named 'Anyblock Analytics' with id 12 in Curated Node Operators Registry
    assert not node_operators_registry.getNodeOperatorIsActive(anyblock_analytics_node_operator_id)

    #
    # III. Change the on-chain name of node operator with id 20 from 'HashQuark' to 'HashKey Cloud'
    #
    # 9. Change the on-chain name of node operator with id 20 from 'HashQuark' to 'HashKey Cloud'
    assert node_operators_registry.getNodeOperator(20, True)["name"] == "HashKey Cloud"

    #
    # IV. Add stETH factories for PML, ATC, RCC
    #

    evm_script_factories_after = easy_track.getEVMScriptFactories()

    # 10. Add RCC stETH top up EVM script factory 0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35
    assert rcc_steth_top_up_evm_script_factory_new in evm_script_factories_after
    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=rcc_multisig_acc,
        factory=rcc_steth_top_up_evm_script_factory_new,
        token=steth,
        recievers=[rcc_multisig_acc],
        transfer_amounts=[10 * 10**18],
        stranger=stranger,
    )

    rcc_steth_allowed_recipients_registry = interface.AllowedRecipientRegistry(
        "0xAAC4FcE2c5d55D1152512fe5FAA94DB267EE4863"
    )
    check_add_and_remove_recipient_with_voting(
        registry=rcc_steth_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    # 11. Add PML stETH top up EVM script factory 0xc5527396DDC353BD05bBA578aDAa1f5b6c721136
    assert pml_steth_top_up_evm_script_factory_new in evm_script_factories_after
    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=pml_multisig_acc,
        factory=pml_steth_top_up_evm_script_factory_new,
        token=steth,
        recievers=[pml_multisig_acc],
        transfer_amounts=[10 * 10**18],
        stranger=stranger,
    )

    pml_steth_allowed_recipients_registry = interface.AllowedRecipientRegistry(
        "0x7b9B8d00f807663d46Fb07F87d61B79884BC335B"
    )
    check_add_and_remove_recipient_with_voting(
        registry=pml_steth_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    # 12. Add ATC stETH top up EVM script factory 0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9
    assert atc_steth_top_up_evm_script_factory_new in evm_script_factories_after
    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=atc_multisig_acc,
        factory=atc_steth_top_up_evm_script_factory_new,
        token=steth,
        recievers=[atc_multisig_acc],
        transfer_amounts=[10 * 10**18],
        stranger=stranger,
    )

    atc_steth_allowed_recipients_registry = interface.AllowedRecipientRegistry(
        "0xd3950eB3d7A9B0aBf8515922c0d35D13e85a2c91"
    )
    check_add_and_remove_recipient_with_voting(
        registry=atc_steth_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    # V. Upgrade the Easy Track setups to allow DAI USDT USDC payments for Lido Contributors Group

    assert len(evm_script_factories_after) == len(evm_script_factories_before) + 3

    # 13. Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977

    # 14. Add CREATE_PAYMENTS_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 with single transfer limits of

    #  1000 ETH
    prepare_agent_for_eth_payment(eth_limit.limit)
    validate_evm_script_executor_token_limit(eth_limit)

    # 1000 stETH
    prepare_agent_for_steth_payment(steth_limit.limit)
    validate_evm_script_executor_token_limit(steth_limit)

    # 5_000_000 LDO
    prepare_agent_for_ldo_payment(ldo_limit.limit)
    validate_evm_script_executor_token_limit(ldo_limit)

    # 2,000,000 DAI
    prepare_agent_for_dai_payment(dai_limit.limit)
    validate_evm_script_executor_token_limit(dai_limit)

    # 2,000,000 USDC
    prepare_agent_for_usdc_payment(usdc_limit.limit)
    validate_evm_script_executor_token_limit(usdc_limit)

    #  2,000,000 USDT
    prepare_agent_for_usdt_payment(usdt_limit.limit)
    validate_evm_script_executor_token_limit(usdt_limit)

    # other tokens transfer is not allowed
    stmatic = "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0"
    assert not has_permission(permission, [convert.to_uint(stmatic), convert.to_uint(stranger.address), 1])
    with reverts("APP_AUTH_FAILED"):
        contracts.finance.newImmediatePayment(
            stmatic,
            stranger,
            1,
            "Transfer of not allowed token should fail",
            {"from": accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)},
        )

    # 15. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
    assert rcc_dai_top_up_evm_script_factory_old not in evm_script_factories_after

    # 16. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
    assert pml_dai_top_up_evm_script_factory_old not in evm_script_factories_after

    # 17. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
    assert atc_dai_top_up_evm_script_factory_old not in evm_script_factories_after

    dai_transfer_amount = 1_000 * 10**18
    prepare_agent_for_dai_payment(4 * dai_transfer_amount)

    usdc_transfer_amount = 1_000 * 10**6
    prepare_agent_for_usdc_payment(4 * usdc_transfer_amount)

    usdt_transfer_amount = 1_000 * 10**6
    prepare_agent_for_usdt_payment(4 * usdt_transfer_amount)

    # 18. Add RCC stables top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4
    assert rcc_stables_top_up_evm_script_factory_new in evm_script_factories_after

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=rcc_multisig_acc,
        factory=rcc_stables_top_up_evm_script_factory_new,
        token=interface.Dai(DAI_TOKEN),
        recievers=[rcc_multisig_acc],
        transfer_amounts=[dai_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=rcc_multisig_acc,
        factory=rcc_stables_top_up_evm_script_factory_new,
        token=interface.Usdc(USDC_TOKEN),
        recievers=[rcc_multisig_acc],
        transfer_amounts=[usdc_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=rcc_multisig_acc,
        factory=rcc_stables_top_up_evm_script_factory_new,
        token=interface.Usdt(USDT_TOKEN),
        recievers=[rcc_multisig_acc],
        transfer_amounts=[usdt_transfer_amount],
        stranger=stranger,
    )

    with reverts("TOKEN_NOT_ALLOWED"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=rcc_multisig_acc,
            factory=rcc_stables_top_up_evm_script_factory_new,
            token=steth,
            recievers=[rcc_multisig_acc],
            transfer_amounts=[1],
            stranger=stranger,
        )

    rcc_stables_allowed_recipients_registry = interface.AllowedRecipientRegistry(
        "0xDc1A0C7849150f466F07d48b38eAA6cE99079f80"
    )
    check_add_and_remove_recipient_with_voting(
        registry=rcc_stables_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    # 19. Add PML stables top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D
    assert pml_stables_top_up_evm_script_factory_new in evm_script_factories_after

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=pml_multisig_acc,
        factory=pml_stables_top_up_evm_script_factory_new,
        token=interface.Dai(DAI_TOKEN),
        recievers=[pml_multisig_acc],
        transfer_amounts=[dai_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=pml_multisig_acc,
        factory=pml_stables_top_up_evm_script_factory_new,
        token=interface.Usdc(USDC_TOKEN),
        recievers=[pml_multisig_acc],
        transfer_amounts=[usdc_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=pml_multisig_acc,
        factory=pml_stables_top_up_evm_script_factory_new,
        token=interface.Usdt(USDT_TOKEN),
        recievers=[pml_multisig_acc],
        transfer_amounts=[usdt_transfer_amount],
        stranger=stranger,
    )

    with reverts("TOKEN_NOT_ALLOWED"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=pml_multisig_acc,
            factory=pml_stables_top_up_evm_script_factory_new,
            token=steth,
            recievers=[pml_multisig_acc],
            transfer_amounts=[1],
            stranger=stranger,
        )

    check_add_and_remove_recipient_with_voting(
        registry=interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB"),
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    # 20. Add ATC stables top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab
    assert atc_stables_top_up_evm_script_factory_new in evm_script_factories_after

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=atc_multisig_acc,
        factory=atc_stables_top_up_evm_script_factory_new,
        token=interface.Dai(DAI_TOKEN),
        recievers=[atc_multisig_acc],
        transfer_amounts=[dai_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=atc_multisig_acc,
        factory=atc_stables_top_up_evm_script_factory_new,
        token=interface.Usdc(USDC_TOKEN),
        recievers=[atc_multisig_acc],
        transfer_amounts=[usdc_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=atc_multisig_acc,
        factory=atc_stables_top_up_evm_script_factory_new,
        token=interface.Usdt(USDT_TOKEN),
        recievers=[atc_multisig_acc],
        transfer_amounts=[usdt_transfer_amount],
        stranger=stranger,
    )

    with reverts("TOKEN_NOT_ALLOWED"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=atc_multisig_acc,
            factory=atc_stables_top_up_evm_script_factory_new,
            token=steth,
            recievers=[atc_multisig_acc],
            transfer_amounts=[1],
            stranger=stranger,
        )

    atc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")
    check_add_and_remove_recipient_with_voting(
        registry=atc_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    #
    # VI. Upgrade the Easy Track setups to allow DAI USDT USDC payments for LEGO
    #

    # 21. Remove LEGO DAI top up EVM script factory (old ver) 0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC from Easy Track
    assert lego_dai_top_up_evm_script_factory_old not in evm_script_factories_after

    # 22. Add LEGO stables top up EVM script factory 0x6AB39a8Be67D9305799c3F8FdFc95Caf3150d17c
    assert lego_stables_top_up_evm_script_factory_new in evm_script_factories_after

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=lego_multisig_acc,
        factory=lego_stables_top_up_evm_script_factory_new,
        token=interface.Dai(DAI_TOKEN),
        recievers=[lego_multisig_acc],
        transfer_amounts=[dai_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=lego_multisig_acc,
        factory=lego_stables_top_up_evm_script_factory_new,
        token=interface.Usdc(USDC_TOKEN),
        recievers=[lego_multisig_acc],
        transfer_amounts=[usdc_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=lego_multisig_acc,
        factory=lego_stables_top_up_evm_script_factory_new,
        token=interface.Usdt(USDT_TOKEN),
        recievers=[lego_multisig_acc],
        transfer_amounts=[usdt_transfer_amount],
        stranger=stranger,
    )

    with reverts("TOKEN_NOT_ALLOWED"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=lego_multisig_acc,
            factory=lego_stables_top_up_evm_script_factory_new,
            token=steth,
            recievers=[lego_multisig_acc],
            transfer_amounts=[1],
            stranger=stranger,
        )

    lego_stables_allowed_recipients_registry = interface.AllowedRecipientRegistry(
        "0xb0FE4D300334461523D9d61AaD90D0494e1Abb43"
    )
    check_add_and_remove_recipient_with_voting(
        registry=lego_stables_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    #
    # VII.  Decrease the limit for Easy Track TRP setup to 9,178,284.42 LDO
    #

    spent_limit = 9178284_42 * 10**16
    trp_allowed_recipients_registry = interface.AllowedRecipientRegistry("0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8")

    # 23. Set spend amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0
    assert trp_allowed_recipients_registry.spendableBalance() == spent_limit

    # 24. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to TBA
    period_duration_month = 12
    period_start = 1704067200  # 2024-01-01 00:00:00 UTC
    period_end = 1735689600  # 2025-01-01 00:00:00 UTC
    assert trp_allowed_recipients_registry.getLimitParameters() == (spent_limit, period_duration_month)
    assert trp_allowed_recipients_registry.getPeriodState() == (0, spent_limit, period_start, period_end)

    trp_multisig_acc = accounts.at("0x834560F580764Bc2e0B16925F8bF229bb00cB759", force=True)
    trp_top_up_evm_script_factory = "0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C"

    ldo_spent = 0
    while spent_limit - ldo_spent > ldo_limit.limit:
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=trp_multisig_acc,
            factory=trp_top_up_evm_script_factory,
            token=contracts.ldo_token,
            recievers=[trp_multisig_acc],
            transfer_amounts=[ldo_limit.limit],
            stranger=stranger,
        )
        ldo_spent += ldo_limit.limit

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=trp_multisig_acc,
        factory=trp_top_up_evm_script_factory,
        token=contracts.ldo_token,
        recievers=[trp_multisig_acc],
        transfer_amounts=[spent_limit - ldo_spent],
        stranger=stranger,
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=trp_multisig_acc,
            factory=trp_top_up_evm_script_factory,
            token=contracts.ldo_token,
            recievers=[trp_multisig_acc],
            transfer_amounts=[1],
            stranger=stranger,
        )

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 24, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)

    assert get_lido_vote_cid_from_str(metadata) == "bafkreibugpzhp7nexxg7c6jpmmszikvaj2vscxw426zewa6uyv3z5y6ak4"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    #
    # I. Replace Jump Crypto with ChainLayer in Lido on Ethereum Oracle set
    #

    validate_grant_role_event(evs[0], MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address, agent.address)
    validate_grant_role_event(evs[1], MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address, agent.address)

    validate_hash_consensus_member_removed(
        evs[2], jump_crypto_oracle_member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM, new_total_members=8
    )
    validate_hash_consensus_member_removed(
        evs[3], jump_crypto_oracle_member, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM, new_total_members=8
    )

    validate_hash_consensus_member_added(
        evs[4], chain_layer_oracle_member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM, new_total_members=9
    )
    validate_hash_consensus_member_added(
        evs[5], chain_layer_oracle_member, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM, new_total_members=9
    )

    #
    # II. Deactivate Jump Crypto and Anyblock Analytics node operators
    #
    validate_node_operator_deactivated(evs[6], jump_crypto_node_operator_id)
    validate_node_operator_deactivated(evs[7], anyblock_analytics_node_operator_id)

    #
    # III. Change the on-chain name of node operator with id 20 from 'HashQuark' to 'HashKey Cloud'
    #
    validate_node_operator_name_set_event(evs[8], node_operator_name_item=node_operator_name_set)

    #
    # IV. Add stETH factories for PML, ATC, RCC
    #
    validate_evmscript_factory_added_event(
        evs[9],
        EVMScriptFactoryAdded(
            factory_addr=rcc_steth_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rcc_steth_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    validate_evmscript_factory_added_event(
        evs[10],
        EVMScriptFactoryAdded(
            factory_addr=pml_steth_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(pml_steth_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    validate_evmscript_factory_added_event(
        evs[11],
        EVMScriptFactoryAdded(
            factory_addr=atc_steth_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(atc_steth_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    #
    # V. Upgrade the Easy Track setups to allow DAI USDT USDC payments for Lido Contributors Group
    #
    validate_permission_revoke_event(evs[12], permission)
    validate_permission_grantp_event(evs[13], permission, amount_limits())

    validate_evmscript_factory_removed_event(evs[14], rcc_dai_top_up_evm_script_factory_old)
    validate_evmscript_factory_removed_event(evs[15], pml_dai_top_up_evm_script_factory_old)
    validate_evmscript_factory_removed_event(evs[16], atc_dai_top_up_evm_script_factory_old)

    validate_evmscript_factory_added_event(
        evs[17],
        EVMScriptFactoryAdded(
            factory_addr=rcc_stables_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rcc_stables_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    pml_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    validate_evmscript_factory_added_event(
        evs[18],
        EVMScriptFactoryAdded(
            factory_addr=pml_stables_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(pml_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    validate_evmscript_factory_added_event(
        evs[19],
        EVMScriptFactoryAdded(
            factory_addr=atc_stables_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(atc_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    #
    # VI. Upgrade the Easy Track setups to allow DAI USDT USDC payments for LEGO
    #
    validate_evmscript_factory_removed_event(evs[20], lego_dai_top_up_evm_script_factory_old)

    validate_evmscript_factory_added_event(
        evs[21],
        EVMScriptFactoryAdded(
            factory_addr=lego_stables_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(lego_stables_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    #
    # VII.Decrease the limit for Easy Track TRP setup to 9,178,284.42 LDO
    #
    old_spent_limit = 22_000_000 * 10**18
    validate_update_spent_amount_event(
        evs[22],
        already_spent_amount=0,
        spendable_balance_in_period=old_spent_limit,
        period_start_timestamp=period_start,
        period_end_timestamp=period_end,
        is_period_advanced=True,
    )
    validate_set_limit_parameter_event(
        evs[23], limit=spent_limit, period_duration_month=period_duration_month, period_start_timestamp=period_start
    )


def has_permission(permission: Permission, how: List[int]) -> bool:
    return contracts.acl.hasPermission["address,address,bytes32,uint[]"](
        permission.entity, permission.app, permission.role, how
    )


def prepare_agent_for_ldo_payment(amount: int):
    agent, ldo = contracts.agent, contracts.ldo_token
    assert ldo.balanceOf(agent) >= amount, "Insufficient LDO balance 🫡"


def prepare_agent_for_eth_payment(amount: int):
    agent = contracts.agent
    web3.provider.make_request("hardhat_setBalance", [agent.address, hex(amount)])
    assert agent.balance() >= eth_limit.limit


def prepare_agent_for_steth_payment(amount: int):
    agent, steth = contracts.agent, contracts.lido
    eth_whale = accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)
    if steth.balanceOf(agent) < amount:
        steth.submit(ZERO_ADDRESS, {"from": eth_whale, "value": amount + 2 * STETH_TRANSFER_MAX_DELTA})
        steth.transfer(agent, amount + STETH_TRANSFER_MAX_DELTA, {"from": eth_whale})
    assert steth.balanceOf(agent) >= amount, "Insufficient stETH balance"


def prepare_agent_for_dai_payment(amount: int):
    agent, dai = contracts.agent, interface.Dai(DAI_TOKEN)
    if dai.balanceOf(agent) < amount:
        dai_ward_impersonated = accounts.at("0x9759A6Ac90977b93B58547b4A71c78317f391A28", force=True)
        dai.mint(agent, amount, {"from": dai_ward_impersonated})

    assert dai.balanceOf(agent) >= amount, f"Insufficient DAI balance"


def prepare_agent_for_usdc_payment(amount: int):
    agent, usdc = contracts.agent, interface.Usdc(USDC_TOKEN)
    if usdc.balanceOf(agent) < amount:
        usdc_minter = accounts.at("0x5B6122C109B78C6755486966148C1D70a50A47D7", force=True)
        usdc_controller = accounts.at("0x79E0946e1C186E745f1352d7C21AB04700C99F71", force=True)
        usdc_master_minter = interface.UsdcMasterMinter("0xE982615d461DD5cD06575BbeA87624fda4e3de17")
        usdc_master_minter.incrementMinterAllowance(amount, {"from": usdc_controller})
        usdc.mint(agent, amount, {"from": usdc_minter})

    assert usdc.balanceOf(agent) >= amount, "Insufficient USDC balance"


def prepare_agent_for_usdt_payment(amount: int):
    agent, usdt = contracts.agent, interface.Usdt(USDT_TOKEN)
    if usdt.balanceOf(agent) < amount:
        usdt_owner = accounts.at("0xC6CDE7C39eB2f0F0095F41570af89eFC2C1Ea828", force=True)
        usdt.issue(amount, {"from": usdt_owner})
        usdt.transfer(agent, amount, {"from": usdt_owner})

    assert usdt.balanceOf(agent) >= amount, "Insufficient USDT balance"


def validate_evm_script_executor_token_limit(token_limit: TokenLimit):
    agent, finance, stranger = contracts.agent, contracts.finance, accounts[0]
    evm_script_executor_acc = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)

    token_uint, recipient_uint = convert.to_uint(token_limit.address), convert.to_uint(stranger.address)
    assert has_permission(permission, [token_uint, recipient_uint, token_limit.limit])
    assert not has_permission(permission, [token_uint, recipient_uint, token_limit.limit + 1])

    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            token_limit.address,
            stranger,
            token_limit.limit + 1,
            "Transfer to stranger should fail",
            {"from": evm_script_executor_acc},
        )

    token = None if token_limit.address == ZERO_ADDRESS else interface.ERC20(token_limit.address)
    agent_balance_before = agent.balance() if token is None else token.balanceOf(agent)
    stranger_balance_before = stranger.balance() if token is None else token.balanceOf(stranger)

    finance.newImmediatePayment(
        token_limit.address,
        stranger,
        token_limit.limit,
        "Successful transfer",
        {"from": evm_script_executor_acc},
    )

    agent_balance_after = agent.balance() if token is None else token.balanceOf(agent)
    stranger_balance_after = stranger.balance() if token is None else token.balanceOf(stranger)
    allowed_diff = STETH_TRANSFER_MAX_DELTA if token_limit.address == LIDO else 0

    assert almostEqWithDiff(agent_balance_after, agent_balance_before - token_limit.limit, diff=allowed_diff)
    assert almostEqWithDiff(stranger_balance_after, stranger_balance_before + token_limit.limit, diff=allowed_diff)
