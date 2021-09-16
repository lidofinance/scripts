"""
Tests for voting 09/16/2021.
"""
import time
import pytest
from scripts.vote_2021_09_16 import start_vote
from collections import namedtuple
from utils.config import (balancer_rewards_manager, ldo_token_address)
from brownie import (interface, chain)


@pytest.fixture(scope='module')
def balancer_manager():
    return interface.BalancerReawardsManager(balancer_rewards_manager)

@pytest.fixture(scope='module')
def ldo():
    return interface.ERC20(ldo_token_address)


def test_2021_09_16_balancer(balancer_manager, ldo_holder, helpers, accounts, dao_voting):

    chain.sleep(1631750400 - chain.time())  # Tuesday, 17 September 2021
    chain.mine()
    print('\n')
    print('Before voting ')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())
    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    assert balancer_manager.available_allocations() == 75000 * 10**18
    assert balancer_manager.rewards_limit_per_period() == 75000 * 10**18
    print('\n')
    print('After voting ')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())

    chain.sleep(1632096000 - chain.time())  # 20 September 2021
    chain.mine()
    print('\n')
    print('Next week')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())
    assert balancer_manager.available_allocations() == 150000 * 10**18
    assert balancer_manager.rewards_limit_per_period() == 75000 * 10**18


    chain.sleep(1632700800 - chain.time())  # 27 September 2021
    chain.mine()
    print('\n')
    print('Next week')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())
    assert balancer_manager.available_allocations() == 225000 * 10**18
    assert balancer_manager.rewards_limit_per_period() == 75000 * 10**18


NodeOperatorIncLimit = namedtuple(
    'NodeOperatorIncLimit', ['name', 'id', 'limit'],
)
Payout = namedtuple(
    'Payout', ['address', 'amount', 'reference']
)

NODE_OPERATORS = [
    # name, id, limit
    NodeOperatorIncLimit('Everstake', 7, 3980),
    NodeOperatorIncLimit('RockX', 9, 1150),
    NodeOperatorIncLimit('Figment', 10, 1000),
    NodeOperatorIncLimit('Allnodes', 11, 5000),
    NodeOperatorIncLimit('Anyblock Analytics', 12, 1800),
]


def test_2021_09_16(balancer_manager, ldo_holder, helpers, accounts, dao_voting, ldo, node_operators_registry):

    _1inch_reward_address = '0xf5436129Cf9d8fa2a1cb6e591347155276550635'
    _1inch_reward_balance_before = ldo.balanceOf(_1inch_reward_address)

    referral_payout_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    referral_payout_balance_before = ldo.balanceOf(referral_payout_address)

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    for node_operator in NODE_OPERATORS:
        assert node_operators_registry.getNodeOperator(
            node_operator.id, True
        )[3] == node_operator.limit, f'Failed on {node_operator.name}'

    _1inch_reward_balance_after = ldo.balanceOf(_1inch_reward_address)
    referral_payout_balance_after = ldo.balanceOf(referral_payout_address)

    assert _1inch_reward_balance_after - _1inch_reward_balance_before == 200_000 * 10**18
    assert referral_payout_balance_after - referral_payout_balance_before == 1_320_784 * 10**18

    assert balancer_manager.rewards_limit_per_period() == 75000 * 10**18
