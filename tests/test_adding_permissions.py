"""
Tests for voting 20/01/2022.
"""

import brownie

from scripts.vote_adding_permission import start_vote, eth_limit, steth_limit, ldo_limit, safety_permission_params
from tx_tracing_helpers import *
from utils.finance import ZERO_ADDRESS

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'
lido_dao_steth_address = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
aragon_eth_pseudoaddress = ZERO_ADDRESS


def check_that_permission_works(deployer, finance, receiver, token_address, limit):
    finance.newImmediatePayment(token_address, receiver, limit, 'Should not be reverted', {'from': deployer})
    with brownie.reverts('APP_AUTH_FAILED'):
        finance.newImmediatePayment(token_address, receiver, limit + 1, 'Should be reverted', {'from': deployer})


def test(
        helpers, accounts, ldo_holder, dao_voting, ldo_token,
        vote_id_from_env, finance, acl
) -> None:
    ##
    # START VOTE
    ##

    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )

    assert count_vote_items_by_events(tx) == 1

    # ETH transfer
    check_that_permission_works(ldo_holder, finance, ldo_holder.address, aragon_eth_pseudoaddress, eth_limit)

    # stETH transfer
    check_that_permission_works(ldo_holder, finance, ldo_holder.address, lido_dao_steth_address, steth_limit)

    # LDO transfer
    check_that_permission_works(ldo_holder, finance, ldo_holder.address, ldo_token.address, ldo_limit)
