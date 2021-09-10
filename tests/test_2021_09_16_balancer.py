"""
Tests for voting 09/16/2021.
"""
import time
import pytest
from scripts.vote_2021_09_16 import start_vote
from utils.config import balancer_rewards_manager
from brownie import (interface, chain)


@pytest.fixture(scope='module')
def balancer_manager():
    return interface.BalancerReawardsManager(balancer_rewards_manager)


def test_common(balancer_manager, ldo_holder, helpers, accounts, dao_voting):

    assert balancer_manager.available_allocations() == 25000 * 10**18
    print('\n')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())
    chain.sleep(1631491200 - chain.time())  # Tuesday, 13 September 2021 
    chain.mine()
    print('\n')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())
    assert balancer_manager.available_allocations() == 50000 * 10**18

    chain.sleep(1631664000 - chain.time())  # Tuesday, 15 September 2021 
    chain.mine()

    balancer_allocator = balancer_manager.allocator()
    balancer_manager.seed_allocations(100, '0x00', 25000 * 10**18, {"from": balancer_allocator})
    assert balancer_manager.available_allocations() == 25000 * 10**18
    print('\n')
    print('Balancer allocates rewards')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())


    chain.sleep(1631750400 - chain.time())  # Tuesday, 17 September 2021 
    chain.mine()
    print('\n')
    print('Before votiong ')
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
    print('After votiong ')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())

    chain.sleep(1632096000 - chain.time())  # Tuesday, 17 September 2021 
    chain.mine()
    print('\n')
    print('Next week')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())
    assert balancer_manager.available_allocations() == 150000 * 10**18
    assert balancer_manager.rewards_limit_per_period() == 75000 * 10**18


    chain.sleep(1632700800 - chain.time())  # Tuesday, 17 September 2021 
    chain.mine()
    print('\n')
    print('Next week')
    print(time.ctime(chain.time()), 'allowance: ', balancer_manager.available_allocations())
    print('                                ', 'rate: ', balancer_manager.rewards_limit_per_period())
    assert balancer_manager.available_allocations() == 225000 * 10**18
    assert balancer_manager.rewards_limit_per_period() == 75000 * 10**18
