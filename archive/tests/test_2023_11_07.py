"""
Tests for voting 07/11/2023

"""

from scripts.vote_2023_11_07 import start_vote
from brownie import interface
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    Payout,
    validate_token_payout_event
)
from utils.test.event_validators.permission import Permission
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    NodeOperatorNameSetItem,
)
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    LIDO,
    AGENT
)

def test_vote(
    helpers,
    accounts,
    vote_ids_from_env
):
    rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
    pml_multisig_address = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
    atc_multisig_address = "0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956"

    rcc_multisig_balance_before = contracts.lido.balanceOf(rcc_multisig_address)
    pml_multisig_balance_before = contracts.lido.balanceOf(pml_multisig_address)
    atc_multisig_balance_before = contracts.lido.balanceOf(atc_multisig_address)
    dao_balance_before = contracts.lido.balanceOf(AGENT)

    NO_registry = interface.NodeOperatorsRegistry(contracts.node_operators_registry)
    prysmatic_labs_node_id = 27
    prysmatic_labs_node_old_name = "Prysmatic Labs"
    prysmatic_labs_node_new_name = "Prysm Team at Offchain Labs"
    prysmatic_labs_node_data_before_voting = NO_registry.getNodeOperator(prysmatic_labs_node_id, True)

    # Check node operator name before
    assert prysmatic_labs_node_data_before_voting["name"] == prysmatic_labs_node_old_name, "Incorrect NO#27 name before"

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    rcc_multisig_balance_after = contracts.lido.balanceOf(rcc_multisig_address)
    pml_multisig_balance_after = contracts.lido.balanceOf(pml_multisig_address)
    atc_multisig_balance_after = contracts.lido.balanceOf(atc_multisig_address)
    dao_balance_after = contracts.lido.balanceOf(AGENT)

    rcc_fund_payout = Payout(token_addr=LIDO, from_addr=contracts.agent, to_addr=rcc_multisig_address, amount=272 * (10**18))
    pml_fund_payout = Payout(token_addr=LIDO, from_addr=contracts.agent, to_addr=pml_multisig_address, amount=434 * (10**18))
    atc_fund_payout = Payout(token_addr=LIDO, from_addr=contracts.agent, to_addr=atc_multisig_address, amount=380 * (10**18))

    steth_balance_checker(rcc_multisig_balance_after - rcc_multisig_balance_before, rcc_fund_payout.amount)
    steth_balance_checker(pml_multisig_balance_after - pml_multisig_balance_before, pml_fund_payout.amount)
    steth_balance_checker(atc_multisig_balance_after - atc_multisig_balance_before, atc_fund_payout.amount)
    steth_balance_checker(dao_balance_before - dao_balance_after, rcc_fund_payout.amount + pml_fund_payout.amount + atc_fund_payout.amount)

    # node operator name
    prysmatic_labs_node_data_after_voting = NO_registry.getNodeOperator(prysmatic_labs_node_id, True)

    assert prysmatic_labs_node_data_before_voting["active"] == prysmatic_labs_node_data_after_voting["active"]
    assert prysmatic_labs_node_data_after_voting["name"] == prysmatic_labs_node_new_name, "Incorrect NO#27 name after"
    assert prysmatic_labs_node_data_before_voting["rewardAddress"] == prysmatic_labs_node_data_after_voting["rewardAddress"]
    compare_NO_validators_data(prysmatic_labs_node_data_before_voting, prysmatic_labs_node_data_after_voting)

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 4, "Incorrect voting items count"

    display_voting_events(vote_tx)

    evs = group_voting_events(vote_tx)

    validate_token_payout_event(evs[0], rcc_fund_payout, True)
    validate_token_payout_event(evs[1], pml_fund_payout, True)
    validate_token_payout_event(evs[2], atc_fund_payout, True)
    validate_node_operator_name_set_event(evs[3], NodeOperatorNameSetItem(nodeOperatorId=prysmatic_labs_node_id, name=prysmatic_labs_node_new_name))

def steth_balance_checker(lhs_value: int, rhs_value: int):
    assert (lhs_value + 5) // 10 == (rhs_value + 5) // 10

def compare_NO_validators_data(data_before, data_after):
    assert data_before["totalVettedValidators"] == data_after["totalVettedValidators"]
    assert data_before["totalExitedValidators"] == data_after["totalExitedValidators"]
    assert data_before["totalAddedValidators"] == data_after["totalAddedValidators"]
    assert data_before["totalDepositedValidators"] == data_after["totalDepositedValidators"]