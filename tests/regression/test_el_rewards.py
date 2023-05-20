"""
Tests for EL rewards distribution for voting 24/05/2022
"""
import pytest
import eth_abi
from brownie import interface, reverts, web3
from brownie.network import chain

from utils.config import contracts


TOTAL_BASIS_POINTS = 10000
EL_REWARDS_FEE_WITHDRAWAL_LIMIT = 2


def test_el_rewards_views_values_is_correct():
    # deployed LidoExecutionLayerRewardsVault has correct values
    assert contracts.execution_layer_rewards_vault.LIDO() == contracts.lido.address
    assert contracts.execution_layer_rewards_vault.TREASURY() == contracts.agent.address

    # Lido contract EL rewards values were set correctly
    assert contracts.lido.getTotalELRewardsCollected() > 0
    assert contracts.lido_locator.elRewardsVault() == contracts.execution_layer_rewards_vault


def test_lido_execution_layer_rewards_vault_receive_events(stranger):
    reward_amount = 10**18 + 1
    el_balance_before = contracts.execution_layer_rewards_vault.balance()
    tx = stranger.transfer(contracts.execution_layer_rewards_vault, reward_amount)
    el_balance_after = contracts.execution_layer_rewards_vault.balance()
    assert (el_balance_after - el_balance_before) == reward_amount
    assert_eth_received_log(log=tx.logs[0], value=reward_amount)


def test_receive_el_rewards_permissions(stranger):
    reward_amount = 10**18

    # receiveELRewards can't be called by the stranger
    assert contracts.lido_locator.elRewardsVault() != stranger
    with reverts():
        contracts.lido.receiveELRewards({"from": stranger, "value": reward_amount})

    # receiveELRewards might be called by LidoExecutionLayerRewardsVault
    el_balance_before = contracts.execution_layer_rewards_vault.balance()
    stranger.transfer(contracts.execution_layer_rewards_vault, reward_amount)
    el_balance_after = contracts.execution_layer_rewards_vault.balance()
    assert (el_balance_after - el_balance_before) == reward_amount

    lido_eth_balance_before = contracts.lido.balance()
    lido_el_rewards_collected_before = contracts.lido.getTotalELRewardsCollected()
    tx = contracts.lido.receiveELRewards({"from": contracts.execution_layer_rewards_vault, "value": reward_amount})
    assert len(tx.logs) == 1
    assert_el_rewards_received_log(log=tx.logs[0], amount=reward_amount)

    assert contracts.lido.getTotalELRewardsCollected() - lido_el_rewards_collected_before == reward_amount
    assert contracts.execution_layer_rewards_vault.balance() == (el_balance_after - reward_amount)
    assert contracts.lido.balance() == lido_eth_balance_before + reward_amount


def has_role(entity, app, role):
    encoded_role = web3.keccak(text=role)
    return contracts.acl.hasPermission["address,address,bytes32,uint[]"](entity, app, encoded_role, [])


def assert_el_rewards_received_log(log, amount):
    topic = web3.keccak(text="ELRewardsReceived(uint256)")
    assert log["topics"][0] == topic

    # validate params
    assert log["data"] == "0x" + eth_abi.encode_abi(["uint256"], [amount]).hex()


def assert_eth_received_log(log, value):
    topic = web3.keccak(text="ETHReceived(uint256)")
    assert log["topics"][0] == topic
    assert log["data"] == "0x" + eth_abi.encode_single("uint256", value).hex()


def filter_transfer_logs(logs):
    transfer_topic = web3.keccak(text="Transfer(address,address,uint256)")
    return list(filter(lambda l: l["topics"][0] == transfer_topic, logs))


def parse_transfer_logs(transfer_logs):
    res = []
    for l in transfer_logs:
        res.append(
            {
                "from": eth_abi.decode_abi(["address"], l["topics"][1])[0],
                "to": eth_abi.decode_abi(["address"], l["topics"][2])[0],
                "value": eth_abi.decode_single("uint256", bytes.fromhex(l["data"][2:])),
            }
        )
    return res


def get_node_operators(node_operators_registry):
    node_operators_count = node_operators_registry.getNodeOperatorsCount()
    node_operators = []
    for node_operator_id in range(0, node_operators_count):
        node_operator = node_operators_registry.getNodeOperator(node_operator_id, False).dict()
        node_operator["id"] = node_operator_id
        node_operator["activeValidators"] = node_operator["usedSigningKeys"] - node_operator["stoppedValidators"]
        node_operators.append(node_operator)
    return node_operators
