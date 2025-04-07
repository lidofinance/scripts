"""
Tests for voting 03/04/2025 [HOLESKY].
"""

from scripts.vote_2024_12_17_holesky import start_vote
from brownie import interface, reverts, chain
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS
from utils.config import contracts
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event,
)

def test_vote(helpers, accounts, vote_ids_from_env, stranger):

    # common values
    STETH = interface.StETH("0x3F1c547b21f65e10480dE3ad8E19fAAC46C95034")
    easy_track = interface.EasyTrack("0x1763b9ED3586B08AE796c7787811a2E1bc16163a")
    lol_allowed_recipients_registry = interface.AllowedRecipientRegistry("0x55B304a585D540421F1fD3579Ef12Abab7304492")
    lol_allowed_recipient = accounts.at("0x1580881349e214Bab9f1E533bF97351271DB95a9", force=True)
    lol_trusted_caller_acc = accounts.at("0x96d2Ff1C4D30f592B91fd731E218247689a76915", force=True)
    lol_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0xBB06DD9a3C7eE8cE093860094e769a1E3D6F97F6")
    
    # before values
    lol_budget_limit_before_exptected = 210 * 10**18
    lol_period_duration_months_before_expected = 3
    lol_period_start_before_exptected = 1704067200 # Mon Jan 01 2024 00:00:00 GMT+0000
    lol_period_end_before_exptected = 1711929600 # Mon Apr 01 2024 00:00:00 GMT+0000

    # after values
    lol_budget_limit_after_expected = 500 * 10**18
    lol_period_duration_months_after_expected = 6
    lol_period_start_after_exptected = 1735689600 # Wed Jan 01 2025 00:00:00 GMT+0000
    lol_period_end_after_exptected = 1751328000 # Tue Jul 01 2025 00:00:00 GMT+0000

    #scenario test values
    h2_motion_time = 1751328001 # Tue Jul 01 2025 00:00:01 GMT+0000
    h2_period_start = 1751328000 # Tue Jul 01 2025 00:00:00 GMT+0000
    h2_period_end = 1767225600 # Thu Jan 01 2026 00:00:00 GMT+0000


    # checks before
    lol_budget_limit_before, lol_period_duration_months_before = interface.AllowedRecipientRegistry(lol_allowed_recipients_registry).getLimitParameters()
    _, _, lol_period_start_before, lol_period_end_before = lol_allowed_recipients_registry.getPeriodState()
    lol_spendable_balance_before = interface.AllowedRecipientRegistry(lol_allowed_recipients_registry).spendableBalance()
    assert lol_budget_limit_before == lol_budget_limit_before_exptected
    assert lol_period_duration_months_before == lol_period_duration_months_before_expected
    assert lol_period_start_before == lol_period_start_before_exptected
    assert lol_period_end_before == lol_period_end_before_exptected


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")


    # checks after
    lol_budget_limit_after, lol_period_duration_months_after = interface.AllowedRecipientRegistry(lol_allowed_recipients_registry).getLimitParameters()
    _, _, lol_period_start_after, lol_period_end_after = interface.AllowedRecipientRegistry(lol_allowed_recipients_registry).getPeriodState()
    lol_spendable_balance_after = interface.AllowedRecipientRegistry(lol_allowed_recipients_registry).spendableBalance()
    assert lol_period_start_after == lol_period_start_after_exptected
    assert lol_period_end_after == lol_period_end_after_exptected
    assert lol_budget_limit_after == lol_budget_limit_after_expected
    assert lol_period_duration_months_after == lol_period_duration_months_after_expected
    assert lol_spendable_balance_before + (lol_budget_limit_after_expected - lol_budget_limit_before_exptected) == lol_spendable_balance_after


    # check events
    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)

    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"

    validate_set_limit_parameter_event(
        evs[0],
        limit=lol_budget_limit_after_expected,
        period_duration_month=lol_period_duration_months_after_expected,
        period_start_timestamp=lol_period_start_after_exptected,
    )

    # scenario tests

    # full withdrawal in H1'2025
    limit_test(easy_track,
               interface.AllowedRecipientRegistry(lol_allowed_recipients_registry).spendableBalance(),
               lol_trusted_caller_acc,
               lol_top_up_evm_script_factory,
               lol_allowed_recipient,
               stranger,
               STETH,
               100 * 10**18
    )

    # partial withdrawal of 300 steth in H2'2025

    # wait until H2'2025
    chain.sleep(h2_motion_time - chain.time())
    chain.mine()
    assert chain.time() == h2_motion_time

    # pay 100 steth
    create_and_enact_payment_motion(
        easy_track,
        lol_trusted_caller_acc,
        lol_top_up_evm_script_factory,
        STETH,
        [lol_allowed_recipient],
        [100 * 10**18],
        stranger,
    )

    # pay 100 steth
    create_and_enact_payment_motion(
        easy_track,
        lol_trusted_caller_acc,
        lol_top_up_evm_script_factory,
        STETH,
        [lol_allowed_recipient],
        [100 * 10**18],
        stranger,
    )

    # pay 100 steth
    create_and_enact_payment_motion(
        easy_track,
        lol_trusted_caller_acc,
        lol_top_up_evm_script_factory,
        STETH,
        [lol_allowed_recipient],
        [100 * 10**18],
        stranger,
    )

    lol_already_spent_h2, _, lol_period_start_h2, lol_period_end_h2 = lol_allowed_recipients_registry.getPeriodState()
    assert lol_already_spent_h2 == 300 * 10**18
    assert lol_period_start_h2 == h2_period_start
    assert lol_period_end_h2 == h2_period_end
    assert interface.AllowedRecipientRegistry(lol_allowed_recipients_registry).spendableBalance() == 200 * 10**18

def limit_test(easy_track, to_spend, trusted_caller_acc, top_up_evm_script_factory, send_to, stranger, token, max_spend_at_once):

    # check that there is no way to spend more then expected
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            token,
            [send_to],
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
            [send_to],
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
            [send_to],
            [1],
            stranger,
        )
