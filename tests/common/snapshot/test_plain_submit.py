import pytest

from typing import Dict

from brownie import interface, accounts, chain, ZERO_ADDRESS

from utils.test.snapshot_helpers import (
    dict_zip, dict_diff, try_or_none,
    assert_no_diffs, ValueChanged,
    assert_expected_diffs
)
from utils.config import (
    contracts,
    lido_dao_agent_address,
    lido_dao_steth_address,
    ldo_token_address,
    lido_dao_voting_address
)
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


@pytest.fixture(scope="module")
def staker():
    return accounts[0]


def execute_vote(ldo_holder, helpers):
    vote_id = start_and_execute_votes({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=contracts.voting,
        skip_time=3 * 60 * 60 * 24,
    )


def snapshot() -> Dict[str, any]:
    lido = contracts.lido
    oracle = contracts.lido_oracle
    self_owned_steth_burner = contracts.self_owned_steth_burner
    composite_receiver = contracts.composite_post_rebase_beacon_receiver

    return {
        'address': lido.address,
        'implementation': interface.AppProxyUpgradeable(lido.address).implementation(),

        'name': lido.name(),
        'hasInitialized()': lido.hasInitialized(),
        'PAUSE_ROLE': lido.PAUSE_ROLE(),
        'DEPOSIT_ROLE': lido.DEPOSIT_ROLE(),
        'DEPOSIT_SIZE': lido.DEPOSIT_SIZE(),
        'MANAGE_WITHDRAWAL_KEY': lido.MANAGE_WITHDRAWAL_KEY(),
        'getInsuranceFund()': lido.getInsuranceFund(),
        'totalSupply': lido.totalSupply(),
        'getOperators()': lido.getOperators(),
        'decimals': lido.decimals(),
        'getRecoveryVault()': lido.getRecoveryVault(),
        'getTotalPooledEther()': lido.getTotalPooledEther(),
        'getTreasury()': lido.getTreasury(),
        'isStopped()': lido.isStopped(),
        'getBufferedEther()': lido.getBufferedEther(),
        'SIGNATURE_LENGTH()': lido.SIGNATURE_LENGTH(),
        'getWithdrawalCredentials()': lido.getWithdrawalCredentials(),
        'getFeeDistribution()': lido.getFeeDistribution(),
        'getPooledEthByShares(100)': lido.getPooledEthByShares(100),
        'allowRecoverability(LDO)': lido.allowRecoverability(ldo_token_address),
        'allowRecoverability(StETH)': lido.allowRecoverability(lido_dao_steth_address),
        'MANAGE_FEE': lido.MANAGE_FEE(),
        'appId': lido.appId(),
        'getOracle()': lido.getOracle(),
        'getInitializationBlock()': lido.getInitializationBlock(),
        'symbol': lido.symbol(),
        'WITHDRAWAL_CREDENTIALS_LENGTH': lido.WITHDRAWAL_CREDENTIALS_LENGTH(),
        'getEVMScriptRegistry': lido.getEVMScriptRegistry(),
        'PUBKEY_LENGTH': lido.PUBKEY_LENGTH(),
        'getDepositContract()': lido.getDepositContract(),
        'getBeaconStat()': lido.getBeaconStat(),
        'BURN_ROLE': lido.BURN_ROLE(),
        'getFee()': lido.getFee(),
        'kernel': lido.kernel(),
        'getTotalShares()': lido.getTotalShares(),
        'isPetrified()': lido.isPetrified(),
        'getSharesByPooledEth(1 ETH)': lido.getSharesByPooledEth(10 ** 18),

        'allowance(accounts[0], TREASURY)': lido.allowance(accounts[0], lido_dao_agent_address),
        'balanceOf(TREASURY)': lido.balanceOf(lido_dao_agent_address),
        'sharesOf(TREASURY)': lido.sharesOf(lido_dao_agent_address),

        'allowance(accounts[0], VOTING)': lido.allowance(accounts[0], lido_dao_voting_address),
        'balanceOf(accounts[0])': lido.balanceOf(accounts[0]),
        'sharesOf(accounts[0])': lido.sharesOf(accounts[0]),

        'canPerform()': lido.canPerform(lido_dao_voting_address, lido.PAUSE_ROLE(), []),
        'getEVMScriptExecutor()': lido.getEVMScriptExecutor(f'0x{str(1).zfill(8)}'),

        'STAKING_CONTROL_ROLE': lido.STAKING_CONTROL_ROLE(),
        'RESUME_ROLE': lido.RESUME_ROLE(),
        'isStakingPaused()': lido.isStakingPaused(),
        'getELRewardsWithdrawalLimit()': lido.getELRewardsWithdrawalLimit(),
        'SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE': lido.SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE(),
        'getELRewardsVault()': lido.getELRewardsVault(),
        'MANAGE_PROTOCOL_CONTRACTS_ROLE': lido.MANAGE_PROTOCOL_CONTRACTS_ROLE(),
        'SET_EL_REWARDS_VAULT_ROLE': lido.SET_EL_REWARDS_VAULT_ROLE(),
        'STAKING_PAUSE_ROLE': lido.STAKING_PAUSE_ROLE(),
        'getTotalELRewardsCollected()': lido.getTotalELRewardsCollected(),

        'getBeaconReportReceiver()': oracle.getBeaconReportReceiver(),
        'callbacksLength()':  composite_receiver.callbacksLength(),
        'callbacks(0)': try_or_none(lambda: composite_receiver.callbacks(0)),
        'getCoverSharesBurnt': self_owned_steth_burner.getCoverSharesBurnt(),
        'getNonCoverSharesBurnt': self_owned_steth_burner.getNonCoverSharesBurnt(),
        'getBurnAmountPerRunQuota': self_owned_steth_burner.getBurnAmountPerRunQuota(),
        'getExcessStETH': self_owned_steth_burner.getExcessStETH()
    }


def test_submit_snapshot(ldo_holder, helpers, lido, staker, dao_voting):
    if not is_there_any_vote_scripts():
        pytest.skip('No vote scripts')

    ether = 10 ** 18

    def steps() -> Dict[str, Dict[str, any]]:
        track = {'init': snapshot()}
        lido.submit(ZERO_ADDRESS, {'from': staker, 'amount': ether})
        track['submit'] = snapshot()
        return track

    before: Dict[str, Dict[str, any]] = steps()
    chain.revert()
    start_and_execute_votes(dao_voting, helpers)
    after: Dict[str, Dict[str, any]] = steps()

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    for step_name, diff in step_diffs.items():
        assert_new_state(step_name, diff)
        assert_no_diffs(step_name, diff)


def assert_new_state(step, diff):
    assert_expected_diffs(step, diff, {
    })
