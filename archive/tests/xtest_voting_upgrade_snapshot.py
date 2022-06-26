import pytest
from collections import namedtuple

from brownie import accounts, chain, MockCallTarget

from archive.scripts.vote_2022_04_07 import start_vote

from utils.voting import create_vote
from utils.evm_script import encode_call_script
from utils.config import ldo_vote_executors_for_tests


@pytest.fixture(scope='module', autouse=True)
def vote_time(dao_voting):
    return dao_voting.voteTime()


@pytest.fixture(scope='module', autouse=True)
def call_target():
    return MockCallTarget.deploy({'from': accounts[0]})


def test_smoke_snapshots(dao_voting, ldo_holder, helpers, vote_time, call_target):
    """
    Run a smoke test before upgrade, then after upgrade, and compare snapshots at each step
    """
    reference_steps = record_create_pass_enact(dao_voting, {'from': ldo_holder}, vote_time, call_target)
    chain.revert()

    upgrade_voting(ldo_holder, helpers, dao_voting)

    after_upgrade = record_create_pass_enact(dao_voting, {'from': ldo_holder}, vote_time, call_target)

    step_diffs = list(map(lambda pair: dictdiff(pair[0], pair[1]), zip(reference_steps, after_upgrade)))

    initial = step_diffs[0]
    check_optional_diff(initial, ['vote_script', 'vote_yea', 'vote_ney',
                                  'vote_voter1_state', 'vote_voter2_state', 'vote_voter3_state'])

    afterVoteTime = step_diffs[5]
    assert_diff(afterVoteTime, {
        'vote_open': ValueChanged(from_val=False, to_val=True),
        'behaviour_vote': ValueChanged(from_val=False, to_val=True),
        'vote_canExecute': ValueChanged(from_val=True, to_val=False),
        'behaviour_enact': ValueChanged(from_val=True, to_val=False),
    })

    for indx, diff in enumerate(step_diffs):
        print(f'Verifying step {indx}')
        assert_time_changed(diff, vote_time)
        assert_last_vote_not_same(diff)
        assert_more_votes(diff)
        assert_no_more_diffs(diff)


def test_upgrade_after_create(dao_voting, ldo_holder, helpers, vote_time, call_target):
    """
    Create a vote then upgrade and check that all is going fine but longer
    """
    reference_steps = record_create_pass_enact(dao_voting, {'from': ldo_holder}, vote_time, call_target)
    chain.revert()

    steps = [snapshot(dao_voting)]  # 0
    vote_id = vote_start(call_target, {'from': ldo_holder})
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
    assert_diff(afterUpgrade, {
        'vote_open': ValueChanged(from_val=False, to_val=True),
        'behaviour_vote': ValueChanged(from_val=False, to_val=True),
        'vote_canExecute': ValueChanged(from_val=True, to_val=False),
        'behaviour_enact': ValueChanged(from_val=True, to_val=False),
    })
    assert_time_changed(afterUpgrade, vote_time)
    assert_more_votes(afterUpgrade)
    assert_last_vote_not_same(afterUpgrade)
    assert_no_more_diffs(afterUpgrade)

    for indx, diff in enumerate(step_diffs[6:]):
        print(f'Verifying step {indx + 6}')
        assert_time_changed(diff, vote_time)
        assert_more_votes(diff)
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)


