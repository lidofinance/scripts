"""
The acceptance tests for the “LIP-10: Proxy initializations and LidoOracle upgrade”
"""
import pytest
import json

from brownie import reverts
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
def autodeploy_contracts(deployer):
    lido_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-lido-base.json'))["data"]
    nos_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-node-operators-registry-base.json'))["data"]
    oracle_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-oracle-base.json'))["data"]
    mev_vault_tx_data = json.load(open('./utils/txs/tx-26-deploy-mev-vault.json'))["data"]

    lido_tx = deployer.transfer(data=lido_tx_data)
    nos_tx = deployer.transfer(data=nos_tx_data)
    oracle_tx = deployer.transfer(data=oracle_tx_data)
    mev_vault_tx = deployer.transfer(data=mev_vault_tx_data)

    update_lido_app['new_address'] = lido_tx.contract_address
    update_lido_app['mevtxfee_vault_address'] = mev_vault_tx.contract_address
    update_nos_app['new_address'] = nos_tx.contract_address
    update_oracle_app['new_address'] = oracle_tx.contract_address


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )


def test_transfer_shares(helpers, lido, stranger, another_stranger):
    stranger.transfer(lido, 10 * 10**18)

    shares_to_transfer = 10**18
    stranger_shares_before = lido.sharesOf(stranger)
    another_stranger_shares_before = lido.sharesOf(another_stranger)

    tx = lido.transferShares(another_stranger, shares_to_transfer, {"from": stranger})

    assert lido.sharesOf(stranger) == stranger_shares_before - shares_to_transfer
    assert lido.sharesOf(another_stranger) == another_stranger_shares_before + shares_to_transfer

    helpers.assert_single_event_named(
        "Transfer",
        tx,
        {"from": stranger, "to": another_stranger, "sharesValue": lido.getPooledEthByShares(shares_to_transfer)}
    )
    helpers.assert_single_event_named(
        "TransferShares",
        tx,
        {"from": stranger, "to": another_stranger, "sharesValue": shares_to_transfer}
    )


def test_transfer(helpers, lido, stranger, another_stranger):
    stranger.transfer(lido, 10*10**18)

    amount_to_transfer = 10**18
    stranger_balance_before = lido.balanceOf(stranger)
    another_stranger_balance_before = lido.balanceOf(another_stranger)

    tx = lido.transfer(another_stranger, amount_to_transfer, {"from": stranger})

    assert lido.balanceOf(stranger) == stranger_balance_before - amount_to_transfer + 1
    assert lido.balanceOf(another_stranger) == another_stranger_balance_before + amount_to_transfer - 1

    helpers.assert_single_event_named(
        "TransferShares",
        tx,
        {"from": stranger, "to": another_stranger, "sharesValue": lido.getSharesByPooledEth(amount_to_transfer)}
    )
    helpers.assert_single_event_named(
        "Transfer",
        tx,
        {"from": stranger, "to": another_stranger, "sharesValue": amount_to_transfer}
    )


def test_oracle_init_reverts(oracle, stranger):
    with reverts('WRONG_BASE_VERSION'):
        oracle.finalizeUpgrade_v3({"from": stranger})


def test_oracle_version(oracle):
    assert oracle.getVersion() == 3


def test_init_v3_reverts_after_deployment(oracle, stranger):
    with reverts('WRONG_BASE_VERSION'):
        oracle.finalizeUpgrade_v3({"from": stranger})
