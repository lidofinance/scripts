"""
The acceptance tests for the “LIP-10: Proxy initializations and LidoOracle upgrade”
"""
import pytest
import json
import eth_abi

from brownie import ZERO_ADDRESS, reverts, web3
from scripts.vote_2022_05_17 import start_vote, update_lido_app, update_nos_app, update_oracle_app


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def another_stranger(accounts):
    return accounts[1]


@pytest.fixture(scope="module")
def deployer(accounts):
    return accounts[2]


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

    update_lido_app["new_address"] = lido_tx.contract_address
    update_lido_app[
        "execution_layer_rewards_vault_address"
    ] = execution_layer_rewards_vault_tx.contract_address
    update_nos_app["new_address"] = nos_tx.contract_address
    update_oracle_app["new_address"] = oracle_tx.contract_address


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )


def test_transfer_shares(lido, stranger, another_stranger):
    stranger.transfer(lido, 10 * 10**18)

    shares_to_transfer = 10**18
    stranger_shares_before = lido.sharesOf(stranger)
    another_stranger_shares_before = lido.sharesOf(another_stranger)

    tx = lido.transferShares(another_stranger, shares_to_transfer, {"from": stranger})

    assert lido.sharesOf(stranger) == stranger_shares_before - shares_to_transfer
    assert lido.sharesOf(another_stranger) == another_stranger_shares_before + shares_to_transfer

    assert_transfer(
        tx.logs[1], 
        stranger.address, 
        another_stranger.address, 
        lido.getPooledEthByShares(shares_to_transfer)
    ) 
    assert_transfer_shares(
        tx.logs[0], 
        stranger.address, 
        another_stranger.address, 
        shares_to_transfer
    ) 


def test_transfer(lido, stranger, another_stranger):
    stranger.transfer(lido, 10*10**18)

    amount_to_transfer = 10**18
    stranger_balance_before = lido.balanceOf(stranger)
    another_stranger_balance_before = lido.balanceOf(another_stranger)

    tx = lido.transfer(another_stranger, amount_to_transfer, {"from": stranger})

    assert lido.balanceOf(stranger) == stranger_balance_before - amount_to_transfer + 1
    assert lido.balanceOf(another_stranger) == another_stranger_balance_before + amount_to_transfer - 1

    assert_transfer(
        tx.logs[0], 
        stranger.address, 
        another_stranger.address, 
        amount_to_transfer
    ) 
    assert_transfer_shares(
        tx.logs[1], 
        stranger.address, 
        another_stranger.address, 
        lido.getSharesByPooledEth(amount_to_transfer)
    ) 


def test_transfer_from(lido, stranger, another_stranger):
    stranger.transfer(lido, 10*10**18)

    amount_to_transfer = 10**18
    stranger_balance_before = lido.balanceOf(stranger)
    another_stranger_balance_before = lido.balanceOf(another_stranger)

    lido.approve(another_stranger, amount_to_transfer, {"from": stranger})
    tx = lido.transferFrom(stranger, another_stranger, amount_to_transfer, {"from": another_stranger})

    assert lido.balanceOf(stranger) == stranger_balance_before - amount_to_transfer + 1
    assert lido.balanceOf(another_stranger) == another_stranger_balance_before + amount_to_transfer - 1

    assert_transfer(
        tx.logs[0], 
        stranger.address, 
        another_stranger.address, 
        amount_to_transfer
    ) 
    assert_transfer_shares(
        tx.logs[1], 
        stranger.address, 
        another_stranger.address, 
        lido.getSharesByPooledEth(amount_to_transfer)
    ) 


def test_deposit(lido, stranger):
    amount_to_transfer = 10**18
    stranger_balance_before = lido.balanceOf(stranger)

    tx = stranger.transfer(lido, amount_to_transfer)

    assert lido.balanceOf(stranger) == stranger_balance_before + amount_to_transfer - 1

    assert_transfer(
        tx.logs[1], 
        ZERO_ADDRESS,
        stranger.address,
        amount_to_transfer - 1 
    ) 
    assert_transfer_shares(
        tx.logs[2], 
        ZERO_ADDRESS,
        stranger.address,
        lido.getSharesByPooledEth(amount_to_transfer)
    ) 


def test_submit(lido, stranger):
    amount_to_transfer = 10**18
    stranger_balance_before = lido.balanceOf(stranger)

    tx = lido.submit(ZERO_ADDRESS, {"from": stranger, "value": amount_to_transfer})

    assert lido.balanceOf(stranger) == stranger_balance_before + amount_to_transfer - 1

    assert_transfer(
        tx.logs[1], 
        ZERO_ADDRESS,
        stranger.address,
        amount_to_transfer - 1 
    ) 
    assert_transfer_shares(
        tx.logs[2], 
        ZERO_ADDRESS,
        stranger.address,
        lido.getSharesByPooledEth(amount_to_transfer)
    )


def test_push_beacon(node_operators_registry, lido, oracle):
    current_ops_count = node_operators_registry.getActiveNodeOperatorsCount()
    total_steth = lido.getTotalPooledEther()
    shares_per_validator = 10**18
    beacon_stats = lido.getBeaconStat()

    report_amount = total_steth + lido.getSharesByPooledEth(beacon_stats[0] * shares_per_validator * 2 * 10)

    tx = lido.handleOracleReport(beacon_stats[0], report_amount, {"from": oracle})
    rewards_per_validator = int(tx.logs[1]["data"], 16)//beacon_stats[0] // 2
    print(rewards_per_validator)
    insurance_address = lido.getInsuranceFund()
    
    assert_transfer(
        tx.logs[0], 
        ZERO_ADDRESS,
        insurance_address,
        shares_per_validator
    ) 
    assert_transfer_shares(
        tx.logs[1], 
        ZERO_ADDRESS,
        insurance_address,
        shares_per_validator // 20
    )

    print(hex(report_amount // 20))
    for no_index in range(current_ops_count):
        no = node_operators_registry.getNodeOperator(no_index, True)
        assert_transfer(
            tx.logs[2+no_index*2], 
            ZERO_ADDRESS,
            no[2],
            lido.getPooledEthByShares(rewards_per_validator * beacon_stats[0])
        ) 
        assert_transfer_shares(
            tx.logs[2+no_index*2 + 1], 
            ZERO_ADDRESS,
            no[2],
            rewards_per_validator * beacon_stats[0]
        )


def test_oracle_init_reverts(oracle, stranger):
    with reverts('WRONG_BASE_VERSION'):
        oracle.finalizeUpgrade_v3({"from": stranger})


def test_oracle_version(oracle):
    assert oracle.getVersion() == 3


def assert_transfer_shares(log, sender, recipient, amount):
    assert log["topics"][0] == web3.keccak(text="TransferShares(address,address,uint256)")
    assert log["topics"][1] == eth_abi.encode_abi(["address"], [sender])
    assert log["topics"][2] == eth_abi.encode_abi(["address"], [recipient])
    # assert log["data"] == "0x"+eth_abi.encode_abi(["uint256"], [amount]).hex()


def assert_transfer(log, sender, recipient, amount):
    assert log["topics"][0] == web3.keccak(text="Transfer(address,address,uint256)")
    assert log["topics"][1] == eth_abi.encode_abi(["address"], [sender])
    assert log["topics"][2] == eth_abi.encode_abi(["address"], [recipient])
    # assert log["data"] == "0x"+eth_abi.encode_abi(["uint256"], [amount]).hex()

