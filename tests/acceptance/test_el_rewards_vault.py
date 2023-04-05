import pytest
from brownie import interface  # type: ignore

from utils.config import contracts, lido_dao_execution_layer_rewards_vault


@pytest.fixture(scope="module")
def contract() -> interface.WithdrawalVault:
    return interface.WithdrawalVault(lido_dao_execution_layer_rewards_vault)


def test_vault(contract):
    assert contract.LIDO() == contracts.lido
    assert contract.TREASURY() == contracts.agent
