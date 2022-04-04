import pytest
# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *

from brownie import accounts, interface
from scripts.vote_2022_04_07 import start_vote
from utils.config import (
    lido_dao_voting_repo,
    lido_dao_voting_address
)

from event_validators.permission import (Permission,
                                         validate_permission_create,
                                         validate_permission_grant_event,
                                         validate_permission_revoke_event)
from event_validators.voting import validate_change_vote_time_event
from tx_tracing_helpers import *


voting_new_app = {
    'address': '0x9059e060113b7394FC964bf86CD246f3e9D4210d',
    'content_uri': '0x697066733a516d5962774366374d6e6932797a31553358334769485667396f35316a6b53586731533877433257547755684859',
    'id': '0xee7f2abf043afe722001aaa900627a6e29adcbcce63a561fbd97e0a0c6429b94',
    'version': (3, 0, 0),
    'vote_time': 259200  # 72 hours
}

voting_old_app = {
    'address': '0xfd5952Ef8dE4707f95E754299e8c0FfD1e876F34',
    'content_uri': '0x697066733a516d5962774366374d6e6932797a31553358334769485667396f35316a6b53586731533877433257547755684859',
    'id': '0xee7f2abf043afe722001aaa900627a6e29adcbcce63a561fbd97e0a0c6429b94',
    'version': (2, 0, 0),
    'vote_time': 14460
}

permission = Permission(entity='0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db',  # Voting
                        app='0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db',  # Voting
                        role='0x068ca51c9d69625c7add396c98ca4f3b27d894c3b973051ad3ee53017d7094ea')  # keccak256('UNSAFELY_MODIFY_VOTE_TIME_ROLE')


def test_2022_04_07(ldo_holder, helpers, dao_voting):
    voting_repo = interface.Repo(lido_dao_voting_repo)
    voting_proxy = interface.AppProxyUpgradeable(lido_dao_voting_address)
    voting_app_from_chain = voting_repo.getLatest()

    assert voting_app_from_chain[0] == voting_old_app['version']
    assert voting_app_from_chain[1] == voting_old_app['address']
    assert voting_app_from_chain[2] == voting_old_app['content_uri']
    assert voting_proxy.implementation() == voting_old_app['address']

    assert dao_voting.voteTime() == voting_old_app['vote_time']

    ##
    # START VOTE
    ##
    vote_id = start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )

    voting_app_from_chain = voting_repo.getLatest()

    assert voting_app_from_chain[0] == voting_new_app['version']
    assert voting_app_from_chain[1] == voting_new_app['address']
    assert voting_app_from_chain[2] == voting_new_app['content_uri']

    assert voting_proxy.implementation() == voting_new_app['address']
    assert dao_voting.voteTime() == voting_new_app['vote_time']
    assert dao_voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE() == permission.role

    # Validating events
    # Need to have mainnet contract to have it right
    # display_voting_events(tx)

    # assert count_vote_items_by_events(tx, dao_voting) == 5, "Incorrect voting items count"
    #
    # evs = group_voting_events(tx)
    # validate_push_to_repo_event()
    # validate_app_update_event()
    # validate_permission_create(evs[2], permission, lido_dao_voting_address)
    # validate_change_vote_time_event(evs[3], voting_new_app['vote_time'])
    # validate_permission_revoke_event(evs[4], permission)
