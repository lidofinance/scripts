import pytest

from brownie import ZERO_ADDRESS
from utils.config import contracts

from utils.test.reward_wrapper_helpers import deploy_reward_wrapper, wrap_and_split_rewards
from utils.test.split_helpers import (
    deploy_split_wallet,
    get_split_percent_allocation,
    get_split_percentage_scale,
    split_and_withdraw_wsteth_rewards,
)

WEI_TOLERANCE = 5  # wei tolerance to avoid rounding issue


# fixtures


@pytest.fixture(scope="module")
def cluster_participants(accounts):
    CLUSTER_PARTICIPANTS = 5

    return sorted(map(lambda participant: participant.address, accounts[0:CLUSTER_PARTICIPANTS]))


@pytest.fixture(scope="module")
def split_percentage_scale():
    return get_split_percentage_scale()


@pytest.fixture(scope="module")
def split_percent_allocation(cluster_participants, split_percentage_scale):
    return get_split_percent_allocation(len(cluster_participants), split_percentage_scale)


@pytest.fixture(scope="module")
def split_wallet(cluster_participants, split_percent_allocation):
    (deployed_contract, _) = deploy_split_wallet(
        cluster_participants, split_percent_allocation, cluster_participants[0]
    )

    return deployed_contract


@pytest.fixture(scope="module")
def reward_wrapper(split_wallet, cluster_participants):
    (deployed_contract, _) = deploy_reward_wrapper(split_wallet, cluster_participants[0])

    return deployed_contract


def test_reward_wrapper_deploy(reward_wrapper, split_wallet):
    """
    Test reward wrapper contract deployment
    """
    connected_split_wallet = reward_wrapper.splitWallet()
    assert connected_split_wallet == split_wallet.address

    steth = reward_wrapper.stETH()
    assert steth == contracts.lido.address

    wsteth = reward_wrapper.wstETH()
    assert wsteth == contracts.wsteth.address

    fee_share = reward_wrapper.feeShare()
    fee_recipient = reward_wrapper.feeRecipient()

    with_fee = fee_share > 0 and fee_recipient != ZERO_ADDRESS
    without_fee = fee_share == 0 and fee_recipient == ZERO_ADDRESS

    assert with_fee or without_fee


def test_split_wallet_deploy(split_wallet):
    """
    Test split wallet contract deployment
    """
    assert split_wallet.splitMain() == contracts.split_main.address


# rewards wrapping tests


def test_wrap_rewards(accounts, reward_wrapper):
    """
    Test rewards wrapping logic
    Should wrap steth rewards to wsteth and split between dvt provider and split wallet
    """
    steth = contracts.lido
    steth_to_distribute = 1 * 10 ** contracts.lido.decimals()
    stranger = accounts[0]

    # get steth to distribute
    eth_to_submit = steth_to_distribute + WEI_TOLERANCE
    steth.submit(ZERO_ADDRESS, {"from": stranger, "value": eth_to_submit})
    assert steth.balanceOf(stranger) >= steth_to_distribute

    # transfer steth to wrapper contract
    assert steth.balanceOf(reward_wrapper.address) == 0
    steth.transfer(reward_wrapper.address, steth_to_distribute, {"from": stranger})
    assert steth.balanceOf(reward_wrapper.address) >= steth_to_distribute - WEI_TOLERANCE

    # wrap rewards and split between dvt provider and split wallet
    wrap_and_split_rewards(reward_wrapper, stranger)


def test_split_rewards(accounts, split_wallet, cluster_participants, split_percent_allocation, split_percentage_scale):
    """
    Test separate split wallet (instance of 0xSplit protocol) contract distribution logic
    Should distribute wsteth rewards between participants according to split wallet shares
    """
    wsteth = contracts.wsteth
    stranger = accounts[0]

    wsteth_to_distribute = 1 * 10 ** contracts.wsteth.decimals()

    # check split wallet balance initial state
    split_wallet_balance_before = wsteth.balanceOf(split_wallet)
    assert split_wallet_balance_before == 0

    # get required wsteth
    eth_to_submit = wsteth.getStETHByWstETH(wsteth_to_distribute) + WEI_TOLERANCE
    stranger.transfer(wsteth.address, eth_to_submit)
    assert wsteth.balanceOf(stranger) >= wsteth_to_distribute

    # transfer wsteth to split wallet contract
    wsteth.transfer(split_wallet.address, wsteth_to_distribute, {"from": stranger})
    assert wsteth.balanceOf(split_wallet.address) == wsteth_to_distribute

    # split wsteth rewards between participants and withdraw
    split_and_withdraw_wsteth_rewards(
        split_wallet.address,
        cluster_participants,
        split_percent_allocation,
        split_percentage_scale,
        stranger,
    )
