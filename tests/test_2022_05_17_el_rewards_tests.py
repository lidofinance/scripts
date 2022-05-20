"""
Tests for EL rewards distribution for voting 17/05/2022
"""
import json
import pytest
import eth_abi
from functools import partial
from brownie import interface, reverts, web3

from utils.config import contracts
from scripts.vote_2022_05_17 import (
    start_vote,
    update_lido_app,
    update_nos_app,
    update_oracle_app,
)

LIDO_EXECUTION_LAYER_REWARDS_VAULT = "0x"
TOTAL_BASIS_POINTS = 10000
EL_REWARDS_FEE_WITHDRAWAL_LIMIT = 0


@pytest.fixture(scope="module", autouse=True)
def autodeploy_contracts(accounts):
    deployer = accounts[2]
    lido_tx_data = json.load(open("./utils/txs/tx-13-1-deploy-lido-base.json"))["data"]
    nos_tx_data = json.load(
        open("./utils/txs/tx-13-1-deploy-node-operators-registry-base.json")
    )["data"]
    oracle_tx_data = json.load(open("./utils/txs/tx-13-1-deploy-oracle-base.json"))[
        "data"
    ]
    execution_layer_rewards_vault_tx_data = json.load(
        open("./utils/txs/tx-26-deploy-execution-layer-rewards-vault.json")
    )["data"]

    lido_tx = deployer.transfer(data=lido_tx_data)
    nos_tx = deployer.transfer(data=nos_tx_data)
    oracle_tx = deployer.transfer(data=oracle_tx_data)
    execution_layer_rewards_vault_tx = deployer.transfer(
        data=execution_layer_rewards_vault_tx_data
    )

    global LIDO_EXECUTION_LAYER_REWARDS_VAULT
    LIDO_EXECUTION_LAYER_REWARDS_VAULT = (
        execution_layer_rewards_vault_tx.contract_address
    )

    update_lido_app["new_address"] = lido_tx.contract_address
    update_lido_app[
        "execution_layer_rewards_vault_address"
    ] = execution_layer_rewards_vault_tx.contract_address
    update_nos_app["new_address"] = nos_tx.contract_address
    update_oracle_app["new_address"] = oracle_tx.contract_address


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def eth_whale(accounts):
    return accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)


@pytest.fixture(scope="module")
def lido_oracle():
    return contracts.lido_oracle


@pytest.fixture(scope="module")
def lido_execution_layer_rewards_vault():
    return interface.LidoExecutionLayerRewardsVault(LIDO_EXECUTION_LAYER_REWARDS_VAULT)


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )


def test_el_rewards_views_values_is_correct(
    lido, dao_agent, lido_execution_layer_rewards_vault
):
    # deployed LidoExecutionLayerRewardsVault has correct values
    assert lido_execution_layer_rewards_vault.LIDO() == lido.address
    assert lido_execution_layer_rewards_vault.TREASURY() == dao_agent.address

    # Lido contract EL rewards values were set correctly
    assert lido.getTotalELRewardsCollected() == 0
    assert lido.getELRewardsWithdrawalLimit() == EL_REWARDS_FEE_WITHDRAWAL_LIMIT
    assert lido.getELRewardsVault() == LIDO_EXECUTION_LAYER_REWARDS_VAULT


def test_set_el_rewards_vault(acl, lido, stranger, dao_voting):
    has_set_el_rewards_vault_role = partial(
        has_role, acl=acl, app=lido, role="SET_EL_REWARDS_VAULT_ROLE"
    )

    # setELRewardsVault can't be called by stranger
    assert not has_set_el_rewards_vault_role(entity=stranger)
    with reverts("APP_AUTH_FAILED"):
        lido.setELRewardsVault(stranger, {"from": stranger})

    # setELRewardsVault might be called by voting
    assert has_set_el_rewards_vault_role(entity=dao_voting)
    tx = lido.setELRewardsVault(stranger, {"from": dao_voting})
    assert len(tx.logs) == 1
    assert_el_rewards_vault_set_log(
        log=tx.logs[0], lido_execution_layer_rewards_vault=stranger.address
    )
    assert lido.getELRewardsVault() == stranger


