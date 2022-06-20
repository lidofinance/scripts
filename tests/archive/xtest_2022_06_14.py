"""
Tests for voting 14/06/2022.
"""
import pytest

from brownie import interface, web3

from scripts.vote_2022_06_14 import start_vote
from common.tx_tracing_helpers import *
from utils.config import (contracts, lido_dao_steth_address)
from event_validators.permission import (Permission, validate_permission_revoke_event, validate_permission_grant_event)

old_dsm_address: str = "0xDb149235B6F40dC08810AA69869783Be101790e7"
new_dsm_address: str = "0x710B3303fB508a84F10793c1106e32bE873C24cd"

# DEPOSIT_ROLE on old DepositSecurityModule
permission_old_deposit_role = Permission(
    entity=old_dsm_address,
    app=lido_dao_steth_address,  # Lido
    role='0x2561bf26f818282a3be40719542054d2173eb0d38539e8a8d3cff22f29fd2384')


# DEPOSIT_ROLE on new DepositSecurityModule
permission_new_deposit_role = Permission(
    entity=new_dsm_address,
    app=lido_dao_steth_address,  # Lido
    role='0x2561bf26f818282a3be40719542054d2173eb0d38539e8a8d3cff22f29fd2384')


def test_vote(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding,
    dao_agent, lido
):
    acl: interface.ACL = contracts.acl
    proposed_deposit_security_module: interface.DepositSecurityModule = interface.DepositSecurityModule(
        new_dsm_address
    )

    assert proposed_deposit_security_module.getOwner() == dao_agent.address
    assert acl.hasPermission(*permission_old_deposit_role)
    assert not acl.hasPermission(*permission_new_deposit_role)

    last_deposited_block: int = 14985614

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 3, 'Incorrect voting items count'

    # Validate vote items 1-3
    assert not acl.hasPermission(*permission_old_deposit_role)
    assert acl.hasPermission(*permission_new_deposit_role)
    assert proposed_deposit_security_module.getLastDepositBlock() == last_deposited_block

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    validate_permission_revoke_event(evs[0], permission_old_deposit_role)
    validate_permission_grant_event(evs[1], permission_new_deposit_role)
    # NB: for evs[2] (setLastDepositBlock) there is no event
