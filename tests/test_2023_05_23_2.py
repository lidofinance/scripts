"""
Tests for voting 25/04/2023 — take 2.

"""
from scripts.vote_2023_05_23_2 import start_vote

from brownie import chain, accounts, web3
from brownie.network.transaction import TransactionReceipt
from eth_abi.abi import encode_single

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    validate_node_operator_reward_address_set_event,
    validate_target_validators_count_changed_event,
    NodeOperatorNameSetItem,
    NodeOperatorRewardAddressSetItem,
    TargetValidatorsCountChanged,
)
from utils.test.event_validators.burner import StETH_burn_requested, validate_burn_requested_event
from utils.test.event_validators.payout import Payout, validate_token_payout_event
from utils.test.event_validators.token import Approve, validate_approval_event
from utils.test.event_validators.vault import transferERC20, validate_transferERC20_event
from utils.test.event_validators.easy_track import (
    validate_motions_count_limit_changed_event,
)
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items
from utils.test.helpers import almostEqWithDiff
import math

#####
# CONSTANTS
#####

STETH_ERROR_MARGIN = 2

def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
    ldo_holder,
    stranger,
):

    ## parameters
    finance = contracts.finance
    agent = contracts.agent
    insurance_fund = contracts.insurance_fund
    burner = contracts.burner
    lido = contracts.lido
    node_operators_registry = contracts.node_operators_registry
    rewards_multisig_address = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
    staking_router = contracts.staking_router
    staking_module_id = 1
    target_NO_id = 12

    # "web3.keccak(text="REQUEST_BURN_MY_STETH_ROLE")
    REQUEST_BURN_MY_STETH_ROLE = "0x28186f938b759084eea36948ef1cd8b40ec8790a98d5f1a09b70879fe054e5cc"
    # web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    stETH_token = interface.ERC20("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")

    agent_balance_before = stETH_token.balanceOf(agent.address)
    rewards_balance_before = stETH_token.balanceOf(rewards_multisig_address)
    insurance_fund_balance_before = stETH_token.balanceOf(insurance_fund.address)
    shares_requested_to_burn_before = burner.getSharesRequestedToBurn()
    NO_summary_before = node_operators_registry.getNodeOperatorSummary(target_NO_id)
    cover_funding = transferERC20(
        token_addr=stETH_token.address,
        from_addr=insurance_fund.address,
        to_addr=agent.address,
        amount=13.45978634 * (10 ** 18)
    )
    cover_approval = Approve(
        owner=agent.address,
        spender=burner.address,
        amount=cover_funding.amount 
    )
    rewards_payout = Payout(
        token_addr=stETH_token.address,
        from_addr=agent.address,
        to_addr=rewards_multisig_address,
        amount=170 * (10 ** 18)
    )    
    shares_to_burn = lido.getSharesByPooledEth(cover_funding.amount)
    
    burn_request = StETH_burn_requested(
        amountOfStETH=cover_funding.amount,
        amountOfShares=shares_to_burn,
        requestedBy=agent.address,
        isCover=True
    )
    target_validators_count_change_request = TargetValidatorsCountChanged(
        nodeOperatorId=12,
        targetValidatorsCount=0
    )
    # 1.
    easy_track = contracts.easy_track
    motionsCountLimit_before = 12
    motionsCountLimit_expected = 20  

    # 1.
    easy_track.motionsCountLimit() == motionsCountLimit_before, "Incorrect motions count limit before"    


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

     # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 10, "Incorrect voting items count"

    display_voting_events(vote_tx)    

    agent_balance_after = stETH_token.balanceOf(agent.address)
    rewards_balance_after = stETH_token.balanceOf(rewards_multisig_address)
    insurance_fund_balance_after = stETH_token.balanceOf(insurance_fund.address)
    shares_requested_to_burn_after = burner.getSharesRequestedToBurn()
    NO_summary_after = node_operators_registry.getNodeOperatorSummary(target_NO_id)

    assert almostEqWithDiff(agent_balance_after, agent_balance_before - rewards_payout.amount, STETH_ERROR_MARGIN)
    assert almostEqWithDiff(rewards_balance_after, rewards_balance_before + rewards_payout.amount, STETH_ERROR_MARGIN)
    assert almostEqWithDiff(insurance_fund_balance_after, insurance_fund_balance_before - cover_funding.amount, STETH_ERROR_MARGIN)

    assert NO_summary_after[0]
    assert NO_summary_after[1] == 0
    assert NO_summary_after[2] == 0
    assert NO_summary_after[3] == 0
    assert NO_summary_after[4] == 0
    assert NO_summary_after[5] == 0
    assert NO_summary_after[6] == 2300
    assert NO_summary_after[7] == 0

    assert shares_requested_to_burn_after[0] == shares_to_burn
    assert shares_requested_to_burn_after[1] == 0
    
    easy_track.motionsCountLimit() == motionsCountLimit_expected, "Incorrect motions count limit after"    

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_transferERC20_event(evs[0], cover_funding, True)        
    validate_approval_event(evs[1], cover_approval)
    validate_grant_role_event(evs[2], REQUEST_BURN_MY_STETH_ROLE, agent.address, agent.address)    
    validate_burn_requested_event(evs[3], burn_request)

    validate_revoke_role_event(evs[4], REQUEST_BURN_MY_STETH_ROLE, agent.address, agent.address)
    
    validate_grant_role_event(evs[5], STAKING_MODULE_MANAGE_ROLE, agent.address, agent.address)
    #evs[6] — set targetLimit
    validate_target_validators_count_changed_event(evs[6], target_validators_count_change_request)
    
    validate_revoke_role_event(evs[7], STAKING_MODULE_MANAGE_ROLE, agent.address, agent.address)
    
    validate_token_payout_event(evs[8], rewards_payout, True)
    
    validate_motions_count_limit_changed_event(
        evs[9],
        motionsCountLimit_expected
    )
