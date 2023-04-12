import pytest
from brownie import interface  # type: ignore

from utils.config import (
    contracts,
    lido_dao_hash_consensus_for_accounting_oracle,
    lido_dao_accounting_oracle_implementation,
    lido_dao_accounting_oracle,
    oracle_committee,
)


def ETH(amount):
    return amount * 10**18


@pytest.fixture(scope="module")
def holder(accounts):
    whale = "0x41318419CFa25396b47A94896FfA2C77c6434040"
    contracts.lido.transfer(accounts[0], ETH(101), {"from": whale})
    return accounts[0]


def steth_balance(account):
    return contracts.lido.balanceOf(account)


def almostEqEth(b1, b2):
    return abs(b1 - b2) < 10


def test_withdraw(holder):
    # approve
    contracts.lido.approve(contracts.withdrawal_queue.address, ETH(100), {"from": holder})

    # request
    balance_before = steth_balance(holder)
    request_tx = contracts.withdrawal_queue.requestWithdrawals([ETH(1) for _ in range(10)], holder, {"from": holder})
    balance_after = steth_balance(holder)
    # post request checks
    assert almostEqEth(balance_before - balance_after, ETH(10))
    assert request_tx.events.count("WithdrawalRequested") == 10

    # check each request
    requests_ids = contracts.withdrawal_queue.getWithdrawalRequests(holder, {"from": holder})
    statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": holder})
    claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, [0 for _ in requests_ids])
    assert len(requests_ids) == 10
    assert len(statuses) == 10

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = statuses[i]
        assert almostEqEth(amountOfStETH, ETH(1))
        assert almostEqEth(amountOfShares, contracts.lido.getSharesByPooledEth(amountOfStETH))
        assert owner == holder
        assert not isFinalized
        assert not isClaimed
        assert claimableEther[i] == 0
