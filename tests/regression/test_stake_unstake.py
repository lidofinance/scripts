"""
Tests for lido staking withdrawal flow
"""
import pytest

from eth_abi.abi import encode_single
from brownie import web3, convert, reverts, ZERO_ADDRESS, chain, accounts
from utils.config import contracts

CONSENSUS_VERSION = 1


def encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()


def triggerConsensusOnHash(hash):
    members = contracts.hash_consensus_for_accounting_oracle.getMembers()
    quorum = contracts.hash_consensus_for_accounting_oracle.getQuorum()
    frame = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()

    for i in range(quorum):
        member = accounts.at(members[0][i], force=True)
        contracts.hash_consensus_for_accounting_oracle.submitReport(
            frame["refSlot"], hash, CONSENSUS_VERSION, {"from": member}
        )

def reportOracle(
    num_validators,
    cl_balance,
):
    frame = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    data = encode_calldata(
        "(uint256,uint256,uint256,uint256,uint256[],uint256[],uint256,uint256,uint256,uint256[],uint256,bool,uint256,bytes32,uint256)",
        [
            CONSENSUS_VERSION,
            frame["refSlot"],
            num_validators,
            cl_balance // 10**9,
            [],
            [],
            0,
            0,
            0,
            [],
            0,
            False,
            0,
            b"",
            0,
        ],
    )

    hash = "172ed631ccaddd5ab37609bf0e8a708f064b41a3c5e634dddd26b89c78786ab6"  #web3.keccak(text=data).hex()
    report = (
            CONSENSUS_VERSION,
            frame["refSlot"],
            num_validators,
            cl_balance // 10**9,
            [],
            [],
            0,
            0,
            0,
            [],
            0,
            False,
            0,
            "0x0000000000000000000000000000000000000000000000000000000000000000",
            0
        )

    triggerConsensusOnHash(hash)

    assert contracts.hash_consensus_for_accounting_oracle.getConsensusState()[1] == hash

    members = contracts.hash_consensus_for_accounting_oracle.getMembers()
    member = accounts.at(members[0][0], force=True)

    oracleVersion = contracts.accounting_oracle.getContractVersion()
    contracts.accounting_oracle.submitReportData(report, oracleVersion, {"from": member})
    contracts.accounting_oracle.submitReportExtraDataEmpty({ "from": member })


def test_stake_withdrawal_flow(stranger):
    deposit_amount = 100 * 10**18

    stranger.transfer(contracts.lido, deposit_amount)

    assert contracts.lido.balanceOf(stranger) == deposit_amount - 1

    # prepare new report data
    prev_report = contracts.lido.getBeaconStat().dict()
    beacon_validators = prev_report["beaconValidators"]
    beacon_balance_delta = 10**18
    beacon_balance = prev_report["beaconBalance"] + beacon_balance_delta
    total_ether_before = contracts.lido.totalSupply()

    reportOracle(beacon_validators, beacon_balance)

    assert (
        abs(
            contracts.lido.balanceOf(stranger)
            - deposit_amount * (total_ether_before + 0.9 * beacon_balance_delta) // total_ether_before
        )
        <= 2
    )

    request_amount = contracts.lido.balanceOf(stranger)

    stranger_balance_before = stranger.balance()

    contracts.lido.approve(contracts.withdrawal_queue, request_amount, {"from": stranger})

    contracts.withdrawal_queue.requestWithdrawals([request_amount], stranger, {"from": stranger})

    assert contracts.withdrawal_queue.balanceOf(stranger) == 1

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

    contracts.withdrawal_queue.finalize(
        [1], contracts.lido.getPooledEthByShares(10**27), {"from": contracts.lido, "value": request_amount}
    )

    contracts.withdrawal_queue.claimWithdrawal(1, {"from": stranger})

    assert abs(stranger.balance() - stranger_balance_before - request_amount) <= 2
