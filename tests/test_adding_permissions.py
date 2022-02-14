"""
Tests for voting 20/01/2022.
"""

import brownie
import pytest
from brownie.test import given, strategy

from scripts.setup_easytrack_limits import eth, steth, ldo, require_amount_limits
from utils.evm_script import encode_call_script
from utils.permissions import encode_permission_grant_p
from utils.voting import confirm_vote_script, create_vote


@pytest.fixture(scope="module", autouse=True)
def voting_tx(finance, acl, ldo_holder, helpers, accounts, dao_voting):
    encoded_call_script = encode_call_script([
        encode_permission_grant_p(finance, 'CREATE_PAYMENTS_ROLE', ldo_holder.address, acl, require_amount_limits())
    ])

    vote_id = confirm_vote_script(encoded_call_script, silent=True) and create_vote(
        vote_desc='Test vote',
        evm_script=encoded_call_script,
        tx_params={'from': ldo_holder}
    )[0]

    return helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )


usdc_token = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'


@given(amount=strategy('uint', min_value=eth['limit'] + 1))
def test_permission_fails_for_eth(acl, finance, ldo_holder, amount):
    assert not acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                                   [eth['address'], ldo_holder.address, amount])
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(eth['address'], ldo_holder.address, amount, 'Should be reverted',
                                    {'from': ldo_holder})


@given(amount=strategy('uint', min_value=1, max_value=eth['limit']))
def test_permission_pass_for_eth(acl, finance, ldo_holder, amount):
    assert acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [eth['address'], ldo_holder.address, amount])
    finance.newImmediatePayment(eth['address'], ldo_holder.address, amount, 'test', {'from': ldo_holder})


@given(amount=strategy('uint', min_value=steth['limit'] + 1))
def test_permission_fails_for_steth(acl, finance, ldo_holder, amount):
    assert not acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                                   [steth['address'], ldo_holder.address, amount])
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(steth['address'], ldo_holder.address, amount, 'Should be reverted',
                                    {'from': ldo_holder})


@given(amount=strategy('uint', min_value=1, max_value=steth['limit']))
def test_permission_pass_for_steth(acl, finance, ldo_holder, amount):
    assert acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [steth['address'], ldo_holder.address, amount])
    finance.newImmediatePayment(steth['address'], ldo_holder.address, amount, 'test', {'from': ldo_holder})


@given(amount=strategy('uint', min_value=ldo['limit'] + 1))
def test_permission_fails_for_ldo(acl, finance, ldo_holder, amount):
    assert not acl.hasPermission['address,address,bytes32,uint[]'](ldo['address'], finance,
                                                                   finance.CREATE_PAYMENTS_ROLE(),
                                                                   [ldo['address'], ldo_holder.address, amount])
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(ldo['address'], ldo_holder.address, amount, 'Should be reverted',
                                    {'from': ldo_holder})


@given(amount=strategy('uint', min_value=1, max_value=ldo['limit']))
def test_permission_pass_for_ldo(acl, finance, ldo_holder, amount):
    assert acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [ldo['address'], ldo_holder.address, amount])
    finance.newImmediatePayment(ldo['address'], ldo_holder.address, amount, 'test', {'from': ldo_holder})


@given(amount=strategy('uint', min_value=1))
def test_permission_fails_for_usdc(acl, finance, ldo_holder, amount):
    assert not acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                                   [usdc_token, ldo_holder.address, amount])
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(usdc_token, ldo_holder.address, amount, 'Should be reverted',
                                    {'from': ldo_holder})
