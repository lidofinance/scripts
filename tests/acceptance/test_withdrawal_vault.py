import pytest
from brownie import interface  # type: ignore

from utils.config import contracts, lido_dao_withdrawal_vault, lido_dao_withdrawal_vault_implementation


@pytest.fixture(scope="module")
def contract() -> interface.WithdrawalVault:
    return interface.WithdrawalVault(lido_dao_withdrawal_vault)


def test_locator(contract):
    assert contract == contracts.lido_locator.withdrawalVault()


def test_proxy(contract):
    proxy = interface.WithdrawalVaultManager(contract)
    assert proxy.implementation() == lido_dao_withdrawal_vault_implementation
    assert proxy.proxy_getAdmin() == contracts.voting.address


def test_versioned(contract):
    assert contract.getContractVersion() == 1


def test_withdrawals_vault(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.TREASURY() == contracts.agent
    assert contract.LIDO() == contracts.lido_locator.lido()
    assert contract.TREASURY() == contracts.lido_locator.treasury()
