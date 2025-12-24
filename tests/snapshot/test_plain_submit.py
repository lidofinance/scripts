import pytest

from typing import Dict

from brownie import accounts, chain, ZERO_ADDRESS

from utils.test.snapshot_helpers import (
    dict_zip,
    dict_diff,
    assert_no_diffs,
    ValueChanged,
)
from utils.config import (
    contracts,
    AGENT,
    LIDO,
    LDO_TOKEN,
    VOTING,
)
from utils.test.helpers import ONE_ETH
from utils.test.governance_helpers import execute_vote_and_process_dg_proposals


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
        "allowRecoverability(StETH)": lido.allowRecoverability(LIDO),
        "appId": lido.appId(),
        "getInitializationBlock()": lido.getInitializationBlock(),
        "symbol": lido.symbol(),
        "getEVMScriptRegistry": lido.getEVMScriptRegistry(),
        "getBeaconStat()": lido.getBeaconStat(),
        "getFee()": lido.getFee(),
        "kernel": lido.kernel(),
        "getTotalShares()": lido.getTotalShares(),
        "isPetrified()": lido.isPetrified(),
        "getSharesByPooledEth(1 ETH)": lido.getSharesByPooledEth(10**18),
        "allowance(accounts[0], TREASURY)": lido.allowance(accounts[0], AGENT),
        "balanceOf(TREASURY)": lido.balanceOf(AGENT),
        "sharesOf(TREASURY)": lido.sharesOf(AGENT),
        "allowance(accounts[0], VOTING)": lido.allowance(accounts[0], VOTING),
        "balanceOf(accounts[0])": lido.balanceOf(accounts[0]),
        "sharesOf(accounts[0])": lido.sharesOf(accounts[0]),
        "canPerform()": lido.canPerform(VOTING, lido.PAUSE_ROLE(), []),
        "getEVMScriptExecutor()": lido.getEVMScriptExecutor(f"0x{str(1).zfill(8)}"),
        "STAKING_CONTROL_ROLE": lido.STAKING_CONTROL_ROLE(),
        "RESUME_ROLE": lido.RESUME_ROLE(),
        "isStakingPaused()": lido.isStakingPaused(),
        "STAKING_PAUSE_ROLE": lido.STAKING_PAUSE_ROLE(),
        "getTotalELRewardsCollected()": lido.getTotalELRewardsCollected(),
    }


def test_submit_snapshot(helpers, staker, vote_ids_from_env, dg_proposal_ids_from_env):
    def steps() -> Dict[str, Dict[str, any]]:
        track = {"init": snapshot()}
        contracts.lido.submit(ZERO_ADDRESS, {"from": staker, "amount": ONE_ETH})
        track["submit"] = snapshot()
        return track

    before: Dict[str, Dict[str, any]] = steps()
    chain.revert()

    execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env)

    after: Dict[str, Dict[str, any]] = steps()
    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    expected_diffs = {
    }

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

        for key in expected_diffs:
            if key in step_diffs[step] and step_diffs[step][key] == expected_diffs[key]:
                del step_diffs[step][key]

    for step_name, diff in step_diffs.items():
        assert_no_diffs(step_name, diff)
