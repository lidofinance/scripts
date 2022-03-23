"""
Tests for voting 22/03/2022.
"""
from scripts.vote_2022_03_22 import start_vote
from tx_tracing_helpers import *

ldo_amount: int = 3_691_500 * 10 ** 18
source_address: str = '0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2'

lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

def test_ldo_recover(
    helpers, accounts, ldo_holder, dao_voting,
    ldo_token, dao_token_manager, acl,
    vote_id_from_env, bypass_events_decoding
):
    total_supply_before = ldo_token.totalSupply()
    source_balance_before = ldo_token.balanceOf(source_address)
    token_manager_balance_before = ldo_token.balanceOf(dao_token_manager)

    assert not acl.hasPermission(dao_voting, dao_token_manager, dao_token_manager.BURN_ROLE())

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    total_supply_after = ldo_token.totalSupply()
    source_balance_after= ldo_token.balanceOf(source_address)
    token_manager_balance_after = ldo_token.balanceOf(dao_token_manager)

    assert total_supply_before == (total_supply_after + ldo_amount), "Total supply changed"
    assert source_balance_before == source_balance_after + ldo_amount, "Incorrect LDO amount"
    assert token_manager_balance_before == token_manager_balance_after, "Incorrect LDO amount"

    assert not acl.hasPermission(dao_voting, dao_token_manager, dao_token_manager.BURN_ROLE())

    ### validate vote events
    assert count_vote_items_by_events(tx) == 3, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return
