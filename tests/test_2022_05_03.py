"""
Tests for voting 03/05/2022.
"""
from scripts.vote_2022_05_03 import start_vote

from event_validators.permission import (
    validate_permission_create_event,
    validate_permission_revoke_event,
    Permission
)

from event_validators.token_manager import (
    validate_ldo_issue_event,
    validate_ldo_vested_event,
    Issue,
    Vested
)

from tx_tracing_helpers import *

ldo_amount: int = 3_691_500 * 10 ** 18
lido_dao_token: str = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'
destination_address: str = '0xe15232f912D92077bF4fAd50dd7BFB0347AeF821'

create_permission: Permission = Permission(
    entity='0x2e59A20f205bB85a89C53f1936454680651E618e', # Voting
    app='0xf73a1260d222f447210581DDf212D915c09a3249', # Token Manager
    role='0x2406f1e99f79cea012fb88c5c36566feaeefee0f4b98d3a376b49310222b53c4' # keccak256('ISSUE_ROLE')
)

revoke_permission: Permission = create_permission

issue: Issue = Issue(
    token_manager_addr=create_permission.app,
    amount=ldo_amount
)

vested: Vested = Vested(
    destination_addr=destination_address,
    amount=ldo_amount,
    start=1648034400,
    cliff=1648034400,
    vesting=1671321600,
    revokable=False
)

def test_ldo_recover(
    helpers, accounts, ldo_holder, dao_voting,
    ldo_token, dao_token_manager, acl,
    vote_id_from_env, bypass_events_decoding
):
    total_supply_before = ldo_token.totalSupply()
    destination_balance_before = ldo_token.balanceOf(destination_address)
    token_manager_balance_before = ldo_token.balanceOf(dao_token_manager)

    vestings_before = dao_token_manager.vestingsLengths(destination_address)

    assert not acl.hasPermission(dao_voting, dao_token_manager, dao_token_manager.ISSUE_ROLE())

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    total_supply_after = ldo_token.totalSupply()
    destination_balance_after = ldo_token.balanceOf(destination_address)
    token_manager_balance_after = ldo_token.balanceOf(dao_token_manager)

    vestings_after = dao_token_manager.vestingsLengths(destination_address)
    assigned_vesting = dao_token_manager.getVesting(destination_address, vestings_before)

    assert assigned_vesting['amount'] == vested.amount
    assert assigned_vesting['start'] == vested.start
    assert assigned_vesting['cliff'] == vested.cliff
    assert assigned_vesting['vesting'] == vested.vesting
    assert assigned_vesting['revokable'] == vested.revokable

    assert total_supply_after == total_supply_before + ldo_amount, "Incorrect total supply"
    assert total_supply_after == 1_000_000_000 * 10 ** 18
    assert destination_balance_after == destination_balance_before + ldo_amount, "Incorrect LDO amount"
    assert token_manager_balance_before == token_manager_balance_after, "Incorrect LDO amount"
    assert vestings_after == vestings_before + 1, "Incorrect vestings length"

    assert not acl.hasPermission(dao_voting, dao_token_manager, dao_token_manager.ISSUE_ROLE())

    transferable_balance_after = dao_token_manager.transferableBalance(destination_address, 1651845600)
    assert transferable_balance_after >= 600_000 * 10**18, "Incorrect transferrable balance"
    assert transferable_balance_after < 610_000 * 10**18, "Incorrect transferrable balance"

    ### validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 4, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_permission_create_event(evs[0], create_permission)

    # asserts on vote item 2
    validate_ldo_issue_event(evs[1], issue)

    # asserts on vote item 3
    validate_ldo_vested_event(evs[2], vested)

    # asserts on vote item 4
    validate_permission_revoke_event(evs[3], revoke_permission)
