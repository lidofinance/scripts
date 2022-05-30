import pytest
import copy

from typing import Dict

from brownie import accounts, chain, Contract

from scripts.archive.vote_2022_05_24 import start_vote
from utils.test.snapshot_helpers import dict_zip, dict_diff, assert_no_more_diffs, ValueChanged
from utils.config import contracts
from utils.node_operators import get_node_operators


@pytest.fixture(scope="module")
def stranger():
    return accounts[0]


@pytest.fixture(scope='module')
def old_fashioned_lido_oracle_report(lido):
    push_beacon = copy.deepcopy(
        list(filter(lambda abi_el: 'name' in abi_el and 'handleOracleReport' in abi_el['name'], lido.abi))
    )
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


def execute_vote(ldo_holder, helpers):
    vote_id = start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=contracts.voting,
        skip_time=3 * 60 * 60 * 24,
    )


def make_snapshot(lido, node_operators_registry) -> Dict[str, any]:
    node_operators = get_node_operators(node_operators_registry)

    snapshot = {}
    for node_operator in node_operators:
        snapshot[node_operator['name']] = lido.balanceOf(node_operator['rewardAddress'])

    return snapshot


def steps(lido, node_operators_registry, lido_oracle_report) -> Dict[str, Dict[str, any]]:
    before_rewards_distribution = make_snapshot(lido, node_operators_registry)

    lido_oracle_report(steth_rebase_mult=1.01)

    after_rewards_distribution = make_snapshot(lido, node_operators_registry)

    lido_oracle_report(steth_rebase_mult=0.99)

    after_negative_rebase_no_rewards = make_snapshot(lido, node_operators_registry)

    return {
        'before_rewards_distribution': before_rewards_distribution,
        'after_rewards_distribution': after_rewards_distribution,
        'after_negative_rebase_no_rewards': after_negative_rebase_no_rewards
    }


def test_rewards_distribution(ldo_holder, lido, node_operators_registry, lido_oracle_report,
                              old_fashioned_lido_oracle_report, helpers):
    before: Dict[str, Dict[str, any]] = steps(lido, node_operators_registry, old_fashioned_lido_oracle_report)
    chain.revert()
    execute_vote(ldo_holder, helpers)
    after: Dict[str, Dict[str, any]] = steps(lido, node_operators_registry, lido_oracle_report)

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    assert_no_more_diffs('before_rewards_distribution', step_diffs['before_rewards_distribution'])
    assert_no_more_diffs('after_rewards_distribution', step_diffs['after_rewards_distribution'])
    assert_no_more_diffs('after_negative_rebase_no_rewards', step_diffs['after_negative_rebase_no_rewards'])
