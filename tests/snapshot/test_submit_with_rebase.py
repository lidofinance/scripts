import pytest

from typing import Dict

from brownie import accounts, chain, ZERO_ADDRESS, Wei

from utils.test.snapshot_helpers import dict_zip, dict_diff, assert_no_diffs, ValueChanged
from utils.config import contracts
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


@pytest.fixture(scope="module")
def stranger():
    return accounts[0]


@pytest.fixture(scope='module')
def lido_oracle_report(lido):
    lido_oracle = accounts.at(lido.getOracle(), force=True)
    dao_voting = accounts.at(contracts.voting.address, force=True)

    def report_beacon_state(steth_rebase_mult):
        lido.setFee(0, {'from': dao_voting})
        (_, beacon_validators, beacon_balance) = lido.getBeaconStat()
        total_supply = lido.totalSupply()
        total_supply_inc = (steth_rebase_mult - 1) * total_supply
        beacon_balance += total_supply_inc
        assert beacon_balance > 0
        lido.handleOracleReport(beacon_validators, beacon_balance, {'from': lido_oracle})

    return report_beacon_state


def make_snapshot(stranger, lido) -> Dict[str, any]:
    curve_pool = '0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'

    _, beacon_validators, beacon_balance = lido.getBeaconStat()

    return {
        'stranger.steth_balance': lido.balanceOf(stranger),
        'stranger.steth_shares': lido.sharesOf(stranger),

        'curve_pool.steth_balance': lido.balanceOf(curve_pool),
        'curve_pool.steth_shares': lido.sharesOf(curve_pool),

        'steth.total_supply': lido.totalSupply(),
        'steth.total_shares': lido.getTotalShares(),

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


@pytest.mark.skipif(condition=not is_there_any_vote_scripts(), reason='No votes')
def test_submit_rebase(dao_voting, stranger, lido, lido_oracle_report, helpers):
    before: Dict[str, Dict[str, any]] = steps(stranger, lido, lido_oracle_report)
    chain.revert()
    start_and_execute_votes(dao_voting, helpers)
    after: Dict[str, Dict[str, any]] = steps(stranger, lido, lido_oracle_report)

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    assert_no_diffs('before_submit', step_diffs['before_submit'])
    assert_no_diffs('after_submit', step_diffs['after_submit'])
    assert_no_diffs('after_positive_rebase', step_diffs['after_positive_rebase'])
    assert_no_diffs('after_negative_rebase', step_diffs['after_negative_rebase'])
    assert_no_diffs('after_last_submit', step_diffs['after_last_submit'])
