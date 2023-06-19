"""
Tests for voting 20/06/2023.
"""
from scripts.vote_2023_06_20 import start_vote

from typing import TypedDict, TypeVar, Any

from brownie import chain
from brownie.network.transaction import TransactionReceipt

from utils.mainnet_fork import chain_snapshot
from utils.config import (
    AGENT,
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.burner import validate_steth_burn_requested_event, StETH_burn_request
from utils.test.event_validators.erc20_token import (
    ERC20Transfer,
    ERC20Approval,
    validate_erc20_approval_event,
    validate_erc20_transfer_event,
)
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.helpers import ETH, almostEqWithDiff
from utils.test.oracle_report_helpers import ONE_DAY, SHARE_RATE_PRECISION, oracle_report


STETH_ERROR_MARGIN_WEI: int = 2
NODE_OPERATOR_ID_1: int = 10
NODE_OPERATOR_ID_2: int = 22
TREASURY: str = AGENT
REBASE_PRECISION: int = 10**9


def test_coverage_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
):
    ## parameters
    burn_request: StETH_burn_request = StETH_burn_request(
        requestedBy=contracts.agent.address,
        amountOfStETH=1345978634 * 10**10,  # 13.45978634 stETH
        amountOfShares=contracts.lido.getSharesByPooledEth(1345978634 * 10**10),
        isCover=True,
    )

    transfer_from_insurance_fund: ERC20Transfer = ERC20Transfer(
        from_addr=contracts.insurance_fund.address,
        to_addr=contracts.agent.address,
        value=burn_request.amountOfStETH,
    )

    approval_to_burner: ERC20Approval = ERC20Approval(
        owner=contracts.agent.address, spender=contracts.burner.address, amount=burn_request.amountOfStETH
    )

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
        burn_request.amountOfStETH,
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
    assert almostEqWithDiff(burner_assigned_for_cover_burn_after, burn_request.amountOfShares, STETH_ERROR_MARGIN_WEI)

    burner_assigned_for_noncover_burn_after: int = contracts.burner.getSharesRequestedToBurn()[1]
    assert burner_assigned_for_noncover_burn_after == burner_assigned_for_noncover_burn_before

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 27, "Incorrect voting items count"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_erc20_transfer_event(evs[0], transfer_from_insurance_fund, is_steth=True)
    validate_erc20_approval_event(evs[1], approval_to_burner)
    validate_grant_role_event(
        evs[2], contracts.burner.REQUEST_BURN_MY_STETH_ROLE(), contracts.agent.address, contracts.agent.address
    )
    validate_steth_burn_requested_event(evs[3], burn_request)
    validate_revoke_role_event(
        evs[4], contracts.burner.REQUEST_BURN_MY_STETH_ROLE(), contracts.agent.address, contracts.agent.address
    )


