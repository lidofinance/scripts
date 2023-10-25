"""
Tests for voting 31/10/2023

"""
from scripts.vote_2023_10_31 import start_vote

from eth_abi.abi import encode_single
from brownie import chain, accounts, ZERO_ADDRESS, reverts
import math

from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    LIDO,
    LDO_TOKEN,
    DAI_TOKEN,
    USDC_TOKEN,
    USDT_TOKEN,
    CHAIN_DEPOSIT_CONTRACT
)
from utils.easy_track import create_permissions
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    validate_evmscript_factory_removed_event,
    EVMScriptFactoryAdded
)
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grantp_event,
    validate_permission_revoke_event,
)
from utils.permission_parameters import Param, SpecialArgumentID, Op, ArgumentValue, encode_argument_value_if

eth = "0x0000000000000000000000000000000000000000"
aragonAgentProxy = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
STETH_ERROR_MARGIN = 2

permission = Permission(
    entity="0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",  # EVMScriptExecutor
    app="0xB9E5CBB9CA5b0d659238807E84D0176930753d86",  # Finance Aragon App
    role="0x5de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc",
)  # keccak256('CREATE_PAYMENTS_ROLE')

eth = {
    "limit": 1_000 * (10**18),
    "address": ZERO_ADDRESS,
}

steth = {
    "limit": 1_000 * (10**18),
    "address": LIDO,
}

ldo = {
    "limit": 5_000_000 * (10**18),
    "address": LDO_TOKEN,
}

dai = {
    "limit": 2_000_000 * (10**18),
    "address": DAI_TOKEN,
}

usdc = {
    "limit": 2_000_000 * (10**6),
    "address": USDC_TOKEN,
}

usdt = {
    "limit": 2_000_000 * (10**6),
    "address": USDT_TOKEN,
}

def amount_limits() -> List[Param]:
    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == LDO)
        Param(token_arg_index, Op.EQ, ArgumentValue(ldo["address"])),
        # 2: { return _amount <= 5_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(ldo["limit"])),
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == ETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(eth["address"])),
        # 5: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(eth["limit"])),
        # 6: else if (7) then (8) else (9)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=7, success=8, failure=9)
        ),
        # 7: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(dai["address"])),
        # 8: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(dai["limit"])),
        # 9: else if (10) then (11) else (12)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=10, success=11, failure=12),
        ),
        # 10: (_token == USDT)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdt["address"])),
        # 11: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdt["limit"])),
        # 12: else if (13) then (14) else (15)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=13, success=14, failure=15),
        ),
        # 13: (_token == USDC)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdc["address"])),
        # 14: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdc["limit"])),
        # 15: else if (16) then (17) else (18)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=16, success=17, failure=18),
        ),
        # 16: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth["address"])),
        # 17: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth["limit"])),
        # 18: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]

def has_payments_permission(acl, finance, sender, token, receiver, amount) -> bool:
    return acl.hasPermission["address,address,bytes32,uint[]"](
        sender, finance, finance.CREATE_PAYMENTS_ROLE(), [token, receiver, amount]
    )

