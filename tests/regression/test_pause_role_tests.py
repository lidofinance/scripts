"""
Tests for contracts.lido resume/pause roles 24/05/2022
"""
import pytest
from functools import partial
from brownie import reverts, web3

from utils.config import contracts


@pytest.fixture(scope="function")
def stop_lido():
    if not contracts.lido.isStopped():
        contracts.lido.stop({"from": contracts.voting})


@pytest.fixture(scope="function")
def resume_lido():
    if contracts.lido.isStopped():
        contracts.lido.resume({"from": contracts.voting})

@pytest.fixture(scope="function")
def pause_withdrawal_queue():
    inf = contracts.withdrawal_queue.PAUSE_INFINITELY()
    if not contracts.withdrawal_queue.isPaused():
        contracts.withdrawal_queue.grantRole(
            web3.keccak(text="PAUSE_ROLE"),
            contracts.agent,
            {"from": contracts.agent},
        )
        contracts.withdrawal_queue.pauseFor(inf, {"from": contracts.agent})

@pytest.fixture(scope="function")
def resume_withdrawal_queue():
    if contracts.withdrawal_queue.isPaused():
        contracts.withdrawal_queue.grantRole(
            web3.keccak(text="RESUME_ROLE"),
            contracts.agent,
            {"from": contracts.agent},
        )
        contracts.withdrawal_queue.resume({"from": contracts.agent})


@pytest.mark.usefixtures("stop_lido")
def test_pause_role_cant_resume(stranger):
    stranger_has_role = partial(has_permission, app=contracts.lido, entity=stranger)
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
    stranger_has_role = partial(has_permission, app=contracts.lido, entity=stranger)
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
    stranger_has_role = partial(has_permission, app=contracts.lido, entity=stranger)
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
    stranger_has_role = partial(has_permission, app=contracts.lido, entity=stranger)
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



@pytest.mark.usefixtures("resume_withdrawal_queue")
def test_withdrawal_queue_pause_role_can_pause(stranger):
    inf = contracts.withdrawal_queue.PAUSE_INFINITELY()
    with reverts():
        contracts.withdrawal_queue.pauseFor(inf, {"from": stranger})

    stranger_has_role = partial(has_role, entity=stranger, contract=contracts.withdrawal_queue)
    assert not stranger_has_role(role="PAUSE_ROLE")

    contracts.withdrawal_queue.grantRole(
        web3.keccak(text="PAUSE_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    assert stranger_has_role(role="PAUSE_ROLE")

    contracts.withdrawal_queue.pauseFor(inf, {"from": stranger})
    assert contracts.withdrawal_queue.isPaused()

@pytest.mark.usefixtures("pause_withdrawal_queue")
def test_withdrawal_queue_pause_role_cant_resume(stranger):
    contracts.withdrawal_queue.grantRole(
        web3.keccak(text="PAUSE_ROLE"),
        stranger,
        {"from": contracts.agent},
    )

    assert contracts.withdrawal_queue.isPaused()
    with reverts():
        contracts.withdrawal_queue.resume({"from": stranger})

@pytest.mark.usefixtures("pause_withdrawal_queue")
def test_withdrawal_queue_resume_role_can_resume(stranger):
    with reverts():
        contracts.withdrawal_queue.resume({"from": stranger})

    stranger_has_role = partial(has_role, entity=stranger, contract=contracts.withdrawal_queue)
    assert not stranger_has_role(role="RESUME_ROLE")

    contracts.withdrawal_queue.grantRole(
        web3.keccak(text="RESUME_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    assert stranger_has_role(role="RESUME_ROLE")

    contracts.withdrawal_queue.resume({"from": stranger})
    assert not contracts.withdrawal_queue.isPaused()

@pytest.mark.usefixtures("resume_withdrawal_queue")
def test_withdrawal_queue_resume_role_cant_pause(stranger):
    inf = contracts.withdrawal_queue.PAUSE_INFINITELY()
    contracts.withdrawal_queue.grantRole(
        web3.keccak(text="RESUME_ROLE"),
        stranger,
        {"from": contracts.agent},
    )

    assert not contracts.withdrawal_queue.isPaused()
    with reverts():
        contracts.withdrawal_queue.pauseFor(inf, {"from": stranger})


def has_permission(entity, app, role):
    encoded_role = web3.keccak(text=role)
    return contracts.acl.hasPermission["address,address,bytes32,uint[]"](entity, app, encoded_role, [])

def has_role(role, contract, entity):
    encoded_role = web3.keccak(text=role)
    return contract.hasRole(encoded_role, entity)
