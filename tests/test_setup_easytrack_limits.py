"""
Tests for setup_easytrack_permissions.py
"""
import brownie
import pytest
from brownie.test import given, strategy

from event_validators.permission import validate_permission_revoke_event, validate_permission_grantp_event, \
    Permission
from scripts.setup_easytrack_limits import start_vote, evmscriptexecutor, amount_limits
from tx_tracing_helpers import count_vote_items_by_events, display_voting_events, \
    group_voting_events

permission = Permission(entity='0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977',
                        app='0xB9E5CBB9CA5b0d659238807E84D0176930753d86',
                        role='0x5de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc')

usdc_token = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'

eth = {
    'limit': 1_000 * (10 ** 18),
    'address': '0x0000000000000000000000000000000000000000',
}

steth = {
    'limit': 1_000 * (10 ** 18),
    'address': '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',
}

ldo = {
    'limit': 5_000_000 * (10 ** 18),
    'address': '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32',
}

dai = {
    'limit': 100_000 * (10 ** 18),
    'address': '0x6b175474e89094c44da98b954eedeac495271d0f',
}


@pytest.fixture(scope="module", autouse=True)
def voting_tx(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    return helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )


def has_payments_permission(acl, finance, sender, token, receiver, amount) -> bool:
    return acl.hasPermission['address,address,bytes32,uint[]'](sender, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [token, receiver, amount])


def test_setup_events(voting_tx):
    assert count_vote_items_by_events(voting_tx) == 2, "Incorrect voting items count"

    display_voting_events(voting_tx)

    evs = group_voting_events(voting_tx)

    validate_permission_revoke_event(evs[0], permission)

    validate_permission_grantp_event(evs[1], permission, amount_limits())


@given(amount=strategy('uint', min_value=1, max_value=eth['limit']))
def test_permission_pass_for_eth(acl, finance, ldo_holder, amount):
    assert has_payments_permission(acl, finance, evmscriptexecutor, eth['address'], ldo_holder.address, amount)
    finance.newImmediatePayment(eth['address'], ldo_holder.address, amount, 'test', {'from': evmscriptexecutor})


@given(amount=strategy('uint', min_value=1, max_value=steth['limit']))
def test_permission_pass_for_steth(acl, finance, ldo_holder, amount):
    assert has_payments_permission(acl, finance, evmscriptexecutor, steth['address'], ldo_holder.address, amount)
    finance.newImmediatePayment(steth['address'], ldo_holder.address, amount, 'test', {'from': evmscriptexecutor})


@given(amount=strategy('uint', min_value=1, max_value=ldo['limit']))
def test_permission_pass_for_ldo(acl, finance, ldo_holder, amount):
    assert has_payments_permission(acl, finance, evmscriptexecutor, ldo['address'], ldo_holder.address, amount)
    finance.newImmediatePayment(ldo['address'], ldo_holder.address, amount, 'test', {'from': evmscriptexecutor})


@given(amount=strategy('uint', min_value=1, max_value=dai['limit']))
def test_permission_pass_for_dai(acl, finance, ldo_holder, amount):
    assert has_payments_permission(acl, finance, evmscriptexecutor, dai['address'], ldo_holder.address, amount)

    # won't pass here because we don't have dai in treasury
    with brownie.reverts('VAULT_TOKEN_TRANSFER_REVERTED'):
        finance.newImmediatePayment(dai['address'], ldo_holder.address, amount, 'test', {'from': evmscriptexecutor})


@given(amount=strategy('uint', min_value=eth['limit'] + 1))
def test_permission_fails_for_eth(acl, finance, ldo_holder, amount):
    assert not has_payments_permission(acl, finance, evmscriptexecutor, eth['address'], ldo_holder.address, amount)
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(eth['address'], ldo_holder.address, amount, 'Should be reverted',
                                    {'from': evmscriptexecutor})


@given(amount=strategy('uint', min_value=steth['limit'] + 1))
def test_permission_fails_for_steth(acl, finance, ldo_holder, amount):
    assert not has_payments_permission(acl, finance, evmscriptexecutor, steth['address'], ldo_holder.address, amount)
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(steth['address'], ldo_holder.address, amount, 'Should be reverted',
                                    {'from': evmscriptexecutor})


@given(amount=strategy('uint', min_value=ldo['limit'] + 1))
def test_permission_fails_for_ldo(acl, finance, ldo_holder, amount):
    assert not has_payments_permission(acl, finance, evmscriptexecutor, ldo['address'], ldo_holder.address, amount)
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(ldo['address'], ldo_holder.address, amount, 'Should be reverted',
                                    {'from': evmscriptexecutor})


@given(amount=strategy('uint', min_value=dai['limit'] + 1))
def test_permission_fails_for_dai(acl, finance, ldo_holder, amount):
    assert not has_payments_permission(acl, finance, evmscriptexecutor, dai['address'], ldo_holder.address, amount)
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(dai['address'], ldo_holder.address, amount, 'Should be reverted',
                                    {'from': evmscriptexecutor})


@given(amount=strategy('uint', min_value=1))
def test_permission_fails_for_usdc(acl, finance, ldo_holder, amount):
    assert not has_payments_permission(acl, finance, evmscriptexecutor, usdc_token, ldo_holder.address, amount)
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(usdc_token, ldo_holder.address, amount, 'Should be reverted',
                                    {'from': evmscriptexecutor})


@pytest.mark.parametrize('token', [eth, steth, ldo, dai])
@given(amount=strategy('uint', min_value=1))
def test_permission_fails_for_other_sender(acl, finance, accounts, token, amount):
    assert not has_payments_permission(acl, finance, accounts[0].address, usdc_token, accounts[0].address, amount)
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(token['address'], accounts[0].address, amount, 'Should be reverted',
                                    {'from': accounts[0]})
