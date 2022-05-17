"""
Tests for lido staking limits for voting 17/05/2022
"""
import pytest
import json

from tx_tracing_helpers import *
from brownie import reverts, ZERO_ADDRESS, chain
from scripts.vote_2022_05_17 import start_vote, update_lido_app, update_nos_app, update_oracle_app

ether = 10 ** 18


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def operator(accounts, dao_voting):
    return accounts.at(dao_voting.address, force=True)


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
    execution_layer_rewards_vault_tx_data = json.load(open("./utils/txs/tx-26-deploy-execution-layer-rewards-vault.json"))[
        "data"
    ]

    lido_tx = deployer.transfer(data=lido_tx_data)
    nos_tx = deployer.transfer(data=nos_tx_data)
    oracle_tx = deployer.transfer(data=oracle_tx_data)
    execution_layer_rewards_vault_tx = deployer.transfer(data=execution_layer_rewards_vault_tx_data)

    update_lido_app['new_address'] = lido_tx.contract_address
    update_lido_app['execution_layer_rewards_vault_address'] = execution_layer_rewards_vault_tx.contract_address
    update_nos_app['new_address'] = nos_tx.contract_address
    update_oracle_app['new_address'] = oracle_tx.contract_address


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )


def test_is_initialized(lido):
    # Should be running from the start
    assert lido.hasInitialized() == True


def test_is_staking_not_paused(lido):
    # Should be running from the start
    assert lido.isStakingPaused() == False


def test_pause_staking_access(lido, stranger):
    # Should not allow to pause staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        lido.pauseStaking({"from": stranger})


def test_resume_staking_access(lido, operator, stranger):
    # Should not allow to resume staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        lido.resumeStaking(ether, ether * 0.01, {"from": stranger})
    lido.resumeStaking(ether, ether * 0.01, {"from": operator})


def test_staking_limit_getter(lido, operator):
    # Should return the same value as it is set because no block has been produced
    lido.resumeStaking(ether, ether * 0.01, {"from": operator})

    assert lido.getCurrentStakeLimit() == ether


def test_staking_limit_updates_correctly(lido, operator, stranger):
    # Should update staking limits after submit
    lido.resumeStaking(ether * 10, ether, {"from": operator})
    staking_limit_before = lido.getCurrentStakeLimit()
    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})

    assert staking_limit_before - ether == lido.getCurrentStakeLimit()

    chain.mine(1)

    assert staking_limit_before == lido.getCurrentStakeLimit()


def test_staking_limit_exceed(lido, operator, stranger):
    # Should not allow to submit if limit is exceeded
    lido.resumeStaking(ether, ether * 0.01, {"from": operator})

    with reverts("STAKE_LIMIT"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether * 10})