def test_coverage_application_on_zero_rewards_report(helpers, vote_ids_from_env, accounts, steth_whale):
    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    block_before_vote_execution = chain.height
    vote_tx: TransactionReceipt = helpers.execute_vote(accounts, vote_id, contracts.voting)

    block_before_report = chain.height
    oracle_tx, _ = oracle_report(cl_diff=0, exclude_vaults_balances=True)
    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(oracle_tx)
    shares_burnt = _try_get_shares_burnt(oracle_tx)
    token_rebased_event = _first_event(oracle_tx, TokenRebased)

    tvl_before = contracts.lido.totalSupply(block_identifier=block_before_report)
    shares_before = contracts.lido.getTotalShares(block_identifier=block_before_report)

    tvl_after = contracts.lido.totalSupply(block_identifier=block_after_report)
    shares_after = contracts.lido.getTotalShares(block_identifier=block_after_report)

    assert tvl_before == tvl_after + withdrawals_finalized["amountOfETHLocked"]
    assert (
        shares_before
        == shares_after
        + contracts.burner.getSharesRequestedToBurn(block_identifier=block_before_report)[0]
        + withdrawals_finalized["sharesToBurn"]
    )
    assert shares_burnt["sharesAmount"] == shares_before - shares_after
    assert token_rebased_event["sharesMintedAsFees"] == 0  # no fee

    assert (
        contracts.burner.getCoverSharesBurnt(block_identifier=block_after_report)
        == shares_burnt["sharesAmount"] - withdrawals_finalized["sharesToBurn"]
    )
    assert (
        contracts.burner.getCoverSharesBurnt(block_identifier=block_after_report)
        == contracts.burner.getSharesRequestedToBurn(block_identifier=block_before_report)[0]
    )
    assert (
        contracts.burner.getNonCoverSharesBurnt(block_identifier=block_after_report)
        == contracts.burner.getNonCoverSharesBurnt(block_identifier=block_before_report)
        + withdrawals_finalized["sharesToBurn"]
    )

    # no new fees sent to TREASURY (Agent)
    assert contracts.lido.sharesOf(TREASURY, block_identifier=block_before_report) == contracts.lido.sharesOf(
        TREASURY, block_identifier=block_after_report
    )
    assert contracts.lido.sharesOf(TREASURY, block_identifier=block_before_vote_execution) == contracts.lido.sharesOf(
        TREASURY, block_identifier=block_after_report
    )

    node_operator_1_addr = contracts.node_operators_registry.getNodeOperator(NODE_OPERATOR_ID_1, False)["rewardAddress"]
    node_operator_2_addr = contracts.node_operators_registry.getNodeOperator(NODE_OPERATOR_ID_2, False)["rewardAddress"]

    # no new fees sent to node operators
    assert contracts.lido.sharesOf(
        node_operator_1_addr,
        block_identifier=block_before_report,
    ) == contracts.lido.sharesOf(
        node_operator_1_addr,
        block_identifier=block_after_report,
    )
    assert contracts.lido.sharesOf(
        node_operator_1_addr,
        block_identifier=block_before_vote_execution,
    ) == contracts.lido.sharesOf(
        node_operator_1_addr,
        block_identifier=block_after_report,
    )
    assert contracts.lido.sharesOf(
        node_operator_2_addr,
        block_identifier=block_before_report,
    ) == contracts.lido.sharesOf(
        node_operator_2_addr,
        block_identifier=block_after_report,
    )
    assert contracts.lido.sharesOf(
        node_operator_2_addr,
        block_identifier=block_before_vote_execution,
    ) == contracts.lido.sharesOf(
        node_operator_2_addr,
        block_identifier=block_after_report,
    )

    share_rate_before_report = (
        contracts.lido.totalSupply(block_identifier=block_before_report)
        * SHARE_RATE_PRECISION
        // contracts.lido.getTotalShares(block_identifier=block_before_report)
    )

    share_rate_after_report = (
        contracts.lido.totalSupply(block_identifier=block_after_report)
        * SHARE_RATE_PRECISION
        // contracts.lido.getTotalShares(block_identifier=block_after_report)
    )

    rebase = share_rate_after_report * REBASE_PRECISION // share_rate_before_report
    assert rebase > 0

    assert (
        contracts.lido.balanceOf(steth_whale, block_identifier=block_after_report)
        * REBASE_PRECISION
        // contracts.lido.balanceOf(steth_whale, block_identifier=block_before_report)
        == rebase
    )

    assert (
        contracts.lido.balanceOf(TREASURY, block_identifier=block_after_report)
        * REBASE_PRECISION
        // contracts.lido.balanceOf(TREASURY, block_identifier=block_before_report)
        == rebase
    )

    assert (
        contracts.lido.balanceOf(node_operator_1_addr, block_identifier=block_after_report)
        * REBASE_PRECISION
        // contracts.lido.balanceOf(node_operator_1_addr, block_identifier=block_before_report)
        == rebase
    )

    assert (
        contracts.lido.balanceOf(node_operator_2_addr, block_identifier=block_after_report)
        * REBASE_PRECISION
        // contracts.lido.balanceOf(node_operator_2_addr, block_identifier=block_before_report)
        == rebase
    )


