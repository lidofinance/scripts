"""
Tests for voting 26/04/2022.
"""
from scripts.archive.vote_2022_04_26 import start_vote
from tx_tracing_helpers import *

ldo_amount: int = 650_000 * 10 ** 18
vesting_start = 1649631600
vesting_cliff = 1649631600
vesting_end = 1712790000

token_manager = '0xf73a1260d222f447210581DDf212D915c09a3249'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'
chorus_one_address = '0x3983083d7fa05f66b175f282ffd83e0d861c777a'


def test_2022_04_26(
    helpers, accounts, ldo_holder, dao_voting,
    ldo_token, dao_token_manager,
    vote_id_from_env, bypass_events_decoding
):
    total_supply_before = ldo_token.totalSupply()
    chorus_balance_before = ldo_token.balanceOf(chorus_one_address)
    token_manager_balance_before = ldo_token.balanceOf(dao_token_manager)

    chorus_vesting_length_before  = dao_token_manager.vestingsLengths(chorus_one_address)

    assert chorus_vesting_length_before == 0, "Incorrect vesting length"

    assert token_manager_balance_before == 0, "Incorrect LDO amount"
    assert chorus_balance_before == 0, "Incorrect Chorus LDO ammount"

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    total_supply_after = ldo_token.totalSupply()
    chorus_balance_after = ldo_token.balanceOf(chorus_one_address)
    token_manager_balance_after = ldo_token.balanceOf(dao_token_manager)

    assert total_supply_after == total_supply_before, "Total supply changed"
    assert chorus_balance_after == chorus_balance_before + ldo_amount, "Incorrect LDO amount"
    assert token_manager_balance_after == token_manager_balance_before, "Incorrect LDO amount"

    chorus_vesting_length_after  = dao_token_manager.vestingsLengths(chorus_one_address)
    assert chorus_vesting_length_after == 1, "Incorrect vesting length "

    [amount, start, cliff, end, revokable] = dao_token_manager.getVesting(chorus_one_address, 0)

    assert amount == ldo_amount, "invalid amount"
    assert start == vesting_start, "Invalid start date"
    assert cliff == vesting_cliff, "Invalid cliff date"
    assert end == vesting_end, "Invalid vested date"
    assert revokable == False, "Should not be revokable"

    ### validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 2, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return
