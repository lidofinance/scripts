# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *

from collections import namedtuple
from brownie import accounts, chain
from scripts.vote_01_voting_upgrade import start_vote
from utils.config import ldo_vote_executors_for_tests
from utils.mainnet_fork import chain_snapshot
from utils.voting import create_vote
from utils.evm_script import encode_call_script

ValueChanged = namedtuple('ValueChanged', ['from_val', 'to_val'])


def dictdiff(from_dict, to_dict):
    result = {}

    all_keys = from_dict.keys() | to_dict.keys()
    for key in all_keys:
        if from_dict.get(key) != to_dict.get(key):
            result[key] = ValueChanged(from_dict.get(key), to_dict.get(key))

    return result


def snapshot(voting):
    length = voting.votesLength()
    last_vote = voting.getVote(length - 1)
    return {
        'address': voting.address,

        'voteTime': voting.voteTime(),

        'CREATE_VOTES_ROLE': voting.CREATE_VOTES_ROLE(),
        'MODIFY_SUPPORT_ROLE': voting.MODIFY_SUPPORT_ROLE(),
        'MODIFY_QUORUM_ROLE': voting.MODIFY_QUORUM_ROLE(),
        'UNSAFELY_MODIFY_VOTE_TIME_ROLE': voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE(),

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

        'lastVote_canExecute': voting.canExecute(length - 1)
    }


def upgrade_voting(ldo_holder, helpers, accounts, dao_voting):
    vote_id = start_vote({'from': ldo_holder}, silent=True)[0]

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )

    return vote_id


def vote_start(tx_params) -> int:
    callscript = encode_call_script([])
    return create_vote("Test voting", callscript, tx_params)[0]


def vote_for_a_vote(voting, vote_id, voter):
    accounts[0].transfer(voter, '0.1 ether')
    account = accounts.at(voter, force=True)
    voting.vote(vote_id, True, False, {'from': account})


def wait24h():
    # wait for the vote to end
    chain.sleep(60 * 60 * 24)
    chain.mine()


def wait48h():
    # wait for the vote to end
    chain.sleep(2 * 60 * 60 * 24)
    chain.mine()


def enact_a_vote(voting, vote_id):
    voting.executeVote(vote_id, {'from': accounts[0]})


def record_create_pass_enact(voting, tx_params):
    history = []
    with chain_snapshot():
        history.append(snapshot(voting))

        vote_id = vote_start(tx_params)
        history.append(snapshot(voting))

        for voter in ldo_vote_executors_for_tests:
            vote_for_a_vote(voting, vote_id, voter)
            history.append(snapshot(voting))

        wait24h()
        history.append(snapshot(voting))

        wait48h()
        history.append(snapshot(voting))

        enact_a_vote(voting, vote_id)
        history.append(snapshot(voting))
    return history


def check_last_vote(snapshot):
    assert snapshot['voteTime'] == ValueChanged(14460, 259200), "voteTime changed"
    assert snapshot['votesLength'].to_val == snapshot['votesLength'].from_val + 1, \
        "We have one more voting in upgraded contract"
    assert 'lastVote_startDate' in snapshot
    assert 'lastVote_snapshotBlock' in snapshot


def test_create_pass_enact(dao_voting, ldo_holder, helpers, accounts):
    before_upgrade = record_create_pass_enact(dao_voting,  {'from': ldo_holder})

    upgrade_voting(ldo_holder, helpers, accounts, dao_voting)

    after_upgrade = record_create_pass_enact(dao_voting, {'from': ldo_holder})

    step_pairs = zip(before_upgrade, after_upgrade)
    diffs = list(map(lambda pair: dictdiff(pair[0], pair[1]), step_pairs))

    initial = diffs[0]

    assert initial['voteTime'] == ValueChanged(14460, 259200), "voteTime changed"
    assert initial['votesLength'].to_val == initial['votesLength'].from_val + 1, "One more voting in upgraded contract"
    assert 'lastVote_script' in initial
    assert 'lastVote_startDate' in initial
    assert 'lastVote_snapshotBlock' in initial
    assert len(initial) == 6, f"Unexpected diff {initial}"

    voting_created = diffs[1]

    assert voting_created['votesLength'].from_val == initial['votesLength'].from_val + 1
    assert voting_created['votesLength'].to_val == initial['votesLength'].to_val + 1
    check_last_vote(voting_created)
    assert len(voting_created) == 4, f"Unexpected diff {voting_created}"

    for voted in diffs[2:5]:
        check_last_vote(voted)
        assert len(voted) == 4, f"Unexpected diff {voted}"

    after24h = diffs[5]

    check_last_vote(after24h)
    assert after24h['lastVote_open'] == ValueChanged(False, True)
    assert len(after24h) == 5, f"Unexpected diff {after24h}"

    after72h = diffs[6]

    check_last_vote(after72h)
    assert len(after72h) == 4, f"Unexpected diff {after72h}"

    afterEnact = diffs[7]

    check_last_vote(afterEnact)
    assert len(after72h) == 4, f"Unexpected diff {afterEnact}"
