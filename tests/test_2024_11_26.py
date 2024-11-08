"""
Tests for voting 26/11/2024.
"""

from scripts.vote_2024_11_26 import start_vote
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert
from utils.test.tx_tracing_helpers import *
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, network_name
from utils.easy_track import create_permissions
from utils.config import contracts
from utils.test.easy_track_helpers import create_and_enact_payment_motion, check_add_and_remove_recipient_with_voting
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event
)
from configs.config_mainnet import (
    DAI_TOKEN,
    USDC_TOKEN,
    USDT_TOKEN,
)


def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder, bypass_events_decoding):

    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")

    nor = contracts.node_operators_registry

    # Item 1
    atc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")
    atc_multisig_acc = accounts.at("0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956", force=True)
    atc_trusted_caller_acc = atc_multisig_acc
    atc_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab")
    atcBudgetLimitAfterExpected = 7_000_000 * 10**18
    atcSpendLimitAfterExpected = 5_500_000 * 10**18

    # Item 2
    pml_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")

    # Item 3, 4
    tmc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0")

    # Item 5
    # NO's data indexes
    activeIndex = 0
    nameIndex = 1
    rewardAddressIndex = 2
    stakingLimitIndex = 3
    stoppedValidatorsIndex = 4
    # Simply Staking params
    SimplyStakingId = 16
    SimplyStakingName = "Simply Staking"
    SimplyStakingOldRewardAddress = "0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd"
    SimplyStakingNewRewardAddress = "0x1EC3Cbe8fb1D8019092500CcA2111C158a35bC82"


    # Item 1
    atcBudgetLimitBefore, atcPeriodDurationMonthsBefore = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getLimitParameters()
    assert atcBudgetLimitBefore == 1_500_000 * 10 ** 18
    assert atcPeriodDurationMonthsBefore == 3

    # Item 2
    pmlBudgetLimitBefore, pmlPeriodDurationMonthsBefore = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).getLimitParameters()
    assert pmlBudgetLimitBefore == 6_000_000 * 10 ** 18
    assert pmlPeriodDurationMonthsBefore == 3

    # Item 3
    tmcBudgetLimitBefore, tmcPeriodDurationMonthsBefore = interface.AllowedRecipientRegistry(tmc_allowed_recipients_registry).getLimitParameters()
    assert tmcBudgetLimitBefore == 9_000 * 10 ** 18
    assert tmcPeriodDurationMonthsBefore == 6

    # Item 4
    alreadySpentAmountBefore, spendableBalanceInPeriodBefore, periodStartTimestampBefore, periodEndTimestampBefore = tmc_allowed_recipients_registry.getPeriodState()
    assert alreadySpentAmountBefore > 0

    # Item 5
    SimplyStakingDataBefore = nor.getNodeOperator(SimplyStakingId, True)
    assert SimplyStakingOldRewardAddress == SimplyStakingDataBefore[rewardAddressIndex]
    assert SimplyStakingName == SimplyStakingDataBefore[nameIndex]


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")


    # Item 1
    atcBudgetLimitAfter, atcPeriodDurationMonthsAfter = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getLimitParameters()
    (already_spent, spend_limit, period_start, period_end) = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getPeriodState()
    atcSpendableBalanceAfter = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).spendableBalance()
    assert atcBudgetLimitAfter == atcBudgetLimitAfterExpected
    assert atcPeriodDurationMonthsAfter == 3
    assert spend_limit == atcSpendLimitAfterExpected
    assert interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).isUnderSpendableBalance(atcSpendableBalanceAfter, 3)
    assert atcSpendableBalanceAfter == atcSpendLimitAfterExpected
    limit_test(easy_track, int(atcSpendableBalanceAfter / (10**18)), atc_trusted_caller_acc, atc_top_up_evm_script_factory, atc_multisig_acc, stranger)

    # Item 2
    pmlBudgetLimitAfter, pmlPeriodDurationMonthsAfter = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).getLimitParameters()
    assert pmlBudgetLimitAfter == 4_000_000 * 10 ** 18
    assert pmlPeriodDurationMonthsAfter == 3
    # TODO limit_test

    # Item 3
    tmcBudgetLimitAfter, tmcPeriodDurationMonthsAfter = interface.AllowedRecipientRegistry(tmc_allowed_recipients_registry).getLimitParameters()
    assert tmcBudgetLimitAfter == 12_000 * 10 ** 18
    assert tmcPeriodDurationMonthsAfter == 6
    # TODO limit_test

    # Item 4
    alreadySpentAmountAfter, spendableBalanceInPeriodAfter, periodStartTimestampAfter, periodEndTimestampAfter = tmc_allowed_recipients_registry.getPeriodState()
    assert alreadySpentAmountAfter == 0
    # TODO limit_test

    # Item 5
    SimplyStakingDataAfter = nor.getNodeOperator(SimplyStakingId, True)
    assert SimplyStakingNewRewardAddress == SimplyStakingDataAfter[rewardAddressIndex]
    assert SimplyStakingDataBefore[nameIndex] == SimplyStakingDataAfter[nameIndex]
    assert SimplyStakingDataBefore[activeIndex] == SimplyStakingDataAfter[activeIndex]
    assert SimplyStakingDataBefore[stakingLimitIndex] == SimplyStakingDataAfter[stakingLimitIndex]
    assert SimplyStakingDataBefore[stoppedValidatorsIndex] == SimplyStakingDataAfter[stoppedValidatorsIndex]
    # TODO limit_test


    # events
    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)

    validate_set_limit_parameter_event(
        evs[0],
        limit=atcBudgetLimitAfterExpected,
        period_duration_month=3,
        period_start_timestamp=1727740800,
    )
    # TODO more events

def limit_test(easy_track, to_spend, trusted_caller_acc, top_up_evm_script_factory, multisig_acc, stranger):

    # can't spend more than 2M USDC at once
    max_usdc_spend_at_once = 2_000_000 * 10**6

    to_spend_usdc = to_spend * 10**6

    # check that there is no way to spend more USDC
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            interface.Usdc(USDC_TOKEN),
            [multisig_acc],
            [to_spend_usdc + 1],
            stranger,
        )    
    
    # spend all USDC step by step (at most 2M each time)
    while to_spend_usdc > 0:
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            interface.Usdc(USDC_TOKEN),
            [multisig_acc],
            [min(max_usdc_spend_at_once, to_spend_usdc)],
            stranger,
        )
        to_spend_usdc -= min(max_usdc_spend_at_once, to_spend_usdc)

    # make sure there is nothing left so that you can't spend anymore
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            interface.Usdc(USDC_TOKEN),
            [multisig_acc],
            [1],
            stranger,
        )
