"""
Tests for voting 10/07/2021.
"""
import pytest

from collections import namedtuple

from scripts.vote_2021_10_07 import (
    start_vote,
    payout_curve_rewards,
    payout_balancer_rewards,
    payout_purchase_contract,
    grant_role_purchase_contract,
    payout_finance_multisig
)

from utils.config import ldo_token_address, lido_dao_acl_address, lido_dao_token_manager_address

def curve_balance(ldo) -> int:
    """Returns LDO balance of Curve rewards distributor"""
    return ldo.balanceOf(payout_curve_rewards['address'])

def balancer_balance(ldo) -> int:
    """Returns LDO balance of Balancer rewards distributor"""
    return ldo.balanceOf(payout_balancer_rewards['address'])

def purchase_contract_balance(ldo) -> int:
    """Returns LDO balance of purchase contract"""
    return ldo.balanceOf(payout_purchase_contract['address'])

def finance_multisig_balance(ldo) -> int:
    """Returns LDO balance of finance multisig contract"""
    return ldo.balanceOf(payout_finance_multisig['address'])

def has_assign_role_permission(acl, token_manager, who) -> int:
    """Returns if address has ASSIGN_ROLE on TokenManager contract"""
    return acl.hasPermission(who, token_manager, token_manager.ASSIGN_ROLE())

@pytest.fixture(scope='module')
def ldo(interface):
    """Returns contract of LDO token."""
    return interface.ERC20(ldo_token_address)

@pytest.fixture(scope='module')
def acl(interface):
    """Returns ACL contract"""
    return interface.ACL(lido_dao_acl_address)

@pytest.fixture(scope='module')
def token_manager(interface):
    """Returns TokenManager contract"""
    return interface.TokenManager(lido_dao_token_manager_address)

def test_common(
        acl, token_manager, ldo_holder,
        helpers, accounts, dao_voting, ldo
):
    """Perform testing for the whole voting."""
    curve_balance_before = curve_balance(ldo)
    balancer_balance_before = balancer_balance(ldo)
    purchase_contract_balance_before = purchase_contract_balance(ldo)
    finance_multisig_balance_before = finance_multisig_balance(ldo)

    assert not has_assign_role_permission(acl, token_manager, grant_role_purchase_contract['address'])

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    curve_balance_after = curve_balance(ldo)
    balancer_balance_after = balancer_balance(ldo)
    purchase_contract_balance_after = purchase_contract_balance(ldo)
    finance_multisig_balance_after = finance_multisig_balance(ldo)

    curve_inc = curve_balance_after - curve_balance_before
    balancer_inc = balancer_balance_after - balancer_balance_before
    purchase_contract_balance_inc = purchase_contract_balance_after - purchase_contract_balance_before
    finance_multisig_balance_inc = finance_multisig_balance_after - finance_multisig_balance_before

    assert curve_inc == payout_curve_rewards['amount'], 'Failed on Curve'
    assert balancer_inc == payout_balancer_rewards['amount'], 'Failed on Balancer'
    assert purchase_contract_balance_inc == payout_purchase_contract['amount'], 'Failed on purchase contract'
    assert has_assign_role_permission(acl, token_manager, grant_role_purchase_contract['address']), 'Failed on grant ASSIGN_ROLE'
    assert finance_multisig_balance_inc == payout_finance_multisig['amount'], 'Failed on purchase contract'