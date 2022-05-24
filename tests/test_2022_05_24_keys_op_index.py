"""
Tests for node operator registry key index counter for voting 24/05/2022
"""
import pytest
import eth_abi

from brownie import web3
from scripts.vote_2022_05_24 import start_vote


@pytest.fixture(scope="module")
def voting(accounts, dao_voting):
    return accounts.at(dao_voting.address, force=True)


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )


def test_keys_op_index_increases(lido, node_operators_registry, voting):
    # keys_op_index is increased after assignNextSigningKeys()
    node_operators_registry.addNodeOperator(
        "foo", "0x0000000000000000000000000000000000000001", {"from": voting}
    )
    node_operators_registry.addSigningKeys(
        0,
        1,
        "0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000aa0101",
        "0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a1",
        {"from": voting},
    )
    keys_op_index_before = node_operators_registry.getKeysOpIndex()
    tx = node_operators_registry.assignNextSigningKeys(1, {"from": lido})
    keys_op_index_after = node_operators_registry.getKeysOpIndex()

    assert len(tx.logs) == 1
    assert keys_op_index_before + 1 == keys_op_index_after
    assert_keys_op_index_set_log(log=tx.logs[0], value=keys_op_index_after)


def assert_keys_op_index_set_log(log, value):
    topic = web3.keccak(text="KeysOpIndexSet(uint256)")

    assert log["topics"][0] == topic
    assert log["data"] == "0x" + eth_abi.encode_single("uint256", value).hex()
