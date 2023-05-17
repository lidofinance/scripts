from brownie.network.account import Account
import pytest
from brownie import Contract, interface, reverts, Wei, chain  # type: ignore
from tests.snapshot.test_lido_snapshot import UINT256_MAX

from utils.config import WITHDRAWAL_QUEUE, contracts
from utils.evm_script import encode_error
from utils.test.oracle_report_helpers import oracle_report

MIN_STETH_WITHDRAWAL_AMOUNT = Wei(100)
MAX_STETH_WITHDRAWAL_AMOUNT = Wei(1000 * 10**18)


def test_request_withdrawals_steth(wq: Contract, steth_whale: Account):
    too_small_amount = MIN_STETH_WITHDRAWAL_AMOUNT - 10
    too_large_amount = MAX_STETH_WITHDRAWAL_AMOUNT + 10
    normal_amount = MIN_STETH_WITHDRAWAL_AMOUNT + 10000

    with reverts(
        encode_error(
            "RequestAmountTooSmall(uint256)",
            [too_small_amount],
        )
    ):
        wq.requestWithdrawals(
            [
                normal_amount,
                too_small_amount,
            ],
            steth_whale,
            {"from": steth_whale},
        )

    with reverts(
        encode_error(
            "RequestAmountTooLarge(uint256)",
            [too_large_amount],
        )
    ):
        wq.requestWithdrawals(
            [
                normal_amount,
                too_large_amount,
            ],
            steth_whale,
            {"from": steth_whale},
        )


def test_request_withdrawals_wsteth(wq: Contract, wsteth_whale: Account):
    too_small_amount = steth_to_wsteth(MIN_STETH_WITHDRAWAL_AMOUNT - 10)
    too_large_amount = steth_to_wsteth(MAX_STETH_WITHDRAWAL_AMOUNT + 10)
    normal_amount = steth_to_wsteth(MIN_STETH_WITHDRAWAL_AMOUNT + 10000)

    with reverts(
        encode_error(
            "RequestAmountTooSmall(uint256)",
            [wsteth_to_steth(too_small_amount)],
        )
    ):
        wq.requestWithdrawalsWstETH(
            [
                normal_amount,
                too_small_amount,
            ],
            wsteth_whale,
            {"from": wsteth_whale},
        )

    with reverts(
        encode_error(
            "RequestAmountTooLarge(uint256)",
            [wsteth_to_steth(too_large_amount)],
        )
    ):
        wq.requestWithdrawalsWstETH(
            [
                normal_amount,
                too_large_amount,
            ],
            wsteth_whale,
            {"from": wsteth_whale},
        )


def test_wq_prefinalize(wq: Contract, steth_whale: Account):
    with reverts(encode_error("EmptyBatches()")):
        wq.prefinalize.transact([], 1, {"from": wq.address})

    last_finalized_id = wq.getLastFinalizedRequestId()  # 0 after enacment
    fill_wq(wq, steth_whale, count=3)

    with reverts(encode_error("InvalidRequestId(uint256)", [last_finalized_id])):
        oracle_report(withdrawalFinalizationBatches=[last_finalized_id])

    with reverts(encode_error("InvalidRequestId(uint256)", [4])):
        oracle_report(withdrawalFinalizationBatches=[1, 4])

    with reverts(encode_error("BatchesAreNotSorted()")):
        oracle_report(withdrawalFinalizationBatches=[3, 2])

    with reverts(encode_error("BatchesAreNotSorted()")):
        oracle_report(withdrawalFinalizationBatches=[1, 1])

    with reverts(encode_error("ZeroShareRate()")):
        oracle_report(withdrawalFinalizationBatches=[1, 2], simulatedShareRate=0)


def test_request_to_finalize_to_close(wq: Contract, steth_whale: Account):
    fill_wq(wq, steth_whale, count=1)
    with reverts(encode_error("IncorrectRequestFinalization(uint256)", [chain.time()])):
        oracle_report(
            withdrawalFinalizationBatches=[1],
            wait_to_next_report_time=False,
        )


def test_wq_finalize(wq: Contract, steth_whale: Account):
    last_finalized_id = wq.getLastFinalizedRequestId()  # 0 after enacment

    with reverts(encode_error("InvalidRequestId(uint256)", [last_finalized_id])):
        wq.finalize(last_finalized_id, 1, {"from": contracts.lido})

    with reverts(
        encode_error(
            "InvalidRequestId(uint256)",
            [last_finalized_id + 1],
        )
    ):
        wq.finalize(last_finalized_id + 1, 1, {"from": contracts.lido})

    max_eth = fill_wq(wq, steth_whale, count=3)

    with reverts(encode_error("InvalidRequestId(uint256)", [4])):
        wq.finalize(4, 1, {"from": contracts.lido})

    with reverts(
        encode_error(
            "TooMuchEtherToFinalize(uint256,uint256)",
            [
                max_eth + 1,
                max_eth,
            ],
        )
    ):
        wq.finalize(3, 1, {"from": contracts.lido, "value": Wei(max_eth + 1)})


# === Fixtures ===


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="module")
def wq() -> Contract:
    return interface.WithdrawalQueueERC721(WITHDRAWAL_QUEUE)


@pytest.fixture(scope="function", autouse=True)
def max_approval_to_wq(steth_whale: Account, wq: Contract) -> None:
    contracts.wsteth.approve(wq.address, UINT256_MAX, {"from": steth_whale})
    contracts.lido.approve(wq.address, UINT256_MAX, {"from": steth_whale})


@pytest.fixture(scope="function")
def wsteth_whale(steth_whale: Account) -> Account:
    contracts.lido.approve(contracts.wsteth.address, UINT256_MAX, {"from": steth_whale})
    steth_to_wrap = contracts.lido.balanceOf(steth_whale) // 2
    contracts.wsteth.wrap(steth_to_wrap, {"from": steth_whale})
    return steth_whale


# === Helpers ===


def fill_wq(wq: Contract, owner: Account, count: int) -> Wei:
    batches = [MIN_STETH_WITHDRAWAL_AMOUNT + 1000] * count
    wq.requestWithdrawals(batches, owner, {"from": owner})
    return Wei(sum(batches))


def steth_to_wsteth(amount: Wei) -> Wei:
    return contracts.wsteth.getWstETHByStETH(amount)


def wsteth_to_steth(amount: Wei) -> Wei:
    return contracts.wsteth.getStETHByWstETH(amount)
