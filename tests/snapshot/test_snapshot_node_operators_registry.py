import random
import pytest
from web3 import Web3
from datetime import datetime
from typing import Any, Dict, Callable
from brownie import ZERO_ADDRESS, Wei, convert
from brownie.convert.datatypes import ReturnValue
from tests.snapshot.utils import get_slot

from utils.config import contracts, lido_dao_deposit_security_module_address_v1
from utils.mainnet_fork import chain_snapshot
from utils.test.snapshot_helpers import dict_zip
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes

PUBKEY_LENGTH = 48
SIGNATURE_LENGTH = 96
DEPOSIT_SIZE = Wei("32 ether")
RANDOM_SEED = datetime.now().timestamp()


@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass


def grant_roles(voting_eoa, agent_eoa):
    contracts.staking_router.grantRole(
        contracts.staking_router.MANAGE_WITHDRAWAL_CREDENTIALS_ROLE(), voting_eoa, {"from": agent_eoa}
    )

    contracts.acl.createPermission(
        contracts.voting,
        contracts.node_operators_registry,
        convert.to_uint(Web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")),
        contracts.voting,
        {"from": contracts.voting},
    )


@pytest.fixture(scope="module")
def agent_eoa(accounts):
    return accounts.at(contracts.agent.address, force=True)


@pytest.fixture(scope="module")
def old_deposit_security_module_eoa(accounts, EtherFunder):
    EtherFunder.deploy(lido_dao_deposit_security_module_address_v1, {"from": accounts[0], "amount": "10 ether"})
    return accounts.at(lido_dao_deposit_security_module_address_v1, force=True)


@pytest.fixture(scope="module")
def new_deposit_security_module_eoa(accounts, EtherFunder):
    EtherFunder.deploy(contracts.deposit_security_module, {"from": accounts[0], "amount": "10 ether"})
    return accounts.at(contracts.deposit_security_module, force=True)


@pytest.fixture(scope="module")
def voting_eoa(accounts):
    return accounts.at(contracts.voting.address, force=True)


@pytest.mark.skipif(condition=not is_there_any_vote_scripts(), reason="No votes")
def test_node_operator_basic_flow(
    accounts, helpers, old_deposit_security_module_eoa, new_deposit_security_module_eoa, voting_eoa, agent_eoa
):
    deposits_count = 8
    submit_amount = deposits_count * DEPOSIT_SIZE

    staker, _ = accounts[0], accounts[1]
    # new_node_operator_id = contracts.node_operators_registry_v1.getNodeOperatorsCount()
    # new_node_operator_validators_count = 10
    new_node_operator = {
        "id": contracts.node_operators_registry_v1.getNodeOperatorsCount(),
        "reward_address": accounts[3].address,
        "staking_limit": 5,
        "validators_count": 10,
        "public_keys_batch": random_hexstr(10 * PUBKEY_LENGTH),
        "signature_batch": random_hexstr(10 * SIGNATURE_LENGTH),
    }

    old_version_actions = {
        "add_node_operator": lambda: contracts.node_operators_registry_v1.addNodeOperator(
            "new_node_operator", new_node_operator["reward_address"], {"from": voting_eoa}
        ),
        "add_signing_keys_operator_bh": lambda: contracts.node_operators_registry_v1.addSigningKeysOperatorBH(
            new_node_operator["id"],
            new_node_operator["validators_count"],
            new_node_operator["public_keys_batch"],
            new_node_operator["signature_batch"],
            {"from": new_node_operator["reward_address"]},
        ),
        "set_staking_limit": lambda: contracts.node_operators_registry_v1.setNodeOperatorStakingLimit(
            new_node_operator["id"], new_node_operator["staking_limit"], {"from": voting_eoa}
        ),
        "submit": lambda: contracts.lido_v1.submit(ZERO_ADDRESS, {"from": staker, "amount": submit_amount}),
        "deposit": lambda: contracts.lido_v1.depositBufferedEther(
            deposits_count, {"from": old_deposit_security_module_eoa}
        ),
        "remove_signing_keys": lambda: contracts.node_operators_registry_v1.removeSigningKeys(
            new_node_operator["id"],
            new_node_operator["staking_limit"],
            1,
            {"from": voting_eoa},
        ),
        "deactivate_node_operator": lambda: contracts.node_operators_registry_v1.setNodeOperatorActive(
            new_node_operator["id"], False, {"from": voting_eoa}
        ),
        "withdrawal_credentials_change": lambda: contracts.lido_v1.setWithdrawalCredentials(
            "0xdeadbeef", {"from": voting_eoa}
        ),
        "activate_node_operator": lambda: contracts.node_operators_registry_v1.setNodeOperatorActive(
            new_node_operator["id"], True, {"from": voting_eoa}
        ),
    }
    new_version_actions = {
        "add_node_operator": lambda: contracts.node_operators_registry.addNodeOperator(
            "new_node_operator", new_node_operator["reward_address"], {"from": voting_eoa}
        ),
        "add_signing_keys_operator_bh": lambda: contracts.node_operators_registry.addSigningKeysOperatorBH(
            new_node_operator["id"],
            new_node_operator["validators_count"],
            new_node_operator["public_keys_batch"],
            new_node_operator["signature_batch"],
            {"from": new_node_operator["reward_address"]},
        ),
        "set_staking_limit": lambda: contracts.node_operators_registry.setNodeOperatorStakingLimit(
            new_node_operator["id"], new_node_operator["staking_limit"], {"from": voting_eoa}
        ),
        "submit": lambda: contracts.lido.submit(ZERO_ADDRESS, {"from": staker, "amount": submit_amount}),
        "deposit": lambda: contracts.lido.deposit(deposits_count, 1, "0x", {"from": new_deposit_security_module_eoa}),
        "remove_signing_keys": lambda: contracts.node_operators_registry.removeSigningKeys(
            new_node_operator["id"],
            new_node_operator["staking_limit"],
            1,
            {"from": voting_eoa},
        ),
        "deactivate_node_operator": lambda: contracts.node_operators_registry.deactivateNodeOperator(
            new_node_operator["id"], {"from": voting_eoa}
        ),
        "withdrawal_credentials_change": lambda: contracts.staking_router.setWithdrawalCredentials(
            "0xdeadbeef", {"from": voting_eoa}
        ),
        "activate_node_operator": lambda: contracts.node_operators_registry.activateNodeOperator(
            new_node_operator["id"], {"from": voting_eoa}
        ),
    }
    snapshot_before_update = {}
    snapshot_after_update = {}

    with chain_snapshot():
        snapshot_before_update = run_scenario(actions=old_version_actions, snapshooter=make_snapshot_v1)

    with chain_snapshot():
        start_and_execute_votes(contracts.voting, helpers)
        grant_roles(voting_eoa, agent_eoa)
        snapshot_after_update = run_scenario(actions=new_version_actions, snapshooter=make_snapshot_v2)

    assert snapshot_before_update.keys() == snapshot_after_update.keys()

    # update key_op_index for all snapshots after the "withdrawal_credentials_change" step cause the
    # old NOR implementation didn't increase the key op index on withdrawal credentials update
    snapshot_before_update["after_withdrawal_credentials_change"]["keys_op_index"] += 1
    snapshot_before_update["after_activate_node_operator"]["keys_op_index"] += 1

    for key in snapshot_before_update.keys():
        assert_snapshot(snapshot_before_update[key], snapshot_after_update[key])


def run_scenario(actions: Dict[str, Callable], snapshooter: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    res: Dict[str, Any] = {"root": snapshooter()}
    for name, action in actions.items():
        action()
        res[f"after_{name}"] = snapshooter()
    return res


def make_snapshot_v1() -> Dict[str, Any]:
    return make_snapshot(contracts.node_operators_registry_v1)


def make_snapshot_v2() -> Dict[str, Any]:
    return make_snapshot(contracts.node_operators_registry)


def make_snapshot(node_operators_registry) -> Dict[str, Any]:
    random.seed(RANDOM_SEED)
    node_operators_count = node_operators_registry.getNodeOperatorsCount()
    snapshot = {
        "keys_op_index": node_operators_registry.getKeysOpIndex(),
        "signing_keys": {},
        "node_operators": {},
        "node_operators_count": node_operators_count,
        "rewards_distribution": node_operators_registry.getRewardsDistribution(Wei("1 ether")),
        "total_signing_keys_count": {},
        "unused_signing_keys_count": {},
        "active_node_operators_count": node_operators_registry.getActiveNodeOperatorsCount(),
    }

    for v1_slot in (
        # NodeOperatorsRegistry.sol
        "lido.NodeOperatorsRegistry.activeOperatorsCount",
        "lido.NodeOperatorsRegistry.keysOpIndex",
        "lido.NodeOperatorsRegistry.lido",
        "lido.NodeOperatorsRegistry.totalOperatorsCount",
        # AragonApp.sol
        "aragonOS.appStorage.kernel",
        "aragonOS.appStorage.appId",
    ):
        snapshot[v1_slot] = get_slot(node_operators_registry.address, name=v1_slot)

    for id in range(node_operators_count):
        snapshot["node_operators"][id] = node_operators_registry.getNodeOperator(id, True).dict()
        snapshot["total_signing_keys_count"][id] = node_operators_registry.getTotalSigningKeyCount(id)
        snapshot["unused_signing_keys_count"][id] = node_operators_registry.getUnusedSigningKeyCount(id)

        signing_keys_count = (
            snapshot["node_operators"][id]["totalSigningKeys"]
            if "totalSigningKeys" in snapshot["node_operators"][id]
            else snapshot["node_operators"][id]["totalAddedValidators"]
        )

        snapshot["signing_keys"][id] = []
        if signing_keys_count == 0:
            continue

        signing_key_indices = random.sample(range(0, signing_keys_count), min(10, signing_keys_count))

        for index in signing_key_indices:
            snapshot["signing_keys"][id].append(node_operators_registry.getSigningKey(id, index).dict())

    return snapshot


def assert_snapshot(before, after):
    assert (
        after["keys_op_index"] == before["keys_op_index"] + 1
    ), f"{after['keys_op_index']} != {before['keys_op_index'] + 1}"
    assert after["node_operators_count"] == before["node_operators_count"]
    assert after["active_node_operators_count"] == before["active_node_operators_count"]
    assert after["total_signing_keys_count"] == before["total_signing_keys_count"]
    assert after["unused_signing_keys_count"] == before["unused_signing_keys_count"]

    assert_signing_keys(before, after)
    assert_node_operators(before, after)
    assert_rewards_distribution(before, after)


def assert_signing_keys(before, after):
    for id in range(after["node_operators_count"]):
        for sk_before, sk_after in zip(before["signing_keys"][id], after["signing_keys"][id]):
            assert sk_before["key"] == sk_after["key"]
            assert sk_before["depositSignature"] == sk_after["depositSignature"]
            assert sk_before["used"] == sk_after["used"]


def assert_rewards_distribution(before, after):
    rewards_distribution_before = before["rewards_distribution"].dict()
    rewards_distribution_after = after["rewards_distribution"].dict()

    for i in range(after["active_node_operators_count"]):
        assert rewards_distribution_before["recipients"][i] == rewards_distribution_after["recipients"][i]
        assert almost_eq(
            rewards_distribution_before["shares"][i],
            rewards_distribution_after["shares"][i],
            epsilon=200000,  # estimated divergence is number of deposited validators
        )
        assert not rewards_distribution_after["penalized"][i]


def assert_node_operators(before: Dict[str, ReturnValue], after: Dict[str, ReturnValue]):
    for id, node_operators_pair in dict_zip(before["node_operators"], after["node_operators"]).items():
        node_operator_before = node_operators_pair[0]
        node_operator_after = node_operators_pair[1]
        assert node_operator_before["active"] == node_operator_after["active"]
        assert node_operator_before["name"] == node_operator_after["name"]
        assert node_operator_before["rewardAddress"] == node_operator_after["rewardAddress"]
        assert node_operator_before["usedSigningKeys"] == node_operator_after["totalDepositedValidators"]
        assert node_operator_before["stoppedValidators"] == node_operator_after["totalExitedValidators"]
        assert node_operator_before["totalSigningKeys"] == node_operator_after["totalAddedValidators"]
        if not node_operator_before["active"]:
            assert node_operator_after["totalVettedValidators"] == node_operator_after["totalDepositedValidators"]
        elif node_operator_before["stakingLimit"] > node_operator_before["totalSigningKeys"]:
            assert node_operator_after["totalVettedValidators"] == node_operator_after["totalAddedValidators"]
        else:
            assert node_operator_before["stakingLimit"] == node_operator_after["totalVettedValidators"]


def almost_eq(a, b, epsilon=0):
    return abs(a - b) <= epsilon


def random_hexstr(length):
    return "0x" + random.randbytes(length).hex()