def test_upgrade_after_pass(dao_voting, ldo_holder, helpers, vote_time, call_target):
    """
    Passed voting should become open after upgrade if started within 72h
    """
    reference_steps = record_create_pass_enact(dao_voting, {'from': ldo_holder}, vote_time, call_target)
    chain.revert()

    steps = [snapshot(dao_voting)]  # 0
    vote_id = vote_start(call_target, {'from': ldo_holder})
    steps.append(snapshot(dao_voting, vote_id))  # 1

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(dao_voting, vote_id, voter)
        steps.append(snapshot(dao_voting, vote_id))  # 2-4

    wait(vote_time)
    steps.append(snapshot(dao_voting, vote_id))  # 5

    upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=vote_time)
    steps.append(snapshot(dao_voting, vote_id))  # 6

    wait(72*60*60 - vote_time)
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
    assert_diff(afterUpgrade, {
        'vote_open': ValueChanged(from_val=False, to_val=True),
        'behaviour_vote': ValueChanged(from_val=False, to_val=True),
        'vote_canExecute': ValueChanged(from_val=True, to_val=False),
        'behaviour_enact': ValueChanged(from_val=True, to_val=False),
    })
    assert_time_changed(afterUpgrade, vote_time)
    assert_more_votes(afterUpgrade)
    assert_last_vote_not_same(afterUpgrade)
    assert_no_more_diffs(afterUpgrade)

    for indx, diff in enumerate(step_diffs[7:]):
        print(f'Verifying step {indx + 7}')
        assert_time_changed(diff, vote_time)
        assert_more_votes(diff)
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)


def test_upgrade_after_72h_after_pass(dao_voting, ldo_holder, helpers, vote_time, call_target):
    """
    Passed voting should not become open after upgrade if started out of 72h period
    """
    reference_steps = record_create_pass_enact(dao_voting, {'from': ldo_holder}, vote_time, call_target)
    chain.revert()

    steps = [snapshot(dao_voting)]  # 0
    vote_id = vote_start(call_target, {'from': ldo_holder})
    steps.append(snapshot(dao_voting, vote_id))  # 1

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(dao_voting, vote_id, voter)
        steps.append(snapshot(dao_voting, vote_id))  # 2-4

    wait(72 * 60 * 60 - vote_time)
    steps.append(snapshot(dao_voting, vote_id))  # 5

    upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=vote_time)
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
    assert_time_changed(afterUpgrade, vote_time)
    assert_more_votes(afterUpgrade)
    assert_last_vote_not_same(afterUpgrade)
    assert_no_more_diffs(afterUpgrade)

    for indx, diff in enumerate(step_diffs[7:]):
        print(f'Verifying step {indx + 7}')
        assert_time_changed(diff, vote_time)
        assert_more_votes(diff)
        assert_last_vote_not_same(diff)
        assert_no_more_diffs(diff)


def test_upgrade_after_enact(dao_voting, ldo_holder, helpers, vote_time, call_target):
    """
    Enacted voting should not become open after upgrade if started within 72h period
    """
    reference_steps = record_create_pass_enact(dao_voting, {'from': ldo_holder}, vote_time, call_target)
    chain.revert()

    steps = [snapshot(dao_voting)]  # 0
    vote_id = vote_start(call_target, {'from': ldo_holder})
    steps.append(snapshot(dao_voting, vote_id))  # 1

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(dao_voting, vote_id, voter)
        steps.append(snapshot(dao_voting, vote_id))  # 2-4

    wait(72*60*60 - vote_time)
    steps.append(snapshot(dao_voting, vote_id))  # 5

    enact_a_vote(dao_voting, vote_id)
    steps.append(snapshot(dao_voting, vote_id))  # 6

    upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=vote_time)
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
        'vote_executed': ValueChanged(from_val=False, to_val=True),
        'vote_canExecute': ValueChanged(from_val=True, to_val=False),
        'behaviour_enact': ValueChanged(from_val=True, to_val=False),
    })
    assert_no_more_diffs(afterEnact)

    afterUpgrade = step_diffs[7]
    print(f'Verifying step 7')
    assert_time_changed(afterUpgrade, vote_time)
    assert_more_votes(afterUpgrade)
    assert_last_vote_not_same(afterUpgrade)
    assert_no_more_diffs(afterUpgrade)


