"""
Tests that checks that votes at 21/06/2022 could be enacted in any order.
"""

from brownie import accounts, chain, interface
from utils.config import ldo_vote_executors_for_tests


import scripts.upgrade_2022_06_21
import scripts.vote_2022_06_21_NOs_onb


from test_2022_06_21 import voting_new_app, permission
from test_2022_06_21_NOs_onb import NEW_NODE_OPERATORS


start_upgrade_vote = scripts.upgrade_2022_06_21.start_vote
start_NO_vote = scripts.vote_2022_06_21_NOs_onb.start_vote


def test_vote_straight_order(ldo_holder, helpers, dao_voting, dao_agent, node_operators_registry):
    no_vote_id = start_NO_vote({"from": ldo_holder}, silent=True)[0]

    # Wait 1 hour and start another vote
    chain.sleep(1 * 60 * 60)
    chain.mine()
    upgrade_vote_id = start_upgrade_vote({"from": ldo_holder}, silent=True)[0]

    # Wait 71 hours because we've already skipped 1 hour
    helpers.execute_vote(
        vote_id=no_vote_id, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether", skip_time=71 * 60 * 60
    )

    # Check that all NO was added
    check_NO_vote_outcome(node_operators_registry)

    # Check that upgrade voting can not be executed yet
    assert not dao_voting.canExecute(upgrade_vote_id)

    # Wait only 1 hour
    helpers.execute_vote(
        vote_id=upgrade_vote_id, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether", skip_time=1 * 60 * 60
    )

    # Check upgrade vote outcome
    check_upgrade_vote_outcome(dao_voting)


def test_vote_inverse_order(ldo_holder, helpers, dao_voting, dao_agent, node_operators_registry):
    upgrade_vote_id = start_upgrade_vote({"from": ldo_holder}, silent=True)[0]

    # Wait 1 hour and start another vote
    chain.sleep(1 * 60 * 60)
    chain.mine()
    no_vote_id = start_NO_vote({"from": ldo_holder}, silent=True)[0]

    # Need to vote on NO adding before the objection phase, since impl would be changed before the vote will finished
    for holder_addr in ldo_vote_executors_for_tests:
        print("voting from acct:", holder_addr)
        accounts[0].transfer(holder_addr, "0.5 ether")
        account = accounts.at(holder_addr, force=True)
        dao_voting.vote(no_vote_id, True, False, {"from": account})

    # Wait 71 hours because we've already skipped 1 hour
    helpers.execute_vote(
        vote_id=upgrade_vote_id, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether", skip_time=71 * 60 * 60
    )

    # Check upgrade vote outcome
    check_upgrade_vote_outcome(dao_voting)

    # Check that upgrade voting can not be executed yet
    assert not dao_voting.canExecute(no_vote_id)

    # Check vote phase
    assert dao_voting.getVotePhase(no_vote_id) == 1  # objection phase

    # Wait only 1 hour
    chain.sleep(1 * 60 * 60)
    chain.mine()

    # Execute vote
    assert dao_voting.canExecute(no_vote_id)
    dao_voting.executeVote(no_vote_id, {"from": ldo_holder})

    # Check that all NO was added
    check_NO_vote_outcome(node_operators_registry)


def check_NO_vote_outcome(node_operators_registry: interface.NodeOperatorsRegistry) -> None:
    for node_operator in NEW_NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(node_operator.id, True)

        message = f"Failed on {node_operator.name}"
        assert no[0] is True, message  # is active
        assert no[1] == node_operator.name, message  # name
        assert no[2] == node_operator.reward_address, message  # rewards address
        assert no[3] == 0  # staking limit


def check_upgrade_vote_outcome(dao_voting: interface.Voting) -> None:
    assert dao_voting.voteTime() == voting_new_app["vote_time"]
    assert dao_voting.objectionPhaseTime() == voting_new_app["objection_time"]
    assert dao_voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE() == permission.role
