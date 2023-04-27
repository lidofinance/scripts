"""
Tests for lido staking limits
"""
import pytest
import eth_abi

from brownie import web3, convert, reverts, ZERO_ADDRESS, chain
from utils.config import contracts
from utils.test.helpers import ONE_ETH


@pytest.fixture(scope="module")
def voting(accounts):
    return accounts.at(contracts.voting, force=True)


def test_is_staking_not_paused(voting):
    contracts.lido.resumeStaking({"from": voting})
    # Should be running from the start
    assert contracts.lido.isStakingPaused() is False


def test_pause_staking_access(voting, stranger):
    contracts.lido.resumeStaking({"from": voting})
    # Should not allow to pause staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        contracts.lido.pauseStaking({"from": stranger})
    contracts.lido.pauseStaking({"from": voting})


def test_pause_staking_works(voting, stranger):
    contracts.lido.resumeStaking({"from": voting})
    # Should not allow to stake until it's paused
    tx = contracts.lido.pauseStaking({"from": voting})

    assert len(tx.logs) == 1
    assert_staking_is_paused(tx.logs[0])
    with reverts("STAKING_PAUSED"):
        contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH})


def test_resume_staking_access(voting, stranger):
    # Should not allow to resume staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        contracts.lido.resumeStaking({"from": stranger})
    contracts.lido.resumeStaking({"from": voting})


def test_resume_staking_works(voting, stranger):
    # Should emit event with correct params
    contracts.lido.pauseStaking({"from": voting})

    with reverts("STAKING_PAUSED"):
        contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH})

    tx = contracts.lido.resumeStaking({"from": voting})

    assert len(tx.logs) == 1
    assert_staking_is_resumed(tx.logs[0])

    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH})


def test_set_staking_limit_access(voting, stranger):
    # Should not allow to resume staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        contracts.lido.setStakingLimit(ONE_ETH, ONE_ETH * 0.01, {"from": stranger})
    contracts.lido.setStakingLimit(ONE_ETH, ONE_ETH * 0.01, {"from": voting})


def test_staking_limit_getter(voting):
    # Should return the same value as it is set because no block has been produced
    assert contracts.lido.getCurrentStakeLimit() != ONE_ETH

    contracts.lido.setStakingLimit(ONE_ETH, ONE_ETH * 0.01, {"from": voting})

    assert contracts.lido.getCurrentStakeLimit() == ONE_ETH


def test_staking_limit_initial_not_zero():
    # By default it's set to 150000 ETH per day
    assert contracts.lido.getCurrentStakeLimit() == 150000 * 10**18


@pytest.mark.parametrize(
    "limit_max,limit_per_block",
    [(10**6, 10**4), (10**12, 10**10), (10**18, 10**16)],
)
def test_staking_limit_updates_per_block_correctly(voting, stranger, limit_max, limit_per_block):
    # Should update staking limits after submit
    contracts.lido.setStakingLimit(limit_max, limit_per_block, {"from": voting})
    staking_limit_before = contracts.lido.getCurrentStakeLimit()
    assert limit_max == staking_limit_before
    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": limit_per_block})

    assert staking_limit_before - limit_per_block == contracts.lido.getCurrentStakeLimit()

    chain.mine(1)

    assert staking_limit_before == contracts.lido.getCurrentStakeLimit()


def test_staking_limit_is_zero(voting):
    # Should be unlimited if 0 is set
    with reverts("ZERO_MAX_STAKE_LIMIT"):
        contracts.lido.setStakingLimit(0, 0, {"from": voting})


def test_staking_limit_is_uint256(voting):
    max_uint256 = convert.to_uint("0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")

    with reverts("TOO_LARGE_MAX_STAKE_LIMIT"):
        contracts.lido.setStakingLimit(max_uint256, max_uint256, {"from": voting})


def test_staking_limit_exceed(voting, stranger):
    # Should not allow to submit if limit is exceeded
    contracts.lido.setStakingLimit(ONE_ETH, ONE_ETH * 0.01, {"from": voting})

    with reverts("STAKE_LIMIT"):
        contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH * 10})


