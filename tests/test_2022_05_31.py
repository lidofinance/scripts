"""
Tests for voting 31/05/2022.
"""
import pytest

from brownie import interface, chain

from scripts.vote_2022_05_31 import start_vote
from tx_tracing_helpers import *
from utils.config import contracts, lido_dao_steth_address, lido_dao_oracle, lido_dao_node_operators_registry, \
    network_name, lido_dao_voting_address
from event_validators.permission import Permission, validate_permission_create_event
from event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from event_validators.lido import (validate_set_version_event,
                                   validate_set_el_rewards_vault_event, validate_staking_resumed_event,
                                   validate_staking_limit_set)


@pytest.fixture(scope="module", autouse=True)
def deployed_contracts():
    return {
        'el_rewards_vault': '0x388C818CA8B9251b393131C08a736A67ccB19297'
    }

# RESUME_ROLE
permission_resume_role = Permission(entity=lido_dao_voting_address,  # Voting
                                    app=lido_dao_steth_address,  # Lido
                                    role='2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7')

# STAKING_PAUSE_ROLE 
permission_staking_pause_role = Permission(entity=lido_dao_voting_address,  # Voting
                                           app=lido_dao_steth_address,  # Lido
                                           role='84ea57490227bc2be925c684e2a367071d69890b629590198f4125a018eb1de8')

# SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE
permission_elrewards_set_limit = Permission(entity=lido_dao_voting_address,  # Voting
                                            app=lido_dao_steth_address,  # Lido
                                            role='ca7d176c2da2028ed06be7e3b9457e6419ae0744dc311989e9b29f6a1ceb1003')


def test_vote(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding,
    lido,
):
    acl: interface.ACL = contracts.acl

    assert not acl.hasPermission(*permission_resume_role)
    assert not acl.hasPermission(*permission_staking_pause_role)
    assert not acl.hasPermission(*permission_elrewards_set_limit)

    assert lido.getELRewardsWithdrawalLimit() == 0
    
    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 4, "Incorrect voting items count"

    assert acl.hasPermission(*permission_resume_role)
    assert acl.hasPermission(*permission_staking_pause_role)
    assert acl.hasPermission(*permission_elrewards_set_limit)
    
    assert lido.getELRewardsWithdrawalLimit() == 2

    # assert lido.getELRewardsVault() == deployed_contracts['el_rewards_vault']
    # assert not lido.isStakingPaused()

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    # evs = group_voting_events(tx)

    # validate_permission_create_event(evs[7], permission_elrewards_vault)

    # validate_permission_create_event(evs[8], permission_stake_control)

    # validate_set_el_rewards_vault_event(evs[9], deployed_contracts['el_rewards_vault'])

    # validate_staking_resumed_event(evs[10])
