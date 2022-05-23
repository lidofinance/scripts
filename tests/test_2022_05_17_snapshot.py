import json
import pytest

from typing import Dict, List

from brownie import interface, accounts, chain

from scripts.vote_2022_05_17 import update_lido_app, update_nos_app, update_oracle_app, start_vote
from utils.test.snapshot_helpers import dict_zip, dict_diff
from utils.config import contracts, network_name


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
        'implementation': interface.AppProxyUpgradeable(lido.address).implementation()
    }


def steps() -> Dict[str, Dict[str, any]]:
    lido = contracts.lido
    interface.AppProxyUpgradeable(lido.address).implementation()
    return {'init': snapshot()}


def test_smoke(ldo_holder, helpers):
    before: Dict[str, Dict[str, any]] = steps()
    chain.revert()

    execute_vote(ldo_holder, helpers)

    after: Dict[str, Dict[str, any]] = steps()

    step_diffs = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    init = step_diffs['init']

    assert init['implementation'] is not None
