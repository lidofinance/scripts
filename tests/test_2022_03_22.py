"""
Tests for voting 22/03/2022.
"""
from scripts.vote_2022_03_22 import start_vote
from tx_tracing_helpers import *

ldo_amount: int = 3_700_000 * 10 ** 18 # FIXME: CHANGE IT
source_address: str = '0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2' #FIXME: CHANGE IT
target_address: str = '0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc' #FIXME: CHANGE IT

start: int = 1639785600   # Sat Dec 18 2021 00:00:00 GMT+0000 (3 months ago) #FIXME: CHANGE IT
cliff: int = 1639785600   # Sat Dec 18 2021 00:00:00 GMT+0000 (3 months ago) #FIXME: CHANGE IT
vesting: int = 1671321600 # Sun Dec 18 2022 00:00:00 GMT+0000 (in 9 months) #FIXME: CHANGE IT

lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

def test_ldo_recover(
    helpers, accounts, ldo_holder, dao_voting,
    ldo_token, dao_token_manager, acl,
    vote_id_from_env, bypass_events_decoding
):
    total_supply_before = ldo_token.totalSupply()
    source_balance_before = ldo_token.balanceOf(source_address)
    target_balance_before = ldo_token.balanceOf(target_address)
    token_manager_balance_before = ldo_token.balanceOf(dao_token_manager)
    vesting_length_before = dao_token_manager.vestingsLengths(target_address)

    assert not acl.hasPermission(dao_voting, dao_token_manager, dao_token_manager.BURN_ROLE())
    assert not acl.hasPermission(dao_voting, dao_token_manager, dao_token_manager.ISSUE_ROLE())

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    total_supply_after = ldo_token.totalSupply()
    source_balance_after= ldo_token.balanceOf(source_address)
    target_balance_after = ldo_token.balanceOf(target_address)
    token_manager_balance_after = ldo_token.balanceOf(dao_token_manager)
    vesting_length_after = dao_token_manager.vestingsLengths(target_address)

    assert total_supply_before == total_supply_after, "Total supply changed"
    assert source_balance_before == source_balance_after + ldo_amount, "Incorrect LDO amount"
    assert target_balance_before == target_balance_after - ldo_amount, "Incorrect LDO amount"
    assert token_manager_balance_before == token_manager_balance_after, "Incorrect LDO amount"

    assert not acl.hasPermission(dao_voting, dao_token_manager, dao_token_manager.BURN_ROLE())
    assert not acl.hasPermission(dao_voting, dao_token_manager, dao_token_manager.ISSUE_ROLE())

    assert vesting_length_after == vesting_length_before + 1, "Incorrect vestings length"

    vesting_params = dao_token_manager.getVesting(target_address, vesting_length_before)

    assert vesting_params['amount'] == ldo_amount
    assert vesting_params['start'] == start
    assert vesting_params['cliff'] == cliff
    assert vesting_params['vesting'] == vesting
    assert vesting_params['revokable'] == False

    ### validate vote events
    assert count_vote_items_by_events(tx) == 7, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return
