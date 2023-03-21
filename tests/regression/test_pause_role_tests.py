"""
Tests for contracts.lido resume/pause roles 24/05/2022
"""
import pytest
from functools import partial
from brownie import reverts, web3

from utils.config import contracts

@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="function")
def stop_lido():
    if not contracts.lido.isStopped():
        contracts.lido.stop({"from": contracts.voting})


@pytest.fixture(scope="function")
def resume_lido():
    if contracts.lido.isStopped():
        contracts.lido.resume({"from": contracts.voting})


@pytest.mark.usefixtures("stop_lido")
def test_pause_role_cant_resume(stranger):
    stranger_has_role = partial(has_role, app=contracts.lido, entity=stranger)
    assert not stranger_has_role(role="RESUME_ROLE")

    contracts.acl.grantPermission(
        stranger,
        contracts.lido,
        web3.keccak(text="PAUSE_ROLE"),
        {"from": contracts.voting},
    )
    assert stranger_has_role(role="PAUSE_ROLE")

    assert contracts.lido.isStopped()
    with reverts("APP_AUTH_FAILED"):
        contracts.lido.resume({"from": stranger})


@pytest.mark.usefixtures("resume_lido")
def test_resume_role_cant_pause(stranger):
    stranger_has_role = partial(has_role, app=contracts.lido, entity=stranger)
    assert not stranger_has_role(role="PAUSE_ROLE")

    contracts.acl.grantPermission(
        stranger,
        contracts.lido,
        web3.keccak(text="RESUME_ROLE"),
        {"from": contracts.voting},
    )
    assert stranger_has_role(role="RESUME_ROLE")

    assert not contracts.lido.isStopped()
    with reverts("APP_AUTH_FAILED"):
        contracts.lido.stop({"from": stranger})


@pytest.mark.usefixtures("stop_lido")
def test_resume_role_can_resume(stranger):
    stranger_has_role = partial(has_role, app=contracts.lido, entity=stranger)
    assert not stranger_has_role(role="PAUSE_ROLE")

    contracts.acl.grantPermission(
        stranger,
        contracts.lido,
        web3.keccak(text="RESUME_ROLE"),
        {"from": contracts.voting},
    )
    assert stranger_has_role(role="RESUME_ROLE")

    assert contracts.lido.isStopped()
    contracts.lido.resume({"from": stranger})
    assert not contracts.lido.isStopped()


@pytest.mark.usefixtures("resume_lido")
def test_pause_role_can_pause(stranger):
    stranger_has_role = partial(has_role, app=contracts.lido, entity=stranger)
    assert not stranger_has_role(role="RESUME_ROLE")

    contracts.acl.grantPermission(
        stranger,
        contracts.lido,
        web3.keccak(text="PAUSE_ROLE"),
        {"from": contracts.voting},
    )
    assert stranger_has_role(role="PAUSE_ROLE")

    assert not contracts.lido.isStopped()
    contracts.lido.stop({"from": stranger})
    assert contracts.lido.isStopped()


def has_role( entity, app, role):
    encoded_role = web3.keccak(text=role)
    return contracts.acl.hasPermission["address,address,bytes32,uint[]"](entity, app, encoded_role, [])
