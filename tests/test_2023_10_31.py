"""
Tests for voting 31/10/2023

"""

import math
from scripts.vote_2023_10_31 import start_vote
from eth_abi.abi import encode_single
from brownie import chain, accounts, ZERO_ADDRESS, reverts
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
from utils.test.easy_track_helpers import (
    create_and_enact_payment_motion,
    check_add_and_remove_recipient_with_voting
)
from utils.test.event_validators.payout import (
    Payout,
    validate_token_payout_event
)
from utils.permission_parameters import (
    Param,
    SpecialArgumentID,
    Op,
    ArgumentValue,
    encode_argument_value_if
)
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    LIDO,
    LDO_TOKEN,
    DAI_TOKEN,
    USDC_TOKEN,
    USDT_TOKEN,
    CHAIN_DEPOSIT_CONTRACT,
    FINANCE,
    AGENT
)

eth = "0x0000000000000000000000000000000000000000"
STETH_ERROR_MARGIN = 2

permission = Permission(
    entity="0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",  # EVMScriptExecutor
    app=FINANCE,  # Finance Aragon App
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

def test_vote(
    helpers,
    accounts,
    interface,
    vote_ids_from_env,
    stranger,
    ldo_holder
):
    agent = accounts.at(AGENT, {"force": True})
    evmscriptexecutor = accounts.at("0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977", {"force": True})
    usdt_holder =  "0xF977814e90dA44bFA03b6295A0616a897441aceC"
    usdc_holder =  "0xcEe284F754E854890e311e3280b767F80797180d"
    dai_holder =  "0x075e72a5eDf65F0A5f44699c7654C1a76941Ddc8"
    rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
    pml_multisig_address = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
    atc_multisig_address = "0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956"

    rcc_trusted_caller_and_recepient = accounts.at(rcc_multisig_address, {"force": True})
    pml_trusted_caller_and_recepient = accounts.at(pml_multisig_address, {"force": True})
    atc_trusted_caller_and_recepient = accounts.at(atc_multisig_address, {"force": True})

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

    old_factories_list = contracts.easy_track.getEVMScriptFactories()
    assert len(old_factories_list) == 16

    # todo: uncomment when u get new factories address
    # assert rcc_stable_topup_factory not in old_factories_list
    # assert pml_stable_topup_factory not in old_factories_list
    # assert atc_stable_topup_factory not in old_factories_list

    assert rcc_dai_topup_factory_old in old_factories_list
    assert pml_dai_topup_factory_old in old_factories_list
    assert atc_dai_topup_factory_old in old_factories_list

    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, eth["address"], ldo_holder.address, eth["limit"])
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, steth["address"], ldo_holder.address, steth["limit"])
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, ldo["address"], ldo_holder.address, ldo["limit"])
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, dai["address"], ldo_holder.address, dai["limit"])
    assert not has_payments_permission(contracts.acl, contracts.finance, permission.entity, usdt["address"], ldo_holder.address, usdt["limit"])
    assert not has_payments_permission(contracts.acl, contracts.finance, permission.entity, usdc["address"], ldo_holder.address, usdc["limit"])

    # check regsitries parameters before voting
    (
        rcc_already_spent_amount_before,
        rcc_spendable_balanceInPeriod_before,
        rcc_period_start_timestamp_before,
        rcc_period_end_timestamp_before
    ) = rcc_stable_registry.getPeriodState()

    assert rcc_already_spent_amount_before == 800000000000000000000000
    assert rcc_spendable_balanceInPeriod_before ==  2200000000000000000000000
    assert rcc_period_start_timestamp_before == 1696118400
    assert rcc_period_end_timestamp_before == 1704067200

    (
        pml_already_spent_amount_before,
        pml_spendable_balanceInPeriod_before,
        pml_period_start_timestamp_before,
        pml_period_end_timestamp_before
    ) = pml_stable_registry.getPeriodState()

    assert pml_already_spent_amount_before == 1500000000000000000000000
    assert pml_spendable_balanceInPeriod_before ==  4500000000000000000000000
    assert pml_period_start_timestamp_before == 1696118400
    assert pml_period_end_timestamp_before == 1704067200

    (
        atc_already_spent_amount_before,
        atc_spendable_balanceInPeriod_before,
        atc_period_start_timestamp_before,
        atc_period_end_timestamp_before
    ) = atc_stable_registry.getPeriodState()

    assert atc_already_spent_amount_before == 800000000000000000000000
    assert atc_spendable_balanceInPeriod_before ==  700000000000000000000000
    assert atc_period_start_timestamp_before == 1696118400
    assert atc_period_end_timestamp_before == 1704067200

    rcc_multisig_balance_before = contracts.lido.balanceOf(rcc_multisig_address)
    pml_multisig_balance_before = contracts.lido.balanceOf(pml_multisig_address)
    atc_multisig_balance_before = contracts.lido.balanceOf(atc_multisig_address)
    dao_balance_before = contracts.lido.balanceOf(AGENT)

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    updated_factories_list = contracts.easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 16

    rcc_multisig_balance_after = contracts.lido.balanceOf(rcc_multisig_address)
    pml_multisig_balance_after = contracts.lido.balanceOf(pml_multisig_address)
    atc_multisig_balance_after = contracts.lido.balanceOf(atc_multisig_address)
    dao_balance_after = contracts.lido.balanceOf(AGENT)

    rcc_fund_payout = Payout(token_addr=LIDO, from_addr=contracts.agent, to_addr=rcc_multisig_address, amount=1 * (10**18))
    pml_fund_payout = Payout(token_addr=LIDO, from_addr=contracts.agent, to_addr=rcc_multisig_address, amount=1 * (10**18))
    atc_fund_payout = Payout(token_addr=LIDO, from_addr=contracts.agent, to_addr=rcc_multisig_address, amount=1 * (10**18))
    dao_fund_payout = Payout(token_addr=LIDO, from_addr=contracts.agent, to_addr=rcc_multisig_address, amount=1 * (10**18) + 1 * (10**18) + 1 * (10**18))

    steth_balance_checker(rcc_multisig_balance_after - rcc_multisig_balance_before, rcc_fund_payout.amount)
    steth_balance_checker(pml_multisig_balance_after - pml_multisig_balance_before, pml_fund_payout.amount)
    steth_balance_checker(atc_multisig_balance_after - atc_multisig_balance_before, atc_fund_payout.amount)
    steth_balance_checker(dao_balance_before - dao_balance_after, dao_fund_payout.amount)

    # check registries parameters after voting
    (
        rcc_already_spent_amount_after,
        rcc_spendable_balanceInPeriod_after,
        rcc_period_start_timestamp_after,
        rcc_period_end_timestamp_after
    ) = rcc_stable_registry.getPeriodState()

    assert rcc_already_spent_amount_before == rcc_already_spent_amount_after == 800000000000000000000000
    assert rcc_spendable_balanceInPeriod_before == rcc_spendable_balanceInPeriod_after == 2200000000000000000000000
    assert rcc_period_start_timestamp_before == rcc_period_start_timestamp_after == 1696118400
    assert rcc_period_end_timestamp_before == rcc_period_end_timestamp_after == 1704067200

    (
        pml_already_spent_amount_after,
        pml_spendable_balanceInPeriod_after,
        pml_period_start_timestamp_after,
        pml_period_end_timestamp_after
    ) = pml_stable_registry.getPeriodState()

    assert pml_already_spent_amount_before == pml_already_spent_amount_after == 1500000000000000000000000
    assert pml_spendable_balanceInPeriod_before == pml_spendable_balanceInPeriod_after == 4500000000000000000000000
    assert pml_period_start_timestamp_before == pml_period_start_timestamp_after == 1696118400
    assert pml_period_end_timestamp_before == pml_period_end_timestamp_after == 1704067200

    (
        atc_already_spent_amount_after,
        atc_spendable_balanceInPeriod_after,
        atc_period_start_timestamp_after,
        atc_period_end_timestamp_after
    ) = atc_stable_registry.getPeriodState()

    assert atc_already_spent_amount_before == atc_already_spent_amount_after == 800000000000000000000000
    assert atc_spendable_balanceInPeriod_before == atc_spendable_balanceInPeriod_after == 700000000000000000000000
    assert atc_period_start_timestamp_before == atc_period_start_timestamp_after == 1696118400
    assert atc_period_end_timestamp_before == atc_period_end_timestamp_after == 1704067200

    # permissions
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, eth["address"], ldo_holder.address, eth["limit"])
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, steth["address"], ldo_holder.address, steth["limit"])
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, ldo["address"], ldo_holder.address, ldo["limit"])
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, dai["address"], ldo_holder.address, dai["limit"])
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, usdt["address"], ldo_holder.address, usdt["limit"])
    assert has_payments_permission(contracts.acl, contracts.finance, permission.entity, usdc["address"], ldo_holder.address, usdc["limit"])

    assert not has_payments_permission(contracts.acl, contracts.finance, permission.entity, eth["address"], ldo_holder.address, eth["limit"] + 1)
    assert not has_payments_permission(contracts.acl, contracts.finance, permission.entity, steth["address"], ldo_holder.address, steth["limit"] + 1)
    assert not has_payments_permission(contracts.acl, contracts.finance, permission.entity, ldo["address"], ldo_holder.address, ldo["limit"] + 1)
    assert not has_payments_permission(contracts.acl, contracts.finance, permission.entity, dai["address"], ldo_holder.address, dai["limit"] + 1)
    assert not has_payments_permission(contracts.acl, contracts.finance, permission.entity, usdt["address"], ldo_holder.address, usdt["limit"] + 1)
    assert not has_payments_permission(contracts.acl, contracts.finance, permission.entity, usdc["address"], ldo_holder.address, usdc["limit"] + 1)

    assert not has_payments_permission(contracts.acl, contracts.finance, accounts[0].address, eth["address"], ldo_holder.address, eth["limit"])
    # assert not has_payments_permission(acl, finance, accounts[0].address, usdc_token, ldo_holder.address, 1)

    # ETH
    deposit = accounts.at(CHAIN_DEPOSIT_CONTRACT, {"force": True})
    deposit.transfer(agent.address, "1000 ether")
    # Check ETH limits. 1000 ETH
    agent_balance_before = agent.balance()
    eth_balance_before = stranger.balance()
    with reverts("APP_AUTH_FAILED"):
        contracts.finance.newImmediatePayment(
            ZERO_ADDRESS,
            stranger,
            1000 * 10**18 + 1,
            "ETH transfer",
            {"from": evmscriptexecutor},
        )
    contracts.finance.newImmediatePayment(
        ZERO_ADDRESS,
        stranger,
        1000 * 10**18,
        "ETH transfer",
        {"from": evmscriptexecutor}
    )
    assert agent.balance() == agent_balance_before - 1000 * 10**18
    assert stranger.balance() == eth_balance_before + 1000 * 10**18

    # stETH
    # Check stETH limits. 1000 stETH.
    steth_token = interface.ERC20(LIDO)
    agent_steth_balance_before = steth_token.balanceOf(agent)
    stETH_balance_before = steth_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        contracts.finance.newImmediatePayment(
            steth_token,
            stranger,
            1000 * 10**18 + 1,
            "stETH transfer",
            {"from": evmscriptexecutor},
        )
    contracts.finance.newImmediatePayment(
        steth_token,
        stranger,
        1000 * 10**18,
        "stETH transfer",
        {"from": evmscriptexecutor}
    )
    assert math.isclose(steth_token.balanceOf(agent), agent_steth_balance_before - 1000 * 10**18, abs_tol=STETH_ERROR_MARGIN)
    assert math.isclose(steth_token.balanceOf(stranger), stETH_balance_before + 1000 * 10**18, abs_tol=STETH_ERROR_MARGIN)

    # LDO
    # Check LDO limits. 5_000_000 LDO
    agent_ldo_balance_before = contracts.ldo_token.balanceOf(agent)
    ldo_balance_before = contracts.ldo_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        contracts.finance.newImmediatePayment(
            contracts.ldo_token,
            stranger,
            5_000_000 * 10**18 + 1,
            "LDO transfer",
            {"from": evmscriptexecutor},
        )
    contracts.finance.newImmediatePayment(
        contracts.ldo_token,
        stranger,
        5_000_000 * 10**18,
        "LDO transfer",
        {"from": evmscriptexecutor}
    )
    assert contracts.ldo_token.balanceOf(agent) == agent_ldo_balance_before - 5_000_000 * 10**18
    assert contracts.ldo_token.balanceOf(stranger) == ldo_balance_before + 5_000_000 * 10**18

    # DAI
    # Top up agent DAI balance.
    contracts.dai_token.transfer(agent.address, 2_000_000 * 10**18, { 'from': dai_holder })
    # Check DAI limits. 2_000_000 DAI
    agent_dai_balance_before = contracts.dai_token.balanceOf(agent)
    dai_balance_before = contracts.dai_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        contracts.finance.newImmediatePayment(
            contracts.dai_token,
            stranger,
            2_000_000 * 10**18 + 1,
            "DAI transfer",
            {"from": evmscriptexecutor},
        )
    contracts.finance.newImmediatePayment(
        contracts.dai_token,
        stranger,
        2_000_000 * 10**18,
        "DAI transfer",
        {"from": evmscriptexecutor}
    )
    assert contracts.dai_token.balanceOf(agent) == agent_dai_balance_before - 2_000_000 * 10**18
    assert contracts.dai_token.balanceOf(stranger) == dai_balance_before + 2_000_000 * 10**18

    # USDC
    # Top up agent USDC balance.
    contracts.usdc_token.transfer(agent.address, 2_000_000 * 10**6, { 'from': usdc_holder })
    # Check USDC limits. 2_000_000 USDC
    agent_usdc_balance_before = contracts.usdc_token.balanceOf(agent)
    usdc_balance_before = contracts.usdc_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        contracts.finance.newImmediatePayment(
            contracts.usdc_token,
            stranger,
            2_000_000 * 10**6 + 1,
            "USDC transfer",
            {"from": evmscriptexecutor},
        )
    contracts.finance.newImmediatePayment(
        contracts.usdc_token,
        stranger,
        2_000_000 * 10**6,
        "USDC transfer",
        {"from": evmscriptexecutor}
    )
    assert contracts.usdc_token.balanceOf(agent) == agent_usdc_balance_before - 2_000_000 * 10**6
    assert contracts.usdc_token.balanceOf(stranger) == usdc_balance_before + 2_000_000 * 10**6

    # USDT
    # Top up agent USDT balance.
    contracts.usdt_token.transfer(agent.address, 2_000_000 * 10**6, { 'from': usdt_holder })
    # Check USDT limits. 2_000_000 USDT
    agent_usdt_balance_before = contracts.usdt_token.balanceOf(agent)
    usdt_balance_before = contracts.usdt_token.balanceOf(stranger)
    with reverts("APP_AUTH_FAILED"):
        contracts.finance.newImmediatePayment(
            contracts.usdt_token,
            stranger,
            2_000_000 * 10**6 + 1,
            "USDT transfer",
            {"from": evmscriptexecutor},
        )
    contracts.finance.newImmediatePayment(
        contracts.usdt_token,
        stranger,
        2_000_000 * 10**6,
        "USDT transfer",
        {"from": evmscriptexecutor}
    )
    assert contracts.usdt_token.balanceOf(agent) == agent_usdt_balance_before - 2_000_000 * 10**6
    assert contracts.usdt_token.balanceOf(stranger) == usdt_balance_before + 2_000_000 * 10**6

    # MATIC
    # Check token that is not supported.
    MATIC_TOKEN = "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0"
    MATIC_HOLDER = "0x5e3Ef299fDDf15eAa0432E6e66473ace8c13D908"
    matic_token = interface.ERC20(MATIC_TOKEN)
    matic_token.transfer(agent.address, 1, { 'from': MATIC_HOLDER })
    with reverts("APP_AUTH_FAILED"):
        contracts.finance.newImmediatePayment(
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
        contracts.easy_track,
        rcc_trusted_caller_and_recepient,
        rcc_stable_topup_factory,
        contracts.dai_token,
        [rcc_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(rcc_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, contracts.voting)

    # 5. Add PML stable top up EVM script factory 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD to Easy Track
    assert pml_stable_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        contracts.easy_track,
        pml_trusted_caller_and_recepient,
        pml_stable_topup_factory,
        contracts.dai_token,
        [pml_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(pml_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, contracts.voting)

    # 6. Add ATC stable top up EVM script factory 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 to Easy Track
    assert atc_stable_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        contracts.easy_track,
        atc_trusted_caller_and_recepient,
        atc_stable_topup_factory,
        contracts.dai_token,
        [atc_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(atc_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, contracts.voting)

    # validate vote events
    print("count_vote_items_by_events", count_vote_items_by_events(vote_tx, contracts.voting))
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 11, "Incorrect voting items count"

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

def has_payments_permission(acl, finance, sender, token, receiver, amount) -> bool:
    return acl.hasPermission["address,address,bytes32,uint[]"](
        sender, finance, finance.CREATE_PAYMENTS_ROLE(), [token, receiver, amount]
    )

def steth_balance_checker(lhs_value: int, rhs_value: int):
    assert (lhs_value + 5) // 10 == (rhs_value + 5) // 10