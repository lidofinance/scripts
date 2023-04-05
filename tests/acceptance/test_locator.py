import pytest
from brownie import interface  # type: ignore

from utils.config import contracts, lido_dao_lido_locator, lido_dao_lido_locator_implementation


@pytest.fixture(scope="module")
def contract() -> interface.LidoLocator:
    return interface.LidoLocator(lido_dao_lido_locator)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == lido_dao_lido_locator_implementation
    assert proxy.proxy__getAdmin() == contracts.agent.address
