"""
Tests for lido staking limits for voting 17/05/2022
"""
import pytest
import json
import eth_abi

from web3 import Web3
from tx_tracing_helpers import *
from utils.config import contracts
from brownie import web3, convert, reverts, ZERO_ADDRESS, chain
from scripts.vote_2022_05_17 import (
    start_vote,
    update_lido_app,
    update_nos_app,
    update_oracle_app,
)

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
    mev_vault_tx_data = json.load(
        open("./utils/txs/tx-26-deploy-execution-layer-rewards-vault.json")
    )["data"]

    lido_tx = deployer.transfer(data=lido_tx_data)
    nos_tx = deployer.transfer(data=nos_tx_data)
    oracle_tx = deployer.transfer(data=oracle_tx_data)
    mev_vault_tx = deployer.transfer(data=mev_vault_tx_data)

    update_lido_app["new_address"] = lido_tx.contract_address
    update_lido_app["mevtxfee_vault_address"] = mev_vault_tx.contract_address
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


def test_is_staking_not_paused(lido):
    # Should be running from the start
    assert lido.isStakingPaused() == False


def test_pause_staking_access(lido, operator, stranger):
    # Should not allow to pause staking from unauthorized account
    create_and_grant_role(operator, lido, "STAKING_PAUSE_ROLE")
    with reverts("APP_AUTH_FAILED"):
        lido.pauseStaking({"from": stranger})
    lido.pauseStaking({"from": operator})


def test_pause_staking_works(lido, operator, stranger):
    # Should not allow to stake until it's paused
    create_and_grant_role(operator, lido, "STAKING_PAUSE_ROLE")
    tx = lido.pauseStaking({"from": operator})

    assert len(tx.logs) == 1
    assert_staking_is_paused(tx.logs[0])
    with reverts("STAKING_PAUSED"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})


def test_resume_staking_access(lido, operator, stranger):
    # Should not allow to resume staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        lido.resumeStaking({"from": stranger})
    lido.resumeStaking({"from": operator})


def test_resume_staking_works(lido, operator, stranger):
    # Should emit event with correct params
    create_and_grant_role(operator, lido, "STAKING_PAUSE_ROLE")
    tx = lido.pauseStaking({"from": operator})

    with reverts("STAKING_PAUSED"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})

    tx = lido.resumeStaking({"from": operator})

    assert len(tx.logs) == 1
    assert_staking_is_resumed(tx.logs[0])

    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})


def test_set_staking_limit_access(lido, operator, stranger):
    # Should not allow to resume staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        lido.setStakingLimit(ether, ether * 0.01, {"from": stranger})
    lido.setStakingLimit(ether, ether * 0.01, {"from": operator})


def test_staking_limit_getter(lido, operator):
    # Should return the same value as it is set because no block has been produced
    assert lido.getCurrentStakeLimit() != ether

    lido.setStakingLimit(ether, ether * 0.01, {"from": operator})

    assert lido.getCurrentStakeLimit() == ether


def test_staking_limit_initial_not_zero(lido):
    # By default it's set to 150000 ETH per day
    assert lido.getCurrentStakeLimit() == 150000 * 10 ** 18


@pytest.mark.parametrize(
    "limit_max,limit_per_block",
    [(10 ** 6, 10 ** 4), (10 ** 12, 10 ** 10), (10 ** 18, 10 ** 16)],
)
def test_staking_limit_updates_per_block_correctly(
    lido, operator, stranger, limit_max, limit_per_block
):
    # Should update staking limits after submit
    lido.setStakingLimit(limit_max, limit_per_block, {"from": operator})
    staking_limit_before = lido.getCurrentStakeLimit()
    assert limit_max == staking_limit_before
    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": limit_per_block})

    assert staking_limit_before - limit_per_block == lido.getCurrentStakeLimit()

    chain.mine(1)

    assert staking_limit_before == lido.getCurrentStakeLimit()


def test_staking_limit_is_zero(lido, operator):
    # Should be unlimited if 0 is set
    with reverts("ZERO_MAX_STAKE_LIMIT"):
        lido.setStakingLimit(0, 0, {"from": operator})


def test_staking_limit_is_uint256(lido, operator):
    max_uint256 = convert.to_uint(
        "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )

    with reverts("TOO_LARGE_MAX_STAKE_LIMIT"):
        lido.setStakingLimit(max_uint256, max_uint256, {"from": operator})


def test_staking_limit_exceed(lido, operator, stranger):
    # Should not allow to submit if limit is exceeded
    lido.setStakingLimit(ether, ether * 0.01, {"from": operator})

    with reverts("STAKE_LIMIT"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether * 10})


def test_remove_staking_limit_access(lido, operator, stranger):
    # Should not allow to resume staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        lido.removeStakingLimit({"from": stranger})
    lido.removeStakingLimit({"from": operator})


def test_remove_staking_limit_works(lido, operator, stranger):
    # Should not allow to resume staking from unauthorized account
    lido.setStakingLimit(ether, ether * 0.01, {"from": operator})

    with reverts("STAKE_LIMIT"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether * 10})

    lido.removeStakingLimit({"from": operator})
    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether * 10})


def test_staking_ability(lido, stranger):
    # Should mint correct stETH amount to the staker account
    assert lido.balanceOf(stranger) == 0

    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})

    assert lido.balanceOf(stranger) >= ether - 1


def create_and_grant_role(operator, target_app, permission_name):
    acl = contracts.acl
    permission_id = convert.to_uint(Web3.keccak(text=permission_name))
    acl.createPermission(
        operator, target_app, permission_id, operator, {"from": operator}
    )
    acl.grantPermission(operator, target_app, permission_id, {"from": operator})


def assert_staking_is_paused(log):
    topic = web3.keccak(text="StakingPaused()")
    assert log["topics"][0] == topic


def assert_staking_is_resumed(log):
    topic = web3.keccak(text="StakingResumed()")
    assert log["topics"][0] == topic


def assert_set_staking_limit(log, limit_max, limit_per_block):
    topic = web3.keccak(text="StakingLimitSet(uint256,uint256)")

    assert log["topics"][0] == topic
    assert (
        log["data"]
        == "0x"
        + eth_abi.encode_abi(["uint256", "uint256"], [limit_max, limit_per_block]).hex()
    )