def snapshot(voting, vote_id=None):
    length = voting.votesLength()
    vote_idx = (length - 1) if vote_id is None else vote_id
    last_vote = voting.getVote(vote_idx)

    def try_to_vote():
        try:
            vote_for_a_vote(voting, vote_idx, ldo_vote_executors_for_tests[0])
            return True
        except:
            return False
        finally:
            chain.undo()

    def try_to_enact():
        try:
            enact_a_vote(voting, vote_idx)
            return True
        except:
            return False
        finally:
            chain.undo()

    return {
        'address': voting.address,

        'voteTime': voting.voteTime(),

        'CREATE_VOTES_ROLE': voting.CREATE_VOTES_ROLE(),
        'MODIFY_SUPPORT_ROLE': voting.MODIFY_SUPPORT_ROLE(),
        'MODIFY_QUORUM_ROLE': voting.MODIFY_QUORUM_ROLE(),

        'minAcceptQuorumPct': voting.minAcceptQuorumPct(),
        'supportRequiredPct': voting.supportRequiredPct(),
        'votesLength': length,

        'vote_open': last_vote[0],
        'vote_executed': last_vote[1],
        'vote_startDate': last_vote[2],
        'vote_snapshotBlock': last_vote[3],
        'vote_supportRequired': last_vote[4],
        'vote_minAcceptQuorum': last_vote[5],
        'vote_yea': last_vote[6],
        'vote_nay': last_vote[7],
        'vote_votingPower': last_vote[8],
        'vote_script': last_vote[9],

        'vote_canExecute': voting.canExecute(vote_idx),
        'vote_voter1_state': voting.getVoterState(vote_idx, ldo_vote_executors_for_tests[0]),
        'vote_voter2_state': voting.getVoterState(vote_idx, ldo_vote_executors_for_tests[1]),
        'vote_voter3_state': voting.getVoterState(vote_idx, ldo_vote_executors_for_tests[2]),

        'behaviour_vote': try_to_vote(),
        'behaviour_enact': try_to_enact(),
    }


def record_create_pass_enact(voting, tx_params, vote_time, call_target):
    steps = [snapshot(voting)]

    vote_id = vote_start(call_target, tx_params)
    steps.append(snapshot(voting))

    for voter in ldo_vote_executors_for_tests:
        vote_for_a_vote(voting, vote_id, voter)
        steps.append(snapshot(voting))

    wait(vote_time)
    steps.append(snapshot(voting))

    wait(72*60*60 - vote_time)
    steps.append(snapshot(voting))

    assert not call_target.called()

    enact_a_vote(voting, vote_id)

    assert call_target.called()

    steps.append(snapshot(voting))
    return steps


def upgrade_voting(ldo_holder, helpers, dao_voting, skip_time=3 * 60 * 60 * 24):
    vote_id = start_vote({'from': ldo_holder}, silent=True)[0]

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether', skip_time=skip_time
    )

    return vote_id


def vote_start(call_target, tx_params) -> int:
    callscript = encode_call_script([
        (
            call_target.address,
            call_target.perform_call.encode_input()
        )
    ])
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


def check_optional_diff(diff, expected):
    """Some keys are optional and can present depending on the state of the chain"""
    for key in expected:
        if key in diff:
            del diff[key]


def assert_diff(diff, expected):
    for key in expected.keys():
        assert diff[key] == expected[key]
        del diff[key]


def assert_time_changed(diff, previous_vote_time):
    assert diff['voteTime'] == ValueChanged(previous_vote_time, 259200), "voteTime changed to 72h"
    del diff['voteTime']


def assert_last_vote_not_same(diff):
    assert 'vote_startDate' in diff, "Start date should be different"
    del diff['vote_startDate']
    check_optional_diff(diff, ['vote_snapshotBlock'])


def assert_more_votes(diff):
    assert diff['votesLength'].to_val == diff['votesLength'].from_val + 1, "Should be more votes after upgrade"
    del diff['votesLength']


def assert_no_more_diffs(diff):
    assert len(diff) == 0, f"Unexpected diff {diff}"


ValueChanged = namedtuple('ValueChanged', ['from_val', 'to_val'])


def dictdiff(from_dict, to_dict):
    result = {}

    all_keys = from_dict.keys() | to_dict.keys()
    for key in all_keys:
        if from_dict.get(key) != to_dict.get(key):
            result[key] = ValueChanged(from_dict.get(key), to_dict.get(key))

    return result
