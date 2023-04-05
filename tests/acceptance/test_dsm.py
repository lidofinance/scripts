import pytest
from brownie import interface, web3  # type: ignore

from utils.config import (
    contracts,
    lido_dao_deposit_security_module_address,
    guardians,
    lido_dao_deposit_security_module_address_old,
    deposit_contract,
)


@pytest.fixture(scope="module")
def contract() -> interface.DepositSecurityModule:
    return interface.DepositSecurityModule(lido_dao_deposit_security_module_address)


def test_locator(contract):
    assert contract == contracts.lido_locator.depositSecurityModule()


def test_owner(contract):
    assert contract.getOwner() == contracts.agent


def test_links(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.LIDO() == contracts.lido_locator.lido()
    assert contract.STAKING_ROUTER() == contracts.staking_router
    assert contract.STAKING_ROUTER() == contracts.lido_locator.stakingRouter()
    assert contract.DEPOSIT_CONTRACT() == deposit_contract


def test_migration(contract):
    old_dsm = interface.DepositSecurityModule(lido_dao_deposit_security_module_address_old)

    assert contract.PAUSE_MESSAGE_PREFIX() != old_dsm.PAUSE_MESSAGE_PREFIX()
    assert contract.ATTEST_MESSAGE_PREFIX() != old_dsm.ATTEST_MESSAGE_PREFIX()
    assert contract.getMaxDeposits() == old_dsm.getMaxDeposits()
    assert contract.getMinDepositBlockDistance() == old_dsm.getMinDepositBlockDistance()
    assert contract.getGuardians() == old_dsm.getGuardians()
    assert contract.getGuardianQuorum() == old_dsm.getGuardianQuorum()
    assert contract.getPauseIntentValidityPeriodBlocks() == old_dsm.getPauseIntentValidityPeriodBlocks()


def test_deposit_security_module(contract):
    assert contract.getMaxDeposits() == 150
    assert contract.getMinDepositBlockDistance() == 25

    assert contract.getGuardians() == guardians
    assert contract.getGuardianQuorum() == 4

    for guardian in guardians:
        assert contract.getGuardianIndex(guardian) >= 0
        assert contract.isGuardian(guardian) == True

    assert contract.getPauseIntentValidityPeriodBlocks() == 6646


def test_prefixes(contract):
    """Test that prefixes are calculated correctly. Fails if chainId of the fork was not =1 during dsm deploy"""
    assert (
        contract.PAUSE_MESSAGE_PREFIX()
        == web3.solidityKeccak(
            ["bytes32", "uint256", "address"],
            [
                web3.keccak(text="lido.DepositSecurityModule.PAUSE_MESSAGE").hex(),
                1,
                lido_dao_deposit_security_module_address,
            ],
        ).hex()
    )
    assert (
        contract.ATTEST_MESSAGE_PREFIX()
        == web3.solidityKeccak(
            ["bytes32", "uint256", "address"],
            [
                web3.keccak(text="lido.DepositSecurityModule.ATTEST_MESSAGE").hex(),
                1,
                lido_dao_deposit_security_module_address,
            ],
        ).hex()
    )
