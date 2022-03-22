"""
Tests for voting 17/03/2022.
"""
import pytest
from event_validators.payout import Payout, validate_payout_event

from scripts.vote_2022_03_24_1inch_recover import start_vote
from tx_tracing_helpers import *

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
ONE_INCH_REWARDS_MANAGER = "0xf5436129Cf9d8fa2a1cb6e591347155276550635"
TOKENS_RECOVERER = '0xE7eD6747FaC5360f88a2EFC03E00d25789F69291'

@pytest.fixture()
def agent_eoa(accounts):
    return accounts.at(dao_agent_address, force = True)

@pytest.fixture()
def rewards_manager(interface):
    return interface.OneInchRewardsManager(ONE_INCH_REWARDS_MANAGER)

def test_2022_03_24_rewards_manager_has_tokens(
        helpers, accounts, ldo_holder, dao_voting, ldo_token,
        vote_id_from_env, bypass_events_decoding, agent_eoa
):

    rewards_manager_balance_before = ldo_token.balanceOf(ONE_INCH_REWARDS_MANAGER)
    # if rewards manager has no tokens transfer it from agent
    if rewards_manager_balance_before == 0:
        ldo_token.transfer(ONE_INCH_REWARDS_MANAGER, 10_000 * 10 ** 18, {"from": agent_eoa})
    rewards_manager_balance_before = ldo_token.balanceOf(ONE_INCH_REWARDS_MANAGER)
    assert rewards_manager_balance_before > 0

    dao_balance_before = ldo_token.balanceOf(dao_agent_address)

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.37 ether'
    )

    rewards_manager_balance_after = ldo_token.balanceOf(ONE_INCH_REWARDS_MANAGER)
    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    assert rewards_manager_balance_before - rewards_manager_balance_after == 50_000 * 10 ** 18
    assert dao_balance_after - dao_balance_before == 50_000 * 10 ** 18

    display_voting_events(tx)

    ### validate vote events
    assert count_vote_items_by_events(tx) == 5, "Incorrect voting items count" # 3 from voting + 2 from agent

def test_2022_03_24_rewards_manager_has_no_tokens(
        helpers, accounts, ldo_holder, dao_voting, ldo_token,
        vote_id_from_env, bypass_events_decoding, agent_eoa, rewards_manager
):

    rewards_manager_balance_before = ldo_token.balanceOf(ONE_INCH_REWARDS_MANAGER)
    # if rewards manager has no tokens transfer it from agent
    if rewards_manager_balance_before > 0:
        rewards_manager.recover_erc20(ldo_token, rewards_manager_balance_before, {"from": agent_eoa})
    rewards_manager_balance_before = ldo_token.balanceOf(ONE_INCH_REWARDS_MANAGER)
    assert rewards_manager_balance_before == 0

    dao_balance_before = ldo_token.balanceOf(dao_agent_address)

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.37 ether'
    )

    rewards_manager_balance_after = ldo_token.balanceOf(ONE_INCH_REWARDS_MANAGER)
    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    assert rewards_manager_balance_before == rewards_manager_balance_after
    assert dao_balance_after == dao_balance_before

    display_voting_events(tx)

    ### validate vote events
    assert count_vote_items_by_events(tx) == 5, "Incorrect voting items count" # 3 from voting + 2 from agent

