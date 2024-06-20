"""
Tests for voting 24/01/2023.
"""

from scripts.vote_2024_07_02 import start_vote
from utils.config import contracts
from utils.mainnet_fork import chain_snapshot
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    validate_token_payout_event,
    Payout,
)
from brownie.network.transaction import TransactionReceipt

agent_addr = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
expected_sdvt_module = StakingModuleItem(
    id=2,
    address="0x7c40c393DC0f283F318791d746d894DdD3693572",
    name="Simple DVT Module",
    target_share=400,
    module_fee=800,
    treasury_fee=200,
)
expected_payout = Payout(
    token_addr="0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",
    from_addr=agent_addr,
    to_addr="0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
    # https://docs.lido.fi/multisigs/lido-contributors-group#41-pool-maintenance-labs-ltd-pml
    amount=180_000 * (10**18),  # 180K LDO in wei,
)


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding):
    dao_voting = contracts.voting
    ldo_token = contracts.ldo_token

    agent_ldo_before = ldo_token.balanceOf(agent_addr)
    pml_balance_before = ldo_token.balanceOf(expected_payout.to_addr)
    sdvtModuleShareBefore = contracts.staking_router.getStakingModule(expected_sdvt_module.id)["targetShare"]
    assert sdvtModuleShareBefore == 50, "Simple DVT Module target share must be 0.5% before vote"

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
        sdvtModule = contracts.staking_router.getStakingModule(expected_sdvt_module.id)
        assert (
            sdvtModule["targetShare"] == expected_sdvt_module.target_share
        ), "Simple DVT Module target share must be updated correctly"

        # Check LDO payment
        assert (
            agent_ldo_before == ldo_token.balanceOf(agent_addr) + expected_payout.amount
        ), "DAO Agent LDO balance must decrease by the correct amount"
        assert (
            ldo_token.balanceOf(expected_payout.to_addr) == pml_balance_before + expected_payout.amount
        ), "Destination address LDO balance must increase by the correct amount"

        # Check events if their decoding is available
        if bypass_events_decoding:
            return

        display_voting_events(tx)

        evs = group_voting_events(tx)
        validate_staking_module_update_event(evs[0], expected_sdvt_module)
        validate_token_payout_event(evs[1], expected_payout)
