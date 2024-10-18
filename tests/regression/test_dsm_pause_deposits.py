import pytest
from brownie import accounts, chain, interface, reverts
from utils.config import (
    contracts
)
from utils.dsm import DSMPauseDepositsMessage, set_single_guardian
from utils.evm_script import encode_error

EMPTY_SIGNATURE = (0, 0)

@pytest.fixture(scope="module")
def dsm() -> interface.DepositSecurityModule:
    return contracts.deposit_security_module

@pytest.fixture
def agent(accounts):
    return accounts.at(contracts.agent.address, force=True)

def generate_pause_deposit_sig(dsm, block_number, private_key):
    DSMPauseDepositsMessage.set_message_prefix(dsm.PAUSE_MESSAGE_PREFIX())

    valid_pause_deposits_message = DSMPauseDepositsMessage(block_number)
    (compact_r, compact_vs) = valid_pause_deposits_message.sign(private_key)

    return (compact_r, compact_vs)

def pause_deposits(dsm, pauser, block_number, sig, guardian):
    assert dsm.isDepositsPaused() == False

    pause_deposit_tx = dsm.pauseDeposits(
        block_number,
        sig,
        {"from": pauser},
    )

    deposits_paused_event =  pause_deposit_tx.events["DepositsPaused"]

    assert len(deposits_paused_event) == 1
    assert deposits_paused_event[0]["guardian"] == guardian
    assert dsm.isDepositsPaused() == True

    return pause_deposit_tx

def owner_unpause_deposits(dsm):
    assert dsm.isDepositsPaused() == True
    owner = dsm.getOwner()

    unpause_deposit_tx = dsm.unpauseDeposits(
        {"from": owner},
    )

    deposits_unpaused_event =  unpause_deposit_tx.events["DepositsUnpaused"]
    assert len(deposits_unpaused_event) == 1
    assert dsm.isDepositsPaused() == False

def test_dsm_pause_by_guardian_happy_path(dsm):
    guardian = dsm.getGuardians()[0]
    pause_deposits(dsm, guardian, chain.height, EMPTY_SIGNATURE, guardian)
    owner_unpause_deposits(dsm)

def test_dsm_pause_by_stranger_with_guardian_sign_happy_path(dsm, stranger, agent):
    new_guardian_private_key="0x516b8a7d9290502f5661da81f0cf43893e3d19cb9aea3c426cfb36e8186e9c09"
    new_guardian = accounts.add(private_key=new_guardian_private_key)

    set_single_guardian(dsm, agent, new_guardian)

    block_number=chain.height
    sig = generate_pause_deposit_sig(dsm, block_number, new_guardian_private_key)

    pause_deposits(dsm, stranger, block_number, sig, new_guardian)
    owner_unpause_deposits(dsm)

def test_dsm_pause_deposits_with_expired_block_number(dsm, agent):
    block_number=chain.height - dsm.getPauseIntentValidityPeriodBlocks() - 1
    guardian = dsm.getGuardians()[0]

    with reverts(encode_error("PauseIntentExpired()")):
        dsm.pauseDeposits(block_number, EMPTY_SIGNATURE, {"from": guardian})

def test_dsm_pause_by_stranger_without_guardian_sign(dsm, stranger):
    assert dsm.isDepositsPaused() == False

    with reverts("ECDSA: invalid signature"):
        dsm.pauseDeposits(
            chain.height,
            (0, 0),  # skip signature
            {"from": stranger},
        )

    block_number=chain.height
    non_guardian_private_key="0x" + "1" * 64
    sig = generate_pause_deposit_sig(dsm, block_number, non_guardian_private_key)

    with reverts(encode_error("InvalidSignature()")):
        dsm.pauseDeposits(block_number, sig, {"from": stranger})

