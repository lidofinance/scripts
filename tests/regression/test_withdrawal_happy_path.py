from brownie import accounts  # type: ignore
from utils.test.oracle_report_helpers import (
    oracle_report,
)

from utils.test.helpers import almostEqEth, steth_balance, ETH

from utils.config import (
    contracts,
)


def test_withdraw(steth_holder):
    account = accounts.at(steth_holder, force=True)
    REQUESTS_COUNT = 10
    REQUEST_AMOUNT = ETH(1)
    REQUESTS_SUM = REQUESTS_COUNT * REQUEST_AMOUNT

    # pre request

    no_requests = contracts.withdrawal_queue.getWithdrawalRequests(steth_holder, {"from": steth_holder})
    assert len(no_requests) == 0

    # request
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    steth_balance_before = steth_balance(steth_holder)
    request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
    )
    steth_balance_after = steth_balance(steth_holder)

    # post request checks
    assert request_tx.events.count("WithdrawalRequested") == REQUESTS_COUNT
    for i, event in enumerate(request_tx.events["WithdrawalRequested"]):
        (requestId, requestor, owner, amountOfStETH, amountOfShares) = event
        assert requestId == i + 1
        assert almostEqEth(amountOfStETH, REQUEST_AMOUNT)
        assert almostEqEth(amountOfShares, contracts.lido.getSharesByPooledEth(amountOfStETH))
        assert owner == steth_holder
        assert requestor == steth_holder

    assert almostEqEth(steth_balance_before - steth_balance_after, REQUESTS_SUM)

    # check each request
    requests_ids = contracts.withdrawal_queue.getWithdrawalRequests(steth_holder, {"from": steth_holder})
    statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": steth_holder})
    claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, [0 for _ in requests_ids])
    assert len(requests_ids) == REQUESTS_COUNT
    assert len(statuses) == REQUESTS_COUNT

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = statuses[i]
        assert almostEqEth(amountOfStETH, REQUEST_AMOUNT)
        assert almostEqEth(amountOfShares, contracts.lido.getSharesByPooledEth(amountOfStETH))
        assert owner == steth_holder
        assert not isFinalized
        assert not isClaimed
        assert claimableEther[i] == 0

    pre_lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    assert pre_lastCheckpointIndex == 0

    # first oracle report, requests might not get finalized due to sanity check requestTimestampMargin
    oracle_report()
    # second report requests will get finalized for sure
    oracle_report()

    # post reports WQ state
    assert contracts.withdrawal_queue.getLastFinalizedRequestId() == requests_ids[-1]
    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    assert lastCheckpointIndex == 1

    # post report requests check

    hints = contracts.withdrawal_queue.findCheckpointHints(requests_ids, 1, lastCheckpointIndex)
    assert len(hints) == REQUESTS_COUNT

    post_report_statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": steth_holder})
    post_report_claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, hints)

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = post_report_statuses[i]
        assert amountOfStETH == statuses[i][0]  # amountOfShares remains unchanged
        assert amountOfShares == statuses[i][1]  # amountOfShares remains unchanged
        assert owner == steth_holder
        assert isFinalized
        assert not isClaimed
        assert almostEqEth(post_report_claimableEther[i], REQUEST_AMOUNT)
        # single first finalization hint is 1
        assert hints[i] == 1

    # claim
    claim_balance_before = account.balance()
    claim_tx = contracts.withdrawal_queue.claimWithdrawals(requests_ids, hints, {"from": steth_holder})
    assert claim_tx.events.count("WithdrawalClaimed") == REQUESTS_COUNT
    claim_balance_after = account.balance()
    assert almostEqEth(
        claim_balance_after - claim_balance_before + claim_tx.gas_used * claim_tx.gas_price, REQUESTS_SUM
    )

    post_claim_statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": steth_holder})
    post_claim_claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, hints)

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = post_claim_statuses[i]
        assert amountOfStETH == statuses[i][0]  # amountOfShares remains unchanged
        assert amountOfShares == statuses[i][1]  # amountOfShares remains unchanged
        assert owner == steth_holder
        assert isFinalized
        assert isClaimed
        assert almostEqEth(post_report_claimableEther[i], REQUEST_AMOUNT)
        assert post_claim_claimableEther[i] == 0
