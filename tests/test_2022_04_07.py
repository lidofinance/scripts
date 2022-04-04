import pytest
# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *

from collections import namedtuple
from brownie import accounts, chain, interface
from scripts.vote_2022_04_07 import start_vote
from utils.config import (
    ldo_vote_executors_for_tests,
    lido_dao_voting_repo,
    lido_dao_voting_address
)
from utils.voting import create_vote
from utils.evm_script import encode_call_script

from event_validators.permission import (Permission,
                                         validate_permission_create,
                                         validate_permission_grant_event,
                                         validate_permission_revoke_event)
from event_validators.voting import validate_change_vote_time_event
from tx_tracing_helpers import *


voting_new_app = {
    'address': '0x9059e060113b7394FC964bf86CD246f3e9D4210d',
    'content_uri': '0x697066733a516d5962774366374d6e6932797a31553358334769485667396f35316a6b53586731533877433257547755684859',
    'id': '0xee7f2abf043afe722001aaa900627a6e29adcbcce63a561fbd97e0a0c6429b94',
    'version': (3, 0, 0),
    'vote_time': 259200  # 72 hours
}

voting_old_app = {
    'address': '0xfd5952Ef8dE4707f95E754299e8c0FfD1e876F34',
    'content_uri': '0x697066733a516d5962774366374d6e6932797a31553358334769485667396f35316a6b53586731533877433257547755684859',
    'id': '0xee7f2abf043afe722001aaa900627a6e29adcbcce63a561fbd97e0a0c6429b94',
    'version': (2, 0, 0),
    'vote_time': 14460
}

permission = Permission(entity='0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db',  # Voting
                        app='0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db',  # Voting
                        role='0x068ca51c9d69625c7add396c98ca4f3b27d894c3b973051ad3ee53017d7094ea')  # keccak256('UNSAFELY_MODIFY_VOTE_TIME_ROLE')


def test_2022_04_07(ldo_holder, helpers, dao_voting):
    voting_repo = interface.Repo(lido_dao_voting_repo)
    voting_proxy = interface.AppProxyUpgradeable(lido_dao_voting_address)
    voting_app_from_chain = voting_repo.getLatest()

    assert voting_app_from_chain[0] == voting_old_app['version']
    assert voting_app_from_chain[1] == voting_old_app['address']
    assert voting_app_from_chain[2] == voting_old_app['content_uri']
    assert voting_proxy.implementation() == voting_old_app['address']

    assert dao_voting.voteTime() == voting_old_app['vote_time']

    ##
    # START VOTE
    ##
    vote_id = start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )

    voting_app_from_chain = voting_repo.getLatest()

    assert voting_app_from_chain[0] == voting_new_app['version']
    assert voting_app_from_chain[1] == voting_new_app['address']
    assert voting_app_from_chain[2] == voting_new_app['content_uri']

    assert voting_proxy.implementation() == voting_new_app['address']
    assert dao_voting.voteTime() == voting_new_app['vote_time']
    assert dao_voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE() == permission.role

    # Validating events
    # Need to have mainnet contract to have it right
    # display_voting_events(tx)

    # assert count_vote_items_by_events(tx, dao_voting) == 5, "Incorrect voting items count"
    #
    # evs = group_voting_events(tx)
    # validate_push_to_repo_event()
    # validate_app_update_event()
    # validate_permission_create(evs[2], permission, lido_dao_voting_address)
    # validate_change_vote_time_event(evs[3], voting_new_app['vote_time'])
    # validate_permission_revoke_event(evs[4], permission)


@pytest.fixture(scope='module', autouse=True)
def vote_time(dao_voting):
    return dao_voting.voteTime()


@pytest.fixture(scope='function', autouse=True)
def reference_steps(dao_voting, ldo_holder, vote_time):
    before_upgrade = record_create_pass_enact(dao_voting, {'from': ldo_holder}, vote_time)
    chain.revert()
    chain.mine(1)
    return before_upgrade


