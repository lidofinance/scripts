import pytest
from brownie import interface  # type: ignore

from utils.config import (
    contracts,
    BURNER,
    TOTAL_NON_COVER_SHARES_BURNT,
    TOTAL_COVER_SHARES_BURNT,
)


@pytest.fixture(scope="module")
def contract() -> interface.Burner:
    return interface.Burner(BURNER)


def test_links(contract):
    assert contract.STETH() == contracts.lido
    assert contract.TREASURY() == contracts.agent
