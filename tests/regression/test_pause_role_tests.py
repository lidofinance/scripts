"""
Tests for lido resume/pause roles 24/05/2022
"""
import pytest
from functools import partial
from brownie import reverts, web3
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(vote_id_from_env, helpers, accounts, dao_voting):
    if vote_id_from_env:
        helpers.execute_vote(vote_id=vote_id_from_env, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether")

    start_and_execute_votes(dao_voting, helpers)


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
    return acl.hasPermission["address,address,bytes32,uint[]"](entity, app, encoded_role, [])