def test_remove_staking_limit_access(voting, stranger):
    # Should not allow to resume staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        contracts.lido.removeStakingLimit({"from": stranger})
    contracts.lido.removeStakingLimit({"from": voting})


def test_remove_staking_limit_works(voting, stranger):
    # Should not allow to resume staking from unauthorized account
    contracts.lido.setStakingLimit(ONE_ETH, ONE_ETH * 0.01, {"from": voting})

    with reverts("STAKE_LIMIT"):
        contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH * 10})

    contracts.lido.removeStakingLimit({"from": voting})
    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH * 10})


def test_protocol_pause(voting, stranger):
    # Should revert if contract is paused

    contracts.lido.stop({"from": voting})

    with reverts("STAKING_PAUSED"):
        contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH})

    contracts.lido.resumeStaking({"from": voting})

    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH})


def test_protocol_resume_after_pause(voting, stranger):
    # Should revert if contract is paused

    contracts.lido.stop({"from": voting})

    with reverts("STAKING_PAUSED"):
        contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH})

    contracts.lido.resume({"from": voting})
    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH})


def test_staking_ability(stranger):
    # Should mint correct stETH amount to the staker account
    assert contracts.lido.balanceOf(stranger) == 0

    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ONE_ETH})

    assert contracts.lido.balanceOf(stranger) >= ONE_ETH - 2


def test_staking_limit_full_info(stranger):
    (
        is_paused,
        is_limit_set,
        limit,
        max_limit,
        growth_limit,
        prev_limit,
        block_number,
    ) = contracts.lido.getStakeLimitFullInfo({"from": stranger})
    assert is_paused is False
    assert is_limit_set is True
    assert limit <= 150000 * 10**18
    assert max_limit == 150000 * 10**18
    assert growth_limit == 6400
    assert prev_limit <= 150000 * 10**18


class TestEventsEmitted:
    def test_staking_limit_emit_events(self, helpers):
        tx = contracts.lido.setStakingLimit(1000, 100, {"from": contracts.voting})
        helpers.assert_single_event_named(
            "StakingLimitSet", tx, {"maxStakeLimit": 1000, "stakeLimitIncreasePerBlock": 100}
        )
        assert is_staking_limit_set(contracts)

    def test_staking_limit_change_emit_events(self, helpers):
        contracts.lido.setStakingLimit(1000, 100, {"from": contracts.voting})
        tx = contracts.lido.setStakingLimit(2000, 200, {"from": contracts.voting})
        helpers.assert_single_event_named(
            "StakingLimitSet", tx, {"maxStakeLimit": 2000, "stakeLimitIncreasePerBlock": 200}
        )
        assert is_staking_limit_set(contracts)

    def test_staking_limit_remove_emit_events(self, helpers):
        contracts.lido.setStakingLimit(1000, 100, {"from": contracts.voting})

        tx = contracts.lido.removeStakingLimit({"from": contracts.voting})
        helpers.assert_single_event_named("StakingLimitRemoved", tx, {})
        helpers.assert_event_not_emitted("StakingLimitSet", tx)
        assert not is_staking_limit_set(contracts)


def assert_staking_is_paused(log):
    topic = web3.keccak(text="StakingPaused()")
    assert log["topics"][0] == topic


def assert_staking_is_resumed(log):
    topic = web3.keccak(text="StakingResumed()")
    assert log["topics"][0] == topic


def assert_set_staking_limit(log, limit_max, limit_per_block):
    topic = web3.keccak(text="StakingLimitSet(uint256,uint256)")

    assert log["topics"][0] == topic
    assert log["data"] == "0x" + eth_abi.encode_abi(["uint256", "uint256"], [limit_max, limit_per_block]).hex()


def is_staking_limit_set(contracts):
    _, value, *_ = contracts.lido.getStakeLimitFullInfo()
    return value
