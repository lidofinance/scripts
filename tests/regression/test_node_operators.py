import os
import pytest
import random
import textwrap
from brownie import Wei, network, chain

from utils.config import contracts
from utils.mainnet_fork import chain_snapshot
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from utils.test.node_operators_helpers import assert_node_operators, assert_summaries, assert_node_operator_added_event

PUBKEY_LENGTH = 48
SIGNATURE_LENGTH = 96
DEPOSIT_SIZE = Wei("32 ether")


@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass


@pytest.fixture(scope="module")
def nor(accounts, interface):
    return interface.NodeOperatorsRegistry(contracts.node_operators_registry.address)


@pytest.fixture(scope="module")
def voting_eoa(accounts):
    return accounts.at(contracts.voting.address, force=True)


@pytest.fixture(scope="module")
def reward_address(accounts):
    return accounts[7]


@pytest.fixture(scope="module")
def new_node_operator_id(nor):
    return nor.getNodeOperatorsCount()


def test_add_node_operator(nor, voting_eoa, reward_address, new_node_operator_id):
    new_node_operator_name = "new_node_operator"

    node_operators_count_before = nor.getNodeOperatorsCount()
    active_node_operators_count_before = nor.getActiveNodeOperatorsCount()

    # new_node_operator_id = node_operators_count_before
    tx = nor.addNodeOperator("new_node_operator", reward_address, {"from": voting_eoa})

    node_operator_count_after = nor.getNodeOperatorsCount()
    active_node_operators_count_after = nor.getActiveNodeOperatorsCount()

    assert node_operator_count_after == node_operators_count_before + 1
    assert active_node_operators_count_after == active_node_operators_count_before + 1

    assert_node_operators(
        nor.getNodeOperator(new_node_operator_id, True),
        {
            "active": True,
            "name": new_node_operator_name,
            "rewardAddress": reward_address,
            "usedSigningKeys": 0,
            "stoppedValidators": 0,
            "totalSigningKeys": 0,
            "stakingLimit": 0,
        },
    )

    assert_summaries(
        nor.getNodeOperatorSummary(new_node_operator_id),
        {
            "isTargetLimitActive": False,
            "targetValidatorsCount": 0,
            "stuckValidatorsCount": 0,
            "refundedValidatorsCount": 0,
            "stuckPenaltyEndTimestamp": 0,
            "totalExitedValidators": 0,
            "totalDepositedValidators": 0,
            "depositableValidatorsCount": 0,
        },
    )
    assert_node_operator_added_event(tx, new_node_operator_id, new_node_operator_name, reward_address, staking_limit=0)

    # assert added_node_operator["active"] == True
    # assert added_node_operator["name"] == new_node_operator_name
    # assert added_node_operator["rewardAddress"] == reward_address
    # assert added_node_operator["usedSigningKeys"] == 0
    # assert added_node_operator["stoppedValidators"] == 0
    # assert added_node_operator["totalSigningKeys"] == 0
    # assert added_node_operator["stakingLimit"] == 0

    # assert "NodeOperatorAdded" in tx.events
    # assert tx.events["NodeOperatorAdded"]["nodeOperatorId"] == new_node_operator_id
    # assert tx.events["NodeOperatorAdded"]["name"] == new_node_operator_name
    # assert tx.events["NodeOperatorAdded"]["rewardAddress"] == reward_address
    # assert tx.events["NodeOperatorAdded"]["stakingLimit"] == 0


def test_add_signing_keys_operator_bh(nor, reward_address, new_node_operator_id):
    node_operator_id = nor.getNodeOperatorsCount() - 1

    keys_count = 13
    pubkeys_batch = random_pubkeys_batch(keys_count)
    signatures_batch = random_signatures_batch(keys_count)

    nonce_before = nor.getNonce()
    total_signing_keys_count_before = nor.getTotalSigningKeyCount(node_operator_id)
    unused_signing_keys_count_before = nor.getUnusedSigningKeyCount(node_operator_id)

    tx = nor.addSigningKeysOperatorBH(
        node_operator_id,
        keys_count,
        pubkeys_batch,
        signatures_batch,
        {"from": reward_address},
    )

    nonce_after = nor.getNonce()
    total_signing_keys_count_after = nor.getTotalSigningKeyCount(node_operator_id)
    unused_signing_keys_count_after = nor.getUnusedSigningKeyCount(node_operator_id)

    assert nonce_after != nonce_before
    assert total_signing_keys_count_after == total_signing_keys_count_before + keys_count
    assert unused_signing_keys_count_after == unused_signing_keys_count_before + keys_count

    new_pubkeys = parse_pukeys_batch(pubkeys_batch)
    new_signatures = parse_signatures_batch(signatures_batch)

    for local_key_index in range(keys_count):
        global_key_index = total_signing_keys_count_before + local_key_index
        signing_key = nor.getSigningKey(node_operator_id, global_key_index).dict()
        assert signing_key["key"] == new_pubkeys[local_key_index]
        assert signing_key["depositSignature"] == new_signatures[local_key_index]
        assert signing_key["used"] == False

    # TODO: validate events


