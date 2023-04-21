from brownie import ZERO_ADDRESS

from utils.test.oracle_report_helpers import oracle_report
from utils.test.helpers import ETH
from utils.config import contracts


def create_single_withdrawal_request(amount, holder):
    request_tx = contracts.withdrawal_queue.requestWithdrawals([amount], holder, {"from": holder})
    return request_tx.events["WithdrawalRequested"][0]["requestId"]


def test_bunker_multiple_batches(accounts):
    amount = ETH(100)
    stranger = accounts[0]
    withdrawal_amount = ETH(10)

    assert contracts.lido.balanceOf(stranger) == 0
    assert contracts.withdrawal_queue.getLastRequestId() == 0

    contracts.lido.approve(contracts.withdrawal_queue.address, amount, {"from": stranger})
    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": amount})

    steth_initial_balance = contracts.lido.balanceOf(stranger)

    oracle_report(cl_diff=-ETH(100), exclude_vaults_balances=True)

    steth_first_negative_report_balance = contracts.lido.balanceOf(stranger)

    assert steth_initial_balance > steth_first_negative_report_balance
    assert contracts.withdrawal_queue.isBunkerModeActive()

    first_request_id = create_single_withdrawal_request(withdrawal_amount, stranger)

    oracle_report(cl_diff=-ETH(100), exclude_vaults_balances=True)

    steth_second_negative_report_balance = contracts.lido.balanceOf(stranger)

    assert steth_first_negative_report_balance > steth_second_negative_report_balance
    assert contracts.withdrawal_queue.isBunkerModeActive()

    second_request_id = create_single_withdrawal_request(withdrawal_amount, stranger)

    [
        (first_steth_emount, first_shares, _, _, _, _),
        (second_steth_emount, second_shares, _, _, _, _),
    ] = contracts.withdrawal_queue.getWithdrawalStatus([first_request_id, second_request_id])

    # amount of requested eth should be equal, but shares are different
    # because second request was affected by negative rebase twice
    assert first_steth_emount == second_steth_emount
    assert first_shares < second_shares

    oracle_report(cl_diff=ETH(0.1), exclude_vaults_balances=True)

    assert not contracts.withdrawal_queue.isBunkerModeActive()

    [
        (_, _, _, _, is_finalized_first, _),
        (_, _, _, _, is_finalized_second, _),
    ] = contracts.withdrawal_queue.getWithdrawalStatus([first_request_id, second_request_id])

    assert is_finalized_first == is_finalized_second == True

    request_ids = [first_request_id, second_request_id]
    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    hints = contracts.withdrawal_queue.findCheckpointHints(request_ids, 1, lastCheckpointIndex)
    withdrawal_tx = contracts.withdrawal_queue.claimWithdrawals(
        request_ids, hints, {"from": stranger}
    )

    claims = withdrawal_tx.events["WithdrawalClaimed"]

    # first claimed request should be less than requested amount because it caught negative rebase
    assert claims[0]["amountOfETH"] < withdrawal_amount
    assert claims[1]["amountOfETH"] == withdrawal_amount
