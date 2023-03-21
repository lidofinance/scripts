"""
Tests for lido staking withdrawal flow
"""
import pytest

from brownie import web3, convert, reverts, ZERO_ADDRESS, chain
from utils.config import contracts


def test_stake_withdrawal_flow(stranger):
    deposit_amount = 100 * 10**18

    stranger.transfer(contracts.lido, deposit_amount)

    assert contracts.lido.balanceOf(stranger) == deposit_amount - 1

    # prepare new report data
    prev_report = contracts.lido.getBeaconStat().dict()
    beacon_validators = prev_report["beaconValidators"]
    beacon_balance_delta = 10 ** 18
    beacon_balance = prev_report["beaconBalance"] + beacon_balance_delta
    total_ether_before = contracts.lido.totalSupply()

    tx = contracts.lido.handleOracleReport(
        chain.time(),
        0,
        beacon_validators,
        beacon_balance,
        0,
        0,
        0,
        [],
        0,
        {"from": contracts.accounting_oracle},
    )

    assert contracts.lido.balanceOf(stranger) == deposit_amount * (total_ether_before + 0.9 * beacon_balance_delta) // total_ether_before

    request_amount = contracts.lido.balanceOf(stranger)

    stranger_balance_before = stranger.balance()

    contracts.lido.approve(contracts.withdrawal_queue, request_amount, { "from": stranger })

    contracts.withdrawal_queue.requestWithdrawals([request_amount], stranger, {"from": stranger})

    assert contracts.withdrawal_queue.balanceOf(stranger) == 1

    contracts.withdrawal_queue.finalize([1], contracts.lido.getPooledEthByShares(10**27), {"from": contracts.lido, "value": request_amount})

    contracts.withdrawal_queue.claimWithdrawal(1, {"from": stranger })

    assert stranger.balance() == stranger_balance_before + request_amount - 1