def test_set_node_operator_staking_limit(nor, voting_eoa):
    node_operator_id = nor.getNodeOperatorsCount() - 1

    nonce_before = nor.getNonce()
    node_operator_before = nor.getNodeOperator(node_operator_id, True)
    node_operator_summary_before = nor.getNodeOperatorSummary(node_operator_id)

    new_staking_limit = nor.getTotalSigningKeyCount(node_operator_id)
    assert new_staking_limit != node_operator_before["stakingLimit"], "invalid new staking limit"

    tx = nor.setNodeOperatorStakingLimit(node_operator_id, new_staking_limit, {"from": voting_eoa})

    nonce_after = nor.getNonce()
    node_operator_after = nor.getNodeOperator(node_operator_id, True)
    node_operator_summary_after = nor.getNodeOperatorSummary(node_operator_id)

    assert_node_operators(node_operator_before, node_operator_after, skip=["stakingLimit"])
    assert node_operator_after["stakingLimit"] == new_staking_limit

    assert_summaries(node_operator_summary_before, node_operator_summary_after, skip=["depositableValidatorsCount"])
    assert node_operator_summary_after["depositableValidatorsCount"] == new_staking_limit

    # TODO: validate events


def test_deactivate_node_operator(nor, voting_eoa):
    node_operators_count_before = nor.getNodeOperatorsCount()
    active_node_operators_count_before = nor.getActiveNodeOperatorsCount()

    node_operator_id = node_operators_count_before - 1

    node_operator_before = nor.getNodeOperator(node_operator_id, False)
    assert node_operator_before["active"] == True

    tx = nor.deactivateNodeOperator(node_operator_id, {"from": voting_eoa})

    node_operators_count_after = nor.getNodeOperatorsCount()
    active_node_operators_count_after = nor.getActiveNodeOperatorsCount()

    assert node_operators_count_after == node_operators_count_before
    assert active_node_operators_count_after == active_node_operators_count_before - 1

    node_operator_after = nor.getNodeOperator(node_operator_id, False)
    assert_node_operators(node_operator_after, node_operator_before, skip=["active", "stakingLimit"])
    assert node_operator_after["active"] == False
    # after deactivation vetted keys count trimmed to used
    assert node_operator_after["stakingLimit"] == node_operator_before["usedSigningKeys"]

    # assert "NodeOperatorActiveSet" in tx.events
    # assert tx.events["NodeOperatorActiveSet"]["nodeOperatorId"] == new_node_operator_id
    # assert tx.events["NodeOperatorActiveSet"]["active"] == False

    # assert "VettedSigningKeysCountChanged" in tx.events
    # assert tx.events["VettedSigningKeysCountChanged"]["nodeOperatorId"] == new_node_operator_id
    # assert (
    #     tx.events["VettedSigningKeysCountChanged"]["approvedValidatorsCount"]
    #     == node_operator_before["usedSigningKeys"]
    # )


def test_activate_node_operator(nor, voting_eoa):
    node_operator_id = nor.getNodeOperatorsCount() - 1

    node_operator_before = nor.getNodeOperator(node_operator_id, True)
    assert node_operator_before["active"] == False

    node_operators_count_before = nor.getNodeOperatorsCount()
    active_node_operators_count_before = nor.getActiveNodeOperatorsCount()

    tx = nor.activateNodeOperator(node_operator_id, {"from": voting_eoa})

    node_operators_count_after = nor.getNodeOperatorsCount()
    active_node_operators_count_after = nor.getActiveNodeOperatorsCount()

    assert node_operators_count_after == node_operators_count_before
    assert active_node_operators_count_after == active_node_operators_count_before + 1

    node_operator_after = nor.getNodeOperator(node_operator_id, True)
    assert_node_operators(node_operator_after, node_operator_before, skip=["active"])
    assert node_operator_after["active"] == True

    # TODO: validate events


def random_pubkeys_batch(pubkeys_count: int):
    return random_hexstr(pubkeys_count * PUBKEY_LENGTH)


def random_signatures_batch(signautes_count: int):
    return random_hexstr(signautes_count * SIGNATURE_LENGTH)


def parse_pukeys_batch(pubkeys_batch: str):
    return hex_chunks(pubkeys_batch, PUBKEY_LENGTH)


def parse_signatures_batch(signatures_batch: str):
    return hex_chunks(signatures_batch, SIGNATURE_LENGTH)


def hex_chunks(hexstr: str, chunk_length: int):
    stripped_hexstr = strip_0x(hexstr)
    assert len(stripped_hexstr) % chunk_length == 0, "invalid hexstr length"
    return [prefix_0x(chunk) for chunk in textwrap.wrap(stripped_hexstr, 2 * chunk_length)]


def random_hexstr(length: int):
    return prefix_0x(random.randbytes(length).hex())


def prefix_0x(hexstr: str):
    return hexstr if hexstr.startswith("0x") else "0x" + hexstr


def strip_0x(hexstr: str):
    return hexstr[2:] if hexstr.startswith("0x") else hexstr
