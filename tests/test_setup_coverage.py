"""
Tests for setup coverage script
"""

from scripts.setup_coverage import start_vote
from brownie import ZERO_ADDRESS, interface, reverts
from tx_tracing_helpers import *
from utils.config import network_name

composite_receiver_address = {
    'mainnet': None,
    'goerli': '0x1D2219E0A1e2F09309643fD8a69Ca0EF7093B739'
}

selfowned_steth_burner_address = {
    'mainnet': None,
    'goerli': '0xf6a64DcB06Ef7eB1ee94aDfD7D10ACB44D9A9888'
}

selfowned_steth_burner_burnt_non_cover = {
    'mainnet': 32145684728326685744,
    'goerli': 0
}

def has_burn_role_permission(acl, lido, who, acc, sharesAmount) -> int:
    """Returns if address has BURN_ROLE on Lido(stETH) contract"""
    return acl.hasPermission['address,address,bytes32,uint[]'](
        who, lido, lido.BURN_ROLE(), [acc, sharesAmount]
    )

def test_setup_coverage(
    helpers, accounts, ldo_holder,
    dao_voting, lido, oracle, acl, dao_agent,
    vote_id_from_env, bypass_events_decoding
):
    netname = network_name().split('-')[0]
    assert netname in ("goerli", "mainnet"), "Incorrect network name"

    # CHECKS BEFORE
    composite_post_rebase_beacon_receiver = interface.CompositePostRebaseBeaconReceiver(
        composite_receiver_address[netname]
    )
    self_owned_steth_burner = interface.SelfOwnedStETHBurner(
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
    assert self_owned_steth_burner.getNonCoverSharesBurnt() == selfowned_steth_burner_burnt_non_cover[netname], \
        "Incorrect non-cover shares burnt amount"

    assert has_burn_role_permission(acl, lido, dao_voting, dao_agent.address, 100), "Incorrect permissions"
    assert not has_burn_role_permission(acl, lido, self_owned_steth_burner, dao_agent.address, 100), "Incorrect permissions"
    assert not has_burn_role_permission(acl, lido, self_owned_steth_burner, self_owned_steth_burner.address, 100), "Incorrect permissions"

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
    assert self_owned_steth_burner.getNonCoverSharesBurnt() == selfowned_steth_burner_burnt_non_cover[netname], \
        "Incorrect non-cover shares burnt amount"

    assert not has_burn_role_permission(acl, lido, dao_voting, dao_agent.address, 100), "Incorrect permissions"
    assert not has_burn_role_permission(acl, lido, self_owned_steth_burner, dao_agent.address, 100), "Incorrect permissions"

    assert has_burn_role_permission(acl, lido, self_owned_steth_burner, self_owned_steth_burner.address, 100), \
        "Incorrect granular permissions"

    cover_application_acceptance_checks(
        self_owned_steth_burner, dao_voting,
        oracle, lido, dao_agent, netname, accounts
    )

    burn_permissions_forehead_check(
        lido, self_owned_steth_burner,
        dao_agent, dao_voting
    )

    oracle_permissions_forehead_check(
        lido, dao_agent, self_owned_steth_burner,
        accounts, oracle, dao_voting
    )

    ### validate vote events
    assert count_vote_items_by_events(tx) == 4, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    #evs = group_voting_events(tx)

def cover_application_acceptance_checks(steth_burner, dao_voting, oracle, lido, agent, netname, accounts):
    steth_amount = 10 ** 18
    shares_to_burn = lido.getSharesByPooledEth(steth_amount)

    assert steth_burner.getNonCoverSharesBurnt() == selfowned_steth_burner_burnt_non_cover[netname], \
        "Incorrect non-cover shares burnt amount"
    assert steth_burner.getCoverSharesBurnt() == 0, \
        "incorrect amount of the shares burnt for cover"

    with reverts("MSG_SENDER_MUST_BE_VOTING"):
        steth_burner.requestBurnMyStETHForCover(steth_amount, {'from': agent.address})
    with reverts("MSG_SENDER_MUST_BE_VOTING"):
        steth_burner.requestBurnMyStETH(steth_amount, {'from': agent.address})

    lido.transfer(dao_voting.address, steth_amount, { 'from': agent.address })

    with reverts("TRANSFER_AMOUNT_EXCEEDS_ALLOWANCE"):
        steth_burner.requestBurnMyStETHForCover(steth_amount, { 'from': dao_voting.address })
    with reverts("TRANSFER_AMOUNT_EXCEEDS_ALLOWANCE"):
        steth_burner.requestBurnMyStETH(steth_amount, { 'from': dao_voting.address })

    lido.approve(steth_burner.address, steth_amount, { 'from': dao_voting.address })

    assert lido.balanceOf(steth_burner.address) == 0, \
        "Incorrect balance"
    assert steth_burner.getExcessStETH() == 0, \
        "Incorrect excess stETH amount"

    steth_burner.requestBurnMyStETHForCover(steth_amount * 1 // 4, { 'from': dao_voting.address })
    steth_burner.requestBurnMyStETH(steth_amount * 3 // 4, { 'from' : dao_voting.address })

    steth_burner.recoverExcessStETH({'from': accounts[0]})

    assert (lido.balanceOf(steth_burner.address) + 9) // 10 == (steth_amount + 9) // 10, \
        "Incorrect balance"

    # abusing ERC721 recovert interface with stETH
    with reverts("TRANSFER_AMOUNT_EXCEEDS_ALLOWANCE"):
        steth_burner.recoverERC721(lido, steth_amount, {'from': accounts[0]})

    assert steth_burner.getNonCoverSharesBurnt() == selfowned_steth_burner_burnt_non_cover[netname], \
        "Incorrect non-cover shares burnt amount"
    assert steth_burner.getCoverSharesBurnt() == 0, \
        "incorrect amount of the shares burnt for cover"
    assert (lido.balanceOf(steth_burner.address) + 9) // 10 == (steth_amount + 9) // 10, \
        "Incorrect balance"
    assert steth_burner.getExcessStETH() == 0, \
        "Incorrect excess stETH amount"

    _, validators, beaconBalance = lido.getBeaconStat()

    expectedEpoch = oracle.getExpectedEpochId()
    reporters = oracle.getOracleMembers()
    quorum = oracle.getQuorum()
    for reporter in reporters[:quorum]:
        print(f'reporting to oracle from: {reporter}')
        oracle.reportBeacon(expectedEpoch, beaconBalance // 10**9, validators, { 'from': reporter })

    assert steth_burner.getCoverSharesBurnt() == shares_to_burn * 1 // 4, \
        "incorrect amount of the shares burnt for cover"
    assert steth_burner.getNonCoverSharesBurnt() == \
        selfowned_steth_burner_burnt_non_cover[netname] + shares_to_burn * 3 // 4, \
        "Incorrect non-cover shares burnt amount"

def burn_permissions_forehead_check(lido, steth_burner, agent, dao_voting):
    lido.transfer(steth_burner.address, 10 ** 9, { 'from': agent.address })
    # legit
    lido.burnShares(steth_burner.address, 10, {'from' : steth_burner})
    # bad destination address
    with reverts("APP_AUTH_FAILED"):
        lido.burnShares(agent.address, 10, { 'from': steth_burner })

    # bad msg.sender
    with reverts("APP_AUTH_FAILED"):
        lido.burnShares(agent.address, 10, { 'from': dao_voting })
    with reverts("APP_AUTH_FAILED"):
        lido.burnShares(steth_burner.address, 10, {'from': dao_voting })

def burn_permissions_forehead_check(lido, steth_burner, agent, dao_voting):
    lido.transfer(steth_burner.address, 10 ** 9, { 'from': agent.address })
    # legit
    lido.burnShares(steth_burner.address, 10, {'from' : steth_burner})
    # bad destination address
    with reverts("APP_AUTH_FAILED"):
        lido.burnShares(agent.address, 10, { 'from': steth_burner })

    # bad msg.sender
    with reverts("APP_AUTH_FAILED"):
        lido.burnShares(agent.address, 10, { 'from': dao_voting })
    with reverts("APP_AUTH_FAILED"):
        lido.burnShares(steth_burner.address, 10, {'from': dao_voting })

def oracle_permissions_forehead_check(lido, agent, steth_burner, accounts, oracle, dao_voting):
    # legit

    # need pending burning requests to prevent early return from processLidoOracleReport
    def burn_req_helper() -> None:
        lido.transfer(dao_voting.address, 10, { 'from': agent.address })
        lido.approve(steth_burner.address, 10, { 'from': dao_voting.address })
        steth_burner.requestBurnMyStETHForCover(10, { 'from': dao_voting.address })


    burn_req_helper()
    steth_burner.processLidoOracleReport(0, 0, 0, { 'from': oracle })

    burn_req_helper()
    steth_burner.processLidoOracleReport(0, 0, 0, { 'from': oracle.getBeaconReportReceiver() })

    burn_req_helper()
    # bad msg.sender
    with reverts("APP_AUTH_FAILED"):
        steth_burner.processLidoOracleReport(0, 0, 0, { 'from': steth_burner })
    with reverts("APP_AUTH_FAILED"):
        steth_burner.processLidoOracleReport(0, 0, 0, { 'from': accounts[0] })
    with reverts("APP_AUTH_FAILED"):
        steth_burner.processLidoOracleReport(0, 0, 0, { 'from': dao_voting })
