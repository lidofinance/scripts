"""
Tests for lido burnShares method for voting 24/05/2022
"""
import eth_abi
import pytest
from brownie import reverts, ZERO_ADDRESS, web3, interface, accounts
from utils.import_current_vote import get_start_and_execute_votes_func


start_and_execute_votes = get_start_and_execute_votes_func()


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def dao_voting_as_eoa(accounts, dao_voting):
    return accounts.at(dao_voting.address, force=True)


@pytest.fixture(scope="module", autouse=(start_and_execute_votes is not None))
def autoexecute_vote(dao_voting, helpers, vote_id_from_env):
    if vote_id_from_env:
        helpers.execute_vote(
            vote_id=vote_id_from_env, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
        )
    elif start_and_execute_votes:
        start_and_execute_votes(dao_voting, helpers)


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


def assert_shares_burnt_log(
    log, account, pre_rebase_token_amount, post_rebase_token_amount, shares_amount
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
            [pre_rebase_token_amount, post_rebase_token_amount, shares_amount],
        ).hex()
    )
