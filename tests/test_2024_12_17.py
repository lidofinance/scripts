"""
Tests for voting 17/12/2024.
"""

from typing import Dict, Tuple, List, NamedTuple
from web3 import Web3
from scripts.vote_2024_12_17 import start_vote
from brownie import interface, reverts, accounts, ZERO_ADDRESS, chain, web3, convert
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS
from utils.config import contracts
from utils.ipfs import get_lido_vote_cid_from_str
from utils.voting import find_metadata_by_vote_id
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event,
    validate_set_spent_amount_event,
)
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_reward_address_set_event,
    NodeOperatorRewardAddressSetItem
)
from configs.config_mainnet import DAI_TOKEN, LDO_TOKEN, LIDO, USDC_TOKEN, USDT_TOKEN
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op, encode_permission_params

STETH_TRANSFER_MAX_DELTA = 2

class TokenLimit(NamedTuple):
    address: str
    limit: int


steth_limit = TokenLimit(LIDO, 8_000 * (10**18))
usdc_limit = TokenLimit(USDC_TOKEN, 3_000_000 * (10**6))
other_limit = TokenLimit("", 1_000 * (10**18))

def amount_limits() -> List[Param]:
    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth_limit.address)),
        # 2: { return _amount <= 5_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth_limit.limit)),
        #
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == USDC)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdc_limit.address)),
        # 5: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdc_limit.limit)),
        # 6: all other
        Param(amount_arg_index, Op.LTE, ArgumentValue(other_limit.limit)),
    ]

