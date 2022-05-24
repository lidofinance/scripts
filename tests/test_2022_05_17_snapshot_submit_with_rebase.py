import pytest
import copy

from typing import Dict

from brownie import accounts, chain, Contract, ZERO_ADDRESS, Wei

from scripts.vote_2022_05_17 import start_vote
from utils.test.snapshot_helpers import dict_zip, dict_diff, assert_no_more_diffs, ValueChanged
from utils.config import contracts


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def deployer():
    return accounts[2]


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
    before_submit = make_snapshot(stranger, lido)

    lido.submit(ZERO_ADDRESS, {'from': stranger, 'value': Wei('50 ether')})

    after_submit = make_snapshot(stranger, lido)

    lido_oracle_report(steth_rebase_mult=1.01)

    after_positive_rebase = make_snapshot(stranger, lido)

    lido_oracle_report(steth_rebase_mult=0.99)

    after_negative_rebase = make_snapshot(stranger, lido)

    lido.submit(ZERO_ADDRESS, {'from': stranger, 'value': Wei('10 ether')})

    after_last_submit = make_snapshot(stranger, lido)

    return {
        'before_submit': before_submit,
        'after_submit': after_submit,
        'after_positive_rebase': after_positive_rebase,
        'after_negative_rebase': after_negative_rebase,
        'after_last_submit': after_last_submit
    }


def test_submit_rebase(ldo_holder, stranger, lido, lido_oracle_report, old_fashioned_lido_oracle_report, helpers):
    before: Dict[str, Dict[str, any]] = steps(stranger, lido, old_fashioned_lido_oracle_report)
    chain.revert()
    execute_vote(ldo_holder, helpers)
    after: Dict[str, Dict[str, any]] = steps(stranger, lido, lido_oracle_report)

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    assert_no_more_diffs('before_submit',step_diffs['before_submit'])
    assert_no_more_diffs('after_submit', step_diffs['after_submit'])
    assert_no_more_diffs('after_positive_rebase', step_diffs['after_positive_rebase'])
    assert_no_more_diffs('after_negative_rebase',step_diffs['after_negative_rebase'])
    assert_no_more_diffs('after_last_submit', step_diffs['after_last_submit'])

