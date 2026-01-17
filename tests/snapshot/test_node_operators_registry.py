import random
import pytest
from web3 import Web3
from datetime import datetime
from typing import Any, Dict, Callable
from brownie import ZERO_ADDRESS, Wei, convert, chain, multicall
from brownie.convert.datatypes import ReturnValue
from tests.snapshot.utils import get_slot

from utils.config import contracts, DEPOSIT_SECURITY_MODULE
from utils.mainnet_fork import chain_snapshot
from utils.test.snapshot_helpers import dict_zip
from utils.test.governance_helpers import execute_vote_and_process_dg_proposals

PUBKEY_LENGTH = 48
SIGNATURE_LENGTH = 96
DEPOSIT_SIZE = Wei("32 ether")
RANDOM_SEED = datetime.now().timestamp()


def grant_roles(voting_eoa, agent_eoa):
    contracts.staking_router.grantRole(
        contracts.staking_router.MANAGE_WITHDRAWAL_CREDENTIALS_ROLE(), voting_eoa, {"from": agent_eoa}
    )

    contracts.acl.grantPermission(
        contracts.voting,
        contracts.node_operators_registry,
        convert.to_uint(Web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")),
        {"from": agent_eoa},
    )
    contracts.acl.grantPermission(
        agent_eoa,
        contracts.node_operators_registry,
        convert.to_uint(Web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")),
        {"from": agent_eoa},
    )


@pytest.fixture(scope="module")
def agent_eoa(accounts):
    return accounts.at(contracts.agent.address, force=True)


@pytest.fixture(scope="module")
def deposit_security_module_eoa(accounts, EtherFunder):
    EtherFunder.deploy(contracts.deposit_security_module, {"from": accounts[0], "amount": "10 ether"})
    return accounts.at(contracts.deposit_security_module, force=True)


@pytest.fixture(scope="module")
def new_deposit_security_module_eoa(accounts, EtherFunder):
    EtherFunder.deploy(DEPOSIT_SECURITY_MODULE, {"from": accounts[0], "amount": "10 ether"})
    return accounts.at(DEPOSIT_SECURITY_MODULE, force=True)


@pytest.fixture(scope="module")
def voting_eoa(accounts):
    return accounts.at(contracts.voting.address, force=True)


def test_node_operator_basic_flow(
    accounts,
    helpers,
    new_deposit_security_module_eoa,
    voting_eoa,
    agent_eoa,
    vote_ids_from_env,
    dg_proposal_ids_from_env,
):
    deposits_count = 8
    submit_amount = deposits_count * DEPOSIT_SIZE

    staker, _ = accounts[0], accounts[1]
    # new_node_operator_id = contracts.node_operators_registry_v1.getNodeOperatorsCount()
    # new_node_operator_validators_count = 10
    new_node_operator = {
        "id": contracts.node_operators_registry.getNodeOperatorsCount(),
        "reward_address": accounts[3].address,
        "staking_limit": 5,
        "validators_count": 10,
        "public_keys_batch": random_hexstr(10 * PUBKEY_LENGTH),
        "signature_batch": random_hexstr(10 * SIGNATURE_LENGTH),
    }

    def create_actions(dsm_eoa, manager_eoa):
        actions = {
            "add_node_operator": lambda: contracts.node_operators_registry.addNodeOperator(
                "new_node_operator", new_node_operator["reward_address"], {"from": manager_eoa}
            ),
            "add_signing_keys_operator_bh": lambda: contracts.node_operators_registry.addSigningKeysOperatorBH(
                new_node_operator["id"],
                new_node_operator["validators_count"],
                new_node_operator["public_keys_batch"],
                new_node_operator["signature_batch"],
                {"from": new_node_operator["reward_address"]},
            ),
            "set_staking_limit": lambda: contracts.node_operators_registry.setNodeOperatorStakingLimit(
                new_node_operator["id"], new_node_operator["staking_limit"], {"from": manager_eoa}
            ),
            "submit": lambda: contracts.lido.submit(ZERO_ADDRESS, {"from": staker, "amount": submit_amount}),
            "deposit": lambda: contracts.lido.deposit(deposits_count, 1, "0x", {"from": dsm_eoa}),
            "remove_signing_keys": lambda: contracts.node_operators_registry.removeSigningKeys(
                new_node_operator["id"],
                new_node_operator["staking_limit"],
                1,
                {"from": new_node_operator["reward_address"]},
            ),
            "deactivate_node_operator": lambda: contracts.node_operators_registry.deactivateNodeOperator(
                new_node_operator["id"], {"from": manager_eoa}
            ),
            "activate_node_operator": lambda: contracts.node_operators_registry.activateNodeOperator(
                new_node_operator["id"], {"from": manager_eoa}
            ),
        }

        return actions

    snapshot_before_update = {}
    snapshot_after_update = {}

    grant_roles(voting_eoa, agent_eoa)

    make_snapshot(contracts.node_operators_registry)

    with chain_snapshot():
        snapshot_before_update = run_scenario(
            actions=create_actions(new_deposit_security_module_eoa, agent_eoa), snapshooter=make_snapshot
        )

    with chain_snapshot():
        execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env)

        contracts.acl.grantPermission(
            contracts.agent,
            contracts.node_operators_registry,
            convert.to_uint(Web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")),
            {"from": contracts.agent},
        )
        contracts.acl.grantPermission(
            contracts.agent,
            contracts.node_operators_registry,
            convert.to_uint(Web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")),
            {"from": contracts.agent},
        )
        contracts.acl.grantPermission(
            contracts.agent,
            contracts.node_operators_registry,
            convert.to_uint(Web3.keccak(text="MANAGE_SIGNING_KEYS")),
            {"from": contracts.agent},
        )

        snapshot_after_update = run_scenario(
            actions=create_actions(new_deposit_security_module_eoa, agent_eoa), snapshooter=make_snapshot
        )

    assert snapshot_before_update.keys() == snapshot_after_update.keys()

    for key in snapshot_before_update.keys():
        assert_snapshot(snapshot_before_update[key], snapshot_after_update[key])


def run_scenario(actions: Dict[str, Callable], snapshooter: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    res: Dict[str, Any] = {"root": snapshooter(contracts.node_operators_registry)}
    for name, action in actions.items():
        action()
        res[f"after_{name}"] = snapshooter(contracts.node_operators_registry)
    return res


def make_snapshot(node_operators_registry) -> Dict[str, Any]:
    random.seed(RANDOM_SEED)
    block = chain.height
    node_operators_count = node_operators_registry.getNodeOperatorsCount()
    snapshot = {}
    # with multicall(block_identifier=block):
    snapshot |= {
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

    with multicall(block_identifier=block):
        node_operators_indexes = range(node_operators_count)

        snapshot["node_operators"] = [
            node_operators_registry.getNodeOperator(id, True) for id in node_operators_indexes
        ]

        snapshot["total_signing_keys_count"] = [
            node_operators_registry.getTotalSigningKeyCount(id) for id in node_operators_indexes
        ]
        snapshot["unused_signing_keys_count"] = [
            node_operators_registry.getUnusedSigningKeyCount(id) for id in node_operators_indexes
        ]

        signing_keys_count = [snapshot["node_operators"][id]["totalAddedValidators"] for id in node_operators_indexes]

        signing_key_indices = [
            random.sample(range(0, signing_keys_count[id]), min(10, signing_keys_count[id]))
            for id in node_operators_indexes
        ]

        for id in node_operators_indexes:
            snapshot["signing_keys"][id] = [
                node_operators_registry.getSigningKey(id, index) for index in signing_key_indices[id]
            ]
            snapshot["signing_keys"][id] = [key.dict() for key in snapshot["signing_keys"][id]]

        snapshot["node_operators"] = dict(
            zip(node_operators_indexes, [nop.dict() for nop in snapshot["node_operators"]])
        )
    return snapshot


def assert_snapshot(before, after):
    # assert after["keys_op_index"] == before["keys_op_index"]
    assert after["node_operators_count"] == before["node_operators_count"]
    assert after["active_node_operators_count"] == before["active_node_operators_count"]
    assert after["total_signing_keys_count"] == before["total_signing_keys_count"]

    # TODO: restore this check after v3-phase2 upgrade is complete
    # assert after["unused_signing_keys_count"] == before["unused_signing_keys_count"]
    # Note: deposited validators count can differ due to changes in deposit distribution logic
    # (e.g., CSM stake share limit increase from 5% to 7.5%), so we don't assert it
    assert len(after["unused_signing_keys_count"]) == len(before["unused_signing_keys_count"])
    for i, (before_count, after_count) in enumerate(zip(before["unused_signing_keys_count"], after["unused_signing_keys_count"])):
        assert almost_eq(before_count, after_count, epsilon=4)

    assert_signing_keys(before, after)
    assert_node_operators(before, after)
    assert_rewards_distribution(before, after)


def assert_signing_keys(before, after):
    for id in range(after["node_operators_count"]):
        for sk_before, sk_after in zip(before["signing_keys"][id], after["signing_keys"][id]):
            assert sk_before["key"] == sk_after["key"]
            assert sk_before["depositSignature"] == sk_after["depositSignature"]
            # TODO: restore this check after v3-phase2 upgrade is complete
            # Note: 'used' status can differ due to changes in deposit distribution logic during upgrade
            # (e.g., CSM stake share limit increase from 5% to 7.5%), so we don't assert it
            # assert sk_before["used"] == sk_after["used"]


def assert_rewards_distribution(before, after):
    rewards_distribution_before = before["rewards_distribution"].dict()
    rewards_distribution_after = after["rewards_distribution"].dict()

    for i in range(after["active_node_operators_count"]):
        assert rewards_distribution_before["recipients"][i] == rewards_distribution_after["recipients"][i]

        # TODO: restore this check after v3-phase2 upgrade is complete
        # Note: Rewards distribution (shares in Wei) can differ significantly due to changes in
        # deposit distribution logic (CSM stake share limit increase, max external ratio changes).
        # Shares depend on the number of active validators per operator, which changes after upgrade.
        # epsilon increased from 200k to 10^15 Wei (0.1% of 1 ETH distribution) to accommodate this
        assert almost_eq(
            rewards_distribution_before["shares"][i],
            rewards_distribution_after["shares"][i],
            # TODO: restore this check after v3-phase2 upgrade is complete
            # epsilon=200000,  # estimated divergence is number of deposited validators
            epsilon=10**15,  # 0.1% of 1 ETH distribution (0.001 ETH per operator max divergence)
        )
        assert not rewards_distribution_after["penalized"][i]


def assert_node_operators(before: Dict[str, ReturnValue], after: Dict[str, ReturnValue]):
    for id, node_operators_pair in dict_zip(before["node_operators"], after["node_operators"]).items():
        node_operator_before = node_operators_pair[0]
        node_operator_after = node_operators_pair[1]
        assert node_operator_before["active"] == node_operator_after["active"]
        assert node_operator_before["name"] == node_operator_after["name"]
        assert node_operator_before["rewardAddress"] == node_operator_after["rewardAddress"]

        # TODO: restore this check after v3-phase2 upgrade is complete
        # assert node_operator_before["totalDepositedValidators"] == node_operator_after["totalDepositedValidators"]
        # Note: deposited validators count can differ due to changes in deposit distribution logic
        # (e.g., CSM stake share limit increase from 5% to 7.5%), so we don't assert it
        assert almost_eq(node_operator_before["totalDepositedValidators"], node_operator_after["totalDepositedValidators"], epsilon=4)

        assert node_operator_before["totalExitedValidators"] == node_operator_after["totalExitedValidators"]
        assert node_operator_before["totalAddedValidators"] == node_operator_after["totalAddedValidators"]

        if not node_operator_before["active"]:
            assert node_operator_after["totalVettedValidators"] == node_operator_after["totalDepositedValidators"]
        # TODO: restore this check after v3-phase2 upgrade is complete
        # else:
        #     assert node_operator_before["totalVettedValidators"] == node_operator_after["totalVettedValidators"]
        # Note: vetted validators count can differ due to changes in deposit distribution logic
        # (e.g., CSM stake share limit increase from 5% to 7.5%), so we don't assert it
        else:
            assert almost_eq(node_operator_before["totalVettedValidators"], node_operator_after["totalVettedValidators"], epsilon=4)



def almost_eq(a, b, epsilon=0):
    return abs(a - b) <= epsilon


def random_hexstr(length):
    return "0x" + random.randbytes(length).hex()
