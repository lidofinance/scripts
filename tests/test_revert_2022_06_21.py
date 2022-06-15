"""
! Downgrade tests for voting 21/06/2022 [in case of emergency].
"""

# noinspection PyUnresolvedReferences
import pytest

from typing import Tuple

from brownie import accounts, interface, reverts
from scripts.revert_vote_2022_06_21 import start_vote

from utils.test.event_validators.aragon import (
    validate_push_to_repo_event,
    validate_app_update_event,
)

from utils.test.tx_tracing_helpers import *


old_good_voting_app: Dict = {
    "address": "0x41D65FA420bBC714686E798a0eB0Df3799cEF092",
    "content_uri":
        "0x697066733a516d514d64696979653134765966724a7753594250646e68656a446f62417877584b72524e45663438735370444d",
    "version": (3, 0, 0),
    "vote_time": 72 * 60 * 60,
}

voting_repo_address: str = "0x4ee3118e3858e8d7164a634825bfe0f73d99c792"
deployer_address: str = "0x3d3be777790ba9F279A188C3F249f0B6F94880Cd"


@pytest.fixture(scope="module")
def acl_check_addrs(accounts, dao_voting, dao_agent, ldo_holder) -> List[str]:
    return [
        dao_voting.address,
        dao_agent.address,
        ldo_holder.address,
        deployer_address,
        accounts[0],
        accounts[1],
    ]


def test_vote(ldo_holder, helpers, dao_voting, acl_check_addrs):
    voting_repo: interface.Repo = interface.Repo(voting_repo_address)
    voting_proxy: interface.AppProxyUpgradeable = interface.AppProxyUpgradeable(
        dao_voting.address
    )

    voting_app_from_chain: Tuple[
        Tuple[int, int, int], str, str
    ] = voting_repo.getLatest()
    voting_appId: str = dao_voting.appId()

    assert voting_app_from_chain[0] != old_good_voting_app["version"]
    # assert voting_app_from_chain[1] != old_good_voting_app["address"]
    # assert voting_app_from_chain[2] != old_good_voting_app["content_uri"]
    # assert dao_voting.implementation() != old_good_voting_app["address"]
    assert dao_voting.voteTime() == old_good_voting_app["vote_time"]

    _acl_checks(dao_voting, acl_check_addrs, reason=None)

    ##
    # START VOTE
    ##
    vote_id = start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether"
    )

    _acl_checks(dao_voting, acl_check_addrs, reason=None)

    voting_app_from_chain = voting_repo.getLatest()

    assert voting_app_from_chain[0] == old_good_voting_app["version"]
    assert voting_app_from_chain[1] == old_good_voting_app["address"]
    assert voting_app_from_chain[2] == old_good_voting_app["content_uri"]

    assert voting_proxy.implementation() == old_good_voting_app["address"]
    assert dao_voting.voteTime() == old_good_voting_app["vote_time"]
    with reverts():
        dao_voting.objectionPhaseTime()

    # Validating events
    # Need to have mainnet contract to have it right
    display_voting_events(tx)

    assert (
        count_vote_items_by_events(tx, dao_voting) == 2
    ), "Incorrect voting items count"
    evs = group_voting_events(tx)
    validate_push_to_repo_event(evs[0], old_good_voting_app["version"])
    validate_app_update_event(evs[1], voting_appId, old_good_voting_app["address"])


def _acl_checks(
    dao_voting: interface.Voting, addrs: List[str], reason: Optional[str]
) -> None:
    for addr in addrs:
        with reverts(reason):
            dao_voting.unsafelyChangeVoteTime(250_000, {"from": addr})
        with reverts(reason):
            dao_voting.unsafelyChangeObjectionPhaseTime(20_000, {"from": addr})
