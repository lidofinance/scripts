import math

import pytest
from brownie import chain, accounts, web3  # type: ignore
from utils.test.oracle_report_helpers import (
    ONE_DAY,
    SHARE_RATE_PRECISION,
    push_oracle_report,
    get_finalization_batches,
    simulate_report,
)

from utils.config import (
    contracts,
)


def ETH(amount):
    return math.floor(amount * 10**18)


def SHARES(amount):
    return ETH(amount)


def steth_balance(account):
    return contracts.lido.balanceOf(account)


def eth_balance(account):
    return web3.eth.getBalance(account)


def almostEqEth(b1, b2):
    return abs(b1 - b2) <= 10


def advance_chain_time(time):
    chain.sleep(time)
    chain.mine(1)


@pytest.fixture(scope="module")
def holder(accounts):
    whale = "0x41318419CFa25396b47A94896FfA2C77c6434040"
    contracts.lido.transfer(accounts[0], ETH(101), {"from": whale})
    return accounts[0]


def oracle_report():
    advance_chain_time(ONE_DAY)

    (refSlot, _) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    elRewardsVaultBalance = eth_balance(contracts.execution_layer_rewards_vault.address)
    withdrawalVaultBalance = eth_balance(contracts.withdrawal_vault.address)
    (coverShares, nonCoverShares) = contracts.burner.getSharesRequestedToBurn()
    (_, beaconValidators, beaconBalance) = contracts.lido.getBeaconStat()

    postCLBalance = beaconBalance + ETH(20)

    (postTotalPooledEther, postTotalShares, withdrawals, elRewards) = simulate_report(
        refSlot=refSlot,
        beaconValidators=beaconValidators,
        postCLBalance=postCLBalance,
        withdrawalVaultBalance=withdrawalVaultBalance,
        elRewardsVaultBalance=elRewardsVaultBalance,
    )
    simulatedShareRate = postTotalPooledEther * SHARE_RATE_PRECISION // postTotalShares
    sharesRequestedToBurn = coverShares + nonCoverShares

    finalization_batches = get_finalization_batches(simulatedShareRate, withdrawals, elRewards)

    push_oracle_report(
        refSlot=refSlot,
        clBalance=postCLBalance,
        numValidators=beaconValidators,
        withdrawalVaultBalance=withdrawalVaultBalance,
        sharesRequestedToBurn=sharesRequestedToBurn,
        withdrawalFinalizationBatches=finalization_batches,
        elRewardsVaultBalance=elRewardsVaultBalance,
        simulatedShareRate=simulatedShareRate,
    )


def test_withdraw(holder):
    account = accounts.at(holder, force=True)
    REQUESTS_COUNT = 10
    REQUEST_AMOUNT = ETH(1)
    REQUESTS_SUM = REQUESTS_COUNT * REQUEST_AMOUNT

    # pre request

    no_requests = contracts.withdrawal_queue.getWithdrawalRequests(holder, {"from": holder})
    assert len(no_requests) == 0

    # request
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": holder})
    steth_balance_before = steth_balance(holder)
    request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], holder, {"from": holder}
    )
    steth_balance_after = steth_balance(holder)
    # post request checks
    assert request_tx.events.count("WithdrawalRequested") == REQUESTS_COUNT
    assert almostEqEth(steth_balance_before - steth_balance_after, REQUESTS_SUM)

    # check each request
    requests_ids = contracts.withdrawal_queue.getWithdrawalRequests(holder, {"from": holder})
    statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": holder})
    claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, [0 for _ in requests_ids])
    assert len(requests_ids) == REQUESTS_COUNT
    assert len(statuses) == REQUESTS_COUNT

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = statuses[i]
        assert almostEqEth(amountOfStETH, REQUEST_AMOUNT)
        assert almostEqEth(amountOfShares, contracts.lido.getSharesByPooledEth(amountOfStETH))
        assert owner == holder
        assert not isFinalized
        assert not isClaimed
        assert claimableEther[i] == 0

    pre_lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    assert pre_lastCheckpointIndex == 0

    oracle_report()
    # post report WQ state
    assert contracts.withdrawal_queue.getLastFinalizedRequestId() == requests_ids[-1]
    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    assert lastCheckpointIndex == 1

    # post report requests cehck

    hints = contracts.withdrawal_queue.findCheckpointHints(requests_ids, 1, lastCheckpointIndex)
    assert len(hints) == REQUESTS_COUNT

    post_report_statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": holder})
    post_report_claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, hints)

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = post_report_statuses[i]
        assert amountOfStETH == statuses[i][0]  # amountOfShares remains unchanged
        assert amountOfShares == statuses[i][1]  # amountOfShares remains unchanged
        assert owner == holder
        assert isFinalized
        assert not isClaimed
        assert almostEqEth(post_report_claimableEther[i], REQUEST_AMOUNT)
        # single first finalization hint is 1
        assert hints[i] == 1

    # claim
    claim_balance_before = account.balance()
    claim_tx = contracts.withdrawal_queue.claimWithdrawals(requests_ids, hints, {"from": holder})
    assert claim_tx.events.count("WithdrawalClaimed") == REQUESTS_COUNT
    claim_balance_after = account.balance()
    assert almostEqEth(
        claim_balance_after - claim_balance_before + claim_tx.gas_used * claim_tx.gas_price, REQUESTS_SUM
    )

    post_claim_statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": holder})
    post_claim_claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, hints)

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = post_claim_statuses[i]
        assert amountOfStETH == statuses[i][0]  # amountOfShares remains unchanged
        assert amountOfShares == statuses[i][1]  # amountOfShares remains unchanged
        assert owner == holder
        assert isFinalized
        assert isClaimed
        assert almostEqEth(post_report_claimableEther[i], REQUEST_AMOUNT)
        assert post_claim_claimableEther[i] == 0
