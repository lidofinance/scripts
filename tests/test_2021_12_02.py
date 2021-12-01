"""
Tests for voting 02/12/2021.
"""

from scripts.vote_2021_12_02 import start_vote, EVM_SCRIPT_EXECUTOR_ADDRESS


def test_2021_12_02(
    helpers, acl, finance, node_operators_registry, accounts, ldo_holder, dao_voting
):
    assert not acl.hasPermission(
        EVM_SCRIPT_EXECUTOR_ADDRESS, finance, finance.CREATE_PAYMENTS_ROLE()
    )
    assert not acl.hasPermission(
        EVM_SCRIPT_EXECUTOR_ADDRESS,
        node_operators_registry,
        node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE(),
    )
    vote_id, _ = start_vote({"from": ldo_holder}, silent=True)
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting)

    assert acl.hasPermission(
        EVM_SCRIPT_EXECUTOR_ADDRESS, finance, finance.CREATE_PAYMENTS_ROLE()
    )
    assert acl.hasPermission(
        EVM_SCRIPT_EXECUTOR_ADDRESS,
        node_operators_registry,
        node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE(),
    )
