"""
Tests for voting 12/12/2023

"""

from typing import List
from scripts.vote_2023_12_12 import start_vote, TokenLimit, amount_limits
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import Payout, validate_token_payout_event
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
from utils.test.easy_track_helpers import create_and_enact_payment_motion
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
from utils.test.event_validators.node_operators_registry import validate_node_operator_deactivated
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
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


def test_vote(helpers, accounts, vote_ids_from_env, stranger, bypass_events_decoding):
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

    rcc_steth_balance_before = steth.balanceOf(rcc_multisig_acc)
    rcc_payout = Payout(
        token_addr=steth.address, from_addr=agent.address, to_addr=rcc_multisig_acc.address, amount=218 * 10**18
    )

    pml_steth_balance_before = steth.balanceOf(pml_multisig_acc)
    pml_payout = Payout(
        token_addr=steth.address, from_addr=agent.address, to_addr=pml_multisig_acc.address, amount=348 * 10**18
    )

    atc_steth_balance_before = steth.balanceOf(atc_multisig_acc)
    atc_payout = Payout(
        token_addr=steth.address, from_addr=agent.address, to_addr=atc_multisig_acc.address, amount=305 * 10**18
    )

    agent_steth_balance_before = steth.balanceOf(agent)

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

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # I. Replacing Jump Crypto with ChainLayer in Lido on Ethereum Oracle set

    # 1. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for AccountingOracle on Lido on Ethereum to Agent
    assert contracts.hash_consensus_for_accounting_oracle.hasRole(MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address)

    # 2. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum to Agent
    assert contracts.hash_consensus_for_validators_exit_bus_oracle.hasRole(
        MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address
    )

    # 3. Remove the oracle member named 'Jump Crypto' with address
    #    0x1d0813bf088be3047d827d98524fbf779bc25f00 from HashConsensus for AccountingOracle on Lido on Ethereum
    assert not accounting_hash_consensus.getIsMember(jump_crypto_oracle_member)

    # 4. Remove the oracle member named 'Jump Crypto' with address
    #    0x1d0813bf088be3047d827d98524fbf779bc25f00 from HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum
    assert not validators_exit_bus_hash_consensus.getIsMember(jump_crypto_oracle_member)

    # 5. Add oracle member named 'ChainLayer' with address
    #    0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to HashConsensus for AccountingOracle on Lido on Ethereum Oracle set
    assert accounting_hash_consensus.getIsMember(chain_layer_oracle_member)

    # 6. Add oracle member named 'ChainLayer' with address
    #    0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set
    assert validators_exit_bus_hash_consensus.getIsMember(chain_layer_oracle_member)

    assert accounting_hash_consensus.getQuorum() == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
    assert validators_exit_bus_hash_consensus.getQuorum() == HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM

    # II. Deactivation of Jump Crypto and Anyblock Analytics node operators
    assert node_operators_registry.getActiveNodeOperatorsCount() == active_node_operators_before - 2

    # 7. Deactivate the node operator named 'Jump Crypto' with id 1 in Curated Node Operator Registry
    assert not node_operators_registry.getNodeOperatorIsActive(jump_crypto_node_operator_id)

    # 8. Deactivate the node operator named ‘Anyblock Analytics' with id 12 in Curated Node Operator Registry
    assert not node_operators_registry.getNodeOperatorIsActive(anyblock_analytics_node_operator_id)

    # III. Replenishment of Lido Contributors Group multisigs with stETH
    agent_steth_balance_after = steth.balanceOf(agent)
    assert almostEqWithDiff(
        agent_steth_balance_after,
        agent_steth_balance_before - (pml_payout.amount + rcc_payout.amount + atc_payout.amount),
        diff=3 * STETH_TRANSFER_MAX_DELTA,  # happens 3 transfers, so max possible error is three times larger
    )

    # 9. Transfer 218 stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
    rcc_steth_balance_after = steth.balanceOf(rcc_multisig_acc)
    assert almostEqWithDiff(
        rcc_steth_balance_after, rcc_steth_balance_before + rcc_payout.amount, diff=STETH_TRANSFER_MAX_DELTA
    )

    # 10. Transfer 348 stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
    pml_steth_balance_after = steth.balanceOf(pml_multisig_acc)
    assert almostEqWithDiff(
        pml_steth_balance_after, pml_steth_balance_before + pml_payout.amount, diff=STETH_TRANSFER_MAX_DELTA
    )

    # 11. Transfer 305 stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956
    atc_steth_balance_after = steth.balanceOf(atc_multisig_acc)
    assert almostEqWithDiff(
        atc_steth_balance_after, atc_steth_balance_before + atc_payout.amount, diff=STETH_TRANSFER_MAX_DELTA
    )

    # IV. Updating the Easy Track setups to allow DAI USDT USDC payments for Lido Contributors Group
    evm_script_factories_after = easy_track.getEVMScriptFactories()
    assert len(evm_script_factories_before) == len(evm_script_factories_after)

    # 12. Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977

    # 13. Add CREATE_PAYMENTS_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 with single transfer limits of

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

    # 14. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
    assert rcc_dai_top_up_evm_script_factory_old not in evm_script_factories_after

    # 15. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
    assert pml_dai_top_up_evm_script_factory_old not in evm_script_factories_after

    # 16. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
    assert atc_dai_top_up_evm_script_factory_old not in evm_script_factories_after

    # 17. Add RCC stable top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4
    assert rcc_stables_top_up_evm_script_factory_new in evm_script_factories_after

    dai_transfer_amount = 1_000 * 10**18
    prepare_agent_for_dai_payment(3 * dai_transfer_amount)

    usdc_transfer_amount = 1_000 * 10**6
    prepare_agent_for_usdc_payment(3 * usdc_transfer_amount)

    usdt_transfer_amount = 1_000 * 10**6
    prepare_agent_for_usdt_payment(3 * usdt_transfer_amount)

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

    # 18. Add PML stable top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D
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

    # 19. Add ATC stable top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab
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

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 19, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)

    assert get_lido_vote_cid_from_str(metadata) == "bafkreibxxfz3stpvlgap23qkrmlqx4qjr6ax4v6h2gdstal6c4fqfwvhji"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

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

    validate_node_operator_deactivated(evs[6], jump_crypto_node_operator_id)
    validate_node_operator_deactivated(evs[7], anyblock_analytics_node_operator_id)

    validate_token_payout_event(evs[8], rcc_payout, is_steth=True)
    validate_token_payout_event(evs[9], pml_payout, is_steth=True)
    validate_token_payout_event(evs[10], atc_payout, is_steth=True)

    validate_permission_revoke_event(evs[11], permission)
    validate_permission_grantp_event(evs[12], permission, amount_limits())

    validate_evmscript_factory_removed_event(evs[13], rcc_dai_top_up_evm_script_factory_old)
    validate_evmscript_factory_removed_event(evs[14], pml_dai_top_up_evm_script_factory_old)
    validate_evmscript_factory_removed_event(evs[15], atc_dai_top_up_evm_script_factory_old)

    rcc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xDc1A0C7849150f466F07d48b38eAA6cE99079f80")
    validate_evmscript_factory_added_event(
        evs[16],
        EVMScriptFactoryAdded(
            factory_addr=rcc_stables_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rcc_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    pml_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    validate_evmscript_factory_added_event(
        evs[17],
        EVMScriptFactoryAdded(
            factory_addr=pml_stables_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(pml_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    atc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")
    validate_evmscript_factory_added_event(
        evs[18],
        EVMScriptFactoryAdded(
            factory_addr=atc_stables_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(atc_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
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
    web3.provider.make_request("evm_setAccountBalance", [agent.address, hex(amount)])
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
