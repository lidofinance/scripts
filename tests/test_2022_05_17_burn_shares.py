"""
Tests for lido burnShares method for voting 17/05/2022
"""
import pytest
from brownie import reverts, ZERO_ADDRESS
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


def test_burn_shares_by_stranger(lido, stranger, dao_voting_as_eoa):
    # Stake ETH by stranger to receive stETH
    stranger_submit_amount = 10**18
    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": stranger_submit_amount})
    stranger_steth_balance_before = lido.balanceOf(stranger)
    assert abs(stranger_submit_amount - stranger_steth_balance_before) <= 1

    # Test that stranger can't burnShares
    shares_to_burn = lido.sharesOf(stranger) // 3
    with reverts("APP_AUTH_FAILED"):
        lido.burnShares(stranger, shares_to_burn, {"from": stranger})


def test_burn_shares_by_voting(lido, stranger, dao_voting_as_eoa):
    # Stake ETH by stranger to receive stETH
    stranger_submit_amount = 10**18
    lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": stranger_submit_amount})
    stranger_steth_balance_before = lido.balanceOf(stranger)
    assert abs(stranger_submit_amount - stranger_steth_balance_before) <= 1

    # Test that voting can burnShares
    shares_to_burn = lido.sharesOf(stranger) // 3
    amount_to_burn = lido.getPooledEthByShares(shares_to_burn)
    tx = lido.burnShares(stranger, shares_to_burn, {"from": dao_voting_as_eoa})

    # Test that event has correct data
    assert tx.events["SharesBurnt"]["account"] == stranger
    assert tx.events["SharesBurnt"]["amount"] == amount_to_burn
    assert tx.events["SharesBurnt"]["sharesAmount"] == shares_to_burn

    # Test that balance updated correctly
    stranger_steth_balance_after = lido.balanceOf(stranger)

    # in the "worst" case, shares might round to the bottom for both parts,
    # and then the sum will differ from the initial value by 2 shares.
    assert (
        abs(
            stranger_steth_balance_before
            - amount_to_burn
            - stranger_steth_balance_after
        )
        <= 2
    )
