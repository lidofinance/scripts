"""
Tests for voting 14/06/2022.
Deposit security module acceptance tests.
"""
import pytest

from brownie import interface, reverts, chain
from brownie import web3

from scripts.vote_2022_06_14 import start_vote
from common.tx_tracing_helpers import *

old_dsm_address: str = '0xDb149235B6F40dC08810AA69869783Be101790e7'
new_dsm_address: str = '0x710B3303fB508a84F10793c1106e32bE873C24cd'

def test_dsm_upgrade(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, dao_agent, lido
) -> None:
    old_dsm: interface.DepositSecurityModule = interface.DepositSecurityModule(old_dsm_address)
    new_dsm: interface.DepositSecurityModule = interface.DepositSecurityModule(new_dsm_address)

    assert_settings_are_same(old_dsm, new_dsm)

    old_dsm_last_deposited_block: int = old_dsm.getLastDepositBlock()

    assert old_dsm_last_deposited_block >= 14929938, "old DSM: last deposit block should be sane"
    assert new_dsm.getLastDepositBlock() == 0, "new DSM: last deposit block should be zero initially" # should be uninitialized

    new_dsm_last_deposited_block: int = 14985614
    pre_vote_block = web3.eth.block_number
    block_offset = new_dsm_last_deposited_block - pre_vote_block

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    assert_settings_are_same(old_dsm, new_dsm)

    assert old_dsm.getLastDepositBlock() == old_dsm_last_deposited_block, "old DSM: vote should preserve last deposited block"
    assert new_dsm.getLastDepositBlock() == new_dsm_last_deposited_block, "new DSM: vote should update last deposit block properly"

    assert old_dsm.canDeposit() == True, "old DSM: should allow deposits"
    with reverts():
        new_dsm.canDeposit()

    current_block = web3.eth.block_number
    assert current_block < new_dsm_last_deposited_block, "new DSM: last deposited block should be in the future"

    chain.mine(block_offset - (current_block - pre_vote_block) - 1)
    with reverts():
        new_dsm.canDeposit()

    chain.mine()
    assert new_dsm.canDeposit() == False, "new DSM: canDeposit should return false"

    chain.mine(new_dsm.getMinDepositBlockDistance())
    assert new_dsm.canDeposit() == True, "new DSM: canDeposit should return true"

# Ensure that settings are translated properly
def assert_settings_are_same(
    old_dsm: interface.DepositSecurityModule,
    new_dsm: interface.DepositSecurityModule
) -> None:
    assert old_dsm.ATTEST_MESSAGE_PREFIX() == new_dsm.ATTEST_MESSAGE_PREFIX()
    assert old_dsm.DEPOSIT_CONTRACT() == new_dsm.DEPOSIT_CONTRACT()
    assert old_dsm.LIDO() == new_dsm.LIDO()
    assert old_dsm.PAUSE_MESSAGE_PREFIX() == new_dsm.PAUSE_MESSAGE_PREFIX()

    assert old_dsm.getGuardianQuorum() == new_dsm.getGuardianQuorum()
    assert old_dsm.getGuardians() == new_dsm.getGuardians()

    assert old_dsm.getMaxDeposits() == new_dsm.getMaxDeposits()
    assert old_dsm.getMinDepositBlockDistance() == new_dsm.getMinDepositBlockDistance()

    assert old_dsm.getNodeOperatorsRegistry() == new_dsm.getNodeOperatorsRegistry()
    assert old_dsm.getOwner() == new_dsm.getOwner()

    assert old_dsm.getPauseIntentValidityPeriodBlocks() == new_dsm.getPauseIntentValidityPeriodBlocks()
    assert old_dsm.isPaused() == new_dsm.isPaused()

    # can't check the following dynamic properties here:
    # `canDeposit`
    # `getLastDepositBlock`
