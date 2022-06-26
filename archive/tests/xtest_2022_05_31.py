"""
Tests for voting 31/05/2022.
"""

from brownie import interface, ZERO_ADDRESS, reverts

from archive.scripts.vote_2022_05_31 import self_owned_burn_role_params, start_vote
from tx_tracing_helpers import *

from utils.config import (
    contracts, lido_dao_steth_address,
    network_name, lido_dao_voting_address,
    lido_dao_composite_post_rebase_beacon_receiver, lido_dao_self_owned_steth_burner
)

from event_validators.permission import (
    Permission, PermissionP, validate_permission_create_event,
    validate_permission_revoke_event, validate_permission_grantp_event
)
from event_validators.lido import validate_set_el_rewards_vault_withdrawal_limit_event
from event_validators.oracle import validate_beacon_report_receiver_set_event
from event_validators.composite_post_rebase_beacon_receiver import validate_composite_receiver_callback_added_event

# RESUME_ROLE
permission_resume_role = Permission(
    entity=lido_dao_voting_address,
    app=lido_dao_steth_address,  # Lido
    role='0x2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7'
)

# STAKING_PAUSE_ROLE
permission_staking_pause_role = Permission(
    entity=lido_dao_voting_address,
    app=lido_dao_steth_address,  # Lido
    role='0x84ea57490227bc2be925c684e2a367071d69890b629590198f4125a018eb1de8'
)

# SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE
permission_elrewards_set_limit_role = Permission(
    entity=lido_dao_voting_address,
    app=lido_dao_steth_address,  # Lido
    role='0xca7d176c2da2028ed06be7e3b9457e6419ae0744dc311989e9b29f6a1ceb1003'
)

# BURN_ROLE on Voting
permission_burn_on_voting = Permission(
    entity=lido_dao_voting_address,
    app=lido_dao_steth_address,  # Lido
    role='0xe97b137254058bd94f28d2f3eb79e2d34074ffb488d042e3bc958e0a57d2fa22'
)

# BURN_ROLE on SelfOwnedStETHBurner
permission_burn_on_steth_burner = PermissionP(
    entity=lido_dao_self_owned_steth_burner,
    app=lido_dao_steth_address,  # Lido
    role='0xe97b137254058bd94f28d2f3eb79e2d34074ffb488d042e3bc958e0a57d2fa22',
    params=['0x000100000000000000000000B280E33812c0B09353180e92e27b8AD399B07f26']
)

# MANAGE_PROTOCOL_CONTRACTS_ROLE
permission_manage_protocol_contracts = Permission(
    entity=lido_dao_voting_address,
    app=lido_dao_steth_address,  # Lido
    role='0xeb7bfce47948ec1179e2358171d5ee7c821994c911519349b95313b685109031'
)

# SET_TREASURY
permission_set_treasury = Permission(
    entity=lido_dao_voting_address,
    app=lido_dao_steth_address,  # Lido
    role='0x9f6f8058e4bcbf364e89c9e8da7eb7cada9d21b7aea6e2fd355b4669842c5795'
)

# SET_INSURANCE_FUND
permission_set_insurance_fund = Permission(
    entity=lido_dao_voting_address,
    app=lido_dao_steth_address,  # Lido
    role='0xd6c7fda17708c7d91354c17ac044fde6f58fb548a5ded80960beba862b1f1d7d'
)

# SET_ORACLE
permission_set_oracle = Permission(
    entity=lido_dao_voting_address,
    app=lido_dao_steth_address,  # Lido
    role='0x11eba3f259e2be865238d718fd308257e3874ad4b3a642ea3af386a4eea190bd'
)


def validate_parametrized_burn_permissions(lido):
    with reverts('APP_AUTH_FAILED'):
        lido.burnShares(lido.address, 123, { 'from': lido_dao_self_owned_steth_burner })

    with reverts('APP_AUTH_FAILED'):
        lido.burnShares(lido_dao_composite_post_rebase_beacon_receiver, 123,
                        { 'from': lido_dao_self_owned_steth_burner })

    with reverts('APP_AUTH_FAILED'):
        lido.burnShares(lido_dao_voting_address, 123,
                        { 'from': lido_dao_self_owned_steth_burner })

    with reverts('BURN_AMOUNT_EXCEEDS_BALANCE'):
        lido.burnShares(lido_dao_self_owned_steth_burner, 123,
                        { 'from': lido_dao_self_owned_steth_burner })

    with reverts('APP_AUTH_FAILED'):
        lido.burnShares(lido_dao_self_owned_steth_burner, 123, { 'from': lido_dao_voting_address })


