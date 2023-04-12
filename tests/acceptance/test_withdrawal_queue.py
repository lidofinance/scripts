import pytest
from brownie import interface, ZERO_ADDRESS  # type: ignore

from utils.config import contracts, lido_dao_withdrawal_queue

lido_dao_withdrawal_queue_impl = "0x8e625031D47721E5FA1D13cEA033EC1dd067F663"


@pytest.fixture(scope="module")
def contract() -> interface.WithdrawalQueueERC721:
    return interface.WithdrawalQueueERC721(lido_dao_withdrawal_queue)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == lido_dao_withdrawal_queue_impl
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_versioned(contract):
    assert contract.getContractVersion() == 1


def test_pusable_until(contract):
    assert contract.isPaused() == False
    assert contract.getResumeSinceTimestamp() > 0


def test_withdrawal_queue(contract):
    assert contract.WSTETH() == contracts.wsteth
    assert contract.STETH() == contracts.lido
    assert contract.bunkerModeSinceTimestamp() == contract.BUNKER_MODE_DISABLED_TIMESTAMP()


def test_withdrawal_queue_erc721(contract):
    assert contract.name() == "stETH Withdrawal NFT"
    assert contract.symbol() == "unstETH"
    assert contract.getBaseURI() == ""
    assert contract.getNFTDescriptorAddress() == ZERO_ADDRESS
