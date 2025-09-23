import pytest
from brownie import interface, reverts  # type: ignore

from utils.config import contracts, WITHDRAWAL_VAULT, WITHDRAWAL_VAULT_IMPL
from utils.evm_script import encode_error


@pytest.fixture(scope="module")
def contract() -> interface.WithdrawalVault:
    return interface.WithdrawalVault(WITHDRAWAL_VAULT)


def test_proxy(contract):
    proxy = interface.WithdrawalVaultManager(contract)
    assert proxy.implementation() == WITHDRAWAL_VAULT_IMPL
    assert proxy.proxy_getAdmin() == contracts.agent.address


def test_versioned(contract):
    assert contract.getContractVersion() == 2


def test_initialize(contract):
    with reverts(encode_error("UnexpectedContractVersion(uint256,uint256)", (2, 0))):
        contract.initialize({"from": contracts.voting})


def test_petrified():
    dummy_version = 115792089237316195423570985008687907853269984665640564039457584007913129639935
    impl = interface.WithdrawalVault(WITHDRAWAL_VAULT_IMPL)
    with reverts(encode_error("UnexpectedContractVersion(uint256,uint256)", (dummy_version, 0))):
        impl.initialize({"from": contracts.voting})


def test_withdrawals_vault(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.TREASURY() == contracts.agent
    assert contract.LIDO() == contracts.lido_locator.lido()
    assert contract.TREASURY() == contracts.lido_locator.treasury()
    assert contract.TRIGGERABLE_WITHDRAWALS_GATEWAY() == contracts.triggerable_withdrawals_gateway.address
    assert contract.TRIGGERABLE_WITHDRAWALS_GATEWAY() == contracts.lido_locator.triggerableWithdrawalsGateway()