def validate_new_manage_contracts_role(lido, voting):
    stranger = lido_dao_self_owned_steth_burner
    new_oracle = '0x1111111111111111111111111111111111111111'
    new_treasury = '0x2222222222222222222222222222222222222222'
    new_insurance = '0x3333333333333333333333333333333333333333'

    with reverts('APP_AUTH_FAILED'):
        lido.setProtocolContracts(new_oracle, new_treasury, new_insurance, { 'from': stranger })

    assert not lido.getOracle() == new_oracle
    assert not lido.getTreasury() == new_treasury
    assert not lido.getInsuranceFund() == new_insurance
    lido.setProtocolContracts(new_oracle, new_treasury, new_insurance, { 'from': voting.address })
    assert lido.getOracle() == new_oracle
    assert lido.getTreasury() == new_treasury
    assert lido.getInsuranceFund() == new_insurance


def test_vote(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding,
    lido, oracle,
    self_owned_steth_burner,
    composite_post_rebase_beacon_receiver,
):
    acl: interface.ACL = contracts.acl

    assert not acl.hasPermission(*permission_resume_role)
    assert not acl.hasPermission(*permission_staking_pause_role)
    assert not acl.hasPermission(*permission_elrewards_set_limit_role)

    assert lido.getELRewardsWithdrawalLimit() == 0

    assert composite_post_rebase_beacon_receiver.callbacksLength() == 0

    assert acl.hasPermission(*permission_burn_on_voting)
    assert not acl.hasPermission['address,address,bytes32,uint[]'](*permission_burn_on_steth_burner)
    assert oracle.getBeaconReportReceiver() == ZERO_ADDRESS

    assert not acl.hasPermission(*permission_manage_protocol_contracts)
    assert acl.hasPermission(*permission_set_treasury)
    assert acl.hasPermission(*permission_set_insurance_fund)
    assert acl.hasPermission(*permission_set_oracle)

    # START VOTE
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 12, 'Incorrect voting items count'

    assert acl.hasPermission(*permission_resume_role)
    assert acl.hasPermission(*permission_staking_pause_role)
    assert acl.hasPermission(*permission_elrewards_set_limit_role)

    assert lido.getELRewardsWithdrawalLimit() == 2

    assert composite_post_rebase_beacon_receiver.callbacksLength() == 1
    assert composite_post_rebase_beacon_receiver.callbacks(0) == self_owned_steth_burner.address

    assert oracle.getBeaconReportReceiver() == lido_dao_composite_post_rebase_beacon_receiver

    assert not acl.hasPermission(*permission_burn_on_voting)
    assert acl.hasPermission['address,address,bytes32,uint[]'](*permission_burn_on_steth_burner)
    validate_parametrized_burn_permissions(lido)

    assert acl.hasPermission(*permission_manage_protocol_contracts)
    validate_new_manage_contracts_role(lido, dao_voting)
    assert not acl.hasPermission(*permission_set_treasury)
    assert not acl.hasPermission(*permission_set_insurance_fund)
    assert not acl.hasPermission(*permission_set_oracle)

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ('goerli', 'goerli-fork'):
        return

    evs = group_voting_events(tx)

    validate_permission_create_event(evs[0], permission_resume_role)
    validate_permission_create_event(evs[1], permission_staking_pause_role)
    validate_permission_create_event(evs[2], permission_elrewards_set_limit_role)

    validate_set_el_rewards_vault_withdrawal_limit_event(evs[3], 2)

    validate_composite_receiver_callback_added_event(evs[4], self_owned_steth_burner.address, 0)

    validate_beacon_report_receiver_set_event(evs[5], lido_dao_composite_post_rebase_beacon_receiver)

    validate_permission_revoke_event(evs[6], permission_burn_on_voting)
    validate_permission_grantp_event(evs[7], permission_burn_on_steth_burner, self_owned_burn_role_params())

    validate_permission_create_event(evs[8], permission_manage_protocol_contracts)

    validate_permission_revoke_event(evs[9], permission_set_treasury)
    validate_permission_revoke_event(evs[10], permission_set_insurance_fund)
    validate_permission_revoke_event(evs[11], permission_set_oracle)
