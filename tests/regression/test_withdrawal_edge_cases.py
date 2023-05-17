from brownie import ZERO_ADDRESS, chain

from utils.test.oracle_report_helpers import oracle_report, wait_to_next_available_report_time
from utils.test.helpers import ETH
from utils.config import contracts


def create_single_withdrawal_request(amount, holder):
    request_tx = contracts.withdrawal_queue.requestWithdrawals([amount], holder, {"from": holder})
    return request_tx.events["WithdrawalRequested"][0]["requestId"]


def check_all_requests_finalization(request_ids, holder):
    statuses = contracts.withdrawal_queue.getWithdrawalStatus(request_ids, {"from": holder})

    for request_status in statuses:
        (_, _, _, _, is_finalized, _) = request_status
        assert is_finalized


def test_bunker_multiple_batches(accounts):
    amount = ETH(100)
    stranger = accounts[0]
    withdrawal_amount = ETH(10)

    assert contracts.lido.balanceOf(stranger) == 0

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
    request_ids = [first_request_id, second_request_id]

    [
        (first_steth_emount, first_shares, _, _, _, _),
        (second_steth_emount, second_shares, _, _, _, _),
    ] = contracts.withdrawal_queue.getWithdrawalStatus(request_ids)

    # amount of requested eth should be equal, but shares are different
    # because second request was affected by negative rebase twice
    assert first_steth_emount == second_steth_emount
    assert first_shares < second_shares

    oracle_report(cl_diff=ETH(0.1), exclude_vaults_balances=True)

    assert not contracts.withdrawal_queue.isBunkerModeActive()

    check_all_requests_finalization(request_ids, stranger)

    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    hints = contracts.withdrawal_queue.findCheckpointHints(request_ids, 1, lastCheckpointIndex)
    withdrawal_tx = contracts.withdrawal_queue.claimWithdrawals(
        request_ids, hints, {"from": stranger}
    )

    claims = withdrawal_tx.events["WithdrawalClaimed"]

    # first claimed request should be less than requested amount because it caught negative rebase
    assert claims[0]["amountOfETH"] < withdrawal_amount
    assert claims[1]["amountOfETH"] == withdrawal_amount


def test_oracle_report_missed(accounts):
    amount = ETH(100)
    stranger = accounts[0]

    assert contracts.lido.balanceOf(stranger) == 0

    contracts.lido.approve(contracts.withdrawal_queue.address, amount, {"from": stranger})
    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": amount})

    oracle_report(cl_diff=ETH(1), exclude_vaults_balances=True)

    withdrawal_request_id = create_single_withdrawal_request(amount, stranger)
    request_ids = [withdrawal_request_id]

    # skipping next report by waiting 24h more
    chain_time_before_missed_report = chain.time()
    wait_to_next_available_report_time(contracts.hash_consensus_for_accounting_oracle)
    chain_time_after_missed_report = chain.time()

    [
        (_, _, _, _, is_finalized, _),
    ] = contracts.withdrawal_queue.getWithdrawalStatus(request_ids)

    # time is passed but request still not finalized
    assert chain_time_before_missed_report < chain_time_after_missed_report
    assert not is_finalized

    oracle_report(cl_diff=ETH(1), exclude_vaults_balances=True)

    # successful report has finalized request
    check_all_requests_finalization(request_ids, stranger)

    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    hints = contracts.withdrawal_queue.findCheckpointHints(request_ids, 1, lastCheckpointIndex)
    withdrawal_tx = contracts.withdrawal_queue.claimWithdrawals(
        request_ids, hints, {"from": stranger}
    )

    claims = withdrawal_tx.events["WithdrawalClaimed"]

    assert claims[0]["amountOfETH"] == amount


def test_several_rebases(accounts):
    amount = ETH(100)
    stranger = accounts[0]
    withdrawal_amount = ETH(10)

    assert contracts.lido.balanceOf(stranger) == 0

    contracts.lido.approve(contracts.withdrawal_queue.address, amount, {"from": stranger})
    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": amount})

    request_ids = []

    oracle_report(cl_diff=ETH(100), exclude_vaults_balances=True)

    first_request_id = create_single_withdrawal_request(withdrawal_amount, stranger)
    request_ids.append(first_request_id)

    oracle_report(cl_diff=-ETH(100), exclude_vaults_balances=True)
    assert contracts.withdrawal_queue.isBunkerModeActive()

    check_all_requests_finalization(request_ids, stranger)

    second_request_id = create_single_withdrawal_request(withdrawal_amount, stranger)
    request_ids.append(second_request_id)

    oracle_report(cl_diff=-ETH(100), exclude_vaults_balances=True)

    assert contracts.withdrawal_queue.isBunkerModeActive()

    third_request_id = create_single_withdrawal_request(withdrawal_amount, stranger)
    request_ids.append(third_request_id)

    oracle_report(cl_diff=ETH(100), exclude_vaults_balances=True)

    assert not contracts.withdrawal_queue.isBunkerModeActive()

    check_all_requests_finalization(request_ids, stranger)

    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    hints = contracts.withdrawal_queue.findCheckpointHints(request_ids, 1, lastCheckpointIndex)
    withdrawal_tx = contracts.withdrawal_queue.claimWithdrawals(
        request_ids, hints, {"from": stranger}
    )

    claims = withdrawal_tx.events["WithdrawalClaimed"]

    assert claims[0]["amountOfETH"] < withdrawal_amount
    assert claims[1]["amountOfETH"] < withdrawal_amount
    assert claims[2]["amountOfETH"] == withdrawal_amount
