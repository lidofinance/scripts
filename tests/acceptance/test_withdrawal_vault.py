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
    assert contract.getContractVersion() == 1


def test_initialize(contract):
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        contract.initialize({"from": contracts.voting})


def test_petrified():
    impl = interface.WithdrawalVault(WITHDRAWAL_VAULT_IMPL)
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        impl.initialize({"from": contracts.voting})


def test_withdrawals_vault(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.TREASURY() == contracts.agent
    assert contract.LIDO() == contracts.lido_locator.lido()
    assert contract.TREASURY() == contracts.lido_locator.treasury()
