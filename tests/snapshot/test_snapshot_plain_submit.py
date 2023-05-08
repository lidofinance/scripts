import pytest

from typing import Dict

from brownie import interface, accounts, chain, ZERO_ADDRESS

from utils.test.snapshot_helpers import (
    dict_zip,
    dict_diff,
    assert_no_diffs,
    ValueChanged,
)
from utils.config import (
    contracts,
    LIDO_AGENT,
    LIDO_LIDO,
    LDO_TOKEN,
    LIDO_VOTING,
)
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from utils.test.helpers import ONE_ETH


@pytest.fixture(scope="module")
def staker():
    return accounts[0]


def snapshot() -> Dict[str, any]:
    lido = contracts.lido

    return {
        "address": lido.address,
        "name": lido.name(),
        "hasInitialized()": lido.hasInitialized(),
        "PAUSE_ROLE": lido.PAUSE_ROLE(),
        "totalSupply": lido.totalSupply(),
        "decimals": lido.decimals(),
        "getRecoveryVault()": lido.getRecoveryVault(),
        "getTotalPooledEther()": lido.getTotalPooledEther(),
        "getTreasury()": lido.getTreasury(),
        "isStopped()": lido.isStopped(),
        "getBufferedEther()": lido.getBufferedEther(),
        "getPooledEthByShares(100)": lido.getPooledEthByShares(100),
        "allowRecoverability(LDO)": lido.allowRecoverability(LDO_TOKEN),
        "allowRecoverability(StETH)": lido.allowRecoverability(LIDO_LIDO),
        "appId": lido.appId(),
        "getOracle()": lido.getOracle(),
        "getInitializationBlock()": lido.getInitializationBlock(),
        "symbol": lido.symbol(),
        "getEVMScriptRegistry": lido.getEVMScriptRegistry(),
        "getBeaconStat()": lido.getBeaconStat(),
        "getFee()": lido.getFee(),
        "kernel": lido.kernel(),
        "getTotalShares()": lido.getTotalShares(),
        "isPetrified()": lido.isPetrified(),
        "getSharesByPooledEth(1 ETH)": lido.getSharesByPooledEth(10**18),
        "allowance(accounts[0], TREASURY)": lido.allowance(accounts[0], LIDO_AGENT),
        "balanceOf(TREASURY)": lido.balanceOf(LIDO_AGENT),
        "sharesOf(TREASURY)": lido.sharesOf(LIDO_AGENT),
        "allowance(accounts[0], VOTING)": lido.allowance(accounts[0], LIDO_VOTING),
        "balanceOf(accounts[0])": lido.balanceOf(accounts[0]),
        "sharesOf(accounts[0])": lido.sharesOf(accounts[0]),
        "canPerform()": lido.canPerform(LIDO_VOTING, lido.PAUSE_ROLE(), []),
        "getEVMScriptExecutor()": lido.getEVMScriptExecutor(f"0x{str(1).zfill(8)}"),
        "STAKING_CONTROL_ROLE": lido.STAKING_CONTROL_ROLE(),
        "RESUME_ROLE": lido.RESUME_ROLE(),
        "isStakingPaused()": lido.isStakingPaused(),
        "STAKING_PAUSE_ROLE": lido.STAKING_PAUSE_ROLE(),
        "getTotalELRewardsCollected()": lido.getTotalELRewardsCollected(),
    }


@pytest.mark.skipif(condition=not is_there_any_vote_scripts(), reason="No votes")
def test_submit_snapshot(helpers, staker):
    def steps() -> Dict[str, Dict[str, any]]:
        track = {"init": snapshot()}
        contracts.lido.submit(ZERO_ADDRESS, {"from": staker, "amount": ONE_ETH})
        track["submit"] = snapshot()
        return track

    before: Dict[str, Dict[str, any]] = steps()
    chain.revert()
    start_and_execute_votes(contracts.voting, helpers)
    after: Dict[str, Dict[str, any]] = steps()

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    for step_name, diff in step_diffs.items():
        assert_no_diffs(step_name, diff)
