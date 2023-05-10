import pytest
from brownie import interface  # type: ignore

from utils.config import contracts, EXECUTION_LAYER_REWARDS_VAULT


@pytest.fixture(scope="module")
def contract() -> interface.WithdrawalVault:
    return interface.WithdrawalVault(EXECUTION_LAYER_REWARDS_VAULT)


def test_vault(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.TREASURY() == contracts.agent
