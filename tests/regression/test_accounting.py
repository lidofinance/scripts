from typing import TypedDict, TypeVar

import pytest
from brownie import Contract, chain
from brownie.exceptions import brownie
from web3 import Web3

from utils.config import contracts
from utils.test.helpers import ETH, almostEqWithDiff, eth_balance, GWEI
from utils.test.oracle_report_helpers import ONE_DAY, SHARE_RATE_PRECISION, oracle_report

LIMITER_PRECISION_BASE = 10**9
MAX_BASIS_POINTS = 10_000


@pytest.fixture(scope="module")
def accounting_oracle() -> Contract:
    return contracts.accounting_oracle


@pytest.fixture(scope="module")
def lido() -> Contract:
    return contracts.lido


def test_accounting_no_cl_rebase(accounting_oracle: Contract, lido: Contract):
    """Check Lido rebase after accounting report with no CL rebase"""

    block_before_report = chain.height
    tx, _ = oracle_report(cl_diff=0, exclude_vaults_balances=True)
    block_after_report = chain.height

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ), "TotalPooledEther has changed"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ), "TotalShares has changed"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_before == shares_rate_after, "Shares rate has changed"

    eth_distributed_event = _first_event(tx, ETHDistributed)
    assert (
        eth_distributed_event["preCLBalance"] == eth_distributed_event["postCLBalance"]
    ), "ETHDistributed preCLBalance <> postCLBalance"

    post_ttl_shares_event = _first_event(tx, PostTotalShares)
    assert (
        post_ttl_shares_event["preTotalPooledEther"] == post_ttl_shares_event["postTotalPooledEther"]
    ), "PostTotalShares preTotalPooledEther <> postTotalPooledEther"

    assert eth_balance(lido.address, block_before_report) == eth_balance(
        lido.address, block_after_report
    ), "Lido ETH balance has changed"


@pytest.mark.parametrize(
    "rebase_amount",
    [ETH(-1_000)],
)
def test_accounting_negative_cl_rebase(accounting_oracle: Contract, lido: Contract, rebase_amount: int):
    """Check Lido rebase after accounting report with negative CL rebase"""

    block_before_report = chain.height
    tx, _ = oracle_report(cl_diff=rebase_amount, exclude_vaults_balances=True)
    block_after_report = chain.height

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) + rebase_amount == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ), "TotalPooledEther change mismatch"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ), "TotalShares has changed"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_after < shares_rate_before, "Shares rate has not decreased"

    eth_distributed_event = _first_event(tx, ETHDistributed)
    assert (
        eth_distributed_event["preCLBalance"] + rebase_amount == eth_distributed_event["postCLBalance"]
    ), "ETHDistributed: CL balance differs from expected"

    post_ttl_shares_event = _first_event(tx, PostTotalShares)
    assert (
        post_ttl_shares_event["preTotalPooledEther"] + rebase_amount == post_ttl_shares_event["postTotalPooledEther"]
    ), "PostTotalShares: TotalPooledEther differs from expected"


def test_accounting_cl_rebase_at_limits(accounting_oracle: Contract, lido: Contract):
    """Check Lido rebase after accounting report with positive CL rebase close to the limits"""

    block_before_report = chain.height

    annual_increase_limit = contracts.oracle_report_sanity_checker.getOracleReportLimits()[2]
    pre_cl_balance = contracts.lido.getBeaconStat()[-1]

    rebase_amount = (annual_increase_limit * ONE_DAY + 1) * pre_cl_balance // (365 * ONE_DAY) // MAX_BASIS_POINTS
    rebase_amount = _round_to_gwei(rebase_amount)

    tx, _ = oracle_report(cl_diff=rebase_amount, exclude_vaults_balances=True)
    block_after_report = chain.height

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) + rebase_amount == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ), "TotalPooledEther change mismatch"

    shares_as_fees_list = [e["sharesValue"] for e in _get_events(tx, TransferShares)]

    assert len(shares_as_fees_list) == 2, "Expected transfer of shares to NodeOperatorsRegistry and DAO"
    assert almostEqWithDiff(
        shares_as_fees_list[0],
        shares_as_fees_list[1],
        1,
    ), "Shares minted to DAO and NodeOperatorsRegistry mismatch"

    minted_shares_sum = sum(shares_as_fees_list)
    assert lido.getTotalShares(block_identifier=block_before_report) + minted_shares_sum == lido.getTotalShares(
        block_identifier=block_after_report,
    ), "TotalShares change mismatch"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_after > shares_rate_before, "Shares rate has not increased"

    eth_distributed_event = _first_event(tx, ETHDistributed)
    assert (
        eth_distributed_event["preCLBalance"] + rebase_amount == eth_distributed_event["postCLBalance"]
    ), "ETHDistributed: CL balance has not increased"

    post_ttl_shares_event = _first_event(tx, PostTotalShares)
    assert (
        post_ttl_shares_event["preTotalPooledEther"] + rebase_amount == post_ttl_shares_event["postTotalPooledEther"]
    ), "PostTotalShares: TotalPooledEther has not increased"


def test_accounting_cl_rebase_above_limits(lido: Contract):
    """Check that report reverts on sanity checks"""

    block_before_report = chain.height

    max_cl_rebase_via_limiter = (
        contracts.oracle_report_sanity_checker.getMaxPositiveTokenRebase(block_identifier=block_before_report)
        * lido.getTotalPooledEther(block_identifier=block_before_report)
        // LIMITER_PRECISION_BASE
    )

    annual_increase_limit = contracts.oracle_report_sanity_checker.getOracleReportLimits()[2]
    pre_cl_balance = contracts.lido.getBeaconStat()[-1]

    rebase_amount = ((annual_increase_limit + 1) * ONE_DAY + 1) * pre_cl_balance // (365 * ONE_DAY) // MAX_BASIS_POINTS
    assert max_cl_rebase_via_limiter > rebase_amount, "Expected annual limit to shot first"

    error_hash = Web3.keccak(text="IncorrectCLBalanceIncrease(uint256)")[:4]
    with brownie.reverts(revert_pattern=f"typed error: {error_hash.hex()}[0-9a-f]+"):  # type: ignore
        oracle_report(cl_diff=rebase_amount, exclude_vaults_balances=True)


class ETHDistributed(TypedDict):
    """ETHDistributed event definition"""

    reportTimestamp: int
    preCLBalance: int
    postCLBalance: int
    withdrawalsWithdrawn: int
    executionLayerRewardsWithdrawn: int
    postBufferedEther: int


class PostTotalShares(TypedDict):
    """PostTotalShares event definition"""

    postTotalPooledEther: int
    preTotalPooledEther: int
    timeElapsed: int
    totalShare: int


class TokenRebased(TypedDict):
    """TokenRebased event definition"""

    reportTimestamp: int
    timeElapsed: int
    preTotalShares: int
    preTotalEther: int
    postTotalShares: int
    postTotalEther: int
    sharesMintedAsFee: int


TransferShares = TypedDict(
    "TransferShares",
    {"from": str, "to": str, "sharesValue": int},
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


def _shares_rate_from_event(tx) -> tuple[int, int]:
    """Get shares rate from TokenRebased event"""

    token_rebased_event = _first_event(tx, TokenRebased)
    return (
        token_rebased_event["preTotalEther"] * SHARE_RATE_PRECISION // token_rebased_event["preTotalShares"],
        token_rebased_event["postTotalEther"] * SHARE_RATE_PRECISION // token_rebased_event["postTotalShares"],
    )


def _round_to_gwei(amount: int) -> int:
    """Round amount to gwei"""

    return amount // GWEI * GWEI