ValueChanged = namedtuple('ValueChanged', ['from_val', 'to_val'])


def dictdiff(from_dict, to_dict):
    result = {}

    all_keys = from_dict.keys() | to_dict.keys()
    for key in all_keys:
        if from_dict.get(key) != to_dict.get(key):
            result[key] = ValueChanged(from_dict.get(key), to_dict.get(key))

    return result


def snapshot(voting, vote_id=None):
    length = voting.votesLength()
    vote_idx = (length - 1) if vote_id is None else vote_id
    last_vote = voting.getVote(vote_idx)
    return {
        'address': voting.address,

        'voteTime': voting.voteTime(),

        'CREATE_VOTES_ROLE': voting.CREATE_VOTES_ROLE(),
        'MODIFY_SUPPORT_ROLE': voting.MODIFY_SUPPORT_ROLE(),
        'MODIFY_QUORUM_ROLE': voting.MODIFY_QUORUM_ROLE(),

        'minAcceptQuorumPct': voting.minAcceptQuorumPct(),
        'supportRequiredPct': voting.supportRequiredPct(),
        'votesLength': length,

        'lastVote_open': last_vote[0],
        'lastVote_executed': last_vote[1],
        'lastVote_startDate': last_vote[2],
        'lastVote_snapshotBlock': last_vote[3],
        'lastVote_supportRequired': last_vote[4],
        'lastVote_minAcceptQuorum': last_vote[5],
        'lastVote_yea': last_vote[6],
        'lastVote_nay': last_vote[7],
        'lastVote_votingPower': last_vote[8],
        'lastVote_script': last_vote[9],

        'lastVote_canExecute': voting.canExecute(vote_idx)
    }


def upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=3 * 60 * 60 * 24):
    vote_id = start_vote({'from': ldo_holder}, silent=True)[0]

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether', skip_time=skip_time
    )

    return vote_id


def vote_start(tx_params) -> int:
    callscript = encode_call_script([])
    return create_vote("Test voting", callscript, tx_params)[0]


def vote_for_a_vote(voting, vote_id, voter):
    accounts[0].transfer(voter, '0.1 ether')
    account = accounts.at(voter, force=True)
    voting.vote(vote_id, True, False, {'from': account})


def wait(time):
    chain.sleep(time + 100)
    chain.mine()


def enact_a_vote(voting, vote_id):
    voting.executeVote(vote_id, {'from': accounts[0]})


def record_create_pass_enact(voting, tx_params, vote_time):
    steps = [snapshot(voting)]

    vote_id = vote_start(tx_params)
    steps.append(snapshot(voting))

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(voting, vote_id, voter)
        steps.append(snapshot(voting))

    wait(vote_time)
    steps.append(snapshot(voting))

    wait(72*60*60)
    steps.append(snapshot(voting))

    enact_a_vote(voting, vote_id)
    steps.append(snapshot(voting))
    return steps


def check_optional_diff(diff, expected):
    """Some keys are optional and can present depending on the state of the chain"""
    for key in expected:
        if key in diff:
            del diff[key]


def assert_diff(diff, expected):
    for key in expected.keys():
        assert diff[key] == expected[key]
        del diff[key]


def assert_time_changed(diff):
    assert diff['voteTime'] == ValueChanged(14460, 259200), "voteTime changed from 24h to 72h"
    del diff['voteTime']


def assert_last_vote_not_same(diff):
    assert 'lastVote_startDate' in diff, "Different start date"
    assert 'lastVote_snapshotBlock' in diff, "Different start block"

    del diff['lastVote_startDate']
    del diff['lastVote_snapshotBlock']


def assert_more_votes(diff):
    assert diff['votesLength'].to_val == diff['votesLength'].from_val + 1, "Should be more votes after upgrade"
    del diff['votesLength']


def assert_no_more_diffs(diff):
    assert len(diff) == 0, f"Unexpected diff {diff}"


