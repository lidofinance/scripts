"""
Tests for voting 08/10/2024
Add ET setup for Alliance

"""

from scripts.vote_limits import start_vote
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert
from utils.test.tx_tracing_helpers import *
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, network_name
from utils.easy_track import create_permissions
from utils.test.easy_track_helpers import create_and_enact_payment_motion, check_add_and_remove_recipient_with_voting
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event
)
from configs.config_holesky import (
    DAI_TOKEN,
    USDC_TOKEN,
    USDT_TOKEN,
)


# STETH_TRANSFER_MAX_DELTA = 2

def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder, bypass_events_decoding):

    easy_track = interface.EasyTrack("0x1763b9ED3586B08AE796c7787811a2E1bc16163a")

    alliance_ops_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xe1ba8dee84a4df8e99e495419365d979cdb19991")
    alliance_ops_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x343fa5f0c79277e2d27e440f40420d619f962a23")

    alliance_multisig_acc = accounts.at("0x96d2Ff1C4D30f592B91fd731E218247689a76915", force=True)
    alliance_trusted_caller_acc = accounts.at("0x96d2Ff1C4D30f592B91fd731E218247689a76915", force=True)

    budgetLimit_config = 250000

    bokkyPooBahsDateTimeContract_before = interface.AllowedRecipientRegistry(alliance_ops_allowed_recipients_registry).bokkyPooBahsDateTimeContract()

    budgetLimit_before, periodDurationMonths_before = interface.AllowedRecipientRegistry(alliance_ops_allowed_recipients_registry).getLimitParameters()
    assert budgetLimit_before>0
    assert periodDurationMonths_before!=0
    assert periodDurationMonths_before<50

    alreadySpentAmount_before, spendableBalanceInPeriod_before, periodStartTimestamp_before, periodEndTimestamp_before = alliance_ops_allowed_recipients_registry.getPeriodState()
    print('periodStartTimestamp_before', periodStartTimestamp_before)
    print('periodEndTimestamp_before', periodEndTimestamp_before)
    assert alreadySpentAmount_before<budgetLimit_config, f'More funds were spent than the planned budget: spent amount: {alreadySpentAmount_before}, budget limit: {budgetLimit_config}'
    assert alreadySpentAmount_before+spendableBalanceInPeriod_before != budgetLimit_config, f'Spent amount ({alreadySpentAmount_before}) and spendable balance ({spendableBalanceInPeriod_before}) sum is equal to budget limit ({budgetLimit_config}).'

    '''
    getAllowedRecipients_before = len(alliance_ops_allowed_recipients_registry.getAllowedRecipients())
    print('getAllowedRecipients_before', getAllowedRecipients_before)
    '''

    isRecipientAllowed_before = alliance_ops_allowed_recipients_registry.isRecipientAllowed(alliance_multisig_acc)
    assert isRecipientAllowed_before, f'Recipient {alliance_multisig_acc} should be allowed.'

    ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE_before = alliance_ops_allowed_recipients_registry.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE()
    DEFAULT_ADMIN_ROLE_before = alliance_ops_allowed_recipients_registry.DEFAULT_ADMIN_ROLE()
    REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE_before = alliance_ops_allowed_recipients_registry.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE()
    SET_PARAMETERS_ROLE_before = alliance_ops_allowed_recipients_registry.SET_PARAMETERS_ROLE()
    UPDATE_SPENT_AMOUNT_ROLE_before = alliance_ops_allowed_recipients_registry.UPDATE_SPENT_AMOUNT_ROLE()

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # 1. Change limits
    bokkyPooBahsDateTimeContract_after = interface.AllowedRecipientRegistry(alliance_ops_allowed_recipients_registry).bokkyPooBahsDateTimeContract()
    assert bokkyPooBahsDateTimeContract_before == bokkyPooBahsDateTimeContract_after, f"bokkyPooBahsDateTimeContract has changed unexpectedly."

    budgetLimit_after, periodDurationMonths_after = interface.AllowedRecipientRegistry(alliance_ops_allowed_recipients_registry).getLimitParameters()
    assert budgetLimit_before!=budgetLimit_after, f'BudgetLimit ({budgetLimit_after}) has not changed unexpectedly.'
    assert budgetLimit_after==budgetLimit_config, f'The new budget limit ({budgetLimit_after}) does not match the one that should have been set ({budgetLimit_config}).'
    assert periodDurationMonths_before == periodDurationMonths_after, f'PeriodDurationMonths ({periodDurationMonths_after}) has changed unexpectedly.'

    alreadySpentAmount_after, spendableBalanceInPeriod_after, periodStartTimestamp_after, periodEndTimestamp_after = alliance_ops_allowed_recipients_registry.getPeriodState()
    print('periodStartTimestamp_after', periodStartTimestamp_after)
    print('periodEndTimestamp_after', periodEndTimestamp_after)
    assert alreadySpentAmount_before == alreadySpentAmount_after, f'AlreadySpentAmount ({alreadySpentAmount_before}) has changed unexpectedly ({alreadySpentAmount_after}).'
    assert spendableBalanceInPeriod_before != spendableBalanceInPeriod_after, f'SpendableBalanceInPeriod ({spendableBalanceInPeriod_after}) has not changed unexpectedly'
    assert spendableBalanceInPeriod_after == budgetLimit_after - alreadySpentAmount_before, f'There may be an error in calculating the spending Balance'
    # assert periodStartTimestamp_before == periodStartTimestamp_after
    # assert periodEndTimestamp_before == periodEndTimestamp_after

    getAllowedRecipients_after = alliance_ops_allowed_recipients_registry.getAllowedRecipients()

    '''
    print('getAllowedRecipients_after', getAllowedRecipients_after)
    assert getAllowedRecipients_before == getAllowedRecipients_after, "getAllowedRecipients has changed unexpectedly"
    '''

    isRecipientAllowed_after = alliance_ops_allowed_recipients_registry.isRecipientAllowed(alliance_multisig_acc)
    assert isRecipientAllowed_after

    ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE_after = alliance_ops_allowed_recipients_registry.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE()
    DEFAULT_ADMIN_ROLE_after = alliance_ops_allowed_recipients_registry.DEFAULT_ADMIN_ROLE()
    REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE_after = alliance_ops_allowed_recipients_registry.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE()
    SET_PARAMETERS_ROLE_after = alliance_ops_allowed_recipients_registry.SET_PARAMETERS_ROLE()
    UPDATE_SPENT_AMOUNT_ROLE_after = alliance_ops_allowed_recipients_registry.UPDATE_SPENT_AMOUNT_ROLE()
    assert ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE_before==ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE_after
    assert DEFAULT_ADMIN_ROLE_before==DEFAULT_ADMIN_ROLE_after
    assert REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE_before == REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE_after
    assert SET_PARAMETERS_ROLE_before==SET_PARAMETERS_ROLE_after
    assert UPDATE_SPENT_AMOUNT_ROLE_before==UPDATE_SPENT_AMOUNT_ROLE_after

    dai_transfer_amount = budgetLimit_config + 1
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=alliance_trusted_caller_acc,
            factory=alliance_ops_top_up_evm_script_factory,
            token=interface.Dai(DAI_TOKEN),
            recievers=[alliance_multisig_acc],
            transfer_amounts=[dai_transfer_amount],
            stranger=stranger,
        )

    usdc_transfer_amount = budgetLimit_config + 1
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=alliance_trusted_caller_acc,
            factory=alliance_ops_top_up_evm_script_factory,
            token=interface.Usdc(USDC_TOKEN),
            recievers=[alliance_multisig_acc],
            transfer_amounts=[usdc_transfer_amount],
            stranger=stranger,
        )

    usdt_transfer_amount = budgetLimit_config + 1
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=alliance_trusted_caller_acc,
            factory=alliance_ops_top_up_evm_script_factory,
            token=interface.Usdt(USDT_TOKEN),
            recievers=[alliance_multisig_acc],
            transfer_amounts=[usdt_transfer_amount],
            stranger=stranger,
        )

    dai_transfer_amount = budgetLimit_config - 1
    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=alliance_trusted_caller_acc,
        factory=alliance_ops_top_up_evm_script_factory,
        token=interface.Dai(DAI_TOKEN),
        recievers=[alliance_multisig_acc],
        transfer_amounts=[dai_transfer_amount],
        stranger=stranger,
    )

    display_voting_events(vote_tx)

    evs = group_voting_events(vote_tx)

    validate_set_limit_parameter_event(
        evs[0],
        limit=250000,
        period_duration_month=3,
        period_start_timestamp=1727740800,
    )