def test_coverage_application_on_nonzero_rewards_report(helpers, vote_ids_from_env, accounts, steth_whale):
    node_operator_1_addr = contracts.node_operators_registry.getNodeOperator(NODE_OPERATOR_ID_1, False)["rewardAddress"]
    node_operator_2_addr = contracts.node_operators_registry.getNodeOperator(NODE_OPERATOR_ID_2, False)["rewardAddress"]

    # Execute oracle report without the vote to exclude the coverage application
    # Save the obtained numbers
    no_coverage_tvl_after_report: int = 0
    no_coverage_total_shares_after_report: int = 0
    no_coverage_fees: int = 0
    no_coverage_shares_burnt_overall: int = 0
    no_coverage_treasury_shares_after_report: int = 0
    no_coverage_node_operator_1_shares_after_report: int = 0
    no_coverage_node_operator_2_shares_after_report: int = 0
    no_coverage_steth_whale_shares_after_report: int = 0

    # wait for one day to ensure withdrawals finalization
    chain.sleep(ONE_DAY)
    chain.mine()

    with chain_snapshot():
        oracle_tx, _ = oracle_report(cl_diff=ETH(523), exclude_vaults_balances=False)

        token_rebased_event = _first_event(oracle_tx, TokenRebased)

        no_coverage_tvl_after_report = contracts.lido.totalSupply()
        assert no_coverage_tvl_after_report > 0
        no_coverage_total_shares_after_report = contracts.lido.getTotalShares()
        assert no_coverage_total_shares_after_report > 0

        no_coverage_fees = token_rebased_event["sharesMintedAsFees"]
        assert no_coverage_fees > 0

        assert contracts.burner.getCoverSharesBurnt() == 0
        no_coverage_shares_burnt_overall = contracts.burner.getNonCoverSharesBurnt() + 0  # see above

        no_coverage_treasury_shares_after_report = contracts.lido.sharesOf(TREASURY)
        no_coverage_node_operator_1_shares_after_report = contracts.lido.sharesOf(node_operator_1_addr)
        no_coverage_node_operator_2_shares_after_report = contracts.lido.sharesOf(node_operator_2_addr)
        no_coverage_steth_whale_shares_after_report = contracts.lido.sharesOf(steth_whale)

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx: TransactionReceipt = helpers.execute_vote(accounts, vote_id, contracts.voting)

    coverage_shares_to_burn = contracts.burner.getSharesRequestedToBurn()[0]

    oracle_tx, _ = oracle_report(cl_diff=ETH(523), exclude_vaults_balances=False)

    token_rebased_event = _first_event(oracle_tx, TokenRebased)

    tvl_after_report = contracts.lido.totalSupply()
    assert tvl_after_report == no_coverage_tvl_after_report

    total_shares_after_report = contracts.lido.getTotalShares()
    assert total_shares_after_report == no_coverage_total_shares_after_report - coverage_shares_to_burn

    fees = token_rebased_event["sharesMintedAsFees"]
    assert fees == no_coverage_fees

    shares_burnt_overall = contracts.burner.getNonCoverSharesBurnt() + contracts.burner.getCoverSharesBurnt()
    assert shares_burnt_overall == no_coverage_shares_burnt_overall + coverage_shares_to_burn

    treasury_shares_after_report = contracts.lido.sharesOf(TREASURY)
    assert treasury_shares_after_report == no_coverage_treasury_shares_after_report

    node_operator_1_shares_after_report = contracts.lido.sharesOf(node_operator_1_addr)
    assert node_operator_1_shares_after_report == no_coverage_node_operator_1_shares_after_report

    node_operator_2_shares_after_report = contracts.lido.sharesOf(node_operator_2_addr)
    assert node_operator_2_shares_after_report == no_coverage_node_operator_2_shares_after_report

    steth_whale_shares_after_report = contracts.lido.sharesOf(steth_whale)
    assert steth_whale_shares_after_report == no_coverage_steth_whale_shares_after_report


class TokenRebased(TypedDict):
    """TokenRebased event definition"""

    reportTimestamp: int
    timeElapsed: int
    preTotalShares: int
    preTotalEther: int
    postTotalShares: int
    postTotalEther: int
    sharesMintedAsFees: int


class SharesBurnt(TypedDict):
    """SharesBurnt event definition"""

    account: str
    preRebaseTokenAmount: int
    postRebaseTokenAmount: int
    sharesAmount: int


WithdrawalsFinalized = TypedDict(
    "WithdrawalsFinalized",
    {"from": str, "to": str, "amountOfETHLocked": int, "sharesToBurn": int, "timestamp": int},
)


T = TypeVar("T")


def _first_event(tx, event: type[T]) -> T:
    """Get first event of type T from transaction"""

    events = _get_events(tx, event)
    assert len(events) == 1, f"Event {event.__name__} was found more than once in the transaction"
    return events[0]


def _get_events(tx, event: type[T]) -> list[T]:
    """Get event of type T from transaction"""

    assert event.__name__ in tx.events, f"Event {event.__name__} was not found in the transaction"
    return tx.events[event.__name__]


def _try_get_withdrawals_finalized(tx: Any) -> WithdrawalsFinalized:
    if WithdrawalsFinalized.__name__ in tx.events:
        return _first_event(tx, WithdrawalsFinalized)
    else:
        return {"from": ZERO_ADDRESS, "to": ZERO_ADDRESS, "amountOfETHLocked": 0, "sharesToBurn": 0, "timestamp": 0}


def _try_get_shares_burnt(tx: Any) -> SharesBurnt:
    if SharesBurnt.__name__ in tx.events:
        return _first_event(tx, SharesBurnt)
    else:
        return SharesBurnt(account=ZERO_ADDRESS, preRebaseTokenAmount=0, postRebaseTokenAmount=0, sharesAmount=0)
