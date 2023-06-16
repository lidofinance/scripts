"""
Tests for voting 20/06/2023.
"""
from scripts.vote_2023_06_20 import start_vote

from brownie import chain, accounts, web3
from brownie.network.transaction import TransactionReceipt

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    validate_target_validators_count_changed_event,
    TargetValidatorsCountChanged,
)

from utils.test.event_validators.payout import Payout, validate_token_payout_event
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.helpers import almostEqWithDiff


STETH_ERROR_MARGIN_WEI: int = 2


def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
):
    ## parameters

    ## checks before the vote
    insurance_fund_steth_balance_before: int = contracts.lido.balanceOf(contracts.insurance_fund.address)
    insurance_fund_shares_before: int = contracts.lido.sharesOf(contracts.insurance_fund.address)

    # https://research.lido.fi/t/redirecting-incoming-revenue-stream-from-insurance-fund-to-dao-treasury/2528/28
    assert insurance_fund_shares_before == 5466460000000000000000
    # retrieved 2023-06-16 at 08:20 UTC
    assert insurance_fund_steth_balance_before >= 6168933603752703174674

    agent_lido_alowance_before: int = contracts.lido.allowance(contracts.agent.address, contracts.burner.address)
    assert agent_lido_alowance_before <= STETH_ERROR_MARGIN_WEI

    request_burn_my_steth_role_holders_before: int = contracts.burner.getRoleMemberCount(
        contracts.burner.REQUEST_BURN_MY_STETH_ROLE()
    )
    assert request_burn_my_steth_role_holders_before == 0

    burner_total_burnt_for_cover_before: int = contracts.burner.getCoverSharesBurnt()
    assert burner_total_burnt_for_cover_before == 0

    burner_total_burnt_for_noncover_before: int = contracts.burner.getNonCoverSharesBurnt()
    # retrieved 2023-06-16 at 08:20 UTC
    assert burner_total_burnt_for_noncover_before >= 506385577569080968748810

    burner_assigned_for_cover_burn_before: int = contracts.burner.getSharesRequestedToBurn()[0]
    assert burner_assigned_for_cover_burn_before == 0

    burner_assigned_for_noncover_burn_before: int = contracts.burner.getSharesRequestedToBurn()[1]
    assert burner_assigned_for_noncover_burn_before == 0

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx: TransactionReceipt = helpers.execute_vote(accounts, vote_id, contracts.voting)

    ## checks after the vote
    insurance_fund_steth_balance_after: int = contracts.lido.balanceOf(contracts.insurance_fund.address)
    insurance_fund_shares_after: int = contracts.lido.sharesOf(contracts.insurance_fund.address)

    assert almostEqWithDiff(
        insurance_fund_steth_balance_before - insurance_fund_steth_balance_after,
        1345978634 * 10**10,  # 13.45978634 stETH
        STETH_ERROR_MARGIN_WEI,
    )

    agent_lido_alowance_after: int = contracts.lido.allowance(contracts.agent.address, contracts.burner.address)
    assert agent_lido_alowance_after <= STETH_ERROR_MARGIN_WEI  # with tolerance

    request_burn_my_steth_role_holders_after: int = contracts.burner.getRoleMemberCount(
        contracts.burner.REQUEST_BURN_MY_STETH_ROLE()
    )
    assert request_burn_my_steth_role_holders_after == 0

    burner_total_burnt_for_cover_after: int = contracts.burner.getCoverSharesBurnt()
    assert burner_total_burnt_for_cover_after == burner_total_burnt_for_cover_before

    burner_total_burnt_for_noncover_after: int = contracts.burner.getNonCoverSharesBurnt()
    assert burner_total_burnt_for_noncover_after == burner_total_burnt_for_noncover_before

    burner_assigned_for_cover_burn_after: int = contracts.burner.getSharesRequestedToBurn()[0]
    assert insurance_fund_shares_before - insurance_fund_shares_after == burner_assigned_for_cover_burn_after

    burner_assigned_for_noncover_burn_after: int = contracts.burner.getSharesRequestedToBurn()[1]
    assert burner_assigned_for_noncover_burn_after == burner_assigned_for_noncover_burn_before

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 5, "Incorrect voting items count"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    ## validate events

    # TODO:
    # validate_insurance_fund_erc20_transfer
    # validate_token_approval
    # validate_grant_role_event
    # validate_request_burn_my_steth_for_cover
    # validate_revoke_role_event


"""

# TODO:
def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
):
    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    # simulate oracle report

    # 1. Need to check that cover is applied “correctly”:
    # 1. regular balances see correct extra rebase (no new shares, extra balance delta prop to the share)
    # 2. Agent balance sees correct extra rebase (new shares from the rewards only (not from cover), extra balance delta prop to the share)
    # 3. any NO balance sees correct extra rebase (new shares from the rewards only (not from cover), extra balance delta prop to the share)
    # Additions:
    # - Burner counters before - middle - after
    # - Events
    # - TVL / Total shares
    # - Rebase
"""