def test_set_el_tx_withdrawal_limit(acl, lido, stranger, dao_voting):
    set_el_rewards_withdrawal_limit_role = "SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE"
    has_set_el_rewards_withdrawal_limit_role = partial(
        has_role, acl=acl, app=lido, role=set_el_rewards_withdrawal_limit_role
    )
    # setELRewardsWithdrawalLimit can't be called by the stranger
    assert not has_set_el_rewards_withdrawal_limit_role(entity=stranger)
    with reverts("APP_AUTH_FAILED"):
        lido.setELRewardsWithdrawalLimit(0, {"from": stranger})

    # ensure voting has SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE
    if not has_set_el_rewards_withdrawal_limit_role(entity=dao_voting):
        acl.createPermission(
            dao_voting,
            lido,
            web3.keccak(text=set_el_rewards_withdrawal_limit_role),
            dao_voting,
            {"from": dao_voting},
        )

    # setELRewardsWithdrawalLimit might be called by the voting
    new_el_tx_fee_withdrawal_limit = 100
    tx = lido.setELRewardsWithdrawalLimit(
        new_el_tx_fee_withdrawal_limit, {"from": dao_voting}
    )
    assert len(tx.logs) == 1
    assert_el_tx_fee_withdrawal_limit_set_log(
        log=tx.logs[0], limit_points=new_el_tx_fee_withdrawal_limit
    )
    assert lido.getELRewardsWithdrawalLimit() == new_el_tx_fee_withdrawal_limit


def test_lido_execution_layer_rewards_vault_receive_events(
    stranger, lido_execution_layer_rewards_vault
):
    reward_amount = 10**18 + 1
    tx = stranger.transfer(lido_execution_layer_rewards_vault, reward_amount)
    assert lido_execution_layer_rewards_vault.balance() == reward_amount
    assert_eth_received_log(log=tx.logs[0], value=reward_amount)


def test_receive_el_rewards_permissions(
    lido, stranger, lido_execution_layer_rewards_vault
):
    reward_amount = 10**18

    # receiveELRewards can't be called by the stranger
    assert lido.getELRewardsVault() != stranger
    with reverts():
        lido.receiveELRewards({"from": stranger, "amount": reward_amount})

    # receiveELRewards might be called by LidoExecutionLayerRewardsVault
    stranger.transfer(lido_execution_layer_rewards_vault, reward_amount)
    assert lido_execution_layer_rewards_vault.balance() == reward_amount

    lido_eth_balance_before = lido.balance()
    tx = lido.receiveELRewards(
        {"from": lido_execution_layer_rewards_vault, "amount": reward_amount}
    )
    assert len(tx.logs) == 1
    assert_el_rewards_received_log(log=tx.logs[0], amount=reward_amount)

    assert lido.getTotalELRewardsCollected() == reward_amount
    assert lido_execution_layer_rewards_vault.balance() == 0
    assert lido.balance() == lido_eth_balance_before + reward_amount


