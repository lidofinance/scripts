"""
Tests for EL rewards distribution for voting 17/05/2022
"""
import json
import pytest
import eth_abi
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
EL_REWARDS_FEE_WITHDRAWAL_LIMIT = 2  # 2 %


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
def dao_voting_as_eoa(accounts, dao_voting):
    return accounts.at(dao_voting.address, force=True)


@pytest.fixture(scope="module")
def lido_execution_layer_rewards_vault_as_eoa(accounts):
    return accounts.at(LIDO_EXECUTION_LAYER_REWARDS_VAULT, force=True)


@pytest.fixture(scope="module")
def lido_oracle():
    return contracts.lido_oracle


@pytest.fixture(scope="module")
def lido_execution_layer_rewards_vault():
    return interface.LidoExecutionLayerRewardsVault(LIDO_EXECUTION_LAYER_REWARDS_VAULT)


@pytest.fixture(scope="module")
def lido_oracle_as_eoa(accounts, stranger, lido_oracle, EtherFunder):
    EtherFunder.deploy(lido_oracle, {"from": stranger, "amount": 10**18})
    return accounts.at(lido_oracle, force=True)


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
    print("TS:", lido.totalSupply())
    # deployed LidoExecutionLayerRewardsVault has correct values
    assert lido_execution_layer_rewards_vault.LIDO() == lido.address
    assert lido_execution_layer_rewards_vault.TREASURY() == dao_agent.address

    # Lido contract EL rewards values were set correctly
    assert lido.getTotalELRewardsCollected() == 0
    assert lido.getELRewardsWithdrawalLimit() == EL_REWARDS_FEE_WITHDRAWAL_LIMIT
    assert lido.getELRewardsVault() == LIDO_EXECUTION_LAYER_REWARDS_VAULT


def test_set_el_rewards_vault(lido, stranger, dao_voting_as_eoa):
    # setELRewardsVault can't be called by stranger
    with reverts("APP_AUTH_FAILED"):
        lido.setELRewardsVault(stranger, {"from": stranger})

    # setELRewardsVault might be called by voting
    tx = lido.setELRewardsVault(stranger, {"from": dao_voting_as_eoa})
    assert len(tx.logs) == 1
    assert_el_rewards_vault_set_log(
        log=tx.logs[0], lido_execution_layer_rewards_vault=stranger.address
    )
    assert lido.getELRewardsVault() == stranger


def test_set_el_tx_withdrawal_limit(lido, stranger, dao_voting_as_eoa):
    # setELRewardsWithdrawalLimit can't be called by the stranger
    with reverts("APP_AUTH_FAILED"):
        lido.setELRewardsWithdrawalLimit(0, {"from": stranger})

    # setELRewardsWithdrawalLimit might be called by the voting
    new_el_tx_fee_withdrawal_limit = 100
    tx = lido.setELRewardsWithdrawalLimit(
        new_el_tx_fee_withdrawal_limit, {"from": dao_voting_as_eoa}
    )
    assert len(tx.logs) == 1
    assert_el_tx_fee_withdrawal_limit_set_log(
        log=tx.logs[0], limit_points=new_el_tx_fee_withdrawal_limit
    )
    assert lido.getELRewardsWithdrawalLimit() == new_el_tx_fee_withdrawal_limit


def test_receive_el_rewards_permissions(
    lido, stranger, lido_execution_layer_rewards_vault_as_eoa
):
    reward_amount = 10**18
    with reverts():
        lido.receiveELRewards({"from": stranger, "amount": reward_amount})

    stranger.transfer(lido_execution_layer_rewards_vault_as_eoa, reward_amount)
    tx = lido.receiveELRewards(
        {"from": lido_execution_layer_rewards_vault_as_eoa, "amount": reward_amount}
    )
    assert len(tx.logs) == 1
    assert_el_rewards_received_log(log=tx.logs[0], amount=reward_amount)
    assert lido.getTotalELRewardsCollected() == reward_amount


@pytest.mark.parametrize("el_reward", [0, 100 * 10**18, 1_000_000 * 10**18])
@pytest.mark.parametrize("beacon_balance_delta", [0, 1000 * 10**18, -1000 * 10**18])
def test_handle_oracle_report_with_el_rewards(
    lido,
    lido_oracle,
    lido_oracle_as_eoa,
    lido_execution_layer_rewards_vault,
    eth_whale,
    el_reward,
    beacon_balance_delta,
):
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

    # simulate oracle report
    tx = lido.handleOracleReport(
        beacon_validators, beacon_balance, {"from": lido_oracle_as_eoa}
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
        fee = lido.getFee()
        total_transferred = sum(t["value"] for t in transfers)
        # due to the stETH shares rounding distributed value might be less than the expected value
        assert total_transferred - fee * (
            beacon_balance_delta + expected_el_reward
        ) // TOTAL_BASIS_POINTS <= len(transfers)


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


def filter_transfer_logs(logs):
    transfer_topic = web3.keccak(text="Transfer(address,address,uint256)")
    return list(filter(lambda l: l["topics"][0] == transfer_topic, logs))


def parse_transfer_logs(transfer_logs):
    res = []
    for l in transfer_logs:
        res.append(
            {
                "from": eth_abi.decode_abi(["address"], l["topics"][1]),
                "to": eth_abi.decode_abi(["address"], l["topics"][2]),
                "value": eth_abi.decode_single("uint256", bytes.fromhex(l["data"][2:])),
            }
        )
    return res
