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
    assert contract.getContractVersion() == 3  # SRv3: finalizeUpgrade_v3


def test_initialize(contract):
    # initialize() does _checkContractVersion(0); post-upgrade version is 3 -> reverts (3, 0).
    # .call() — anvil does not surface custom-error data for reverted txs.
    with reverts(encode_error("UnexpectedContractVersion(uint256,uint256)", (3, 0))):
        contract.initialize.call({"from": contracts.voting})


def test_finalize_upgrade_v3(contract):
    # finalizeUpgrade_v3 does _checkContractVersion(2); already at 3 -> reverts (3, 2).
    with reverts(encode_error("UnexpectedContractVersion(uint256,uint256)", (3, 2))):
        contract.finalizeUpgrade_v3.call({"from": contracts.voting})


def test_petrified():
    dummy_version = 115792089237316195423570985008687907853269984665640564039457584007913129639935
    impl = interface.WithdrawalVault(WITHDRAWAL_VAULT_IMPL)
    with reverts(encode_error("UnexpectedContractVersion(uint256,uint256)", (dummy_version, 0))):
        impl.initialize.call({"from": contracts.voting})


def test_withdrawals_vault(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.TREASURY() == contracts.agent
    assert contract.LIDO() == contracts.lido_locator.lido()
    assert contract.TREASURY() == contracts.lido_locator.treasury()
    assert contract.TRIGGERABLE_WITHDRAWALS_GATEWAY() == contracts.triggerable_withdrawals_gateway.address
    assert contract.TRIGGERABLE_WITHDRAWALS_GATEWAY() == contracts.lido_locator.triggerableWithdrawalsGateway()
