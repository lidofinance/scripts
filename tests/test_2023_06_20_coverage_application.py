"""
Coverage application scenario tests for voting 20/06/2023.
"""
from scripts.vote_2023_06_20 import start_vote

from typing import TypedDict, TypeVar, Any

from brownie import chain

from utils.mainnet_fork import chain_snapshot
from utils.config import (
    AGENT,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.helpers import ETH
from utils.test.oracle_report_helpers import ONE_DAY, SHARE_RATE_PRECISION, oracle_report


STETH_ERROR_MARGIN_WEI: int = 2
NODE_OPERATOR_ID_1: int = 10
NODE_OPERATOR_ID_2: int = 23
TREASURY: str = AGENT
REBASE_PRECISION: int = 10**9


def test_coverage_application_on_zero_rewards_report(helpers, vote_ids_from_env, accounts, steth_whale):
    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    # EXECUTE VOTE
    block_before_vote_execution = chain.height
    helpers.execute_vote(accounts, vote_id, contracts.voting)

    # RUN ORACLE REPORT
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

    # TESTS
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

    # Ensure rebase correctness for various accounts
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

    # wait for one day to ensure withdrawals finalization
    chain.sleep(ONE_DAY)
    chain.mine()

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

    # Execute the vote and oracle report both to include coverage application
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    helpers.execute_vote(accounts, vote_id, contracts.voting)

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


# Internal helpers


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
    """Get the WithdrawalsFinalized event from the given tx, return a zeroed structure otherwise"""
    if WithdrawalsFinalized.__name__ in tx.events:
        return _first_event(tx, WithdrawalsFinalized)
    else:
        return {"from": ZERO_ADDRESS, "to": ZERO_ADDRESS, "amountOfETHLocked": 0, "sharesToBurn": 0, "timestamp": 0}


def _try_get_shares_burnt(tx: Any) -> SharesBurnt:
    """Get the SharesBurnt event from the given tx, return a zeroed structure otherwise"""
    if SharesBurnt.__name__ in tx.events:
        return _first_event(tx, SharesBurnt)
    else:
        return SharesBurnt(account=ZERO_ADDRESS, preRebaseTokenAmount=0, postRebaseTokenAmount=0, sharesAmount=0)
