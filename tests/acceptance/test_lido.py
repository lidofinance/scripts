import pytest
from brownie import interface, web3, reverts  # type: ignore

from utils.test.helpers import ONE_ETH
from utils.config import (
    contracts,
    LIDO,
    LIDO_IMPL,
    INITIAL_DEAD_TOKEN_HOLDER,
    LIDO_ARAGON_APP_ID,
    LIDO_MAX_STAKE_LIMIT_ETH,
)

last_seen_deposited_validators = 176018
last_seen_total_rewards_collected = 50327973200740183385860
last_seen_beacon_validators = 175906

@pytest.fixture(scope="module")
def contract() -> interface.Lido:
    return interface.Lido(LIDO)


def test_aragon(contract):
    proxy = interface.AppProxyUpgradeable(contract)
    assert proxy.implementation() == LIDO_IMPL
    assert contract.kernel() == contracts.kernel
    assert contract.appId() == LIDO_ARAGON_APP_ID
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


def test_initialize(contract):
    with reverts("INIT_ALREADY_INITIALIZED"):
        contract.initialize(contracts.lido_locator, contracts.eip712_steth, {"from": contracts.voting})


def test_finalize_upgrade(contract):
    with reverts("UNEXPECTED_CONTRACT_VERSION"):
        contract.finalizeUpgrade_v2(contracts.lido_locator, contracts.eip712_steth, {"from": contracts.voting})


def test_petrified():
    impl = interface.Lido(LIDO_IMPL)
    with reverts("INIT_ALREADY_INITIALIZED"):
        impl.initialize(contracts.lido_locator, contracts.eip712_steth, {"from": contracts.voting})

    with reverts("UNEXPECTED_CONTRACT_VERSION"):
        impl.finalizeUpgrade_v2(contracts.lido_locator, contracts.eip712_steth, {"from": contracts.voting})


def test_links(contract):
    assert contract.getEIP712StETH() == contracts.eip712_steth
    assert contract.getLidoLocator() == contracts.lido_locator


def test_steth(contract):
    # stone
    assert contract.balanceOf(INITIAL_DEAD_TOKEN_HOLDER) > 0
    assert contract.sharesOf(INITIAL_DEAD_TOKEN_HOLDER) > 0

    assert contract.getTotalShares() > contract.sharesOf(INITIAL_DEAD_TOKEN_HOLDER)
    # unlimited allowance for burner to burn shares from withdrawal queue
    assert contract.allowance(contracts.withdrawal_queue, contracts.burner) == 2**256 - 1
    assert contract.allowance(contracts.node_operators_registry, contracts.burner) == 0


def test_lido_state(contract):
    stake_limit = contract.getStakeLimitFullInfo()

    modules = contracts.staking_router.getStakingModules()
    total_exited_validators = sum(
        contracts.staking_router.getStakingModuleSummary(module[0])[0]
        for module in modules
    )

    assert stake_limit["isStakingPaused"] == False
    assert stake_limit["isStakingLimitSet"] == True
    assert stake_limit["maxStakeLimit"] == LIDO_MAX_STAKE_LIMIT_ETH * ONE_ETH

    assert contract.getBufferedEther() > 0

    beacon_stat = contract.getBeaconStat()
    assert beacon_stat["depositedValidators"] >= last_seen_deposited_validators
    assert beacon_stat["beaconValidators"] >= last_seen_beacon_validators
    # might break once enough exited validators registered
    # they are not excluded from the 'beaconValidators' counter even though have zero balance
    assert beacon_stat["beaconBalance"] >= 32 * 1e18 * (beacon_stat["beaconValidators"] - total_exited_validators), "no full withdrawals happened"
    assert beacon_stat["depositedValidators"] >= beacon_stat["beaconValidators"]

    assert contract.getTotalELRewardsCollected() >= last_seen_total_rewards_collected
