from brownie import ZERO_ADDRESS

from utils.test.oracle_report_helpers import oracle_report
from utils.test.helpers import ETH, almostEqEth
from utils.config import contracts


def test_all_round_happy_path(accounts):
    stranger = accounts[0]
    amount = ETH(100)
    max_deposit = 150
    curated_module_id = 1

    steth_balance_before_submit = contracts.lido.balanceOf(stranger)
    eth_balance_before_submit = stranger.balance()

    assert steth_balance_before_submit == 0

    # Submitting ETH

    total_supply_before_submit = contracts.lido.totalSupply()
    buffered_ether_before_submit = contracts.lido.getBufferedEther()
    staking_limit_before_submit = contracts.lido.getCurrentStakeLimit()

    submit_tx = contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": amount})

    steth_balance_after_submit = contracts.lido.balanceOf(stranger)
    total_supply_after_submit = contracts.lido.totalSupply()
    buffered_ether_after_submit = contracts.lido.getBufferedEther()
    staking_limit_after_submit = contracts.lido.getCurrentStakeLimit()

    assert almostEqEth(steth_balance_after_submit, steth_balance_before_submit + amount)
    assert eth_balance_before_submit == stranger.balance() + amount

    submit_event = submit_tx.events["Submitted"]
    transfer_shares_event = submit_tx.events["TransferShares"]

    assert submit_event["sender"] == stranger
    assert submit_event["amount"] == amount
    assert submit_event["referral"] == ZERO_ADDRESS

    shares_to_be_minted = contracts.lido.getSharesByPooledEth(amount)

    assert transfer_shares_event["from"] == ZERO_ADDRESS
    assert transfer_shares_event["to"] == stranger
    assert almostEqEth(transfer_shares_event["sharesValue"], shares_to_be_minted)

    assert total_supply_after_submit == total_supply_before_submit + amount
    assert buffered_ether_after_submit == buffered_ether_before_submit + amount
    assert staking_limit_after_submit == staking_limit_before_submit - amount

    # Depositing ETH
    dsm = accounts.at(contracts.deposit_security_module.address, force=True)

    contracts.lido.deposit(max_deposit, curated_module_id, "0x0", {"from": dsm})
    buffered_ether_after_deposit = contracts.lido.getBufferedEther()

    assert buffered_ether_after_submit > buffered_ether_after_deposit

    # Rebasing (Increasing balance)

    report_tx, _ = oracle_report(cl_diff=ETH(100), exclude_vaults_balances=True)
    steth_balance_after_rebase = contracts.lido.balanceOf(stranger)

    token_rebased_event = report_tx.events["TokenRebased"]

    assert report_tx.events.count("TokenRebased") == 1
    assert report_tx.events.count("WithdrawalsFinalized") == 0
    assert token_rebased_event["postTotalEther"] - token_rebased_event["preTotalEther"] == amount

    assert steth_balance_after_rebase > steth_balance_after_submit

    # Requesting withdrawal

    assert len(contracts.withdrawal_queue.getWithdrawalRequests(stranger, {"from": stranger})) == 0

    approve_tx = contracts.lido.approve(
        contracts.withdrawal_queue.address, amount, {"from": stranger}
    )

    approve_event = approve_tx.events["Approval"]

    assert approve_event["value"] == amount
    assert approve_event["owner"] == stranger
    assert approve_event["spender"] == contracts.withdrawal_queue.address

    assert contracts.withdrawal_queue.getLastRequestId() == 0

    withdrawal_request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [amount], stranger, {"from": stranger}
    )

    withdrawal_request_event = withdrawal_request_tx.events["WithdrawalRequested"]
    withdrawal_request_transfer_event = withdrawal_request_tx.events["Transfer"]

    request_ids = [withdrawal_request_event["requestId"]]

    assert withdrawal_request_transfer_event[0]["from"] == stranger
    assert withdrawal_request_transfer_event[0]["to"] == contracts.withdrawal_queue.address
    assert withdrawal_request_transfer_event[0]["value"] == amount

    assert withdrawal_request_transfer_event[1]["tokenId"] == request_ids[0]
    assert withdrawal_request_transfer_event[1]["from"] == ZERO_ADDRESS
    assert withdrawal_request_transfer_event[1]["to"] == stranger

    assert withdrawal_request_event["requestor"] == stranger
    assert withdrawal_request_event["owner"] == stranger
    assert withdrawal_request_event["amountOfStETH"] == amount

    steth_balance_after_withdrawal_request = contracts.lido.balanceOf(stranger)
    [(_, _, _, _, finalized, _)] = contracts.withdrawal_queue.getWithdrawalStatus(request_ids)

    assert almostEqEth(steth_balance_after_withdrawal_request, steth_balance_after_rebase - amount)
    assert len(contracts.withdrawal_queue.getWithdrawalRequests(stranger, {"from": stranger})) == 1
    assert contracts.withdrawal_queue.getLastRequestId() == 1
    assert not finalized

    # Rebasing (Withdrawal finalization)

    locked_ether_amount_before_finalization = contracts.withdrawal_queue.getLockedEtherAmount()
    report_tx, _ = oracle_report(cl_diff=ETH(100))

    locked_ether_amount_after_finalization = contracts.withdrawal_queue.getLockedEtherAmount()
    withdrawal_finalized_event = report_tx.events["WithdrawalsFinalized"]

    assert withdrawal_finalized_event["amountOfETHLocked"] == amount
    assert withdrawal_finalized_event["from"] == request_ids[0]
    assert withdrawal_finalized_event["to"] == request_ids[0]
    assert (
        locked_ether_amount_before_finalization == locked_ether_amount_after_finalization - amount
    )

    # Withdrawing

    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    hints = contracts.withdrawal_queue.findCheckpointHints(request_ids, 1, lastCheckpointIndex)
    [(_, _, _, _, finalized, _)] = contracts.withdrawal_queue.getWithdrawalStatus(request_ids)

    [claimable_ether_before_claim] = contracts.withdrawal_queue.getClaimableEther(
        request_ids, hints
    )
    eth_balance_before_withdrawal = stranger.balance()

    assert finalized
    assert claimable_ether_before_claim == amount

    claim_tx = contracts.withdrawal_queue.claimWithdrawals(request_ids, hints, {"from": stranger})

    claim_event = claim_tx.events["WithdrawalClaimed"]
    transfer_event = claim_tx.events["Transfer"]

    assert claim_event["requestId"] == request_ids[0]
    assert claim_event["owner"] == stranger
    assert claim_event["receiver"] == stranger
    assert claim_event["amountOfETH"] == amount
    assert transfer_event["from"] == stranger
    assert transfer_event["to"] == ZERO_ADDRESS
    assert transfer_event["tokenId"] == request_ids[0]

    assert eth_balance_before_withdrawal == stranger.balance() - amount
    assert (
        locked_ether_amount_after_finalization
        == contracts.withdrawal_queue.getLockedEtherAmount() + amount
    )

    [(_, _, _, _, finalized, claimed)] = contracts.withdrawal_queue.getWithdrawalStatus(
        request_ids, {"from": stranger}
    )
    [claimable_ether_after_claim] = contracts.withdrawal_queue.getClaimableEther(request_ids, hints)

    assert finalized
    assert claimed
    assert not claimable_ether_after_claim
