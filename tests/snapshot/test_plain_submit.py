import pytest

from typing import Any, Dict

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

SNAPSHOT_ABS_TOLERANCES: dict[str, int] = {
    # Conversion between shares and pooled ETH rounds down. A small share-rate
    # change may therefore shift this view by one or two wei.
    "getPooledEthByShares(100)": 2,
}


IGNORED_SNAPSHOT_KEYS = {
    # Lido v4 finalization requires an AccountingOracle report. The report rebases
    # stETH and v4 changes CL-accounting representation, so these values cannot be
    # compared directly between the pre- and post-upgrade scenarios.
    "totalSupply",
    "getTotalPooledEther()",
    "getBufferedEther()",
    "getBeaconStat()",
    "getTotalShares()",
    "getSharesByPooledEth(1 ETH)",
    "getTotalELRewardsCollected()",
    "balanceOf(TREASURY)",
    "sharesOf(TREASURY)",
    "balanceOf(accounts[0])",
    "sharesOf(accounts[0])",
}


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


def _within_snapshot_tolerance(key: str, before: Any, after: Any) -> bool:
    tolerance = SNAPSHOT_ABS_TOLERANCES.get(key)
    if tolerance is None or not isinstance(before, int) or not isinstance(after, int):
        return False
    return abs(before - after) <= tolerance


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

    expected_diffs = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

        for key in expected_diffs:
            if key in step_diffs[step] and step_diffs[step][key] == expected_diffs[key]:
                del step_diffs[step][key]

        for key in IGNORED_SNAPSHOT_KEYS:
            step_diffs[step].pop(key, None)

        for key, change in tuple(step_diffs[step].items()):
            if _within_snapshot_tolerance(key, change.from_val, change.to_val):
                del step_diffs[step][key]

    for step_name, diff in step_diffs.items():
        assert_no_diffs(step_name, diff)