def test_vote(helpers, accounts, vote_ids_from_env, stranger):

    # misc
    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")
    nor = interface.NodeOperatorsRegistry("0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5")

    # Item 1
    atc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")
    atc_multisig_acc = accounts.at("0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956", force=True)
    atc_trusted_caller_acc = atc_multisig_acc
    atc_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab")
    atc_budget_limit_after_expected = 7_000_000 * 10**18
    atc_spent_amount_after_expected = 5_500_000 * 10**18
    atc_period_start_exptected = 1727740800
    atc_period_end_exptected = 1735689600

    # Item 2
    pml_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    pml_multisig_acc = accounts.at("0x17F6b2C738a63a8D3A113a228cfd0b373244633D", force=True)
    pml_trusted_caller_acc = pml_multisig_acc
    pml_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D")
    pml_budget_limit_after_expected = 4_000_000 * 10**18
    pml_budget_limit_diff_expected = 2_000_000 * 10**18
    pml_period_start_exptected = 1727740800
    pml_period_end_exptected = 1735689600

    # Item 3, 4
    stonks_steth_allowed_recipients_registry = interface.AllowedRecipientRegistry("0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0")
    stonks_steth_multisig = accounts.at("0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647", force=True)
    stonks_steth_trusted_caller = stonks_steth_multisig
    stonks_steth_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x6e04aED774B7c89BB43721AcDD7D03C872a51B69")
    stETH_token = interface.ERC20("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
    stonks_steth_contract = accounts.at("0x3e2D251275A92a8169A3B17A2C49016e2de492a7", force=True)
    stonks_steth_budget_after_expected = 12_000 * 10**18
    stonks_steth_new_spent_amount_expected = 0
    stonks_steth_period_start_exptected = 1719792000
    stonks_steth_period_end_exptected = 1735689600

    # Item 5
    # NO's data indexes
    activeIndex = 0
    nameIndex = 1
    rewardAddressIndex = 2
    stakingLimitIndex = 3
    stoppedValidatorsIndex = 4
    # Simply Staking params
    simply_staking_id = 16
    simply_staking_name = "Simply Staking"
    simply_staking_old_reward_address = "0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd"
    simply_staking_new_reward_address = "0x1EC3Cbe8fb1D8019092500CcA2111C158a35bC82"


    # Item 1
    atc_budget_limit_before, atc_period_duration_months_before = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getLimitParameters()
    assert atc_budget_limit_before == 1_500_000 * 10 ** 18
    assert atc_period_duration_months_before == 3
    assert 0 == interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).spendableBalance()
    _, _, atc_period_start_before, atc_period_end_before = atc_allowed_recipients_registry.getPeriodState()
    assert atc_period_start_before == atc_period_start_exptected
    assert atc_period_end_before == atc_period_end_exptected

    # Item 2
    pml_budget_limit_before, pml_period_duration_months_before = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).getLimitParameters()
    assert pml_budget_limit_before == 6_000_000 * 10 ** 18
    assert pml_period_duration_months_before == 3
    pml_initial_spendable_balance = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).spendableBalance()
    assert pml_initial_spendable_balance >= 0
    assert pml_initial_spendable_balance <= pml_budget_limit_before
    _, _, pml_period_start_before, pml_period_end_before = pml_allowed_recipients_registry.getPeriodState()
    assert pml_period_start_before == pml_period_start_exptected
    assert pml_period_end_before == pml_period_end_exptected

    # Item 3
    stonks_steth_budget_limit_before, stonks_steth_period_duration_months_before = interface.AllowedRecipientRegistry(stonks_steth_allowed_recipients_registry).getLimitParameters()
    assert stonks_steth_budget_limit_before == 9_000 * 10 ** 18
    assert stonks_steth_period_duration_months_before == 6

    # Item 4
    stonks_steth_already_spent_amount_before, _, stonks_steth_period_start_before, stonks_steth_period_end_before = stonks_steth_allowed_recipients_registry.getPeriodState()
    assert stonks_steth_already_spent_amount_before > 0
    assert stonks_steth_period_start_before == stonks_steth_period_start_exptected
    assert stonks_steth_period_end_before == stonks_steth_period_end_exptected

    # Item 5
    simply_staking_data_before = nor.getNodeOperator(simply_staking_id, True)
    assert simply_staking_old_reward_address == simply_staking_data_before[rewardAddressIndex]
    assert simply_staking_name == simply_staking_data_before[nameIndex]


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")


    # Item 1
    atc_budget_limit_after, atc_period_duration_months_after = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getLimitParameters()
    _, atc_spend_limit_after, atc_period_start_after, atc_period_end_after = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getPeriodState()
    atc_spendable_balance_after = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).spendableBalance()
    assert atc_period_start_after == atc_period_start_exptected
    assert atc_period_end_after == atc_period_end_exptected
    assert atc_budget_limit_after == atc_budget_limit_after_expected
    assert atc_period_duration_months_after == 3
    assert atc_spend_limit_after == atc_spent_amount_after_expected
    assert interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).isUnderSpendableBalance(atc_spendable_balance_after, 3)
    assert atc_spendable_balance_after == atc_spent_amount_after_expected

    # Item 2
    pml_budget_limit_after, pml_period_duration_months_after = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).getLimitParameters()
    _, pml_spend_limit_after, pml_period_start_after, pml_period_end_after = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).getPeriodState()
    pmlSpendableBalanceAfter = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).spendableBalance()
    assert pml_period_start_after == pml_period_start_exptected
    assert pml_period_end_after == pml_period_end_exptected
    assert pml_budget_limit_after == pml_budget_limit_after_expected
    assert pml_period_duration_months_after == 3
    assert pml_spend_limit_after == pml_initial_spendable_balance - pml_budget_limit_diff_expected
    assert interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).isUnderSpendableBalance(pmlSpendableBalanceAfter, 3)
    assert pmlSpendableBalanceAfter == pml_initial_spendable_balance - pml_budget_limit_diff_expected

    # Item 3
    stonks_steth_budget_limit_after, stonks_steth_period_duration_months_after = interface.AllowedRecipientRegistry(stonks_steth_allowed_recipients_registry).getLimitParameters()
    assert stonks_steth_budget_limit_after == stonks_steth_budget_after_expected
    assert stonks_steth_period_duration_months_after == 6

    # Item 4
    already_spent_amount_after, _, stonks_steth_period_start_after, stonks_steth_period_end_after = stonks_steth_allowed_recipients_registry.getPeriodState()
    assert stonks_steth_period_start_after == stonks_steth_period_start_exptected
    assert stonks_steth_period_end_after == stonks_steth_period_end_exptected
    assert already_spent_amount_after == stonks_steth_new_spent_amount_expected
    stonks_steth_spendable_balance_after = interface.AllowedRecipientRegistry(stonks_steth_allowed_recipients_registry).spendableBalance()
    assert stonks_steth_spendable_balance_after == stonks_steth_budget_after_expected

    # Item 5
    simply_staking_data_after = nor.getNodeOperator(simply_staking_id, True)
    assert simply_staking_new_reward_address == simply_staking_data_after[rewardAddressIndex]
    assert simply_staking_data_before[nameIndex] == simply_staking_data_after[nameIndex]
    assert simply_staking_data_before[activeIndex] == simply_staking_data_after[activeIndex]
    assert simply_staking_data_before[stakingLimitIndex] == simply_staking_data_after[stakingLimitIndex]
    assert simply_staking_data_before[stoppedValidatorsIndex] == simply_staking_data_after[stoppedValidatorsIndex]


    # events
    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)

    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == "bafkreia2qh6xvoowgwukqfyyer2zz266e2jifxovnddgqawruhe2g5asgi"

    assert count_vote_items_by_events(vote_tx, contracts.voting) == 5, "Incorrect voting items count"

    validate_set_limit_parameter_event(
        evs[0],
        limit=atc_budget_limit_after_expected,
        period_duration_month=3,
        period_start_timestamp=atc_period_start_exptected,
    )
    validate_set_limit_parameter_event(
        evs[1],
        limit=pml_budget_limit_after_expected,
        period_duration_month=3,
        period_start_timestamp=pml_period_start_exptected,
    )
    validate_set_limit_parameter_event(
        evs[2],
        limit=stonks_steth_budget_after_expected,
        period_duration_month=6,
        period_start_timestamp=stonks_steth_period_start_exptected,
    )
    validate_set_spent_amount_event(
        evs[3],
        new_spent_amount=stonks_steth_new_spent_amount_expected,
    )
    validate_node_operator_reward_address_set_event(
        evs[4],
        NodeOperatorRewardAddressSetItem(
            nodeOperatorId=simply_staking_id,
            reward_address=simply_staking_new_reward_address
        )
    )

    # check withdrawals

    # ensure agent balance
    prepare_agent_for_usdc_payment(15_000_000 * (10**6))
    prepare_agent_for_steth_payment(20_000 * 10**18)

    # elevate permissions for the amount of max stETH transfer at once
    # this is required in order to create and enact fewer motions to transfer a huge amount stETH
    EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
    perm_manager = contracts.acl.getPermissionManager(contracts.finance, convert.to_uint(Web3.keccak(text="CREATE_PAYMENTS_ROLE")))
    contracts.acl.grantPermissionP(
        EVM_SCRIPT_EXECUTOR,
        contracts.finance,
        convert.to_uint(Web3.keccak(text="CREATE_PAYMENTS_ROLE")),
        encode_permission_params(amount_limits()),
        {"from": perm_manager}
    )

    limit_test(easy_track,
               int(atc_spendable_balance_after / (10**18)) * 10**6,
               atc_trusted_caller_acc,
               atc_top_up_evm_script_factory,
               atc_multisig_acc,
               stranger,
               interface.Usdc(USDC_TOKEN),
               3_000_000 * 10**6
    )

    limit_test(easy_track,
               int(pmlSpendableBalanceAfter / (10**18)) * 10**6,
               pml_trusted_caller_acc,
               pml_top_up_evm_script_factory,
               pml_multisig_acc,
               stranger,
               interface.Usdc(USDC_TOKEN),
               3_000_000 * 10**6
    )

    limit_test(easy_track,
               stonks_steth_spendable_balance_after,
               stonks_steth_trusted_caller,
               stonks_steth_top_up_evm_script_factory,
               stonks_steth_contract,
               stranger,
               stETH_token,
               8_000 * 10 ** 18
    )

