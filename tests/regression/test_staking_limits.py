"""
Tests for lido staking limits
"""
import pytest
import eth_abi

from brownie import web3, convert, reverts, ZERO_ADDRESS, chain
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


ether = 10 ** 18


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def operator(accounts, dao_voting):
    return accounts.at(dao_voting.address, force=True)


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(vote_id_from_env, helpers, accounts, dao_voting):
    if vote_id_from_env:
        helpers.execute_vote(
            vote_id=vote_id_from_env, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
        )

    start_and_execute_votes(dao_voting, helpers)


def test_is_staking_not_paused(lido):
    # Should be running from the start
    assert lido.isStakingPaused() is False


def test_pause_staking_access(lido, operator, stranger):
    # Should not allow to pause staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        lido.pauseStaking({"from": stranger})
    lido.pauseStaking({"from": operator})


def test_pause_staking_works(lido, operator, stranger):
    # Should not allow to stake until it's paused
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
    lido.pauseStaking({"from": operator})

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


def test_protocol_pause(lido, operator, stranger):
    # Should revert if contract is paused

    lido.stop({"from": operator})

    with reverts("STAKING_PAUSED"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})

    lido.resumeStaking({"from": operator})

    with reverts("CONTRACT_IS_STOPPED"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})


def test_protocol_resume_after_pause(lido, operator, stranger):
    # Should revert if contract is paused

    lido.stop({"from": operator})

    with reverts("STAKING_PAUSED"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})

    lido.resume({"from": operator})
    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})


def test_staking_ability(lido, stranger):
    # Should mint correct stETH amount to the staker account
    assert lido.balanceOf(stranger) == 0

    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})

    assert lido.balanceOf(stranger) >= ether - 2


def test_staking_limit_full_info(lido, stranger):
    (
        is_paused,
        is_limit_set,
        limit,
        max_limit,
        growth_limit,
        prev_limit,
        block_number,
    ) = lido.getStakeLimitFullInfo({"from": stranger})
    assert is_paused is False
    assert is_limit_set is True
    assert limit <= 150000 * 10 ** 18
    assert max_limit == 150000 * 10 ** 18
    assert growth_limit == 6400
    assert prev_limit <= 150000 * 10 ** 18


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
