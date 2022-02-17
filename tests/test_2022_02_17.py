"""
Tests for voting 20/01/2022.
"""

from brownie import interface

from event_validators.permission import validate_permission_revoke_event, validate_permission_grantp_event, \
    Permission

from scripts.vote_2022_02_17 import amount_limits, start_vote
from tx_tracing_helpers import *

from event_validators.payout import Payout, validate_payout_event

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

referral_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=147_245 * (10 ** 18)
)

isidoros_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=6_400 * (10 ** 18)
)

jacob_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=10_700 * (10 ** 18)
)

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

permission = Permission(entity='0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977',
                        app='0xB9E5CBB9CA5b0d659238807E84D0176930753d86',
                        role='0x5de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc')

usdc_token = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'


def has_payments_permission(acl, finance, sender, token, receiver, amount) -> bool:
    return acl.hasPermission['address,address,bytes32,uint[]'](sender, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [token, receiver, amount])


def test_2022_02_17(
        helpers, accounts, ldo_holder, dao_voting, ldo_token,
        vote_id_from_env, bypass_events_decoding, acl, finance,
):
    multisig_balance_before = ldo_token.balanceOf(finance_multisig_address)
    dao_balance_before = ldo_token.balanceOf(dao_agent_address)

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.37 ether'
    )

    multisig_balance_after = ldo_token.balanceOf(finance_multisig_address)
    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    assert multisig_balance_after - multisig_balance_before == isidoros_payout.amount + jacob_payout.amount + referral_payout.amount
    assert dao_balance_before - dao_balance_after == isidoros_payout.amount + jacob_payout.amount + referral_payout.amount

    assert has_payments_permission(acl, finance, permission.entity, eth['address'], ldo_holder.address, eth['limit'])
    assert has_payments_permission(acl, finance, permission.entity, steth['address'], ldo_holder.address,
                                   steth['limit'])
    assert has_payments_permission(acl, finance, permission.entity, ldo['address'], ldo_holder.address, ldo['limit'])
    assert has_payments_permission(acl, finance, permission.entity, dai['address'], ldo_holder.address, dai['limit'])

    assert not has_payments_permission(acl, finance, permission.entity, eth['address'], ldo_holder.address,
                                       eth['limit'] + 1)
    assert not has_payments_permission(acl, finance, permission.entity, steth['address'], ldo_holder.address,
                                       steth['limit'] + 1)
    assert not has_payments_permission(acl, finance, permission.entity, ldo['address'], ldo_holder.address,
                                       ldo['limit'] + 1)
    assert not has_payments_permission(acl, finance, permission.entity, dai['address'], ldo_holder.address,
                                       dai['limit'] + 1)

    assert not has_payments_permission(acl, finance, accounts[0].address, eth['address'], ldo_holder.address,
                                       eth['limit'])
    assert not has_payments_permission(acl, finance, accounts[0].address, usdc_token, ldo_holder.address, 1)

    ### validate vote events
    assert count_vote_items_by_events(tx) == 5, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_payout_event(evs[0], referral_payout)

    # asserts on vote item 2
    validate_payout_event(evs[1], isidoros_payout)

    # asserts on vote item 3
    validate_payout_event(evs[2], jacob_payout)

    # asserts on vote item 4
    validate_permission_revoke_event(evs[3], permission)

    # asserts on vote item 5
    validate_permission_grantp_event(evs[4], permission, amount_limits())
