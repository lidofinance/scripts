import pytest

from typing import Dict

from brownie import accounts, chain

from utils.test.snapshot_helpers import dict_zip, dict_diff, assert_no_diffs, ValueChanged
from utils.config import contracts
from utils.node_operators import get_node_operators
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


@pytest.fixture(scope="module")
def stranger():
    return accounts[0]


@pytest.fixture(scope='module')
def lido_oracle_report(lido):
    lido_oracle = accounts.at(lido.getOracle(), force=True)
    dao_voting = accounts.at(contracts.voting.address, force=True)

    def report_beacon_state(steth_rebase_factor):
        lido.setFee(0, {'from': dao_voting})
        (_, beacon_validators, beacon_balance) = lido.getBeaconStat()
        total_supply = lido.totalSupply()
        total_supply_inc = (steth_rebase_factor - 1) * total_supply
        beacon_balance += total_supply_inc
        assert beacon_balance > 0
        lido.handleOracleReport(beacon_validators, beacon_balance, {'from': lido_oracle})

    return report_beacon_state


def make_snapshot(lido, node_operators_registry) -> Dict[str, any]:
    node_operators = get_node_operators(node_operators_registry)

    snapshot = {}
    for node_operator in node_operators:
        snapshot[node_operator['name']] = lido.balanceOf(node_operator['rewardAddress'])

    return snapshot


def steps(lido, node_operators_registry, lido_oracle_report) -> Dict[str, Dict[str, any]]:
    before_rewards_distribution = make_snapshot(lido, node_operators_registry)

    lido_oracle_report(steth_rebase_factor=1.01)
    after_rewards_distribution = make_snapshot(lido, node_operators_registry)

    lido_oracle_report(steth_rebase_factor=0.99)
    after_negative_rebase_no_rewards = make_snapshot(lido, node_operators_registry)

    return {
        'before_rewards_distribution': before_rewards_distribution,
        'after_rewards_distribution': after_rewards_distribution,
        'after_negative_rebase_no_rewards': after_negative_rebase_no_rewards
    }


def test_rewards_distribution(dao_voting, lido, node_operators_registry, lido_oracle_report, helpers):
    if not is_there_any_vote_scripts():
        pytest.skip('No vote scripts')

    before: Dict[str, Dict[str, any]] = steps(lido, node_operators_registry, lido_oracle_report)
    chain.revert()
    start_and_execute_votes(dao_voting, helpers)
    after: Dict[str, Dict[str, any]] = steps(lido, node_operators_registry, lido_oracle_report)

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    assert_no_diffs('before_rewards_distribution', step_diffs['before_rewards_distribution'])
    assert_no_diffs('after_rewards_distribution', step_diffs['after_rewards_distribution'])
    assert_no_diffs('after_negative_rebase_no_rewards', step_diffs['after_negative_rebase_no_rewards'])


def test_rewards_distribution_with_el_rewards(
    dao_voting, lido, node_operators_registry, lido_oracle_report, helpers, stranger,
    execution_layer_rewards_vault
):
    if not is_there_any_vote_scripts():
        pytest.skip('No vote scripts')

    stranger.transfer(execution_layer_rewards_vault.address, '1 ether')
    before: Dict[str, Dict[str, any]] = steps(lido, node_operators_registry, lido_oracle_report)

    chain.revert()
    start_and_execute_votes(dao_voting, helpers)

    stranger.transfer(execution_layer_rewards_vault.address, '1 ether')
    assert execution_layer_rewards_vault.balance() == '1 ether'
    after: Dict[str, Dict[str, any]] = steps(lido, node_operators_registry, lido_oracle_report)

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    assert_no_diffs('before_rewards_distribution', step_diffs['before_rewards_distribution'])

    for _, value_change in step_diffs['after_rewards_distribution'].items():
        assert value_change.to_val > value_change.from_val
