import pytest

from typing import Dict

from brownie import interface, accounts, chain, ZERO_ADDRESS

from archive.scripts.vote_2022_05_24 import start_vote
from utils.test.snapshot_helpers import dict_zip, dict_diff, try_or_none, assert_no_diffs, ValueChanged, \
    assert_expected_diffs
from utils.config import (contracts,
                          lido_dao_agent_address,
                          lido_dao_steth_address,
                          ldo_token_address,
                          lido_dao_voting_address)


@pytest.fixture(scope="module")
def staker():
    return accounts[0]


def execute_vote(ldo_holder, helpers):
    vote_id = start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=contracts.voting,
        skip_time=3 * 60 * 60 * 24,
    )


def snapshot() -> Dict[str, any]:
    lido = contracts.lido

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

        # New getters
        'STAKING_CONTROL_ROLE': try_or_none(lambda: lido.STAKING_CONTROL_ROLE()),
        'RESUME_ROLE': try_or_none(lambda: lido.RESUME_ROLE()),
        'isStakingPaused()': try_or_none(lambda: lido.isStakingPaused()),
        'getELRewardsWithdrawalLimit()': try_or_none(lambda: lido.getELRewardsWithdrawalLimit()),
        'getCurrentStakeLimit()': try_or_none(lambda: lido.getCurrentStakeLimit()),
        'getStakeLimitFullInfo()': try_or_none(lambda: lido.getStakeLimitFullInfo()),
        'SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE': try_or_none(lambda: lido.SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE()),
        'getELRewardsVault()': try_or_none(lambda: lido.getELRewardsVault()),
        'MANAGE_PROTOCOL_CONTRACTS_ROLE': try_or_none(lambda: lido.MANAGE_PROTOCOL_CONTRACTS_ROLE()),
        'SET_EL_REWARDS_VAULT_ROLE': try_or_none(lambda: lido.SET_EL_REWARDS_VAULT_ROLE()),
        'STAKING_PAUSE_ROLE': try_or_none(lambda: lido.STAKING_PAUSE_ROLE()),
        'getTotalELRewardsCollected()': try_or_none(lambda: lido.getTotalELRewardsCollected()),
    }


def test_submit(ldo_holder, helpers, lido, staker):
    ether = 10 ** 18
    stake_limit = 150_000 * 10 ** 18
    height = chain.height

    def steps() -> Dict[str, Dict[str, any]]:
        track = {'init': snapshot()}
        lido.submit(ZERO_ADDRESS, {'from': staker, 'amount': ether})
        track['submit'] = snapshot()
        return track

    before: Dict[str, Dict[str, any]] = steps()
    chain.revert()
    execute_vote(ldo_holder, helpers)
    after: Dict[str, Dict[str, any]] = steps()

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    step = 'init'
    assert_stake_limit(step, step_diffs[step], stake_limit, height)

    step = 'submit'
    assert_stake_limit(step, step_diffs[step], stake_limit - ether, height + 1)

    for step_name, diff in step_diffs.items():
        assert_new_static_methods(step_name, diff)
        assert_no_diffs(step_name, diff)


def assert_new_static_methods(step, diff):
    assert_expected_diffs(step, diff, {
        'implementation': ValueChanged(
            from_val='0xC7B5aF82B05Eb3b64F12241B04B2cF14469E39F7',
            to_val='0x47EbaB13B806773ec2A2d16873e2dF770D130b50'
        ),
        'RESUME_ROLE': ValueChanged(
            from_val=None,
            to_val='0x2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7'
        ),
        'MANAGE_PROTOCOL_CONTRACTS_ROLE': ValueChanged(
            from_val=None,
            to_val='0xeb7bfce47948ec1179e2358171d5ee7c821994c911519349b95313b685109031'
        ),
        'SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE': ValueChanged(
            from_val=None,
            to_val='0xca7d176c2da2028ed06be7e3b9457e6419ae0744dc311989e9b29f6a1ceb1003'
        ),
        'STAKING_PAUSE_ROLE': ValueChanged(
            from_val=None,
            to_val='0x84ea57490227bc2be925c684e2a367071d69890b629590198f4125a018eb1de8'
        ),
        'SET_EL_REWARDS_VAULT_ROLE': ValueChanged(
            from_val=None,
            to_val='0x9d68ad53a92b6f44b2e8fb18d211bf8ccb1114f6fafd56aa364515dfdf23c44f'
        ),
        'STAKING_CONTROL_ROLE': ValueChanged(
            from_val=None,
            to_val='0xa42eee1333c0758ba72be38e728b6dadb32ea767de5b4ddbaea1dae85b1b051f'
        ),
        'isStakingPaused()': ValueChanged(from_val=None, to_val=False),
        'getELRewardsVault()': ValueChanged(from_val=None, to_val='0x388C818CA8B9251b393131C08a736A67ccB19297'),
        'getTotalELRewardsCollected()': ValueChanged(from_val=None, to_val=0),
        'getELRewardsWithdrawalLimit()': ValueChanged(from_val=None, to_val=0),
    })


def assert_stake_limit(step, diff, current_stake_limit, block_number):
    assert_expected_diffs(step, diff,
                          {'getCurrentStakeLimit()': ValueChanged(from_val=None, to_val=current_stake_limit)})

    assert diff.get('getStakeLimitFullInfo()') is not None
    full_info_diff = diff['getStakeLimitFullInfo()']
    assert full_info_diff.from_val is None
    new_full_info = full_info_diff.to_val
    assert new_full_info[0] is False
    assert new_full_info[1] is True
    assert new_full_info[2] == current_stake_limit
    assert new_full_info[3] == 150_000 * 10**18
    assert new_full_info[4] == 6400
    assert new_full_info[5] == current_stake_limit
    assert new_full_info[6] > block_number

    del diff['getStakeLimitFullInfo()']
