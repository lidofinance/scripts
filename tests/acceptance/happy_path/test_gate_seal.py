import math

import pytest
from brownie import accounts, web3  # type: ignore
from utils.test.oracle_report_helpers import oracle_report

from utils.config import (
    contracts,
)

from utils.test.helpers import ETH


def test_gate_seal_withdraw(steth_holder):
    REQUESTS_COUNT = 1
    REQUEST_AMOUNT = ETH(1)
    REQUESTS_SUM = REQUESTS_COUNT * REQUEST_AMOUNT

    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
    )
    requests_ids_finalized = [e["requestId"] for e in tx.events["WithdrawalRequested"]]

    # first oracle report, requests might not get finalized due to sanity check requestTimestampMargin
    oracle_report()
    # second report requests will get finalized for sure
    oracle_report()

    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
    )
    requests_ids_not_finalized = [e["requestId"] for e in tx.events["WithdrawalRequested"]]

    # assert state
    statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids_finalized, {"from": steth_holder})
    for status in statuses:
        (_, _, _, _, isFinalized, isClaimed) = status
        assert isFinalized
        assert not isClaimed

    statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids_not_finalized, {"from": steth_holder})
    for status in statuses:
        (_, _, _, _, isFinalized, isClaimed) = status
        assert not isFinalized
        assert not isClaimed
