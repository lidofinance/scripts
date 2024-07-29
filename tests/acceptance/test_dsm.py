import pytest
from brownie import interface, web3  # type: ignore

from utils.config import (
    contracts,
    DEPOSIT_SECURITY_MODULE,
    DSM_GUARDIANS,
    CHAIN_DEPOSIT_CONTRACT,
    DSM_MAX_OPERATORS_PER_UNVETTING,
    DSM_PAUSE_INTENT_VALIDITY_PERIOD_BLOCKS,
    DSM_GUARDIAN_QUORUM,
)


@pytest.fixture(scope="module")
def dsm() -> interface.DepositSecurityModule:
    return contracts.deposit_security_module


def test_owner(dsm):
    assert dsm.getOwner() == contracts.agent

def test_versioned(dsm):
    assert dsm.VERSION() == 3

def test_links(dsm):
    assert dsm.LIDO() == contracts.lido
    assert dsm.STAKING_ROUTER() == contracts.staking_router
    assert dsm.DEPOSIT_CONTRACT() == CHAIN_DEPOSIT_CONTRACT


def test_deposit_security_module(dsm):
    assert dsm.getMaxOperatorsPerUnvetting() == DSM_MAX_OPERATORS_PER_UNVETTING
    assert dsm.getPauseIntentValidityPeriodBlocks() == DSM_PAUSE_INTENT_VALIDITY_PERIOD_BLOCKS

    assert dsm.getGuardians() == DSM_GUARDIANS
    assert dsm.getGuardianQuorum() == DSM_GUARDIAN_QUORUM

    for guardian in DSM_GUARDIANS:
        assert dsm.getGuardianIndex(guardian) >= 0
        assert dsm.isGuardian(guardian) == True


def test_prefixes(dsm):
    """Test that prefixes are calculated correctly. Fails if chainId of the fork was not =1 during dsm deploy"""
    assert (
        dsm.PAUSE_MESSAGE_PREFIX()
        == web3.solidity_keccak(
            ["bytes32", "uint256", "address"],
            [
                web3.keccak(text="lido.DepositSecurityModule.PAUSE_MESSAGE").hex(),
                1,
                DEPOSIT_SECURITY_MODULE,
            ],
        ).hex()
    )
    assert (
        dsm.ATTEST_MESSAGE_PREFIX()
        == web3.solidity_keccak(
            ["bytes32", "uint256", "address"],
            [
                web3.keccak(text="lido.DepositSecurityModule.ATTEST_MESSAGE").hex(),
                1,
                DEPOSIT_SECURITY_MODULE,
            ],
        ).hex()
    )
