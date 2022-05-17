"""
Tests for lido resume method for voting 17/05/2022
"""
import json
import pytest
from brownie import reverts, web3
from scripts.vote_2022_05_17 import (
    start_vote,
    update_lido_app,
    update_nos_app,
    update_oracle_app,
)


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


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def dao_voting_as_eoa(accounts, dao_voting):
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
    print(f"vote {vote_id} was executed")


@pytest.fixture(scope="module", autouse=True)
def autopause_lido(lido, dao_voting_as_eoa):
    lido.stop({"from": dao_voting_as_eoa})
    assert lido.isStopped()


def test_resume_by_stranger(lido, stranger, dao_voting_as_eoa, acl):
    resume_role = web3.keccak(text="RESUME_ROLE")
    # Test that stranger has no RESUME_ROLE permission
    assert not acl.hasPermission["address,address,bytes32,uint[]"](
        stranger, lido, resume_role, []
    )
    # Test that stranger can't resume the Lido
    with reverts("APP_AUTH_FAILED"):
        lido.resume({"from": stranger})

    acl.createPermission(
        stranger,
        lido,
        resume_role,
        dao_voting_as_eoa,
        {"from": dao_voting_as_eoa},
    )
    assert acl.hasPermission["address,address,bytes32,uint[]"](
        stranger, lido, resume_role, []
    )
    # Test that stranger now can resume the Lido
    lido.resume({"from": stranger})
    assert not lido.isStopped()
