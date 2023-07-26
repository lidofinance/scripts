"""
Coverage application scenario tests for voting 20/06/2023.
"""
from scripts.vote_2023_06_20 import start_vote

from typing import TypedDict, TypeVar, Any, Dict

from brownie import chain

from utils.mainnet_fork import chain_snapshot
from utils.config import (
    AGENT,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.helpers import ETH
from utils.test.oracle_report_helpers import ONE_DAY, SHARE_RATE_PRECISION, oracle_report


STETH_ERROR_MARGIN_WEI: int = 2  # https://github.com/lidofinance/lido-dao/issues/442
TREASURY: str = AGENT  # semantic alias
REBASE_PRECISION: int = 10**9  # precision to compare balance changes due to oracle report induced rebase

# https://github.com/lidofinance/lido-dao/blob/cadffa46a2b8ed6cfa1127fca2468bae1a82d6bf/contracts/0.8.9/Burner.sol#L332
COVER_INDEX: int = 0


#
# Test scenario:
# - start vote containing coverage application
# - remember the pre-execution chain state
# - execute the vote
# - remember the pre-oracle report chain state
# - do oracle report with zero EL and CL rewards
# - remember the post-oracle report chain state
#
# Invariants to check after the oracle report:
# - total supply was changed only due to withdrawals finalization
# - there were burnt only shares due to withdrawals AND coverage applications
#   + only Burner treats this burn events differently (internal counters)
# - no fees were minted on behalf of treasury and node operators
#   + shares of the following accounts weren't changed:
#     + treasury
#     + node operator
# - balances of the following accounts changed according to the expected rebase:
#   + random steth holder (steth whale)
#   + treasury
#   + node operator
#
def test_coverage_application_on_zero_rewards_report(helpers, vote_ids_from_env, accounts, steth_whale):
    # START VOTE
    vote_ids = []
    if len(vote_ids_from_env) > 0:
        vote_ids = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
        vote_ids = [vote_id]

    block_before_vote_execution = chain.height

    # EXECUTE VOTE
    helpers.execute_votes(accounts, vote_ids, contracts.voting)

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
    assert rebase > REBASE_PRECISION
    print(f"rebase {rebase}")

    nos = contracts.node_operators_registry.getNodeOperatorsCount()
    no_addrs = [contracts.node_operators_registry.getNodeOperator(no, False)["rewardAddress"] for no in range(nos)]

    # TESTS
    assert contracts.lido.sharesOf(contracts.burner, block_identifier=block_after_report) == 0
    assert contracts.lido.balanceOf(contracts.burner, block_identifier=block_after_report) == 0

    assert tvl_before == tvl_after + withdrawals_finalized["amountOfETHLocked"]
    assert (
        shares_before
        == shares_after
        + contracts.burner.getSharesRequestedToBurn(block_identifier=block_before_report)[COVER_INDEX]
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
        == contracts.burner.getSharesRequestedToBurn(block_identifier=block_before_report)[COVER_INDEX]
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

    # no new fees sent to node operators
    for no_addr in no_addrs:
        assert contracts.lido.sharesOf(no_addr, block_identifier=block_before_report,) == contracts.lido.sharesOf(
            no_addr,
            block_identifier=block_after_report,
        )
        assert contracts.lido.sharesOf(
            no_addr,
            block_identifier=block_before_vote_execution,
        ) == contracts.lido.sharesOf(
            no_addr,
            block_identifier=block_after_report,
        )

    # check balances (ensure rebase is correct for all actors)
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

    for no_addr in no_addrs:
        # prevent rounding errors for the dust-containing accounts
        if contracts.lido.balanceOf(no_addr, block_identifier=block_before_report) < REBASE_PRECISION:
            continue

        assert (
            contracts.lido.balanceOf(no_addr, block_identifier=block_after_report)
            * REBASE_PRECISION
            // contracts.lido.balanceOf(no_addr, block_identifier=block_before_report)
            == rebase
        )


#
# Test scenario relies on alternative chain paths (I and II)
#
# Path I:
# - pretend there is no vote at all
# - do an oracle report with usual daily reward numbers
# - memorize the state of:
#   + TVL
#   + Total shares
#   + Account shares for
#     + Treasury
#     + Random stETH holder
#     + Node operators
#
# Path II.
# - start vote containing coverage application
# - execute the vote
# - do an oracle report with exactly the same rewards as in Path I
# - remember the post-oracle report chain state
#
# Invariants to check between the two alternative chain paths:
#
# - TVL is the same
# - Burnt shares differs on coverage (Path II contains coverage application)
# - Account shares for the memorized holders are the same (no new rewards due to coverage)
# - Account balances for the memorized holders are changed according to the share rate (balances are higher)
#
def test_coverage_application_on_nonzero_rewards_report(helpers, vote_ids_from_env, accounts, steth_whale):
    # wait for one day to ensure uniform withdrawals finalization across alternative chain paths
    chain.sleep(ONE_DAY)
    chain.mine()

    # Execute oracle report without the vote to exclude the coverage application
    # Save the obtained numbers
    no_coverage_tvl_after_report: int = 0
    no_coverage_total_shares_after_report: int = 0
    no_coverage_fees: int = 0
    no_coverage_shares_burnt_overall: int = 0
    no_coverage_treasury_shares_after_report: int = 0
    no_coverage_node_operators_shares_after_report: Dict[str, int] = {}
    no_coverage_steth_whale_shares_after_report: int = 0
    no_coverage_treasury_balance_after_report: int = 0
    no_coverage_node_operators_balance_after_report: Dict[str, int] = {}
    no_coverage_steth_whale_balance_after_report: int = 0
    with chain_snapshot():
        # Execute the vote and oracle report both to include coverage application
        vote_ids = []
        if len(vote_ids_from_env) > 0:
            vote_ids = vote_ids_from_env
            helpers.execute_vote(accounts, vote_ids[1], contracts.voting)

        nos = contracts.node_operators_registry.getNodeOperatorsCount()
        no_addrs = [contracts.node_operators_registry.getNodeOperator(no, False)["rewardAddress"] for no in range(nos)]
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
        for no_addr in no_addrs:
            no_coverage_node_operators_shares_after_report[no_addr] = contracts.lido.sharesOf(no_addr)
        no_coverage_steth_whale_shares_after_report = contracts.lido.sharesOf(steth_whale)

        no_coverage_treasury_balance_after_report = contracts.lido.balanceOf(TREASURY)
        for no_addr in no_addrs:
            no_coverage_node_operators_balance_after_report[no_addr] = contracts.lido.balanceOf(no_addr)
        no_coverage_steth_whale_balance_after_report = contracts.lido.balanceOf(steth_whale)

        # Checks could revert while rebase limits exceeded (eg sum of withdrawal vault and EL rewards vault income)
        # Could be temporary fixed with excluding vaults balances at line 222
        assert contracts.lido.sharesOf(contracts.burner) == 0
        assert contracts.lido.balanceOf(contracts.burner) == 0

    # Execute the vote and oracle report both to include coverage application
    vote_ids = []
    if len(vote_ids_from_env) > 0:
        vote_ids = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
        vote_ids = [vote_id]

    helpers.execute_votes(accounts, vote_ids, contracts.voting)

    nos = contracts.node_operators_registry.getNodeOperatorsCount()
    no_addrs = [contracts.node_operators_registry.getNodeOperator(no, False)["rewardAddress"] for no in range(nos)]
    coverage_shares_to_burn = contracts.burner.getSharesRequestedToBurn()[COVER_INDEX]

    tvl_before_report = contracts.lido.totalSupply()
    total_shares_before_report = contracts.lido.getTotalShares()

    oracle_tx, _ = oracle_report(cl_diff=ETH(523), exclude_vaults_balances=False)

    token_rebased_event = _first_event(oracle_tx, TokenRebased)

    tvl_after_report = contracts.lido.totalSupply()
    assert tvl_after_report == no_coverage_tvl_after_report

    total_shares_after_report = contracts.lido.getTotalShares()
    assert total_shares_after_report == no_coverage_total_shares_after_report - coverage_shares_to_burn

    # Checks could revert while rebase limits exceeded (eg sum of withdrawal vault and EL rewards vault income)
    # Could be temporary fixed with excluding vaults balances at line 268
    assert contracts.lido.sharesOf(contracts.burner) == 0
    assert contracts.lido.balanceOf(contracts.burner) == 0

    share_rate_before_report = tvl_before_report * SHARE_RATE_PRECISION // total_shares_before_report
    share_rate_after_report = tvl_after_report * SHARE_RATE_PRECISION // total_shares_after_report

    # Ensure rebase correctness for various accounts
    rebase = share_rate_after_report * REBASE_PRECISION // share_rate_before_report
    assert rebase > REBASE_PRECISION
    print(f"rebase: {rebase}")

    fees = token_rebased_event["sharesMintedAsFees"]
    assert fees == no_coverage_fees

    shares_burnt_overall = contracts.burner.getNonCoverSharesBurnt() + contracts.burner.getCoverSharesBurnt()
    assert shares_burnt_overall == no_coverage_shares_burnt_overall + coverage_shares_to_burn

    steth_whale_shares_after_report = contracts.lido.sharesOf(steth_whale)
    assert steth_whale_shares_after_report == no_coverage_steth_whale_shares_after_report
    steth_whale_balance_after_report = contracts.lido.balanceOf(steth_whale)
    assert (
        steth_whale_balance_after_report
        == steth_whale_shares_after_report * tvl_after_report // total_shares_after_report
    )
    assert (
        no_coverage_steth_whale_balance_after_report
        == steth_whale_shares_after_report * no_coverage_tvl_after_report // no_coverage_total_shares_after_report
    )

    treasury_shares_after_report = contracts.lido.sharesOf(TREASURY)
    assert treasury_shares_after_report == no_coverage_treasury_shares_after_report
    treasury_balance_after_report = contracts.lido.balanceOf(TREASURY)
    assert treasury_balance_after_report == treasury_shares_after_report * tvl_after_report // total_shares_after_report
    assert (
        no_coverage_treasury_balance_after_report
        == treasury_shares_after_report * no_coverage_tvl_after_report // no_coverage_total_shares_after_report
    )

    for no_addr in no_addrs:
        if not no_addr in no_coverage_node_operators_shares_after_report:
            continue

        node_operator_shares_after_report = contracts.lido.sharesOf(no_addr)
        assert node_operator_shares_after_report == no_coverage_node_operators_shares_after_report[no_addr]
        node_operator_balance_after_report = contracts.lido.balanceOf(no_addr)
        assert (
            node_operator_balance_after_report
            == node_operator_shares_after_report * tvl_after_report // total_shares_after_report
        )
        assert (
            no_coverage_node_operators_balance_after_report[no_addr]
            == node_operator_shares_after_report * no_coverage_tvl_after_report // no_coverage_total_shares_after_report
        )


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