@pytest.mark.parametrize("el_reward", [0, 100 * 10**18, 1_000_000 * 10**18])
@pytest.mark.parametrize("beacon_balance_delta", [0, 1000 * 10**18, -1000 * 10**18])
def test_handle_oracle_report_with_el_rewards(
    acl,
    lido,
    lido_oracle,
    dao_voting,
    lido_execution_layer_rewards_vault,
    eth_whale,
    el_reward,
    beacon_balance_delta,
    node_operators_registry,
):
    if lido.getELRewardsWithdrawalLimit() == 0:
        el_rewards_withdrawal_limit = 2
        set_el_rewards_withdrawal_limit_role = "SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE"
        has_set_el_rewards_withdrawal_limit_role = partial(
            has_role, acl=acl, app=lido, role=set_el_rewards_withdrawal_limit_role
        )
        if not has_set_el_rewards_withdrawal_limit_role(entity=dao_voting):
            acl.createPermission(
                dao_voting,
                lido,
                web3.keccak(text=set_el_rewards_withdrawal_limit_role),
                dao_voting,
                {"from": dao_voting},
            )
        lido.setELRewardsWithdrawalLimit(
            el_rewards_withdrawal_limit, {"from": dao_voting}
        )
        assert lido.getELRewardsWithdrawalLimit() == el_rewards_withdrawal_limit

    # prepare EL rewards
    if el_reward > 0:
        eth_whale.transfer(lido_execution_layer_rewards_vault, el_reward)
    assert lido_execution_layer_rewards_vault.balance() == el_reward

    # prepare new report data
    prev_report = lido.getBeaconStat().dict()
    beacon_validators = prev_report["beaconValidators"]
    beacon_balance = prev_report["beaconBalance"] + beacon_balance_delta
    buffered_ether_before = lido.getBufferedEther()

    max_allowed_el_reward = (
        (lido.getTotalPooledEther() + beacon_balance_delta)
        * lido.getELRewardsWithdrawalLimit()
        // TOTAL_BASIS_POINTS
    )

    treasury_address = lido.getTreasury()
    treasury_fund_balance_before = lido.balanceOf(treasury_address)
    node_operators = get_node_operators(node_operators_registry=node_operators_registry)
    node_operators_balances_before = {}
    for node_operator in node_operators:
        reward_address = node_operator["rewardAddress"]
        node_operators_balances_before[reward_address] = lido.balanceOf(reward_address)

    # simulate oracle report
    tx = lido.handleOracleReport(
        beacon_validators, beacon_balance, {"from": lido_oracle}
    )

    # validate that EL rewards were added to the buffered ether
    expected_el_reward = min(max_allowed_el_reward, el_reward)
    assert lido.getBufferedEther() == buffered_ether_before + expected_el_reward

    # validate that rewards were distributed
    transfer_logs = filter_transfer_logs(logs=tx.logs)
    if beacon_balance_delta <= 0:
        assert len(transfer_logs) == 0
    else:
        assert len(transfer_logs) > 0

        # validate that the correct amount of rewards was distributed
        transfers = parse_transfer_logs(transfer_logs)
        total_rewards = sum(t["value"] for t in transfers)
        total_reward_expected = (
            lido.getFee()
            * (beacon_balance_delta + expected_el_reward)
            // TOTAL_BASIS_POINTS
        )
        # due to the stETH shares rounding distributed value might be less than the expected value
        assert total_rewards - total_reward_expected <= len(transfers)

        fee_distribution = lido.getFeeDistribution().dict()
        # validate treasury rewards
        treasury_fund_expected_reward = (
            (
                fee_distribution["insuranceFeeBasisPoints"]
                + fee_distribution["treasuryFeeBasisPoints"]
            )
            * total_reward_expected
            // TOTAL_BASIS_POINTS
        )
        assert (
            lido.balanceOf(treasury_address)
            >= treasury_fund_balance_before + treasury_fund_expected_reward
        )

        # validate node operators rewards
        active_node_operators = list(filter(lambda n: n["active"], node_operators))
        total_number_of_node_operators = sum(
            no["activeValidators"] for no in active_node_operators
        )
        for node_operator in active_node_operators:
            reward_address = node_operator["rewardAddress"]
            expected_node_operator_reward = (
                fee_distribution["operatorsFeeBasisPoints"]
                * total_reward_expected
                * node_operator["activeValidators"]
            ) // (TOTAL_BASIS_POINTS * total_number_of_node_operators)
            node_operator_balance_after = lido.balanceOf(reward_address)
            assert (
                node_operator_balance_after
                >= node_operators_balances_before[reward_address]
                + expected_node_operator_reward
            )


def has_role(acl, entity, app, role):
    encoded_role = web3.keccak(text=role)
    return acl.hasPermission["address,address,bytes32,uint[]"](
        entity, app, encoded_role, []
    )


def assert_role(acl, entity, app, role, is_granted):
    encoded_role = web3.keccak(text=role)
    assert (
        acl.hasPermission["address,address,bytes32,uint[]"](
            entity, app, encoded_role, []
        )
        == is_granted
    )


def assert_el_rewards_vault_set_log(log, lido_execution_layer_rewards_vault):
    topic = web3.keccak(text="ELRewardsVaultSet(address)")
    assert log["topics"][0] == topic

    # validate params
    assert (
        log["data"]
        == "0x"
        + eth_abi.encode_abi(["address"], [lido_execution_layer_rewards_vault]).hex()
    )


def assert_el_tx_fee_withdrawal_limit_set_log(log, limit_points):
    topic = web3.keccak(text="ELRewardsWithdrawalLimitSet(uint256)")
    assert log["topics"][0] == topic

    # validate params
    assert log["data"] == "0x" + eth_abi.encode_abi(["uint256"], [limit_points]).hex()


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
        node_operator = node_operators_registry.getNodeOperator(
            node_operator_id, False
        ).dict()
        node_operator["activeValidators"] = (
            node_operator["usedSigningKeys"] - node_operator["stoppedValidators"]
        )
        node_operators.append(node_operator)
    return node_operators
