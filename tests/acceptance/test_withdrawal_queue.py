import pytest
from brownie import interface, ZERO_ADDRESS, reverts  # type: ignore

from utils.config import (
    contracts,
    LIDO_WITHDRAWAL_QUEUE,
    LIDO_WITHDRAWAL_QUEUE_IMPL,
    WQ_ERC721_TOKEN_NAME,
    WQ_ERC721_TOKEN_SYMBOL,
    WQ_ERC721_TOKEN_BASE_URI,
)
from utils.evm_script import encode_error


@pytest.fixture(scope="module")
def contract() -> interface.WithdrawalQueueERC721:
    return interface.WithdrawalQueueERC721(LIDO_WITHDRAWAL_QUEUE)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == LIDO_WITHDRAWAL_QUEUE_IMPL
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_versioned(contract):
    assert contract.getContractVersion() == 1


def test_initialize(contract):
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        contract.initialize(contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0), {"from": contracts.voting})


def test_petrified(contract):
    impl = interface.WithdrawalQueueERC721(LIDO_WITHDRAWAL_QUEUE_IMPL)
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
    assert contract.name() == WQ_ERC721_TOKEN_NAME
    assert contract.symbol() == WQ_ERC721_TOKEN_SYMBOL
    assert contract.getBaseURI() == WQ_ERC721_TOKEN_BASE_URI
    assert contract.getNFTDescriptorAddress() == ZERO_ADDRESS
