"""
Tests for voting 20/01/2022.
"""

import brownie
import pytest
from brownie.test import given, strategy

from scripts.add_granular_permission import start_vote, eth_limit, steth_limit, ldo_limit
from utils.finance import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def tx(helpers, ldo_holder, vote_id_from_env, accounts, dao_voting):
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    return helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )


ldo_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'
steth_token = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
usdc_token = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'


@given(amount=strategy('uint', min_value=eth_limit + 1))
def test_permission_fails_for_eth(acl, finance, ldo_holder, amount):
    assert not acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                                   [ZERO_ADDRESS, ldo_holder.address, amount])
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(ZERO_ADDRESS, ldo_holder.address, amount, 'Should be reverted',
                                    {'from': ldo_holder})


@given(amount=strategy('uint', min_value=1, max_value=eth_limit))
def test_permission_pass_for_eth(acl, finance, ldo_holder, amount):
    assert acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [ZERO_ADDRESS, ldo_holder.address, amount])
    finance.newImmediatePayment(ZERO_ADDRESS, ldo_holder.address, amount, 'test', {'from': ldo_holder})


@given(amount=strategy('uint', min_value=steth_limit + 1))
def test_permission_fails_for_steth(acl, finance, ldo_holder, amount):
    assert not acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                                   [steth_token, ldo_holder.address, amount])
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(steth_token, ldo_holder.address, amount, 'Should be reverted',
                                    {'from': ldo_holder})


@given(amount=strategy('uint', min_value=1, max_value=steth_limit))
def test_permission_pass_for_steth(acl, finance, ldo_holder, amount):
    assert acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [steth_token, ldo_holder.address, amount])
    finance.newImmediatePayment(steth_token, ldo_holder.address, amount, 'test', {'from': ldo_holder})


@given(amount=strategy('uint', min_value=ldo_limit + 1))
def test_permission_fails_for_ldo(acl, finance, ldo_holder, amount):
    assert not acl.hasPermission['address,address,bytes32,uint[]'](ldo_token, finance,
                                                                   finance.CREATE_PAYMENTS_ROLE(),
                                                                   [steth_token, ldo_holder.address, amount])
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(ldo_token, ldo_holder.address, amount, 'Should be reverted',
                                    {'from': ldo_holder})


@given(amount=strategy('uint', min_value=1, max_value=ldo_limit))
def test_permission_pass_for_ldo(acl, finance, ldo_holder, amount):
    assert acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [ldo_token, ldo_holder.address, amount])
    finance.newImmediatePayment(ldo_token, ldo_holder.address, amount, 'test', {'from': ldo_holder})


@given(amount=strategy('uint', min_value=1))
def test_permission_fails_for_usdc(acl, finance, ldo_holder, amount):
    assert not acl.hasPermission['address,address,bytes32,uint[]'](ldo_holder, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                                   [usdc_token, ldo_holder.address, amount])
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(usdc_token, ldo_holder.address, amount, 'Should be reverted',
                                    {'from': ldo_holder})
