"""
Tests for setup coverage script
"""

from scripts.setup_coverage import start_vote
from brownie import ZERO_ADDRESS, interface
from tx_tracing_helpers import *
from utils.config import network_name
from utils.permissions import require_first_param_is_addr

composite_receiver_address = {
    'mainnet': '0xBADDF00D',
    'goerli': '0x1D2219E0A1e2F09309643fD8a69Ca0EF7093B739'
}

selfowned_steth_burner_address = {
    'mainnet': '0xBADDF00D',
    'goerli': '0xf6a64DcB06Ef7eB1ee94aDfD7D10ACB44D9A9888'
}

selfowned_steth_burner_burnt_non_cover = {
    'mainnet': 32145684728326685744,
    'goerli': 0
}

def has_burn_role_permission(acl, lido, who) -> int:
    """Returns if address has BURN_ROLE on Lido(stETH) contract"""
    return acl.hasPermission(who, lido, lido.BURN_ROLE())

def has_burn_role_permission_granular(acl, lido, who, acl_param) -> int:
    return acl.hasPermission['address,address,bytes32,uint[]'](who, lido, lido.BURN_ROLE(), acl_param)

def cover_application_check(steth_burner, dao_voting, oracle, lido, agent):
    steth_amount = 1 * 10**18

    assert steth_burner.getCoverSharesBurnt() == 0, \
        "incorrect amount of the shares burnt for cover"

    lido.transfer(dao_voting.address, steth_amount, { 'from': agent.address })
    lido.approve(steth_burner.address, steth_amount, { 'from': dao_voting.address })
    shares_to_burn = lido.getSharesByPooledEth(steth_amount)
    steth_burner.requestBurnMyStETHForCover(steth_amount, { 'from': dao_voting.address })

    _, validators, beaconBalance = lido.getBeaconStat()

    expectedEpoch = oracle.getExpectedEpochId()
    reporters = oracle.getOracleMembers()
    quorum = oracle.getQuorum()
    for reporter in reporters[:quorum]:
        print(f'reporting to oracle from: {reporter}')
        oracle.reportBeacon(expectedEpoch, beaconBalance // 10**9, validators, { 'from': reporter })

    assert steth_burner.getCoverSharesBurnt() == shares_to_burn, \
        "incorrect amount of the shares burnt for cover"

def test_setup_coverage(
    helpers, accounts, ldo_holder,
    dao_voting, lido, oracle, acl, dao_agent,
    vote_id_from_env, bypass_events_decoding
):
    netname = network_name().split('-')[0]
    assert netname in ("goerli", "mainnet"), "Incorrect network name"

    # CHECKS BEFORE
    composite_post_rebase_beacon_receiver \
        = interface.CompositePostRebaseBeaconReceiver( \
            composite_receiver_address[netname] \
        )

    self_owned_steth_burner = interface.SelfOwnedStETHBurner( \
        selfowned_steth_burner_address[netname]
    )

    assert oracle.getBeaconReportReceiver() == ZERO_ADDRESS, \
        "Incorrect old beacon report receiver"
    assert oracle.getLido() == lido.address, \
        "Incorrect lido address"
    assert lido.getOracle() == oracle.address, \
        "Incorrect oracle address"

    assert composite_post_rebase_beacon_receiver.VOTING() == dao_voting.address, \
        "Incorrect voting"
    assert composite_post_rebase_beacon_receiver.ORACLE() == oracle.address, \
        "Incorrect oracle"
    assert composite_post_rebase_beacon_receiver.callbacksLength() == 0, \
        "Incorrect callbacks length"

    assert self_owned_steth_burner.VOTING() == dao_voting.address, \
        "Incorrect voting address"
    assert self_owned_steth_burner.LIDO() == lido.address, \
        "Incorrect lido address"
    assert self_owned_steth_burner.TREASURY() == dao_agent.address, \
        "Incorrect lido treasury address"
    assert self_owned_steth_burner.getBurnAmountPerRunQuota() == 4, \
        "Incorrect quota"
    assert self_owned_steth_burner.getCoverSharesBurnt() == 0, \
        "Incorrect cover shares burnt amount"
    assert self_owned_steth_burner.getNonCoverSharesBurnt() \
        == selfowned_steth_burner_burnt_non_cover[netname], \
        "Incorrect non-cover shares burnt amount"

    assert has_burn_role_permission(acl, lido, dao_voting), "Incorrect permissions"
    assert not has_burn_role_permission(acl, lido, self_owned_steth_burner), "Incorrect permissions"

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({ 'from': ldo_holder }, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.37 ether'
    )

    # CHECKS AFTER

    assert oracle.getBeaconReportReceiver() == composite_post_rebase_beacon_receiver.address, \
        "Incorrect new beacon report receiver"
    assert oracle.getLido() == lido.address, \
        "Incorrect lido address"
    assert lido.getOracle() == oracle.address, \
        "Incorrect oracle address"

    assert composite_post_rebase_beacon_receiver.VOTING() == dao_voting.address, \
        "Incorrect voting"
    assert composite_post_rebase_beacon_receiver.ORACLE() == oracle.address, \
        "Incorrect oracle"
    assert composite_post_rebase_beacon_receiver.callbacksLength() == 1, \
        "Incorrect callbacks length"
    assert composite_post_rebase_beacon_receiver.callbacks(0) == self_owned_steth_burner.address, \
        "Incorrect callback"

    assert self_owned_steth_burner.VOTING() == dao_voting.address, "Incorrect voting address"
    assert self_owned_steth_burner.LIDO() == lido.address, "Incorrect lido address"
    assert self_owned_steth_burner.TREASURY() == dao_agent.address, "Incorrect lido treasury address"
    assert self_owned_steth_burner.getBurnAmountPerRunQuota() == 4, "Incorrect quota"
    assert self_owned_steth_burner.getCoverSharesBurnt() == 0, "Incorrect cover shares burnt amount"
    assert self_owned_steth_burner.getNonCoverSharesBurnt() \
        == selfowned_steth_burner_burnt_non_cover[netname], "Incorrect non-cover shares burnt amount"

    assert not has_burn_role_permission(acl, lido, dao_voting), "Incorrect permissions"
    assert not has_burn_role_permission(acl, lido, self_owned_steth_burner), "Incorrect permissions"

    acl_param = require_first_param_is_addr(self_owned_steth_burner.address)
    assert has_burn_role_permission_granular(acl, lido, self_owned_steth_burner, acl_param), \
        "Incorrect granular permissions"

    cover_application_check(
        self_owned_steth_burner, dao_voting,
        oracle, lido, dao_agent
    )

    ### validate vote events
    assert count_vote_items_by_events(tx) == 4, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    #evs = group_voting_events(tx)
