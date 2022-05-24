"""
Tests for lido burnShares method for voting 24/05/2022
"""
import eth_abi
import pytest
from brownie import reverts, ZERO_ADDRESS, web3
from scripts.vote_2022_05_24 import start_vote


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
    balance_before = lido.balanceOf(stranger)
    assert abs(stranger_submit_amount - balance_before) <= 1

    # Test that voting can burnShares
    shares_before = lido.sharesOf(stranger)
    shares_to_burn = shares_before // 3
    amount_to_burn = lido.getPooledEthByShares(shares_to_burn)
    tx = lido.burnShares(stranger, shares_to_burn, {"from": dao_voting_as_eoa})

    # Test that balance updated correctly
    balance_after = lido.balanceOf(stranger)
    expected_balance_after = lido.getPooledEthByShares(shares_before - shares_to_burn)
    assert balance_after == expected_balance_after

    # Test that event has correct data
    # Use raw logs to assert cause sometimes brownie can't parse events properly
    assert len(tx.logs) == 1
    assert_shares_burnt_log(
        log=tx.logs[0],
        account=stranger.address,
        pre_rebase_token_amount=amount_to_burn,
        post_reabse_token_amount=lido.getPooledEthByShares(shares_to_burn),
        shares_amount=shares_to_burn,
    )


def assert_shares_burnt_log(
    log, account, pre_rebase_token_amount, post_reabse_token_amount, shares_amount
):
    topic = web3.keccak(text="SharesBurnt(address,uint256,uint256,uint256)")
    assert log["topics"][0] == topic

    # validate indexed account topic
    assert log["topics"][1] == eth_abi.encode_abi(["address"], [account])

    # validate other params
    assert (
        log["data"]
        == "0x"
        + eth_abi.encode_abi(
            ["uint256", "uint256", "uint256"],
            [pre_rebase_token_amount, post_reabse_token_amount, shares_amount],
        ).hex()
    )
