"""
Tests for voting 18/11/2021.
"""
import pytest
from collections import namedtuple
from brownie import network

from scripts.vote_2021_11_18 import start_vote

Payout = namedtuple(
    'Payout', ['address', 'amount']
)

Burn = namedtuple(
    'Burn', ['address', 'amount']
)

NodeOperatorIncLimit = namedtuple(
    'NodeOperatorIncLimit', ['name', 'id', 'limit'],
)

LidoDomain = namedtuple(
    'LidoDomain', ['name', 'address'],
)

rockx_limits = NodeOperatorIncLimit(
    name='RockX', 
    id=9, 
    limit=2100);


token_purchase_contract_address = '0x689E03565e36B034EcCf12d182c3DC38b2Bb7D33'
jacob_payout = Payout(
    address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
    amount=4_219_7469 * (10 ** 14)
)
isidoros_payout = Payout(
    address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
    amount=2_531_9495 * (10 ** 14)
)
oneinch_payout = Payout(
    address='0xf5436129Cf9d8fa2a1cb6e591347155276550635',
    amount=50_000 * (10 ** 18)
)

treasury_burn  = Burn(
    address='0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c',
    amount=500 * (10 ** 18)
)

lido_old = LidoDomain(
    name='lido.eth',
    address='0x06601571AA9D3E8f5f7CDd5b993192618964bAB5'
)
lido_new = LidoDomain(
    name='lido.eth',
    address='0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
)

def test_2021_11_18(ldo_holder, helpers, accounts, dao_voting, ldo_token, lido, node_operators_registry):
    finance_balance_before = ldo_token.balanceOf(jacob_payout.address)
    oneinch_payout_balance_before = ldo_token.balanceOf(oneinch_payout.address)
    treasury_before = lido.sharesOf(treasury_burn.address)

    rockx_limit_before = node_operators_registry.getNodeOperator( rockx_limits.id, True )[3]

    lido_domain_addr_before = network.web3.ens.resolve('lido.eth')
    assert lido_old.address == lido_domain_addr_before


    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    lido_domain_addr_after = network.web3.ens.resolve('lido.eth')
    assert lido_new.address == lido_domain_addr_after

    rockx_limit_after = node_operators_registry.getNodeOperator( rockx_limits.id, True )[3]
    assert rockx_limit_after > rockx_limit_before
    assert rockx_limit_after - rockx_limits.limit == 0

    finance_balance_after = ldo_token.balanceOf(jacob_payout.address)
    oneinch_payout_balance_after = ldo_token.balanceOf(oneinch_payout.address)
    treasury_after = lido.sharesOf(treasury_burn.address)

    assert finance_balance_after - finance_balance_before == jacob_payout.amount + isidoros_payout.amount
    assert oneinch_payout_balance_after - oneinch_payout_balance_before == oneinch_payout.amount
    assert treasury_before - treasury_after == treasury_burn.amount
