"""
Tests for setup_easytrack_permissions.py
"""

from event_validators.permission import validate_permission_revoke_event, validate_permission_grantp_event, \
    Permission
from scripts.setup_easytrack_limits import start_vote, evmscriptexecutor_address
from tx_tracing_helpers import count_vote_items_by_events, TransactionReceipt, display_voting_events, \
    group_voting_events

permission = Permission(entity='0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977',
                        app='0xB9E5CBB9CA5b0d659238807E84D0176930753d86',
                        role='0x5de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc')

usdc_token = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'

eth = {
    'limit': 1_000 * (10 ** 18),
    'address': '0x0000000000000000000000000000000000000000',
}

steth = {
    'limit': 1_000 * (10 ** 18),
    'address': '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',
}

ldo = {
    'limit': 5_000_000 * (10 ** 18),
    'address': '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32',
}

dai = {
    'limit': 100_000 * (10 ** 18),
    'address': '0x6b175474e89094c44da98b954eedeac495271d0f',
}


def has_payments_permission(acl, finance, sender, token, receiver, amount) -> bool:
    return acl.hasPermission['address,address,bytes32,uint[]'](sender, finance, finance.CREATE_PAYMENTS_ROLE(),
                                                               [token, receiver, amount])


def test_setup_easytrack_permissions(
        helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, finance, acl
):
    ##
    # START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.37 ether'
    )

    assert has_payments_permission(acl, finance, evmscriptexecutor_address, eth['address'], ldo_holder.address,
                                   eth['limit']), 'Should pass under eth limit'
    assert has_payments_permission(acl, finance, evmscriptexecutor_address, steth['address'], ldo_holder.address,
                                   steth['limit']), 'Should pass under steth limit'
    assert has_payments_permission(acl, finance, evmscriptexecutor_address, ldo['address'], ldo_holder.address,
                                   ldo['limit']), 'Should pass under ldo limit'
    assert has_payments_permission(acl, finance, evmscriptexecutor_address, dai['address'], ldo_holder.address,
                                   dai['limit']), 'Should pass under dai limit'

    assert not has_payments_permission(acl, finance, evmscriptexecutor_address, eth['address'], ldo_holder.address,
                                       eth['limit'] + 1), 'Should not pass over eth limit'
    assert not has_payments_permission(acl, finance, evmscriptexecutor_address, steth['address'], ldo_holder.address,
                                       steth['limit'] + 1), 'Should not pass over steth limit'
    assert not has_payments_permission(acl, finance, evmscriptexecutor_address, ldo['address'], ldo_holder.address,
                                       ldo['limit'] + 1), 'Should not pass over ldo limit'
    assert not has_payments_permission(acl, finance, evmscriptexecutor_address, dai['address'], ldo_holder.address,
                                       dai['limit'] + 1), 'Should not pass over dai limit'

    assert not has_payments_permission(acl, finance, evmscriptexecutor_address, usdc_token, ldo_holder.address,
                                       1), 'Should not pass with usdc'
    assert not has_payments_permission(acl, finance, accounts[0].address, eth['address'], ldo_holder.address,
                                       eth['limit']), 'Should pass from random address'

    assert count_vote_items_by_events(tx) == 2, "Incorrect voting items count"

    display_voting_events(tx)

    evs = group_voting_events(tx)

    validate_permission_revoke_event(evs[0], permission)

    validate_permission_grantp_event(evs[1], permission)