def test_smoke_snapshots(dao_voting, ldo_holder, helpers, reference_steps, vote_time):
    """
    Run a smoke test before upgrade, then after upgrade, and compare snapshots at each step
    """
    upgrade_voting(ldo_holder, helpers, dao_voting)
    after_upgrade = record_create_pass_enact(dao_voting, {'from': ldo_holder}, vote_time)

    step_diffs = list(map(lambda pair: dictdiff(pair[0], pair[1]), zip(reference_steps, after_upgrade)))

    initial = step_diffs[0]
    check_optional_diff(initial, ['lastVote_script', 'lastVote_yea', 'lastVote_ney'])

    afterVoteTime = step_diffs[5]
    assert_diff(afterVoteTime, {'lastVote_open': ValueChanged(False, True)})

    for indx, diff in enumerate(step_diffs):
        print(f'Verifying step {indx}')
        assert_time_changed(diff)
        assert_last_vote_not_same(diff)
        assert_more_votes(diff)
        assert_no_more_diffs(diff)


def test_upgrade_after_create(dao_voting, ldo_holder, helpers, reference_steps, vote_time):
    """
    Create a vote then upgrade and check that all is going fine but longer
    """
    steps = [snapshot(dao_voting)]  # 0
    vote_id = vote_start({'from': ldo_holder})
    steps.append(snapshot(dao_voting, vote_id))  # 1

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(dao_voting, vote_id, voter)
        steps.append(snapshot(dao_voting, vote_id))  # 2-4

    upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=vote_time)  # wait24h
    steps.append(snapshot(dao_voting, vote_id))  # 5

    wait(72*60*60)
    steps.append(snapshot(dao_voting, vote_id))  # 6

    enact_a_vote(dao_voting, vote_id)
    steps.append(snapshot(dao_voting, vote_id))  # 7

    step_diffs = list(map(lambda pair: dictdiff(pair[0], pair[1]), zip(reference_steps, steps)))

    # Verification

    initial = step_diffs[0]
    print(f'Verifying step 0')
    assert_no_more_diffs(initial)

    for indx, diff in enumerate(step_diffs[1:5]):
        print(f'Verifying step {indx + 1}')
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)

    afterUpgrade = step_diffs[5]
    print(f'Verifying step 5')
    assert_diff(afterUpgrade, {'lastVote_open': ValueChanged(from_val=False, to_val=True)})
    assert_time_changed(afterUpgrade)
    assert_more_votes(afterUpgrade)
    assert_last_vote_not_same(afterUpgrade)
    assert_no_more_diffs(afterUpgrade)

    for indx, diff in enumerate(step_diffs[6:]):
        print(f'Verifying step {indx + 6}')
        assert_time_changed(diff)
        assert_more_votes(diff)
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)


def test_upgrade_after_pass(dao_voting, ldo_holder, helpers, reference_steps, vote_time):
    """
    Passed voting should become open after upgrade if started within 72h
    """
    steps = [snapshot(dao_voting)]  # 0
    vote_id = vote_start({'from': ldo_holder})
    steps.append(snapshot(dao_voting, vote_id))  # 1

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(dao_voting, vote_id, voter)
        steps.append(snapshot(dao_voting, vote_id))  # 2-4

    wait(vote_time)
    steps.append(snapshot(dao_voting, vote_id))  # 5

    upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=0)
    steps.append(snapshot(dao_voting, vote_id))  # 6

    wait(72*60*60)
    enact_a_vote(dao_voting, vote_id)
    steps.append(snapshot(dao_voting, vote_id))  # 7

    step_diffs = list(map(lambda pair: dictdiff(pair[0], pair[1]), zip(reference_steps, steps)))

    # Verification

    initial = step_diffs[0]
    print(f'Verifying step 0')
    assert_no_more_diffs(initial)

    for indx, diff in enumerate(step_diffs[1:6]):
        print(f'Verifying step {indx + 1}')
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)

    afterUpgrade = step_diffs[6]
    print(f'Verifying step 6')
    assert_diff(afterUpgrade, {'lastVote_open': ValueChanged(from_val=False, to_val=True)})
    assert_time_changed(afterUpgrade)
    assert_more_votes(afterUpgrade)
    assert_last_vote_not_same(afterUpgrade)
    assert_no_more_diffs(afterUpgrade)

    for indx, diff in enumerate(step_diffs[7:]):
        print(f'Verifying step {indx + 7}')
        assert_time_changed(diff)
        assert_more_votes(diff)
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)


