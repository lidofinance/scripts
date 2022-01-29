"""
Tests for voting 20/01/2022.
"""

from scripts.vote_adding_permission import start_vote
from brownie import interface
from brownie import network
from tx_tracing_helpers import *
from utils.finance import ZERO_ADDRESS

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'


def test(
        helpers, accounts, ldo_holder, dao_voting, ldo_token,
        vote_id_from_env, finance
) -> None:
    ##
    # START VOTE
    ##

    network.priority_fee('1 wei')

    accounts[1].transfer(ldo_holder, '10 ether')

    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='5 ether'
    )

    # try to do a handful of wrong transactions and check balances
    tx: TransactionReceipt = finance.newImmediatePayment(ZERO_ADDRESS, ldo_holder, 1001, 'Should be reverted',
                                                         {'from': ldo_holder})

    

    # try to do a handful of right transactions and check balances

    # parse Remove Permission and AddPermission Events
