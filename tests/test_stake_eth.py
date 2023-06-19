"""
Tests for voting

"""
from scripts.vote_stake_eth import start_vote

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.helpers import almostEqWithDiff
from utils.test.event_validators.common import validate_events_chain

from brownie import ZERO_ADDRESS

#####
# CONSTANTS
#####

STETH_ERROR_MARGIN = 2
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
STETH = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"

def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
):
    agent = interface.Agent(AGENT)
    stETH_token = interface.StETH(STETH)

    agent_steth_balance_before = stETH_token.balanceOf(agent.address)
    agent_eth_balance_before = agent.balance()

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

     # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"

    display_voting_events(vote_tx)

    agent_steth_balance_after = stETH_token.balanceOf(agent.address)
    agent_eth_balance_after = agent.balance()

    assert almostEqWithDiff(agent_steth_balance_after, agent_steth_balance_before + agent_eth_balance_before, STETH_ERROR_MARGIN)
    assert agent_eth_balance_after == 0

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_submit_event(evs[0], agent_eth_balance_before, stETH_token)


def validate_submit_event(event: EventDict, value: int, steth: any):
    _events_chain = ["LogScriptCall", "Submitted", "Transfer", "TransferShares", "Execute", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event["Submitted"]["sender"] == AGENT
    assert event["Submitted"]["amount"] == value
    assert event["Submitted"]["referral"] == ZERO_ADDRESS

    assert event["Transfer"]["from"] == ZERO_ADDRESS
    assert event["Transfer"]["to"] == AGENT
    assert almostEqWithDiff(event["Transfer"]["value"], value, STETH_ERROR_MARGIN)

    assert event["TransferShares"]["from"] == ZERO_ADDRESS
    assert event["TransferShares"]["to"] == AGENT
    assert almostEqWithDiff(event["TransferShares"]["sharesValue"], steth.getSharesByPooledEth(value), STETH_ERROR_MARGIN)

    assert event["Execute"]["sender"] == VOTING
    assert event["Execute"]["target"] == STETH
    assert event["Execute"]["ethValue"] == value
    assert event["Execute"]["data"] == steth.submit.encode_input(ZERO_ADDRESS)
