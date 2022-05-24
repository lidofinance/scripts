import json
import pytest

from typing import Dict

from brownie import accounts, chain, Contract, ZERO_ADDRESS, Wei

from scripts.vote_2022_05_17 import update_lido_app, update_nos_app, update_oracle_app, start_vote
from utils.test.snapshot_helpers import dict_zip, dict_diff, assert_no_more_diffs, ValueChanged
from utils.config import contracts, network_name


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def deployer():
    return accounts[2]


@pytest.fixture(scope='module')
def old_fashioned_lido_oracle_report(lido):
    push_beacon = list(filter(lambda abi_el: 'name' in abi_el and 'handleOracleReport' in abi_el['name'], lido.abi))
    push_beacon[0]['name'] = 'pushBeacon'
    old_fashioned_lido = Contract.from_abi("Old-Fashioned Lido", lido.address, lido.abi + push_beacon)

    lido_oracle = accounts.at(lido.getOracle(), force=True)
    dao_voting = accounts.at(contracts.voting.address, force=True)

    def report_beacon_state(steth_rebase_mult):
        lido.setFee(0, {'from': dao_voting})
        (deposited_validators, beacon_validators, beacon_balance) = lido.getBeaconStat()
        total_supply = lido.totalSupply()
        total_supply_inc = (steth_rebase_mult - 1) * total_supply
        beacon_balance += total_supply_inc
        assert beacon_balance > 0
        old_fashioned_lido.pushBeacon(beacon_validators, beacon_balance, {'from': lido_oracle})
    return report_beacon_state


@pytest.fixture(scope='module')
def lido_oracle_report(lido):
    lido_oracle = accounts.at(lido.getOracle(), force=True)
    dao_voting = accounts.at(contracts.voting.address, force=True)

    def report_beacon_state(steth_rebase_mult):
        lido.setFee(0, {'from': dao_voting})
        (deposited_validators, beacon_validators, beacon_balance) = lido.getBeaconStat()
        total_supply = lido.totalSupply()
        total_supply_inc = (steth_rebase_mult - 1) * total_supply
        beacon_balance += total_supply_inc
        assert beacon_balance > 0
        lido.handleOracleReport(beacon_validators, beacon_balance, {'from': lido_oracle})
    return report_beacon_state


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


def make_snapshot(stranger, lido) -> Dict[str, any]:
    curve_pool = '0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'

    _, beacon_validators, beacon_balance = lido.getBeaconStat()

    return {
        'stranger.steth_balance': lido.balanceOf(stranger),
        'stranger.steth_shares': lido.sharesOf(stranger),

        'curve_pool.steth_balance': lido.balanceOf(curve_pool),
        'curve_pool.steth_shares': lido.sharesOf(curve_pool),

        'steth.total_supply': lido.totalSupply(),
        'steth.total_sthares': lido.getTotalShares(),

        'lido.beacon_validators': beacon_validators,
        'lido.beacon_balance': beacon_balance
    }


def steps(stranger, lido, lido_oracle_report) -> Dict[str, Dict[str, any]]:
    before_deposit = make_snapshot(stranger, lido)

    lido.submit(ZERO_ADDRESS, {'from': stranger, 'value': Wei('50 ether')})

    after_deposit = make_snapshot(stranger, lido)

    lido_oracle_report(steth_rebase_mult=1.01)

    after_rebase = make_snapshot(stranger, lido)

    return {
        'before_deposit': before_deposit,
        'after_deposit': after_deposit,
        'after_rebase': after_rebase
    }


def test_deposit_rebase(ldo_holder, stranger, lido, lido_oracle_report, old_fashioned_lido_oracle_report, helpers):
    before: Dict[str, Dict[str, any]] = steps(stranger, lido, old_fashioned_lido_oracle_report)
    chain.revert()
    execute_vote(ldo_holder, helpers)
    after: Dict[str, Dict[str, any]] = steps(stranger, lido, lido_oracle_report)

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    assert_no_more_diffs('before_deposit',step_diffs['before_deposit'])
    assert_no_more_diffs('after_deposit', step_diffs['after_deposit'])
    assert_no_more_diffs('after_rebase', step_diffs['after_rebase'])

