import pytest
from brownie import interface  # type: ignore

from utils.config import (
    contracts,
    lido_dao_burner,
    TOTAL_NON_COVER_SHARES_BURNT,
    TOTAL_COVER_SHARES_BURNT,
)


@pytest.fixture(scope="module")
def contract() -> interface.Burner:
    return interface.Burner(lido_dao_burner)


def test_links(contract):
    assert contract.STETH() == contracts.lido
    assert contract.TREASURY() == contracts.agent


def test_burner(contract):
    shares_requested_to_burn = contract.getSharesRequestedToBurn()

    assert shares_requested_to_burn["coverShares"] == 0
    assert shares_requested_to_burn["nonCoverShares"] == 0

    assert contract.getCoverSharesBurnt() == TOTAL_COVER_SHARES_BURNT
    assert contract.getExcessStETH() == 0

    assert contract.getNonCoverSharesBurnt() == TOTAL_NON_COVER_SHARES_BURNT
