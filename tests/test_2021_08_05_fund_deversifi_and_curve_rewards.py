from brownie import interface
from utils.config import (ldo_token_address)
from scripts.vote_2021_08_05_fund_deversifi_and_curve_rewards import (start_vote)

def test_send_funds(ldo_holder, helpers, accounts, dao_voting):

    ldo = interface.ERC20(ldo_token_address)

    ops_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    ops_ldo_balance_before = ldo.balanceOf(ops_address)

    reward_manager_address = '0x753D5167C31fBEB5b49624314d74A957Eb271709'
    reward_manager_ldo_balance_before = ldo.balanceOf(reward_manager_address)

    assert ops_ldo_balance_before == 0
    assert reward_manager_ldo_balance_before == 0

    (vote_id, _) = start_vote({"from": ldo_holder}, silent=True)
    print(f'Vote {vote_id} created')
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting)
    print(f'Vote {vote_id} executed')

    ops_ldo_balance_after = ldo.balanceOf(ops_address)
    reward_manager_ldo_balance_after = ldo.balanceOf(reward_manager_address)

    assert ops_ldo_balance_after - ops_ldo_balance_before == 97680*10**18
    assert reward_manager_ldo_balance_after - reward_manager_ldo_balance_before == 3_750_000*10**18
