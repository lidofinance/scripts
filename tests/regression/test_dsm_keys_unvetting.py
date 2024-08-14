import pytest
from brownie import accounts, convert, interface, reverts, web3
from web3 import Web3
from utils.config import (
    contracts,
    DSM_MAX_OPERATORS_PER_UNVETTING,
    NODE_OPERATORS_REGISTRY,
)
from utils.dsm import DSMUnvetMessage, UnvetArgs, to_bytes, set_single_guardian
from utils.evm_script import encode_error
from utils.staking_module import add_node_operator
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch

STAKING_MODULE_ID = 1

@pytest.fixture(scope="module")
def dsm() -> interface.DepositSecurityModule:
    return contracts.deposit_security_module

@pytest.fixture
def voting(accounts):
    return accounts.at(contracts.voting.address, force=True)

@pytest.fixture
def agent(accounts):
    return accounts.at(contracts.agent.address, force=True)

@pytest.fixture
def new_guardian(accounts):
    return accounts[9]

def test_dsm_max_operators_per_unvetting(dsm, agent, stranger):
    assert dsm.getMaxOperatorsPerUnvetting() == DSM_MAX_OPERATORS_PER_UNVETTING

    with reverts(encode_error("NotAnOwner(string)", [stranger.address.lower()])):
        dsm.setMaxOperatorsPerUnvetting(1, {"from": stranger})

    dsm.setMaxOperatorsPerUnvetting(1, {"from": agent})
    assert dsm.getMaxOperatorsPerUnvetting() == 1


def test_dsm_keys_unvetting_by_stranger_without_guardian_sign(dsm, stranger):
    staking_module_id= 1
    operator_id = 0
    block_number = web3.eth.get_block_number()
    block = web3.eth.get_block(block_number)
    staking_module_nonce = contracts.staking_router.getStakingModuleNonce(1)

    args = UnvetArgs(
        block_number=block_number,
        block_hash=block.hash,
        staking_module_id=staking_module_id,
        nonce=staking_module_nonce,
        node_operator_ids=to_bytes(operator_id, 16),
        vetted_signing_keys_counts=to_bytes(1, 32),
    ).to_tuple()

    non_guardian_private_key="0x" + "1" * 64

    DSMUnvetMessage.set_message_prefix(dsm.UNVET_MESSAGE_PREFIX())
    valid_unvet_message = DSMUnvetMessage(*args)
    (compact_r, compact_vs) = valid_unvet_message.sign(non_guardian_private_key)

    with reverts(encode_error("InvalidSignature()")):
        dsm.unvetSigningKeys(*args, (compact_r, compact_vs), {"from": stranger})



def test_dsm_keys_unvetting_by_stranger_with_guardian_sign(dsm, agent, stranger):
    private_key="0x516b8a7d9290502f5661da81f0cf43893e3d19cb9aea3c426cfb36e8186e9c09"
    new_guardian = accounts.add(private_key=private_key)

    set_single_guardian(dsm, agent, new_guardian)

    staking_module_id= 1
    operator_id = 0
    block_number = web3.eth.get_block_number()
    block = web3.eth.get_block(block_number)
    staking_module_nonce = contracts.staking_router.getStakingModuleNonce(1)

    args = UnvetArgs(
        block_number=block_number,
        block_hash=block.hash,
        staking_module_id=staking_module_id,
        nonce=staking_module_nonce,
        node_operator_ids=to_bytes(operator_id, 16),
        vetted_signing_keys_counts=to_bytes(1, 32),
    ).to_tuple()

    DSMUnvetMessage.set_message_prefix(dsm.UNVET_MESSAGE_PREFIX())
    valid_unvet_message = DSMUnvetMessage(*args)
    (compact_r, compact_vs) = valid_unvet_message.sign(private_key)

    dsm.unvetSigningKeys(*args, (compact_r, compact_vs), {"from": stranger})

def test_dsm_keys_unvetting_by_guardian(dsm, agent, stranger):
    new_guardian = stranger

    staking_module_id= 1
    operator_id = 0

    staking_module = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    node_operator_before_unvetting = staking_module.getNodeOperator(operator_id, True)
    totalDepositedValidators = node_operator_before_unvetting["totalDepositedValidators"]
    assert totalDepositedValidators > 1

    block_number = web3.eth.get_block_number()
    block = web3.eth.get_block(block_number)
    staking_module_nonce = contracts.staking_router.getStakingModuleNonce(1)

    unvet_args = UnvetArgs(
        block_number=block_number,
        block_hash=block.hash,
        staking_module_id=staking_module_id,
        nonce=staking_module_nonce,
        node_operator_ids=to_bytes(operator_id, 16),
        # try to unvet less than totalDepositedValidators
        vetted_signing_keys_counts=to_bytes(1, 32),
    )

    set_single_guardian(dsm, agent, new_guardian)

    dsm.unvetSigningKeys(*unvet_args.to_tuple(), (0, 0), {"from": new_guardian.address})

    node_operator_after_unvetting = staking_module.getNodeOperator(operator_id, True)
    assert node_operator_after_unvetting["totalDepositedValidators"] == totalDepositedValidators
    assert node_operator_after_unvetting["totalVettedValidators"] == totalDepositedValidators


def test_dsm_decrease_vetted_signing_keys_count(dsm, agent, voting, stranger):
    staking_module_id= 1
    staking_module = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    operator_id = add_node_operator(staking_module, voting, stranger)
    operator = staking_module.getNodeOperator(operator_id, True)

    keys_count = 10
    staking_module.addSigningKeys(
        operator_id,
        keys_count,
        random_pubkeys_batch(keys_count),
        random_signatures_batch(keys_count),
        {"from": operator["rewardAddress"]},
    )

    contracts.acl.grantPermission(
        stranger,
        staking_module,
        convert.to_uint(Web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")),
        {"from": voting},
    )

    staking_module.setNodeOperatorStakingLimit(operator_id, 8, {"from": stranger})

    node_operator_before_unvetting = staking_module.getNodeOperator(operator_id, True)
    assert node_operator_before_unvetting["totalAddedValidators"] == keys_count
    assert node_operator_before_unvetting["totalVettedValidators"] == 8

    block_number = web3.eth.get_block_number()
    block = web3.eth.get_block(block_number)
    staking_module_nonce = contracts.staking_router.getStakingModuleNonce(1)
    vetted_signing_keys_counts_after_unvet = 4
    unvet_args = UnvetArgs(
        block_number=block_number,
        block_hash=block.hash,
        staking_module_id=staking_module_id,
        nonce=staking_module_nonce,
        node_operator_ids=to_bytes(operator_id, 16),
        # try to unvet less than totalDepositedValidators
        vetted_signing_keys_counts=to_bytes(vetted_signing_keys_counts_after_unvet, 32),
    )

    new_guardian = stranger
    set_single_guardian(dsm, agent, new_guardian)

    dsm.unvetSigningKeys(*unvet_args.to_tuple(), (0, 0), {"from": new_guardian.address})
    node_operator_after_unvetting = staking_module.getNodeOperator(operator_id, True)
    assert node_operator_after_unvetting["totalVettedValidators"] == vetted_signing_keys_counts_after_unvet


