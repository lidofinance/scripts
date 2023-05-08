import pytest
from brownie import interface, web3  # type: ignore

from utils.config import (
    contracts,
    LIDO_DEPOSIT_SECURITY_MODULE,
    DSM_GUARDIANS,
    LIDO_DEPOSIT_SECURITY_MODULE_V1,
    CHAIN_DEPOSIT_CONTRACT,
    DSM_MAX_DEPOSITS_PER_BLOCK,
    DSM_MIN_DEPOSIT_BLOCK_DISTANCE,
    DSM_PAUSE_INTENT_VALIDITY_PERIOD_BLOCKS,
    DSM_GUARDIAN_QUORUM,
)


@pytest.fixture(scope="module")
def contract() -> interface.DepositSecurityModule:
    return interface.DepositSecurityModule(LIDO_DEPOSIT_SECURITY_MODULE)


def test_owner(contract):
    assert contract.getOwner() == contracts.agent


def test_links(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.STAKING_ROUTER() == contracts.staking_router
    assert contract.DEPOSIT_CONTRACT() == CHAIN_DEPOSIT_CONTRACT


def test_migration(contract):
    old_dsm = interface.DepositSecurityModule(LIDO_DEPOSIT_SECURITY_MODULE_V1)

    assert contract.PAUSE_MESSAGE_PREFIX() != old_dsm.PAUSE_MESSAGE_PREFIX()
    assert contract.ATTEST_MESSAGE_PREFIX() != old_dsm.ATTEST_MESSAGE_PREFIX()
    assert contract.getMaxDeposits() == old_dsm.getMaxDeposits()
    assert contract.getMinDepositBlockDistance() == old_dsm.getMinDepositBlockDistance()
    assert contract.getGuardians() == old_dsm.getGuardians()
    assert contract.getGuardianQuorum() == old_dsm.getGuardianQuorum()
    assert contract.getPauseIntentValidityPeriodBlocks() == old_dsm.getPauseIntentValidityPeriodBlocks()


def test_deposit_security_module(contract):
    assert contract.getMaxDeposits() == DSM_MAX_DEPOSITS_PER_BLOCK
    assert contract.getMinDepositBlockDistance() == DSM_MIN_DEPOSIT_BLOCK_DISTANCE
    assert contract.getPauseIntentValidityPeriodBlocks() == DSM_PAUSE_INTENT_VALIDITY_PERIOD_BLOCKS

    assert contract.getGuardians() == DSM_GUARDIANS
    assert contract.getGuardianQuorum() == DSM_GUARDIAN_QUORUM

    for guardian in DSM_GUARDIANS:
        assert contract.getGuardianIndex(guardian) >= 0
        assert contract.isGuardian(guardian) == True


def test_prefixes(contract):
    """Test that prefixes are calculated correctly. Fails if chainId of the fork was not =1 during dsm deploy"""
    assert (
        contract.PAUSE_MESSAGE_PREFIX()
        == web3.solidityKeccak(
            ["bytes32", "uint256", "address"],
            [
                web3.keccak(text="lido.DepositSecurityModule.PAUSE_MESSAGE").hex(),
                1,
                LIDO_DEPOSIT_SECURITY_MODULE,
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
                LIDO_DEPOSIT_SECURITY_MODULE,
            ],
        ).hex()
    )
