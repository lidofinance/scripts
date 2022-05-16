"""
Tests for lido staking limits for voting 17/05/2022
"""
import pytest
from brownie import reverts, ZERO_ADDRESS
from scripts.vote_2022_05_17 import start_vote

ether = 10 ** 18


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def operator(accounts):
    return accounts[1]


def test_is_staking_not_paused(lido):
    # Should be running from the start
    assert lido.isStakingPaused() == False


def test_staking_pause_works(lido, operator, stranger):
    # Should not allow to submit if staking is paused
    lido.pauseStaking({"from": operator})

    assert lido.isStakingPaused() == True
    with reverts("STAKING_PAUSED"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": 10 ** 18})


def test_pause_staking_access(lido, operator, stranger):
    # Should not allow to pause staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        lido.pauseStaking({"from": stranger})
    lido.pauseStaking({"from": operator})


def test_resume_staking_access(lido, operator, stranger):
    # Should not allow to resume staking from unauthorized account
    with reverts("APP_AUTH_FAILED"):
        lido.resumeStaking(ether, ether * 0.01, {"from": stranger})
    lido.resumeStaking(ether, ether * 0.01, {"from": operator})


def test_staking_limit_getter(lido, operator):
    # Should return the same value as it is set because no block has been produced
    lido.resumeStaking(ether, ether * 0.01, {"from": operator})

    assert lido.getCurrentStakeLimit() == ether * 0.01


def test_staking_limit_updates_correctly(lido, stranger):
    # Should update staking limits after submit
    lido.resumeStaking(ether * 10, ether, {"from": operator})
    staking_limit_before = lido.getCurrentStakeLimit()
    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether})
    assert staking_limit_before == lido.getCurrentStakeLimit()


def test_staking_limit_exceed(lido, stranger):
    # Should not allow to submit if limit is exceeded
    lido.resumeStaking(ether, ether * 0.01, {"from": operator})

    with reverts("STAKE_LIMIT"):
        lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": ether * 10})
