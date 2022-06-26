from brownie import interface
from utils.config import (ldo_token_address)
from scripts.vote_2021_08_12_fund_sushi_lp_rewards_increase_no_limits import (start_vote)

NODE_OPERATORS = [
    {
        "id": 0,
        "limit": 3500
    },
    {
        "id": 6,
        "limit": 2000
    },
    {
        "id": 7,
        "limit": 2200
    },
    {
        "id": 8,
        "limit": 3001
    },
]


def test_vote(ldo_holder, helpers, accounts, dao_voting, node_operators_registry):
    ldo = interface.ERC20(ldo_token_address)

    ops_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    ops_ldo_balance_before = ldo.balanceOf(ops_address)

    assert ops_ldo_balance_before == 0

    (vote_id, _) = start_vote({"from": ldo_holder}, silent=True)
    print(f'Vote {vote_id} created')
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting)
    print(f'Vote {vote_id} executed')

    ops_ldo_balance_after = ldo.balanceOf(ops_address)

    assert ops_ldo_balance_after - ops_ldo_balance_before == 200_000 * 10 ** 18

    for node_operator in NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(node_operator["id"], True)
        assert node_operator["limit"] == no[3]
