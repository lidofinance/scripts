import pytest
from brownie import interface, web3  # type: ignore

from utils.config import (
    contracts,
    BURNER,
    CURATED_V2_ACCOUNTING,
    TOTAL_NON_COVER_SHARES_BURNT,
    TOTAL_COVER_SHARES_BURNT,
)


@pytest.fixture(scope="module")
def contract() -> interface.Burner:
    return interface.Burner(BURNER)


def test_links(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.LOCATOR() == contracts.lido_locator


def test_roles(contract):
    # Burner role changes made by the SRv3/CMv2 vote (the Burner contract itself is not upgraded).
    REQUEST_BURN_SHARES_ROLE = web3.keccak(text="REQUEST_BURN_SHARES_ROLE").hex()
    REQUEST_BURN_MY_STETH_ROLE = web3.keccak(text="REQUEST_BURN_MY_STETH_ROLE").hex()

    # CSM Accounting: REQUEST_BURN_SHARES_ROLE revoked, REQUEST_BURN_MY_STETH_ROLE granted
    assert not contract.hasRole(REQUEST_BURN_SHARES_ROLE, contracts.cs_accounting)
    assert contract.hasRole(REQUEST_BURN_MY_STETH_ROLE, contracts.cs_accounting)

    # Curated (CMv2) Accounting: REQUEST_BURN_MY_STETH_ROLE granted
    assert contract.hasRole(REQUEST_BURN_MY_STETH_ROLE, CURATED_V2_ACCOUNTING)
