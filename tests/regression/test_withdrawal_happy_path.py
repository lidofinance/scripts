import pytest
from brownie import accounts  # type: ignore
from utils.test.oracle_report_helpers import (
    oracle_report,
)

from utils.test.helpers import almostEqEth, almostEqWithDiff, steth_balance, ETH, ZERO_ADDRESS

from utils.config import (
    contracts,
)


def test_withdraw(steth_holder, eth_whale):
    account = accounts.at(steth_holder, force=True)
    REQUESTS_COUNT = 10
    REQUEST_AMOUNT = ETH(1)
    REQUESTS_SUM = REQUESTS_COUNT * REQUEST_AMOUNT

    """ report """
    while contracts.withdrawal_queue.getLastRequestId() != contracts.withdrawal_queue.getLastFinalizedRequestId():
        # finalize all current requests first
        report_tx = oracle_report()[0]
        # stake new ether to increase buffer
        contracts.lido.submit(ZERO_ADDRESS, {"from": eth_whale.address, "value": ETH(10000)})

    """ pre request """
    no_requests = contracts.withdrawal_queue.getWithdrawalRequests(steth_holder, {"from": steth_holder})
    assert len(no_requests) == 0

    last_request_id = contracts.withdrawal_queue.getLastRequestId()
    last_finalized_request_id = contracts.withdrawal_queue.getLastFinalizedRequestId()
    last_checkpoint_index_before = contracts.withdrawal_queue.getLastCheckpointIndex()
    unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()
    PRE_REPORT_REQUEST_SHARES = contracts.lido.getSharesByPooledEth(REQUEST_AMOUNT)
    PRE_REPORT_REQUEST_SHARES_SUM = contracts.lido.getSharesByPooledEth(REQUESTS_SUM + unfinalized_steth)

    """ request """
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    steth_balance_before = steth_balance(steth_holder)
    request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
    )
    steth_balance_after = steth_balance(steth_holder)

    shares_to_burn = contracts.lido.sharesOf(contracts.withdrawal_queue)
    # post request checks

    assert almostEqWithDiff(steth_balance_before - steth_balance_after, REQUESTS_SUM, 2 * REQUESTS_COUNT)
    # Withdrawal Events
    assert request_tx.events.count("WithdrawalRequested") == REQUESTS_COUNT
    for i, event in enumerate(request_tx.events["WithdrawalRequested"]):
        assert event["requestId"] == i + last_request_id + 1
        assert almostEqEth(event["amountOfStETH"], REQUEST_AMOUNT)
        assert almostEqEth(event["amountOfShares"], PRE_REPORT_REQUEST_SHARES)
        assert event["requestor"] == steth_holder
        assert event["owner"] == steth_holder

    # NFT Events, filter out ERC20 Transfer events
    nft_events = [event for event in request_tx.events["Transfer"] if not "value" in event]
    assert len(nft_events) == REQUESTS_COUNT
    for i, event in enumerate(nft_events):
        assert event["tokenId"] == i + last_request_id + 1
        assert event["from"] == ZERO_ADDRESS
        assert event["to"] == steth_holder

    # check each request
    requests_ids = contracts.withdrawal_queue.getWithdrawalRequests(steth_holder, {"from": steth_holder})
    statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": steth_holder})
    claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, [0 for _ in requests_ids])
    assert len(requests_ids) == REQUESTS_COUNT
    assert len(statuses) == REQUESTS_COUNT

    for i, request_id in enumerate(requests_ids):
        assert i + last_request_id + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = statuses[i]
        assert almostEqEth(amountOfStETH, REQUEST_AMOUNT)
        assert almostEqEth(amountOfShares, PRE_REPORT_REQUEST_SHARES)
        assert owner == steth_holder
        assert not isFinalized
        assert not isClaimed
        assert claimableEther[i] == 0

    pre_lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    assert pre_lastCheckpointIndex > 0

    # first report
    report_tx = oracle_report()[0]
    # second report requests will get finalized for sure
    if not report_tx.events.count("WithdrawalsFinalized") == 1:
        report_tx = oracle_report()[0]

    # post report event
    finalization_event = report_tx.events["WithdrawalsFinalized"]
    assert finalization_event["from"] == last_finalized_request_id + 1
    assert finalization_event["to"] == REQUESTS_COUNT + last_request_id
    assert almostEqEth(finalization_event["amountOfETHLocked"], REQUESTS_SUM + unfinalized_steth)
    assert almostEqEth(finalization_event["sharesToBurn"], shares_to_burn)

    # post reports WQ state
    assert contracts.withdrawal_queue.getLastFinalizedRequestId() == requests_ids[-1]
    last_checkpoint_index = contracts.withdrawal_queue.getLastCheckpointIndex()
    assert last_checkpoint_index == last_checkpoint_index_before + 1

    # post report requests check
    hints = contracts.withdrawal_queue.findCheckpointHints(requests_ids, 1, last_checkpoint_index)
    assert len(hints) == REQUESTS_COUNT

    post_report_statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": steth_holder})
    post_report_claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, hints)

    for i, request_id in enumerate(requests_ids):
        assert i + last_request_id + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = post_report_statuses[i]
        assert amountOfStETH == statuses[i][0]  # amountOfShares remains unchanged
        assert amountOfShares == statuses[i][1]  # amountOfShares remains unchanged
        assert owner == steth_holder
        assert isFinalized
        assert not isClaimed
        assert almostEqEth(post_report_claimableEther[i], REQUEST_AMOUNT)
        assert hints[i] == last_checkpoint_index

    """ claim """
    claim_balance_before = account.balance()
    claim_tx = contracts.withdrawal_queue.claimWithdrawals(requests_ids, hints, {"from": steth_holder})
    claim_balance_after = account.balance()

    # balance check
    assert almostEqEth(
        claim_balance_after - claim_balance_before + claim_tx.gas_used * claim_tx.gas_price, REQUESTS_SUM
    )

    # events
    assert claim_tx.events.count("WithdrawalClaimed") == REQUESTS_COUNT
    for i, event in enumerate(claim_tx.events["WithdrawalClaimed"]):
        assert event["requestId"] == i + last_request_id + 1
        assert event["receiver"] == steth_holder
        assert event["owner"] == steth_holder
        assert almostEqEth(event["amountOfETH"], REQUEST_AMOUNT)

    assert claim_tx.events.count("Transfer") == REQUESTS_COUNT
    for i, event in enumerate(claim_tx.events["Transfer"]):
        assert event["tokenId"] == i + last_request_id + 1
        assert event["to"] == ZERO_ADDRESS
        assert event["from"] == steth_holder

    post_claim_statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": steth_holder})
    post_claim_claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, hints)

    for i, request_id in enumerate(requests_ids):
        assert i + last_request_id + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = post_claim_statuses[i]
        assert amountOfStETH == statuses[i][0]  # amountOfShares remains unchanged
        assert amountOfShares == statuses[i][1]  # amountOfShares remains unchanged
        assert owner == steth_holder
        assert isFinalized
        assert isClaimed
        assert almostEqEth(post_report_claimableEther[i], REQUEST_AMOUNT)
        assert post_claim_claimableEther[i] == 0

    assert claim_tx.events.count("WithdrawalClaimed") == REQUESTS_COUNT
    for i, event in enumerate(claim_tx.events["WithdrawalClaimed"]):
        assert event["requestId"] == i + last_request_id + 1
        assert event["receiver"] == steth_holder
        assert event["owner"] == steth_holder
        assert almostEqEth(event["amountOfETH"], REQUEST_AMOUNT)

    assert claim_tx.events.count("Transfer") == REQUESTS_COUNT
    for i, event in enumerate(claim_tx.events["Transfer"]):
        assert event["tokenId"] == i + last_request_id + 1
        assert event["to"] == ZERO_ADDRESS
        assert event["from"] == steth_holder
