import pytest
from brownie import Wei, reverts

from utils.config import lido_dao_agent_address

ONE_INCH_REWARDS_MANAGER = '0xf5436129Cf9d8fa2a1cb6e591347155276550635'

@pytest.fixture()
def deployer(accounts):
    return accounts[0]

@pytest.fixture()
def agent_eoa(accounts):
    return accounts.at(lido_dao_agent_address, force=True)


@pytest.fixture()
def stranger(accounts):
    return accounts[1]


@pytest.fixture()
def rewards_manager(interface):
    return interface.RewardsManager(ONE_INCH_REWARDS_MANAGER)


@pytest.fixture()
def tokens_recoverer(RewardsManagerTokensRecoverer, deployer):
    return RewardsManagerTokensRecoverer.deploy(lido_dao_agent_address, {"from": deployer})



@pytest.mark.parametrize("is_owner", [True, False])
@pytest.mark.parametrize("initial_balance", [0, 50_000 * 10 ** 18])
@pytest.mark.parametrize(
    "amount_to_recover", [0, 100_000 * 10 ** 18, 10_000 * 10 ** 18]
)
def test_recover(
    rewards_manager,
    tokens_recoverer,
    ldo_token,
    agent_eoa,
    stranger,
    is_owner,
    initial_balance,
    amount_to_recover,
):
    # validate that owner of the rewards manager is agent
    assert rewards_manager.owner() == agent_eoa

    # set balance for rewards manager
    refill_rewards_manager_balance(rewards_manager, agent_eoa, ldo_token, initial_balance)
    assert ldo_token.balanceOf(rewards_manager) == initial_balance

    # prepare rewards manager ownership
    if is_owner:
        rewards_manager.transfer_ownership(tokens_recoverer, {"from": agent_eoa})
        assert rewards_manager.owner() == tokens_recoverer

    # recover tokens
    agent_balance_before = ldo_token.balanceOf(agent_eoa)
    rewards_manager_balance_before = ldo_token.balanceOf(rewards_manager)
    tx = tokens_recoverer.recover(
        rewards_manager, ldo_token, amount_to_recover, {"from": stranger}
    )

    expected_amount_to_recover = (
        min(amount_to_recover, initial_balance) if is_owner else 0
    )

    expected_agent_balance = agent_balance_before + expected_amount_to_recover
    expected_rewards_manager_balance = (
        rewards_manager_balance_before - expected_amount_to_recover
    )

    # validate balances updated correctly
    assert ldo_token.balanceOf(agent_eoa) == expected_agent_balance
    assert ldo_token.balanceOf(rewards_manager) == expected_rewards_manager_balance

    # validate events
    assert tx.events["Recover"]["sender"] == stranger
    assert tx.events["Recover"]["manager"] == rewards_manager
    assert tx.events["Recover"]["token"] == ldo_token
    assert tx.events["Recover"]["amount"] == amount_to_recover
    assert tx.events["Recover"]["recovered_amount"] == expected_amount_to_recover

    if is_owner:
        assert tx.events["OwnershipTransferred"]["previous_owner"] == tokens_recoverer
        assert tx.events["OwnershipTransferred"]["new_owner"] == agent_eoa
    else:
        assert "OwnershipTransferred" not in tx.events

    if expected_amount_to_recover > 0:
        assert tx.events["ERC20TokenRecovered"]["token"] == ldo_token
        assert tx.events["ERC20TokenRecovered"]["recipient"] == agent_eoa
        assert tx.events["ERC20TokenRecovered"]["amount"] == expected_amount_to_recover
    else:
        assert "ERC20TokenRecovered" not in tx.events

    # check that ownership returned back to agent in any case
    assert rewards_manager.owner() == agent_eoa


def reset_rewards_manager_balance(rewards_manager, agent_eoa, ldo):
    current_balance = ldo.balanceOf(rewards_manager)
    rewards_manager.recover_erc20(ldo, current_balance, {"from": agent_eoa})
    assert ldo.balanceOf(rewards_manager) == 0


def refill_rewards_manager_balance(rewards_manager, agent_eoa, ldo, amount):
    reset_rewards_manager_balance(rewards_manager, agent_eoa, ldo)
    if amount > 0:
        ldo.transfer(rewards_manager, amount, {"from": agent_eoa})
