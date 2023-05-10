import pytest

from typing import Dict

from brownie import interface, accounts, chain, ZERO_ADDRESS

from utils.test.snapshot_helpers import (
    dict_zip,
    dict_diff,
    assert_no_diffs,
    assert_expected_diffs,
    ValueChanged,
)
from utils.config import (
    contracts,
    lido_dao_agent_address,
    lido_dao_steth_address,
    ldo_token_address,
    lido_dao_voting_address,
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
        "allowRecoverability(LDO)": lido.allowRecoverability(ldo_token_address),
        "allowRecoverability(StETH)": lido.allowRecoverability(lido_dao_steth_address),
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
        "allowance(accounts[0], TREASURY)": lido.allowance(accounts[0], lido_dao_agent_address),
        "balanceOf(TREASURY)": lido.balanceOf(lido_dao_agent_address),
        "sharesOf(TREASURY)": lido.sharesOf(lido_dao_agent_address),
        "allowance(accounts[0], VOTING)": lido.allowance(accounts[0], lido_dao_voting_address),
        "balanceOf(accounts[0])": lido.balanceOf(accounts[0]),
        "sharesOf(accounts[0])": lido.sharesOf(accounts[0]),
        "canPerform()": lido.canPerform(lido_dao_voting_address, lido.PAUSE_ROLE(), []),
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

    lido = contracts.lido
    shares_of_treasury_before = lido.sharesOf(lido_dao_agent_address)
    balance_treasury_before = lido.balanceOf(lido_dao_agent_address)
    shares_of_treasury_after = shares_of_treasury_before - lido.getSharesByPooledEth(50 * (10**18))
    balance_treasury_after = lido.getPooledEthByShares(shares_of_treasury_after)

    before: Dict[str, Dict[str, any]] = steps()
    chain.revert()
    start_and_execute_votes(contracts.voting, helpers)
    after: Dict[str, Dict[str, any]] = steps()

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    for step_name, diff in step_diffs.items():
        assert_expected_diffs(
            step_name, diff, {
                "sharesOf(TREASURY)": ValueChanged(
                    from_val=shares_of_treasury_before, to_val=shares_of_treasury_after
                ),
                "balanceOf(TREASURY)": ValueChanged(
                    from_val=balance_treasury_before,
                    to_val=balance_treasury_after
                )
            }
        )
        assert_no_diffs(step_name, diff)