def limit_test(easy_track, to_spend, trusted_caller_acc, top_up_evm_script_factory, multisig_acc, stranger, token, max_spend_at_once):

    chain.snapshot()

    # check that there is no way to spend more then expected
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            token,
            [multisig_acc],
            [to_spend + 1],
            stranger,
        )
    
    # spend all step by step
    while to_spend > 0:
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            token,
            [multisig_acc],
            [min(max_spend_at_once, to_spend)],
            stranger,
        )
        to_spend -= min(max_spend_at_once, to_spend)

    # make sure there is nothing left so that you can't spend anymore
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            token,
            [multisig_acc],
            [1],
            stranger,
        )

    chain.revert()

def prepare_agent_for_steth_payment(amount: int):
    agent, steth = contracts.agent, contracts.lido
    eth_whale = accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)
    if steth.balanceOf(agent) < amount:
        steth.submit(ZERO_ADDRESS, {"from": eth_whale, "value": amount + 2 * STETH_TRANSFER_MAX_DELTA})
        steth.transfer(agent, amount + STETH_TRANSFER_MAX_DELTA, {"from": eth_whale})
    assert steth.balanceOf(agent) >= amount, "Insufficient stETH balance"

def prepare_agent_for_usdc_payment(amount: int):
    agent, usdc = contracts.agent, interface.Usdc(USDC_TOKEN)
    if usdc.balanceOf(agent) < amount:
        usdc_minter = accounts.at("0x5B6122C109B78C6755486966148C1D70a50A47D7", force=True)
        usdc_controller = accounts.at("0x79E0946e1C186E745f1352d7C21AB04700C99F71", force=True)
        usdc_master_minter = interface.UsdcMasterMinter("0xE982615d461DD5cD06575BbeA87624fda4e3de17")

        web3.provider.make_request("evm_setAccountBalance", [usdc_controller.address, hex(100_000 * 10**18)])
        assert usdc_controller.balance() >= 100_000 * 10**18

        usdc_master_minter.incrementMinterAllowance(amount, {"from": usdc_controller})
        usdc.mint(agent, amount, {"from": usdc_minter})

    assert usdc.balanceOf(agent) >= amount, "Insufficient USDC balance"
