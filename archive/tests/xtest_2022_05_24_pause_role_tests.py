"""
Tests for lido resume/pause roles 24/05/2022
"""
import pytest
from functools import partial
from brownie import reverts, web3
from archive.scripts.vote_2022_05_24 import start_vote


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )


@pytest.fixture(scope="module", autouse=True)
def create_resume_role_permission(acl, lido, dao_voting):
    resume_role_encoded = web3.keccak(text="RESUME_ROLE")
    acl.createPermission(
        dao_voting,
        lido,
        resume_role_encoded,
        dao_voting,
        {"from": dao_voting},
    )
    assert has_role(acl=acl, entity=dao_voting, app=lido, role="RESUME_ROLE")


@pytest.fixture(scope="function")
def stop_lido(lido, dao_voting):
    if not lido.isStopped():
        lido.stop({"from": dao_voting})


@pytest.fixture(scope="function")
def resume_lido(lido, dao_voting):
    if lido.isStopped():
        lido.resume({"from": dao_voting})


@pytest.mark.usefixtures("stop_lido")
def test_pause_role_cant_resume(acl, lido, dao_voting, stranger):
    stranger_has_role = partial(has_role, acl=acl, app=lido, entity=stranger)
    assert not stranger_has_role(role="RESUME_ROLE")

    acl.grantPermission(
        stranger,
        lido,
        web3.keccak(text="PAUSE_ROLE"),
        {"from": dao_voting},
    )
    assert stranger_has_role(role="PAUSE_ROLE")

    assert lido.isStopped()
    with reverts("APP_AUTH_FAILED"):
        lido.resume({"from": stranger})


@pytest.mark.usefixtures("resume_lido")
def test_resume_role_cant_pause(acl, lido, dao_voting, stranger):
    stranger_has_role = partial(has_role, acl=acl, app=lido, entity=stranger)
    assert not stranger_has_role(role="PAUSE_ROLE")

    acl.grantPermission(
        stranger,
        lido,
        web3.keccak(text="RESUME_ROLE"),
        {"from": dao_voting},
    )
    assert stranger_has_role(role="RESUME_ROLE")

    assert not lido.isStopped()
    with reverts("APP_AUTH_FAILED"):
        lido.stop({"from": stranger})


@pytest.mark.usefixtures("stop_lido")
def test_resume_role_can_resume(acl, lido, dao_voting, stranger):
    stranger_has_role = partial(has_role, acl=acl, app=lido, entity=stranger)
    assert not stranger_has_role(role="PAUSE_ROLE")

    acl.grantPermission(
        stranger,
        lido,
        web3.keccak(text="RESUME_ROLE"),
        {"from": dao_voting},
    )
    assert stranger_has_role(role="RESUME_ROLE")

    assert lido.isStopped()
    lido.resume({"from": stranger})
    assert not lido.isStopped()


@pytest.mark.usefixtures("resume_lido")
def test_pause_role_can_pause(acl, lido, dao_voting, stranger):
    stranger_has_role = partial(has_role, acl=acl, app=lido, entity=stranger)
    assert not stranger_has_role(role="RESUME_ROLE")

    acl.grantPermission(
        stranger,
        lido,
        web3.keccak(text="PAUSE_ROLE"),
        {"from": dao_voting},
    )
    assert stranger_has_role(role="PAUSE_ROLE")

    assert not lido.isStopped()
    lido.stop({"from": stranger})
    assert lido.isStopped()


def has_role(acl, entity, app, role):
    encoded_role = web3.keccak(text=role)
    return acl.hasPermission["address,address,bytes32,uint[]"](
        entity, app, encoded_role, []
    )
