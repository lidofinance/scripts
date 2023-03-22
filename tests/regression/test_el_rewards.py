"""
Tests for EL rewards distribution for voting 24/05/2022
"""
import pytest
import eth_abi
from functools import partial
from brownie import interface, reverts, web3
from brownie.network import chain

from utils.config import contracts


TOTAL_BASIS_POINTS = 10000
EL_REWARDS_FEE_WITHDRAWAL_LIMIT = 2


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


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


# @pytest.mark.parametrize("el_reward", [0, 10**18])
# @pytest.mark.parametrize("beacon_balance_delta", [0, 10**18, 10**18])
# def test_handle_oracle_report_with_el_rewards(
#     eth_whale,
#     el_reward,
#     beacon_balance_delta,
# ):
#     el_balance_before = contracts.execution_layer_rewards_vault.balance()
#     # prepare EL rewards
#     if el_reward > 0:
#         assert eth_whale.balance() >= el_reward
#         eth_whale.transfer(contracts.execution_layer_rewards_vault, el_reward)
#     el_balance_after = contracts.execution_layer_rewards_vault.balance()
#     assert (el_balance_after - el_balance_before) == el_reward

#     # prepare node operators data
#     node_operators = get_node_operators(node_operators_registry=contracts.node_operators_registry)
#     node_operators_balances_before = {}
#     for node_operator in node_operators:
#         reward_address = node_operator["rewardAddress"]
#         balance = contracts.lido.balanceOf(reward_address)

#         # top up the node operator balance if it's too low to avoid reverts caused by the shares rounding
#         if balance <= 10**9:
#             eth_whale.transfer(contracts.lido, 2 * 10**9)
#             contracts.lido.transfer(reward_address, 10**9, {"from": eth_whale})
#             balance = contracts.lido.balanceOf(reward_address)
#         node_operators_balances_before[reward_address] = balance

#     # prepare new report data
#     prev_report = contracts.lido.getBeaconStat().dict()
#     beacon_validators = prev_report["beaconValidators"]
#     beacon_balance = prev_report["beaconBalance"] + beacon_balance_delta
#     buffered_ether_before = contracts.lido.getBufferedEther()

#     print(contracts.oracle_report_sanity_checker.getMaxPositiveTokenRebase())
#     # max_allowed_el_reward = (
#     #     (contracts.lido.getTotalPooledEther() + beacon_balance_delta)
#     #     * contracts.lido_locator.elRewardsVault()
#     #     // TOTAL_BASIS_POINTS
#     # )

#     treasury_address = contracts.lido.getTreasury()
#     treasury_fund_balance_before = contracts.lido.balanceOf(treasury_address)

#     print(contracts.lido.getBufferedEther())
#     # simulate oracle report
#     tx = contracts.lido.handleOracleReport(
#         chain.time(),
#         0,
#         beacon_validators,
#         beacon_balance,
#         0,
#         el_reward,
#         0,
#         [],
#         0,
#         {"from": contracts.accounting_oracle},
#     )

#     # validate that EL rewards were added to the buffered ether
#     # expected_el_reward = min(max_allowed_el_reward, el_balance_after)
#     expected_el_reward = el_balance_after

#     print(expected_el_reward)
#     print(contracts.lido.getBufferedEther() - buffered_ether_before)
#     assert contracts.lido.getBufferedEther() == buffered_ether_before + expected_el_reward

#     # validate that rewards were distributed
#     transfer_logs = filter_transfer_logs(logs=tx.logs)
#     if beacon_balance_delta <= 0:
#         assert len(transfer_logs) == 0
#     else:
#         assert len(transfer_logs) > 0

#         # validate that the correct amount of rewards was distributed
#         transfers = parse_transfer_logs(transfer_logs)
#         total_rewards = sum(t["value"] for t in transfers)
#         total_reward_expected = (
#             contracts.lido.getFee() * (beacon_balance_delta + expected_el_reward) // TOTAL_BASIS_POINTS
#         )
#         # due to the stETH shares rounding distributed value might be less than the expected value
#         assert abs(total_rewards - total_reward_expected) <= len(transfers)

#         fee_distribution = contracts.lido.getFeeDistribution().dict()
#         # validate treasury rewards
#         treasury_fund_expected_reward = (
#             (fee_distribution["insuranceFeeBasisPoints"] + fee_distribution["treasuryFeeBasisPoints"])
#             * total_rewards
#             // TOTAL_BASIS_POINTS
#         )
#         assert (
#             contracts.lido.balanceOf(treasury_address) >= treasury_fund_balance_before + treasury_fund_expected_reward
#         )

#         # validate node operators rewards
#         active_node_operators = list(filter(lambda n: n["active"], node_operators))
#         total_number_of_node_operators = sum(no["activeValidators"] for no in active_node_operators)
#         total_node_operators_reward = fee_distribution["operatorsFeeBasisPoints"] * total_rewards // TOTAL_BASIS_POINTS
#         for node_operator in active_node_operators:
#             # if node_operator["id"] == 11:
#             #     continue
#             reward_address = node_operator["rewardAddress"]

#             expected_node_operator_reward = (node_operator["activeValidators"] - node_operator["stoppedValidators"]) * (
#                 total_node_operators_reward // total_number_of_node_operators
#             )

#             node_operator_balance_after = contracts.ido.balanceOf(reward_address)

#             assert (
#                 node_operator_balance_after
#                 >= node_operators_balances_before[reward_address] + expected_node_operator_reward
#             )


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
