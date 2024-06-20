"""
Tests for voting 24/01/2023.
"""

from configs.config_mainnet import VOTING, LDO_TOKEN, AGENT, SIMPLE_DVT_MODULE_ID
from scripts.vote_2024_07_02 import start_vote, payout
from utils.config import ContractsLazyLoader
from utils.mainnet_fork import chain_snapshot
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    validate_token_payout_event,
)
from brownie.network.transaction import TransactionReceipt


def test_vote(
    helpers,
    accounts,
    ldo_holder,
    vote_ids_from_env,
    bypass_events_decoding,
):
    contracts = ContractsLazyLoader()
    dao_voting = contracts.voting
    ldo_token = contracts.ldo_token

    agent_ldo_before = ldo_token.balanceOf(AGENT)
    pml_balance_before = ldo_token.balanceOf(payout.to_addr)
    sdvtModuleShareBefore = contracts.staking_router.getStakingModule(SIMPLE_DVT_MODULE_ID)["targetShare"]
    assert sdvtModuleShareBefore == 50, "Simple DVT Module target share must be 50%"

    with chain_snapshot():
        # START VOTE
        vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

        tx: TransactionReceipt = helpers.execute_vote(
            vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
        )

        # Validate vote events
        if not bypass_events_decoding:
            assert count_vote_items_by_events(tx, dao_voting) == 2, "Incorrect voting items count"

        # Check Simple DVT Module target share
        sdvtModule = contracts.staking_router.getStakingModule(SIMPLE_DVT_MODULE_ID)
        assert sdvtModule["targetShare"] == 400, "Simple DVT Module target share must be updated correctly"

        # Check LDO payment
        assert (
            agent_ldo_before == ldo_token.balanceOf(AGENT) + payout.amount
        ), "DAO Agent LDO balance must decrease by the correct amount"
        assert (
            ldo_token.balanceOf(payout.to_addr) == pml_balance_before + payout.amount
        ), "Destination address LDO balance must increase by the correct amount"

        # Check events if their decoding is available
        if bypass_events_decoding:
            return

        display_voting_events(tx)

        evs = group_voting_events(tx)
        validate_token_payout_event(evs[1], payout)
