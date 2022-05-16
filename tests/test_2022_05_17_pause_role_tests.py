"""
Tests for lido resume method for voting 17/05/2022
"""
import pytest
from brownie import reverts
from scripts.vote_2022_05_17 import start_vote


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def dao_voting_as_eoa(accounts, dao_voting):
    return accounts.at(dao_voting.address, force=True)


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    pass
    # vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]
    # helpers.execute_vote(
    #     vote_id=vote_id,
    #     accounts=accounts,
    #     dao_voting=dao_voting,
    #     skip_time=3 * 60 * 60 * 24,
    # )
    # print(f"vote {vote_id} was executed")


@pytest.fixture(scope="module", autouse=True)
def autopause_lido(lido, dao_voting_as_eoa):
    lido.stop({"from": dao_voting_as_eoa})
    assert lido.isStopped()


def test_resume_by_stranger(lido, stranger, dao_voting_as_eoa):
    # Test that stranger can't resume the Lido
    with reverts("APP_AUTH_FAILED"):
        lido.resume({"from": stranger})


def test_resume_by_voting(lido, stranger, dao_voting_as_eoa):
    # Test that voting can resume the Lido
    lido.resume({"from": dao_voting_as_eoa})
    assert not lido.isStopped()
