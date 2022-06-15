"""
Tests for voting 11/11/2021.
"""
import pytest
from collections import namedtuple

from utils.config import lido_dao_acl_address, lido_dao_token_manager_address
from scripts.vote_2021_11_11 import start_vote

Payout = namedtuple(
    'Payout', ['address', 'amount']
)


@pytest.fixture(scope='module')
def acl(interface):
    """Returns ACL contract"""
    return interface.ACL(lido_dao_acl_address)


@pytest.fixture(scope='module')
def token_manager(interface):
    """Returns TokenManager contract"""
    return interface.TokenManager(lido_dao_token_manager_address)


@pytest.fixture(scope='module')
def deposit_security_module(interface):
    return interface.DepositSecurityModule('0xdb149235b6f40dc08810aa69869783be101790e7')


def has_assign_role_permission(acl, token_manager, who) -> int:
    """Returns if address has ASSIGN_ROLE on TokenManager contract"""
    return acl.hasPermission(who, token_manager, token_manager.ASSIGN_ROLE())


token_purchase_contract_address = '0x689E03565e36B034EcCf12d182c3DC38b2Bb7D33'
referral_payout = Payout(
    address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
    amount=161_984_4659 * 10 ** 14
)
sushi_rewards_payout = Payout(
    address='0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4',
    amount=200_000 * 10 ** 18
)


def test_2021_11_11(acl, token_manager, ldo_holder, helpers, accounts, dao_voting, ldo_token, deposit_security_module):
    assert has_assign_role_permission(acl, token_manager, token_purchase_contract_address)
    assert deposit_security_module.isPaused()
    referral_payout_balance_before = ldo_token.balanceOf(referral_payout.address)
    sushi_rewards_payout_balance_before = ldo_token.balanceOf(sushi_rewards_payout.address)

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    referral_payout_balance_after = ldo_token.balanceOf(referral_payout.address)
    sushi_rewards_payout_balance_after = ldo_token.balanceOf(sushi_rewards_payout.address)

    assert not has_assign_role_permission(acl, token_manager, token_purchase_contract_address)
    assert not deposit_security_module.isPaused()
    assert referral_payout_balance_after - referral_payout_balance_before == referral_payout.amount
    assert sushi_rewards_payout_balance_after - sushi_rewards_payout_balance_before == sushi_rewards_payout.amount
