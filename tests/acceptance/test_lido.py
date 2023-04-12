import pytest
from brownie import interface, web3  # type: ignore

from utils.config import (
    contracts,
    lido_dao_steth_address,
)

lido_v2_implementation = "0xE5418393B2D9D36e94b7a8906Fb2e4E9dce9DEd3"
lido_dao_lido_app_id = "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320"
initial_token_holder = "0x000000000000000000000000000000000000dead"
last_seen_deposited_validators = 176018
last_seen_total_rewards_collected = 50327973200740183385860
last_seen_beacon_validators = 175906


@pytest.fixture(scope="module")
def contract() -> interface.AccountingOracle:
    return interface.Lido(lido_dao_steth_address)


def test_aragon(contract):
    proxy = interface.AppProxyUpgradeable(contract)
    assert proxy.implementation() == lido_v2_implementation
    assert contract.kernel() == contracts.kernel
    assert contract.appId() == lido_dao_lido_app_id
    assert contract.hasInitialized() == True
    assert contract.isPetrified() == False


def test_role_keccaks(contract):
    assert contract.PAUSE_ROLE() == web3.keccak(text="PAUSE_ROLE").hex()
    assert contract.RESUME_ROLE() == web3.keccak(text="RESUME_ROLE").hex()
    assert contract.STAKING_PAUSE_ROLE() == web3.keccak(text="STAKING_PAUSE_ROLE").hex()
    assert contract.STAKING_CONTROL_ROLE() == web3.keccak(text="STAKING_CONTROL_ROLE").hex()
    assert (
        contract.UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE()
        == web3.keccak(text="UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE").hex()
    )


def test_pausable(contract):
    assert contract.isStopped() == False


def test_versioned(contract):
    assert contract.getContractVersion() == 2


def test_links(contract):
    assert contract.getEIP712StETH() == contracts.eip712_steth
    assert contract.getLidoLocator() == contracts.lido_locator


def test_steth(contract):
    # stone
    assert contract.balanceOf(initial_token_holder) > 0
    assert contract.sharesOf(initial_token_holder) > 0

    assert contract.getTotalShares() > contract.sharesOf(initial_token_holder)
    # unlimited allowance for burner to burn shares from withdrawal queue
    assert contract.allowance(contracts.withdrawal_queue, contracts.burner) == 2**256 - 1
    assert contract.allowance(contracts.node_operators_registry, contracts.burner) == 2**256 - 1


def test_lido_state(contract):
    stake_limit = contract.getStakeLimitFullInfo()
    assert stake_limit["isStakingPaused"] == False
    assert stake_limit["isStakingLimitSet"] == True
    assert stake_limit["maxStakeLimit"] == 150_000 * 1e18

    assert contract.getBufferedEther() > 0

    beacon_stat = contract.getBeaconStat()
    assert beacon_stat["depositedValidators"] >= last_seen_deposited_validators
    assert beacon_stat["beaconValidators"] >= last_seen_beacon_validators
    assert beacon_stat["beaconBalance"] >= 32 * 1e18 * beacon_stat["beaconValidators"], "no full withdrawals happened"
    assert beacon_stat["depositedValidators"] >= beacon_stat["beaconValidators"]

    assert contract.getTotalELRewardsCollected() >= last_seen_total_rewards_collected