def test_upgrade_after_72h_after_pass(dao_voting, ldo_holder, helpers, reference_steps, vote_time):
    """
    Passed voting should not become open after upgrade if started out of 72h period
    """
    steps = [snapshot(dao_voting)]  # 0
    vote_id = vote_start({'from': ldo_holder})
    steps.append(snapshot(dao_voting, vote_id))  # 1

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(dao_voting, vote_id, voter)
        steps.append(snapshot(dao_voting, vote_id))  # 2-4

    wait(72 * 60 * 60)
    steps.append(snapshot(dao_voting, vote_id))  # 5

    upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=0)
    steps.append(snapshot(dao_voting, vote_id))  # 6

    enact_a_vote(dao_voting, vote_id)
    steps.append(snapshot(dao_voting, vote_id))  # 7

    step_diffs = list(map(lambda pair: dictdiff(pair[0], pair[1]), zip(reference_steps, steps)))

    # Verification

    initial = step_diffs[0]
    print(f'Verifying step 0')
    assert_no_more_diffs(initial)

    for indx, diff in enumerate(step_diffs[1:6]):
        print(f'Verifying step {indx + 1}')
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)

    afterUpgrade = step_diffs[6]
    print(f'Verifying step 6')
    assert_time_changed(afterUpgrade)
    assert_more_votes(afterUpgrade)
    assert_last_vote_not_same(afterUpgrade)
    assert_no_more_diffs(afterUpgrade)

    for indx, diff in enumerate(step_diffs[7:]):
        print(f'Verifying step {indx + 7}')
        assert_time_changed(diff)
        assert_more_votes(diff)
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)


def test_upgrade_after_enact(dao_voting, ldo_holder, helpers, reference_steps, vote_time):
    """
    Enacted voting should not become open after upgrade if started within 72h period
    """
    steps = [snapshot(dao_voting)]  # 0
    vote_id = vote_start({'from': ldo_holder})
    steps.append(snapshot(dao_voting, vote_id))  # 1

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(dao_voting, vote_id, voter)
        steps.append(snapshot(dao_voting, vote_id))  # 2-4

    wait(vote_time)
    steps.append(snapshot(dao_voting, vote_id))  # 5

    enact_a_vote(dao_voting, vote_id)
    steps.append(snapshot(dao_voting, vote_id))  # 6

    upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=0)
    steps.append(snapshot(dao_voting, vote_id))  # 7

    step_diffs = list(map(lambda pair: dictdiff(pair[0], pair[1]), zip(reference_steps, steps)))

    # Verification

    initial = step_diffs[0]
    print(f'Verifying step 0')
    assert_no_more_diffs(initial)

    for indx, diff in enumerate(step_diffs[1:6]):
        print(f'Verifying step {indx + 1}')
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)

    afterEnact = step_diffs[6]
    print(f'Verifying step 6')
    assert_last_vote_not_same(afterEnact)
    assert_diff(afterEnact, {
        'lastVote_executed': ValueChanged(from_val=False, to_val=True),
        'lastVote_canExecute': ValueChanged(from_val=True, to_val=False)
    })
    assert_no_more_diffs(afterEnact)

    afterUpgrade = step_diffs[7]
    print(f'Verifying step 6')
    assert_time_changed(afterUpgrade)
    assert_more_votes(afterUpgrade)
    assert_last_vote_not_same(afterUpgrade)
    assert_no_more_diffs(afterUpgrade)
