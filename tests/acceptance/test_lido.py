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
    LIDO_DEPOSITS_RESERVE_TARGET,
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
    assert contract.BUFFER_RESERVE_MANAGER_ROLE() == web3.keccak(text="BUFFER_RESERVE_MANAGER_ROLE").hex()


def test_pausable(contract):
    assert contract.isStopped() == False


def test_versioned(contract):
    assert contract.getContractVersion() == 4


def test_initialize(contract):
    # v4 signature: initialize(lidoLocator, eip712StETH, depositsReserveTarget)
    with reverts("INIT_ALREADY_INITIALIZED"):
        contract.initialize(
            contracts.lido_locator,
            contracts.eip712_steth,
            LIDO_DEPOSITS_RESERVE_TARGET,
            {"from": contracts.voting},
        )


def test_finalize_upgrade(contract):
    # Re-calling finalizeUpgrade_v4 reverts: NO_REPORT if the current oracle frame
    # has no submitted report, UNEXPECTED_CONTRACT_VERSION otherwise.
    main_data_submitted = contracts.accounting_oracle.getProcessingState()["mainDataSubmitted"]
    expected_error = "UNEXPECTED_CONTRACT_VERSION" if main_data_submitted else "NO_REPORT"
    with reverts(expected_error):
        contract.finalizeUpgrade_v4(LIDO_DEPOSITS_RESERVE_TARGET, {"from": contracts.voting})


def test_deposits_reserve_target(contract):
    assert contract.getDepositsReserveTarget() == LIDO_DEPOSITS_RESERVE_TARGET


def test_petrified():
    impl = interface.Lido(LIDO_IMPL)

    with reverts("INIT_ALREADY_INITIALIZED"):
        impl.initialize(
            contracts.lido_locator,
            contracts.eip712_steth,
            LIDO_DEPOSITS_RESERVE_TARGET,
            {"from": contracts.voting},
        )

    # For petrified implementation, hasInitialized() returns false because
    # AragonApp (LIDO) sets initializationBlock to PETRIFIED_BLOCK = uint256(-1)
    # and hasInitialized() requires getBlockNumber() >= initializationBlock.
    with reverts("NOT_INITIALIZED"):
        impl.finalizeUpgrade_v4(LIDO_DEPOSITS_RESERVE_TARGET, {"from": contracts.voting})


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
    module_summaries = [contracts.staking_router.getStakingModuleSummary(module[0]) for module in modules]
    total_exited_validators = sum(s["totalExitedValidators"] for s in module_summaries)
    total_deposited_validators = sum(s["totalDepositedValidators"] for s in module_summaries)

    assert stake_limit["isStakingPaused_"] == False
    assert stake_limit["isStakingLimitSet"] == True
    assert stake_limit["maxStakeLimit"] == LIDO_MAX_STAKE_LIMIT_ETH * ONE_ETH

    assert contract.getBufferedEther() > 0

    beacon_stat = contract.getBeaconStat()
    # beaconValidators == depositedValidators
    assert beacon_stat["depositedValidators"] == beacon_stat["beaconValidators"]
    assert beacon_stat["depositedValidators"] >= last_seen_deposited_validators

    # counters cross-check: Lido's global deposited counter (seedDepositsCount after
    # the v3->v4 storage migration) equals the sum of per-module counters in the SR
    assert beacon_stat["depositedValidators"] == total_deposited_validators
    # exited validators can never exceed ever-deposited
    assert total_exited_validators <= beacon_stat["depositedValidators"]

    assert contract.getTotalELRewardsCollected() >= last_seen_total_rewards_collected


def test_balance_stats(contract):
    (
        cl_validators_balance,
        cl_pending_balance,
        deposited_since_last_report,
        deposited_for_current_report,
    ) = contract.getBalanceStats()

    assert cl_validators_balance > 0

    # getBeaconStat().beaconBalance is exactly active + pending
    assert contract.getBeaconStat()["beaconBalance"] == cl_validators_balance + cl_pending_balance

    # deposits attributable to the current report are a subset of all deposits
    # made since the last report
    assert deposited_for_current_report <= deposited_since_last_report
