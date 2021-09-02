"""
Tests for voting 02/09/2021.
"""
import pytest

from typing import Union
from collections import namedtuple

from brownie import interface  # noqa

from scripts.vote_2021_09_02 import start_vote

from utils.config import ldo_token_address

NodeOperatorIncLimit = namedtuple(
    'NodeOperatorIncLimit', ['name', 'id', 'limit'],
)
NodeOperatorAdd = namedtuple(
    'NodeOperatorAdd', ['name', 'id', 'address']
)
ReferralPayout = namedtuple(
    'ReferralPayout', ['address', 'amount']
)

NODE_OPERATORS = [
    # name, id, limit
    NodeOperatorIncLimit('p2p', 2, 4800),
    NodeOperatorIncLimit('stakefish', 4, 6000),
    NodeOperatorIncLimit('Blockscape', 5, 7000),
    NodeOperatorIncLimit('DSRV', 6, 3700),
    NodeOperatorIncLimit('SkillZ', 8, 7000),
    NodeOperatorIncLimit('RockX', 9, 100),
    NodeOperatorIncLimit('Figment', 10, 100),
    NodeOperatorIncLimit('Allnodes', 11, 100),
    NodeOperatorIncLimit('Anyblock', 12, 100)
]

NEW_NODE_OPERATORS = [
    # name, id, address
    NodeOperatorAdd(
        'Blockdaemon', 13, '0x4f42A816dC2DBa82fF927b6996c14a741DCbD902'
    )
]

referral_payout = ReferralPayout(
    address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
    amount=3_523_767_186 * (10 ** 15)
)


def _balance(ldo) -> int:
    """Return balance for target of referral payout."""
    return ldo.balanceOf(referral_payout.address)


@pytest.fixture(scope='module')
def ldo():
    """Return contract of LDO token."""
    return interface.ERC20(ldo_token_address)


def test_common(
        ldo_holder, helpers, accounts,
        dao_voting, ldo, node_operators_registry
):
    """Perform testing for the whole voting."""
    referral_balance_before = _balance(ldo)
    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)
    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )
    referral_balance_after = _balance(ldo)
    inc = referral_balance_after - referral_balance_before
    assert inc == referral_payout.amount

    for node_operator in NODE_OPERATORS:
        assert node_operators_registry.getNodeOperator(
            node_operator.id, True
        )[3] == node_operator.limit, f'Failed on {node_operator.name}'

    for node_operator in NEW_NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(
            node_operator.id, True
        )

        message = f'Failed on {node_operator.name}'
        assert no[0] is True, message
        assert no[1] == node_operator.name, message
        assert no[2] == node_operator.address, message
        assert no[3] == 0

# @pytest.fixture(scope='module')
# def deversifi_ledger_balance_before(ldo):
#     """Get balance before payout."""
#     return _deversifi_ledger_balance(ldo)
#
#
# @pytest.fixture(scope='module')
# def _start_vote(
#         ldo_holder, helpers, accounts, dao_voting,
#         deversifi_ledger_balance_before
# ):
#     """Prepare and execute voting."""
#     vote_id, _ = start_vote({
#         'from': ldo_holder
#     }, silent=True)
#     helpers.execute_vote(
#         vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
#     )
#     return vote_id
#
#
# @pytest.fixture(scope='module')
# def deversifi_ledger_balance_after(_start_vote, ldo):
#     """Get balance after payout."""
#     return _deversifi_ledger_balance(ldo)
#
#
# def _ids(node_operator: Union[NodeOperatorIncLimit, NodeOperatorAdd]) -> str:
#     """Extract name for a test case."""
#     return node_operator.name
#
#
# @pytest.fixture(scope='module', params=NODE_OPERATORS, ids=_ids)
# def node_operator_limit(_start_vote, request):
#     """Return a single test case for limits increasing."""
#     return request.param
#
#
# @pytest.fixture(scope='module', params=NEW_NODE_OPERATORS, ids=_ids)
# def node_operator_new(_start_vote, request):
#     """Return a single test case for adding new operator."""
#     return request.param
#
#
# def test_referral_payout(
#         deversifi_ledger_balance_before, deversifi_ledger_balance_after
# ):
#     """Perform testing of referral payout."""
#     inc = deversifi_ledger_balance_after - deversifi_ledger_balance_before
#     assert inc == deversifi_ledger_referral_payout.amount
#
#
# def test_limit_increasing(node_operator_limit, node_operators_registry):
#     """Perform testing for limits increasing."""
#     assert node_operators_registry.getNodeOperator(
#         node_operator_limit.id, True
#     )[3] == node_operator_limit.limit
#
#
# def test_add_node_operator(node_operator_new, node_operators_registry):
#     """Perform testing for adding new node operators."""
#     no = node_operators_registry.getNodeOperator(
#         node_operator_new.id, True
#     )
#
#     assert no[0] is True
#     assert no[1] == node_operator_new.name
#     assert no[2] == node_operator_new.address
#     assert no[3] == 0
