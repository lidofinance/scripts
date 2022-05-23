import json
import pytest

from typing import Dict

from brownie import interface, accounts, chain

from scripts.vote_2022_05_17 import update_lido_app, update_nos_app, update_oracle_app, start_vote
from utils.test.snapshot_helpers import dict_zip, dict_diff, try_or_none, assert_no_more_diffs, ValueChanged, \
    assert_expected_diffs
from utils.config import (contracts, network_name,
                          lido_dao_agent_address,
                          lido_dao_steth_address,
                          ldo_token_address,
                          lido_dao_voting_address)


@pytest.fixture(scope="module")
def deployer():
    return accounts[2]


@pytest.fixture(scope="module", autouse=True)
def deployed_contracts(deployer):
    if update_lido_app['new_address'] is None:
        lido_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-lido-base.json'))["data"]
        nos_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-node-operators-registry-base.json'))["data"]
        oracle_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-oracle-base.json'))["data"]
        execution_layer_rewards_vault_tx_data = \
            json.load(open('./utils/txs/tx-26-deploy-execution-layer-rewards-vault.json'))["data"]

        lido_tx = deployer.transfer(data=lido_tx_data)
        nos_tx = deployer.transfer(data=nos_tx_data)
        oracle_tx = deployer.transfer(data=oracle_tx_data)
        execution_layer_rewards_vault_tx = deployer.transfer(data=execution_layer_rewards_vault_tx_data)

        update_lido_app['new_address'] = lido_tx.contract_address
        update_lido_app['execution_layer_rewards_vault_address'] = execution_layer_rewards_vault_tx.contract_address
        update_nos_app['new_address'] = nos_tx.contract_address
        update_oracle_app['new_address'] = oracle_tx.contract_address

        return {
            'lido': lido_tx.contract_address,
            'nos': nos_tx.contract_address,
            'oracle': oracle_tx.contract_address,
            'el_rewards_vault': execution_layer_rewards_vault_tx.contract_address
        }
    else:
        return {  # Hardcode contract addresses here
            'lido': '0xb16876f11324Fbf02b9B294FBE307B3DB0C02DBB',
            'nos': '0xbb001978bD0d5b36D95c54025ac6a5822b2b1Aec',
            'oracle': '0x7FDef26e3bBB8206135071A52e44f8460A243De5',
            'el_rewards_vault': '0x94750381bE1AbA0504C666ee1DB118F68f0780D4'
        } if network_name() in ("goerli", "goerli-fork") else {
            'lido': '',
            'nos': '',
            'oracle': '',
            'el_rewards_vault': ''
        }


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
        'balanceOf(TREASURY)': lido.balanceOf(lido_dao_agent_address),
        'getFeeDistribution()': lido.getFeeDistribution(),
        'getPooledEthByShares(1)': lido.getPooledEthByShares(1),
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
        'sharesOf(TREASURY)': lido.sharesOf(lido_dao_agent_address),
        'getSharesByPooledEth(1)': lido.getSharesByPooledEth(1),

        'allowance(TREASURY, accounts[0])': lido.allowance(lido_dao_agent_address, accounts[0]),
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


def test_getters(ldo_holder, helpers):
    def steps() -> Dict[str, Dict[str, any]]:
        return {'init': snapshot()}

    before: Dict[str, Dict[str, any]] = steps()
    chain.revert()
    execute_vote(ldo_holder, helpers)
    after: Dict[str, Dict[str, any]] = steps()

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    init = step_diffs['init']

    assert_new_methods(init)
    assert_no_more_diffs(init)


def assert_new_methods(diff):
    assert_expected_diffs(diff, {
        'implementation': ValueChanged(from_val='0xC7B5aF82B05Eb3b64F12241B04B2cF14469E39F7',
                                       to_val='0x1596Ff8ED308a83897a731F3C1e814B19E11D68c'),
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
        'getCurrentStakeLimit()': ValueChanged(from_val=None, to_val=150000000000000000000000),
        'getStakeLimitFullInfo()': ValueChanged(
            from_val=None, to_val=(
                False, True, 150000000000000000000000, 150000000000000000000000, 6400, 150000000000000000000000,
                14828618)),
        'isStakingPaused()': ValueChanged(from_val=None, to_val=False),
        'getELRewardsVault()': ValueChanged(from_val=None, to_val='0x98E230B2eE9c99B23D96153E37EA536eBBcBD0f2'),
        'getTotalELRewardsCollected()': ValueChanged(from_val=None, to_val=0),
        'getELRewardsWithdrawalLimit()': ValueChanged(from_val=None, to_val=0),
    })
