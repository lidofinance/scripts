import pytest
from brownie import interface, ZERO_ADDRESS, reverts  # type: ignore

from utils.config import (
    contracts,
    lido_dao_withdrawal_queue,
    lido_dao_withdrawal_queue_implementation,
    WITHDRAWAL_QUEUE_ERC721_NAME,
    WITHDRAWAL_QUEUE_ERC721_SYMBOL,
    WITHDRAWAL_QUEUE_ERC721_BASE_URI,
)
from utils.evm_script import encode_error


@pytest.fixture(scope="module")
def contract() -> interface.WithdrawalQueueERC721:
    return interface.WithdrawalQueueERC721(lido_dao_withdrawal_queue)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == lido_dao_withdrawal_queue_implementation
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_versioned(contract):
    assert contract.getContractVersion() == 1


def test_initialize(contract):
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        contract.initialize(contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0), {"from": contracts.voting})


def test_petrified(contract):
    impl = interface.WithdrawalQueueERC721(lido_dao_withdrawal_queue_implementation)
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        impl.initialize(contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0), {"from": contracts.voting})


def test_pausable_until(contract):
    assert contract.isPaused() == False
    assert contract.getResumeSinceTimestamp() > 0


def test_withdrawal_queue(contract):
    assert contract.WSTETH() == contracts.wsteth
    assert contract.STETH() == contracts.lido
    assert contract.bunkerModeSinceTimestamp() == contract.BUNKER_MODE_DISABLED_TIMESTAMP()


def test_withdrawal_queue_erc721(contract):
    assert contract.name() == WITHDRAWAL_QUEUE_ERC721_NAME
    assert contract.symbol() == WITHDRAWAL_QUEUE_ERC721_SYMBOL
    assert contract.getBaseURI() == WITHDRAWAL_QUEUE_ERC721_BASE_URI
    assert contract.getNFTDescriptorAddress() == ZERO_ADDRESS
