"""
Tests for voting 21/06/2022.
"""

from brownie import accounts, interface, reverts
from scripts.upgrade_2022_06_21 import start_vote
from utils.config import (
    lido_dao_voting_repo,
    lido_dao_lido_repo,
    lido_dao_voting_address,
    lido_dao_steth_address,
    network_name,
)

from utils.test.event_validators.aragon import validate_push_to_repo_event, validate_app_update_event

from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grant_event,
    validate_permission_revoke_event,
)
from utils.test.event_validators.voting import validate_change_objection_time_event
from utils.test.tx_tracing_helpers import *

voting_old_app = {
    "address": "0x41D65FA420bBC714686E798a0eB0Df3799cEF092",
    "content_uri": "0x697066733a516d514d64696979653134765966724a7753594250646e68656a446f62417877584b72524e45663438735370444d",
    "version": (2, 0, 0),
    "vote_time": 259_200,  # 72 h
}

voting_new_app = {
    "address": "0x72fb5253AD16307B9E773d2A78CaC58E309d5Ba4",
    "ipfsCid": "QmesiVLTy1ddvGoLnoPCgFeQWtF9itwNuYVufavnYWa65g",
    "version": (3, 0, 0),
    "vote_time": 259_200,  # 72 h
    "objection_time": 86_400,  # 24 hours
}

lido_old_app = {
    "address": "0x47EbaB13B806773ec2A2d16873e2dF770D130b50",
    "content_uri": "0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053",
    "version": (3, 0, 0),
}

lido_new_app = {
    "ipfsCid": "QmRjCTdRbjkGUa7t6H2PnswGZyecnNSg8osk4kY2i82xUn",
    "version": (3, 1, 0),
}

deployer_address = "0x3d3be777790ba9F279A188C3F249f0B6F94880Cd"

permission = Permission(
    entity="0x2e59A20f205bB85a89C53f1936454680651E618e",  # Voting
    app="0x2e59A20f205bB85a89C53f1936454680651E618e",  # Voting
    role="0x068ca51c9d69625c7add396c98ca4f3b27d894c3b973051ad3ee53017d7094ea",
    # keccak256('UNSAFELY_MODIFY_VOTE_TIME_ROLE')
)


def test_vote(ldo_holder, helpers, dao_voting, dao_agent):
    # Voting App before
    voting_repo = interface.Repo(lido_dao_voting_repo)
    voting_proxy = interface.AppProxyUpgradeable(lido_dao_voting_address)
    voting_app_from_chain = voting_repo.getLatest()
    voting_appId = voting_proxy.appId()

    assert voting_app_from_chain[0] == voting_old_app["version"]
    assert voting_app_from_chain[1] == voting_old_app["address"]
    assert voting_app_from_chain[2] == voting_old_app["content_uri"]
    assert voting_proxy.implementation() == voting_old_app["address"]

    assert dao_voting.voteTime() == voting_old_app["vote_time"]

    # Lido app before
    lido_repo = interface.Repo(lido_dao_lido_repo)
    lido_proxy = interface.AppProxyUpgradeable(lido_dao_steth_address)
    lido_app_from_chain = lido_repo.getLatest()

    assert lido_app_from_chain[0] == lido_old_app["version"]
    assert lido_app_from_chain[1] == lido_old_app["address"]
    assert lido_app_from_chain[2] == lido_old_app["content_uri"]
    assert lido_proxy.implementation() == lido_old_app["address"]

    # ACL checks
    acl_check_addrs: List[str] = [
        dao_voting.address,
        dao_agent.address,
        ldo_holder.address,
        accounts[0],
        accounts[1],
        deployer_address,
    ]

    _acl_checks(dao_voting, acl_check_addrs, reason=None)

    ##
    # START VOTE
    ##
    vote_id = start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether"
    )

    _acl_checks(dao_voting, acl_check_addrs, reason="APP_AUTH_FAILED")

    # Voting App after
    assert voting_proxy.implementation() == voting_new_app["address"]
    voting_app_from_chain = voting_repo.getLatest()

    assert voting_app_from_chain[0] == voting_new_app["version"]
    assert voting_app_from_chain[1] == voting_new_app["address"]
    content_uri_bytes = voting_app_from_chain[2][:]
    assert content_uri_bytes.decode("ASCII") == f"ipfs:{voting_new_app['ipfsCid']}"

    assert dao_voting.voteTime() == voting_new_app["vote_time"]
    assert dao_voting.objectionPhaseTime() == voting_new_app["objection_time"]
    assert dao_voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE() == permission.role

    # Lido App after
    assert lido_proxy.implementation() == lido_old_app["address"]
    lido_app_from_chain = lido_repo.getLatest()

    assert lido_app_from_chain[0] == lido_new_app["version"]
    assert lido_app_from_chain[1] == lido_old_app["address"]
    content_uri_bytes = lido_app_from_chain[2][:]
    assert content_uri_bytes.decode("ASCII") == f"ipfs:{lido_new_app['ipfsCid']}"

    # Validating events
    # Need to have mainnet contract to have it right
    display_voting_events(tx)

    if network_name() in ["mainnet-fork", "mainnet"]:
        assert count_vote_items_by_events(tx, dao_voting) == 6, "Incorrect voting items count"

        evs = group_voting_events(tx)
        validate_push_to_repo_event(evs[0], voting_new_app["version"])
        validate_app_update_event(evs[1], voting_appId, voting_new_app["address"])
        validate_push_to_repo_event(evs[2], lido_new_app["version"])

        validate_permission_grant_event(evs[3], permission)
        validate_change_objection_time_event(evs[4], voting_new_app["objection_time"])
        validate_permission_revoke_event(evs[5], permission)


def _acl_checks(dao_voting: interface.Voting, addrs: List[str], reason: Optional[str]) -> None:
    for addr in addrs:
        with reverts(reason):
            dao_voting.unsafelyChangeVoteTime(250_000, {"from": addr})
        with reverts(reason):
            dao_voting.unsafelyChangeObjectionPhaseTime(20_000, {"from": addr})
