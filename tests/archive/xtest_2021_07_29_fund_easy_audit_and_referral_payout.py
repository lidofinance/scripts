from brownie import interface
from utils.config import (ldo_token_address)
from scripts.vote_2021_07_29_fund_easy_audit_and_referral_payout import (start_vote)


def test_send_funds(ldo_holder, helpers, accounts, dao_voting):
    ldo = interface.ERC20(ldo_token_address)

    ops_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    ops_acc = accounts.at(ops_address, force=True)
    ops_eth_balance_before = ops_acc.balance()
    ops_ldo_balance_before = ldo.balanceOf(ops_address)

    (vote_id, _) = start_vote({"from": ldo_holder}, silent=True)
    print(f'Vote {vote_id} created')
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting)
    print(f'Vote {vote_id} executed')

    ops_eth_balance_after = ops_acc.balance()
    ops_ldo_balance_after = ldo.balanceOf(ops_address)

    assert ops_eth_balance_after - ops_eth_balance_before == 39.9174659279 * 10 ** 18
    assert ops_ldo_balance_after - ops_ldo_balance_before == 250_000 * 10 ** 18
