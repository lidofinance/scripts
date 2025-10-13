import pytest
from brownie import Contract, interface, web3  # type: ignore
from brownie.network.account import Account

from utils.config import GATE_SEAL_EXPIRY_TIMESTAMP, GATE_SEAL_PAUSE_DURATION, contracts, GATE_SEAL, \
    GATE_SEAL_COMMITTEE, RESEAL_MANAGER, VEB_TWG_GATE_SEAL


@pytest.fixture(scope="module")
def gate_seal_committee(accounts) -> Account:
    return accounts.at(GATE_SEAL_COMMITTEE, force=True)


@pytest.fixture(scope="module")
def contract() -> Contract:
    return interface.GateSeal(GATE_SEAL)


@pytest.fixture(scope="module")
def veb_twg_contract() -> Contract:
    return interface.GateSeal(VEB_TWG_GATE_SEAL)


@pytest.fixture(scope="module")
def reseal_manager() -> Contract:
    return interface.ResealManager(RESEAL_MANAGER)


def test_gate_seal(contract: Contract, gate_seal_committee: Account, reseal_manager: Contract):
    assert contract.get_sealing_committee() == gate_seal_committee

    sealables = contract.get_sealables()
    assert len(sealables) == 1
    assert contracts.withdrawal_queue.address in sealables

    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", reseal_manager.address)
    _check_role(contracts.withdrawal_queue, "RESUME_ROLE", reseal_manager.address)

    assert contract.get_seal_duration_seconds() == GATE_SEAL_PAUSE_DURATION
    assert contract.get_expiry_timestamp() == GATE_SEAL_EXPIRY_TIMESTAMP
    assert not contract.is_expired()


def test_veb_twg_gate_seal(veb_twg_contract: Contract, gate_seal_committee: Account, reseal_manager: Contract):
    assert veb_twg_contract.get_sealing_committee() == gate_seal_committee

    sealables = veb_twg_contract.get_sealables()
    assert len(sealables) == 2
    assert contracts.validators_exit_bus_oracle.address in sealables
    assert contracts.triggerable_withdrawals_gateway.address in sealables

    role = "PAUSE_ROLE"
    role_bytes = web3.keccak(text=role).hex()

    assert contracts.validators_exit_bus_oracle.getRoleMemberCount(role_bytes) == 2, f"Role {role} on {contracts.validators_exit_bus_oracle.address} should have exactly two holders"
    assert contracts.validators_exit_bus_oracle.getRoleMember(role_bytes, 0) == reseal_manager.address, f"Role {role} holder on {contracts.validators_exit_bus_oracle.address} should be {reseal_manager.address}"
    assert contracts.validators_exit_bus_oracle.getRoleMember(role_bytes, 1) == veb_twg_contract.address, f"Role {role} holder on {contracts.validators_exit_bus_oracle.address} should be {contracts.veb_twg_contract.address}"

    assert contracts.triggerable_withdrawals_gateway.getRoleMemberCount(role_bytes) == 2, f"Role {role} on {contracts.triggerable_withdrawals_gateway.address} should have exactly two holders"
    assert contracts.triggerable_withdrawals_gateway.getRoleMember(role_bytes, 0) == veb_twg_contract.address, f"Role {role} holder on {contracts.triggerable_withdrawals_gateway.address} should be {contracts.veb_twg_contract.address}"
    assert contracts.triggerable_withdrawals_gateway.getRoleMember(role_bytes, 1) == reseal_manager.address, f"Role {role} holder on {contracts.triggerable_withdrawals_gateway.address} should be {reseal_manager.address}"

    assert veb_twg_contract.get_seal_duration_seconds() == GATE_SEAL_PAUSE_DURATION
    assert veb_twg_contract.get_expiry_timestamp() == GATE_SEAL_EXPIRY_TIMESTAMP
    assert not veb_twg_contract.is_expired()


    _check_role(contracts.validators_exit_bus_oracle, "RESUME_ROLE", reseal_manager.address, 1)
    _check_role(contracts.triggerable_withdrawals_gateway, "RESUME_ROLE", reseal_manager.address, 1)


def _check_role(contract: Contract, role: str, holder: str, holders_count: int = 2):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == holders_count, f"Role {role} on {contract} should have exactly '{holders_count}' holders"
    assert contract.getRoleMember(role_bytes, 0) == holder, f"Role {role} holder on {contract} should be {holder}"
