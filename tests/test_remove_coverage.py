"""
Tests for emergency remove coverage script
"""

from scripts.remove_coverage import start_vote
from brownie import ZERO_ADDRESS, interface
from tx_tracing_helpers import *
from utils.config import network_name
from utils.permissions import require_first_param_is_addr

selfowned_steth_burner_address = {
    'mainnet': '0xBADDF00D',
    'goerli': '0xf6a64DcB06Ef7eB1ee94aDfD7D10ACB44D9A9888'
}

def has_burn_role_permission(acl, lido, who) -> int:
    """Returns if address has BURN_ROLE on Lido(stETH) contract"""
    return acl.hasPermission(who, lido, lido.BURN_ROLE())

def has_burn_role_permission_granular(acl, lido, who, acl_param) -> int:
    return acl.hasPermission['address,address,bytes32,uint[]'](who, lido, lido.BURN_ROLE(), acl_param)

def test_setup_coverage(
    helpers, accounts, ldo_holder, oracle, dao_voting,
    vote_id_from_env, bypass_events_decoding, acl, lido
):
    netname = network_name().split('-')[0]
    assert netname in ("goerli", "mainnet"), "Incorrect network name"

    self_owned_steth_burner = interface.SelfOwnedStETHBurner( \
        selfowned_steth_burner_address[netname]
    )
    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({ 'from': ldo_holder }, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.37 ether'
    )

    # CHECKS AFTER

    assert not has_burn_role_permission(acl, lido, self_owned_steth_burner), \
        "Incorrect permissions"

    acl_param = require_first_param_is_addr(self_owned_steth_burner.address)
    assert not has_burn_role_permission_granular(acl, lido, self_owned_steth_burner, acl_param), \
        "Incorrect permissions"

    assert oracle.getBeaconReportReceiver() == ZERO_ADDRESS, \
        "Incorrect new beacon report receiver"

    ### validate vote events
    assert count_vote_items_by_events(tx) == 2, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    #evs = group_voting_events(tx)
