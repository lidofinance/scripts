"""
Tests for voting 14/06/2022.
"""
import pytest

from brownie import interface, chain, ZERO_ADDRESS

from scripts.vote_2022_06_14 import (get_last_deposit_block, start_vote,
    get_proposed_deposit_security_module_address)
from tx_tracing_helpers import *
from utils.config import (contracts, lido_dao_steth_address,
    network_name, lido_dao_deposit_security_module_address,
)
from event_validators.permission import (Permission, 
    validate_permission_revoke_event, validate_permission_grant_event)


# DEPOSIT_ROLE on old DepositSecurityModule
permission_old_deposit_role = Permission(
    entity=lido_dao_deposit_security_module_address,
    app=lido_dao_steth_address,  # Lido
    role='0x2561bf26f818282a3be40719542054d2173eb0d38539e8a8d3cff22f29fd2384')


# DEPOSIT_ROLE on new DepositSecurityModule
permission_new_deposit_role = Permission(
    entity=get_proposed_deposit_security_module_address(),
    app=lido_dao_steth_address,  # Lido
    role='0x2561bf26f818282a3be40719542054d2173eb0d38539e8a8d3cff22f29fd2384')


def test_vote(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding,
    dao_agent
):
    acl: interface.ACL = contracts.acl
    proposed_deposit_security_module = interface.DepositSecurityModule(get_proposed_deposit_security_module_address())

    assert acl.hasPermission(*permission_old_deposit_role)
    assert not acl.hasPermission(*permission_new_deposit_role)
    assert proposed_deposit_security_module.getOwner() == dao_agent.address


    # START VOTE
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 3, 'Incorrect voting items count'

    assert not acl.hasPermission(*permission_old_deposit_role)
    assert acl.hasPermission(*permission_new_deposit_role)
    assert proposed_deposit_security_module.getLastDepositBlock() == get_last_deposit_block()

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ('goerli', 'goerli-fork'):
        return

    evs = group_voting_events(tx)

    validate_permission_revoke_event(evs[0], permission_old_deposit_role)
    validate_permission_grant_event(evs[1], permission_new_deposit_role)
    # NB: for evs[2] (setLastDepositBlock) there is no event