def test_vote(
    helpers,
    accounts,
    interface,
    vote_ids_from_env,
    stranger,
    ldo_holder
):
    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")
    dao_voting = interface.Voting("0x2e59A20f205bB85a89C53f1936454680651E618e")
    acl = interface.ACL("0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb")
    finance = interface.Finance("0xB9E5CBB9CA5b0d659238807E84D0176930753d86")
    agent = accounts.at("0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c", {"force": True})
    evmscriptexecutor = accounts.at("0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977", {"force": True})

    rcc_trusted_caller_and_recepient = accounts.at("0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437", {"force": True})
    pml_trusted_caller_and_recepient = accounts.at("0x17F6b2C738a63a8D3A113a228cfd0b373244633D", {"force": True})
    atc_trusted_caller_and_recepient = accounts.at("0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956", {"force": True})

    rcc_dai_topup_factory_old = interface.IEVMScriptFactory("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_dai_topup_factory_old = interface.IEVMScriptFactory("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_dai_topup_factory_old = interface.IEVMScriptFactory("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    # todo: change addresses
    rcc_stable_topup_factory = interface.TopUpAllowedRecipients("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_stable_topup_factory = interface.TopUpAllowedRecipients("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_stable_topup_factory = interface.TopUpAllowedRecipients("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    # todo: change addresses
    rcc_stable_registry = interface.AllowedRecipientRegistry("0xDc1A0C7849150f466F07d48b38eAA6cE99079f80")
    pml_stable_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    atc_stable_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")

    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 16

    # todo: uncomment when u get new factories address
    # assert rcc_stable_topup_factory not in old_factories_list
    # assert pml_stable_topup_factory not in old_factories_list
    # assert atc_stable_topup_factory not in old_factories_list

    assert rcc_dai_topup_factory_old in old_factories_list
    assert pml_dai_topup_factory_old in old_factories_list
    assert atc_dai_topup_factory_old in old_factories_list

    assert has_payments_permission(acl, finance, permission.entity, eth["address"], ldo_holder.address, eth["limit"])
    assert has_payments_permission(acl, finance, permission.entity, steth["address"], ldo_holder.address, steth["limit"])
    assert has_payments_permission(acl, finance, permission.entity, ldo["address"], ldo_holder.address, ldo["limit"])
    assert has_payments_permission(acl, finance, permission.entity, dai["address"], ldo_holder.address, dai["limit"])
    assert not has_payments_permission(acl, finance, permission.entity, usdt["address"], ldo_holder.address, usdt["limit"])
    assert not has_payments_permission(acl, finance, permission.entity, usdc["address"], ldo_holder.address, usdc["limit"])

    # check regsitries limits before voting
    (
        rcc_already_spent_amount,
        rcc_spendable_balanceInPeriod,
        rcc_period_start_timestamp,
        rcc_period_end_timestamp
    ) = rcc_stable_registry.getPeriodState()

    assert rcc_already_spent_amount == 800000000000000000000000
    assert rcc_spendable_balanceInPeriod ==  2200000000000000000000000
    assert rcc_period_start_timestamp == 1696118400
    assert rcc_period_end_timestamp == 1704067200

    (
        pml_already_spent_amount,
        pml_spendable_balanceInPeriod,
        pml_period_start_timestamp,
        pml_period_end_timestamp
    ) = pml_stable_registry.getPeriodState()

    assert pml_already_spent_amount == 1500000000000000000000000
    assert pml_spendable_balanceInPeriod ==  4500000000000000000000000
    assert pml_period_start_timestamp == 1696118400
    assert pml_period_end_timestamp == 1704067200

    (
        atc_already_spent_amount,
        atc_spendable_balanceInPeriod,
        atc_period_start_timestamp,
        atc_period_end_timestamp
    ) = atc_stable_registry.getPeriodState()

    assert atc_already_spent_amount == 800000000000000000000000
    assert atc_spendable_balanceInPeriod ==  700000000000000000000000
    assert atc_period_start_timestamp == 1696118400
    assert atc_period_end_timestamp == 1704067200

    # Check node operator name before
    NO_registry = interface.NodeOperatorsRegistry(contracts.node_operators_registry)
    prysmatic_labs_node_id = 27
    prysmatic_labs_node_old_name = "Prysmatic Labs"
    prysmatic_labs_node_new_name = "Prysm Team at Offchain Labs"
    prysmatic_labs_node_data_before_voting = NO_registry.getNodeOperator(prysmatic_labs_node_id, True)

    assert prysmatic_labs_node_data_before_voting["name"] == prysmatic_labs_node_old_name, "Incorrect NO#27 name before"

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 16

    # check regsitries limits after voting
    (
        rcc_already_spent_amount,
        rcc_spendable_balanceInPeriod,
        rcc_period_start_timestamp,
        rcc_period_end_timestamp
    ) = rcc_stable_registry.getPeriodState()

    assert rcc_already_spent_amount == 800000000000000000000000
    assert rcc_spendable_balanceInPeriod ==  2200000000000000000000000
    assert rcc_period_start_timestamp == 1696118400
    assert rcc_period_end_timestamp == 1704067200

    (
        pml_already_spent_amount,
        pml_spendable_balanceInPeriod,
        pml_period_start_timestamp,
        pml_period_end_timestamp
    ) = pml_stable_registry.getPeriodState()

    assert pml_already_spent_amount == 1500000000000000000000000
    assert pml_spendable_balanceInPeriod ==  4500000000000000000000000
    assert pml_period_start_timestamp == 1696118400
    assert pml_period_end_timestamp == 1704067200

    (
        atc_already_spent_amount,
        atc_spendable_balanceInPeriod,
        atc_period_start_timestamp,
        atc_period_end_timestamp
    ) = atc_stable_registry.getPeriodState()

    assert atc_already_spent_amount == 800000000000000000000000
    assert atc_spendable_balanceInPeriod ==  700000000000000000000000
    assert atc_period_start_timestamp == 1696118400
    assert atc_period_end_timestamp == 1704067200

    # node operator name
    prysmatic_labs_node_data_after_voting = NO_registry.getNodeOperator(prysmatic_labs_node_id, True)
    assert prysmatic_labs_node_data_after_voting["name"] == prysmatic_labs_node_new_name, "Incorrect NO#27 name after"

    # permissions
    assert has_payments_permission(acl, finance, permission.entity, eth["address"], ldo_holder.address, eth["limit"])
    assert has_payments_permission(acl, finance, permission.entity, steth["address"], ldo_holder.address, steth["limit"])
    assert has_payments_permission(acl, finance, permission.entity, ldo["address"], ldo_holder.address, ldo["limit"])
    assert has_payments_permission(acl, finance, permission.entity, dai["address"], ldo_holder.address, dai["limit"])
    assert has_payments_permission(acl, finance, permission.entity, usdt["address"], ldo_holder.address, usdt["limit"])
    assert has_payments_permission(acl, finance, permission.entity, usdc["address"], ldo_holder.address, usdc["limit"])

    assert not has_payments_permission(acl, finance, permission.entity, eth["address"], ldo_holder.address, eth["limit"] + 1)
    assert not has_payments_permission(acl, finance, permission.entity, steth["address"], ldo_holder.address, steth["limit"] + 1)
    assert not has_payments_permission(acl, finance, permission.entity, ldo["address"], ldo_holder.address, ldo["limit"] + 1)
    assert not has_payments_permission(acl, finance, permission.entity, dai["address"], ldo_holder.address, dai["limit"] + 1)
    assert not has_payments_permission(acl, finance, permission.entity, usdt["address"], ldo_holder.address, usdt["limit"] + 1)
    assert not has_payments_permission(acl, finance, permission.entity, usdc["address"], ldo_holder.address, usdc["limit"] + 1)

    assert not has_payments_permission(acl, finance, accounts[0].address, eth["address"], ldo_holder.address, eth["limit"])
    # assert not has_payments_permission(acl, finance, accounts[0].address, usdc_token, ldo_holder.address, 1)

    # ETH
    deposit = accounts.at(CHAIN_DEPOSIT_CONTRACT, {"force": True})
    deposit.transfer(agent.address, "1000 ether")

    # 1000 ETH
    agent_balance_before = agent.balance()
    eth_balance_before = stranger.balance()
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            ZERO_ADDRESS,
            stranger,
            1000 * 10**18 + 1,
            "ETH transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        ZERO_ADDRESS,
        stranger,
        1000 * 10**18,
        "ETH transfer",
        {"from": evmscriptexecutor}
    )
    assert agent.balance() == agent_balance_before - 1000 * 10**18
    assert stranger.balance() == eth_balance_before + 1000 * 10**18


    # 1000 stETH
    steth_token = interface.ERC20(LIDO)
    agent_steth_balance_before = steth_token.balanceOf(agent)
    stETH_balance_before = steth_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            steth_token,
            stranger,
            1000 * 10**18 + 1,
            "stETH transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        steth_token,
        stranger,
        1000 * 10**18,
        "stETH transfer",
        {"from": evmscriptexecutor}
    )
    assert math.isclose(steth_token.balanceOf(agent), agent_steth_balance_before - 1000 * 10**18, abs_tol=STETH_ERROR_MARGIN)
    assert math.isclose(steth_token.balanceOf(stranger), stETH_balance_before + 1000 * 10**18, abs_tol=STETH_ERROR_MARGIN)

    # # 5_000_000 LDO
    ldo_token = interface.ERC20(LDO_TOKEN)
    agent_ldo_balance_before = ldo_token.balanceOf(agent)
    ldo_balance_before = ldo_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            ldo_token,
            stranger,
            5_000_000 * 10**18 + 1,
            "LDO transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        ldo_token,
        stranger,
        5_000_000 * 10**18,
        "LDO transfer",
        {"from": evmscriptexecutor}
    )
    assert ldo_token.balanceOf(agent) == agent_ldo_balance_before - 5_000_000 * 10**18
    assert ldo_token.balanceOf(stranger) == ldo_balance_before + 5_000_000 * 10**18

    # DAI
    dai_token = interface.ERC20(DAI_TOKEN)
    DAI_HOLDER =  "0x075e72a5eDf65F0A5f44699c7654C1a76941Ddc8"
    dai_token.transfer(agent.address, 2_000_000 * 10**18, { 'from': DAI_HOLDER })

    # # 2_000_000 DAI
    agent_dai_balance_before = dai_token.balanceOf(agent)
    dai_balance_before = dai_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            dai_token,
            stranger,
            2_000_000 * 10**18 + 1,
            "DAI transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        dai_token,
        stranger,
        2_000_000 * 10**18,
        "DAI transfer",
        {"from": evmscriptexecutor}
    )
    assert dai_token.balanceOf(agent) == agent_dai_balance_before - 2_000_000 * 10**18
    assert dai_token.balanceOf(stranger) == dai_balance_before + 2_000_000 * 10**18

    # USDC
    usdc_token = interface.ERC20(USDC_TOKEN)
    USDC_HOLDER =  "0xcEe284F754E854890e311e3280b767F80797180d"
    usdc_token.transfer(agent.address, 2_000_000 * 10**6, { 'from': USDC_HOLDER })

    # # 2_000_000 USDC
    agent_usdc_balance_before = usdc_token.balanceOf(agent)
    usdc_balance_before = usdc_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            usdc_token,
            stranger,
            2_000_000 * 10**6 + 1,
            "USDC transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        usdc_token,
        stranger,
        2_000_000 * 10**6,
        "USDC transfer",
        {"from": evmscriptexecutor}
    )
    assert usdc_token.balanceOf(agent) == agent_usdc_balance_before - 2_000_000 * 10**6
    assert usdc_token.balanceOf(stranger) == usdc_balance_before + 2_000_000 * 10**6

    # USDT
    usdt_token = interface.ERC20(USDT_TOKEN)
    USDT_HOLDER =  "0xF977814e90dA44bFA03b6295A0616a897441aceC"
    usdt_token.transfer(agent.address, 2_000_000 * 10**6, { 'from': USDT_HOLDER })

    # # 2_000_000 USDT
    agent_usdt_balance_before = usdt_token.balanceOf(agent)
    usdt_balance_before = usdt_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            usdt_token,
            stranger,
            2_000_000 * 10**6 + 1,
            "USDT transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        usdt_token,
        stranger,
        2_000_000 * 10**6,
        "USDT transfer",
        {"from": evmscriptexecutor}
    )
    assert usdt_token.balanceOf(agent) == agent_usdt_balance_before - 2_000_000 * 10**6
    assert usdt_token.balanceOf(stranger) == usdt_balance_before + 2_000_000 * 10**6

    # MATIC
    MATIC_TOKEN = "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0"
    MATIC_HOLDER = "0x5e3Ef299fDDf15eAa0432E6e66473ace8c13D908"
    matic_token = interface.ERC20(MATIC_TOKEN)
    matic_token.transfer(agent.address, 1, { 'from': MATIC_HOLDER })

    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            matic_token,
            stranger,
            1,
            "MATIC transfer",
            {"from": evmscriptexecutor},
        )

    ## todo: uncomment tests
    # 1. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
    # assert rcc_dai_topup_factory_old not in updated_factories_list
    # 2. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
    # assert pml_dai_topup_factory_old not in updated_factories_list
    # 3. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
    # assert atc_dai_topup_factory_old not in updated_factories_list

    # 4. Add RCC stable top up EVM script factory 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e to Easy Track
    assert rcc_stable_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        rcc_trusted_caller_and_recepient,
        rcc_stable_topup_factory,
        dai_token,
        [rcc_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(rcc_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, dao_voting)

    # 5. Add PML stable top up EVM script factory 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD to Easy Track
    assert pml_stable_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        pml_trusted_caller_and_recepient,
        pml_stable_topup_factory,
        dai_token,
        [pml_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(pml_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, dao_voting)

    # 6. Add ATC stable top up EVM script factory 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 to Easy Track
    assert atc_stable_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        atc_trusted_caller_and_recepient,
        atc_stable_topup_factory,
        dai_token,
        [atc_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(atc_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, dao_voting)

    # validate vote events
    assert count_vote_items_by_events(vote_tx, dao_voting) == 11, "Incorrect voting items count"

    display_voting_events(vote_tx)

    evs = group_voting_events(vote_tx)

    validate_permission_revoke_event(evs[0], permission)
    validate_permission_grantp_event(evs[1], permission, amount_limits())

    validate_evmscript_factory_removed_event(evs[2], rcc_dai_topup_factory_old)
    validate_evmscript_factory_removed_event(evs[3], pml_dai_topup_factory_old)
    validate_evmscript_factory_removed_event(evs[4], atc_dai_topup_factory_old)
    validate_evmscript_factory_added_event(
        evs[5],
        EVMScriptFactoryAdded(
            factory_addr=rcc_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rcc_stable_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[6],
        EVMScriptFactoryAdded(
            factory_addr=pml_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(pml_stable_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[7],
        EVMScriptFactoryAdded(
            factory_addr=atc_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(atc_stable_registry, "updateSpentAmount")[2:],
        ),
    )

# todo: move to utils
def create_and_enact_payment_motion(
    easy_track,
    trusted_caller,
    factory,
    token,
    recievers,
    transfer_amounts,
    stranger,
):
    agent = accounts.at(aragonAgentProxy, {"force": True})
    agent_balance_before = balance_of(agent, token)
    recievers_balance_before = [balance_of(reciever, token) for reciever in recievers]
    motions_before = easy_track.getMotions()

    recievers_addresses = [reciever.address for reciever in recievers]

    calldata = _encode_calldata("(address[],uint256[])", [recievers_addresses, transfer_amounts])

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    recievers_balance_after = [balance_of(reciever, token)for reciever in recievers]
    for i in range(len(recievers)):
        assert recievers_balance_after[i] == recievers_balance_before[i] + transfer_amounts[i]

    agent_balance_after = balance_of(agent, token)

    assert agent_balance_after == agent_balance_before - sum(transfer_amounts)

def _encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()

def balance_of(address, token):
    if token == eth:
        return address.balance()
    else:
        return token.balanceOf(address)
    
def check_add_and_remove_recipient_with_voting(registry, helpers, ldo_holder, dao_voting):
    recipient_candidate = accounts[0]
    title = ""
    recipients_length_before = len(registry.getAllowedRecipients())

    assert not registry.isRecipientAllowed(recipient_candidate)

    call_script_items = [
        agent_forward(
            [
                (
                    registry.address,
                    registry.addRecipient.encode_input(recipient_candidate, title),
                )
            ]
        )
    ]
    vote_desc_items = ["Add recipient"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )

    assert registry.isRecipientAllowed(recipient_candidate)
    assert len(registry.getAllowedRecipients()) == recipients_length_before + 1, 'Wrong whitelist length'

    call_script_items = [
        agent_forward(
            [
                (
                    registry.address,
                    registry.removeRecipient.encode_input(recipient_candidate),
                )
            ]
        )
    ]
    vote_desc_items = ["Remove recipient"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )

    assert not registry.isRecipientAllowed(recipient_candidate)
    assert len(registry.getAllowedRecipients()) == recipients_length_before, 'Wrong whitelist length'


