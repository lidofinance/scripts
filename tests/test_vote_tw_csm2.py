"""
Tests for triggerable withdrawals voting.
"""

from typing import Dict, Tuple, List, NamedTuple
from scripts.vote_tw_csm2 import create_tw_vote
from brownie import interface, convert, web3, ZERO_ADDRESS
from utils.test.tx_tracing_helpers import *
from utils.config import (
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    WITHDRAWAL_VAULT_IMPL,
    LIDO_LOCATOR_IMPL,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    CS_MODULE_ID,
    CS_ACCOUNTING_IMPL_V2_ADDRESS,
    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
    CS_FEE_ORACLE_IMPL_V2_ADDRESS,
    CS_GATE_SEAL_ADDRESS,
    CS_GATE_SEAL_V2_ADDRESS,
    CSM_COMMITTEE_MS,
    CSM_IMPL_V2_ADDRESS,
    CS_MODULE_NEW_TARGET_SHARE_BP,
    CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
    CSM_SET_VETTED_GATE_TREE_FACTORY,
    ACCOUNTING_ORACLE_IMPL,
    STAKING_ROUTER_IMPL,
    contracts,
)

# Contract versions expected after upgrade
CSM_V2_VERSION = 2
CS_ACCOUNTING_V2_VERSION = 2
CS_FEE_ORACLE_V2_VERSION = 2
CS_FEE_DISTRIBUTOR_V2_VERSION = 2


def get_ossifiable_proxy_impl(proxy_address):
    """Get implementation address from an OssifiableProxy"""
    proxy = interface.OssifiableProxy(proxy_address)
    return proxy.proxy__getImplementation()


def check_proxy_implementation(proxy_address, expected_impl):
    """Check that proxy has expected implementation"""
    actual_impl = get_ossifiable_proxy_impl(proxy_address)
    assert actual_impl == expected_impl, f"Expected impl {expected_impl}, got {actual_impl}"


def test_tw_vote(helpers, accounts, vote_ids_from_env, stranger):
    # Define constants and initial states
    app_manager_role = web3.keccak(text="APP_MANAGER_ROLE")
    vebo_consensus_version = 4
    ao_consensus_version = 4
    exit_events_lookback_window_in_slots = 7200
    nor_exit_deadline_in_sec = 30 * 60

    # Save original implementations for comparison
    locator_impl_before = interface.OssifiableProxy(contracts.lido_locator).proxy__getImplementation()
    accounting_oracle_impl_before = interface.OssifiableProxy(contracts.accounting_oracle).proxy__getImplementation()
    vebo_impl_before = interface.OssifiableProxy(contracts.validators_exit_bus_oracle).proxy__getImplementation()
    withdrawal_vault_impl_before = interface.WithdrawalContractProxy(contracts.withdrawal_vault).implementation()
    staking_router_impl_before = interface.OssifiableProxy(contracts.staking_router).proxy__getImplementation()

    csm_impl_before = get_ossifiable_proxy_impl(contracts.csm.address)
    cs_accounting_impl_before = get_ossifiable_proxy_impl(contracts.cs_accounting.address)
    cs_fee_oracle_impl_before = get_ossifiable_proxy_impl(contracts.cs_fee_oracle.address)
    cs_fee_distributor_impl_before = get_ossifiable_proxy_impl(contracts.cs_fee_distributor.address)

    # --- Initial state checks ---

    # Assert Lido Locator implementation initial state
    assert locator_impl_before != LIDO_LOCATOR_IMPL

    # Assert VEBO implementation and configuration
    initial_vebo_consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    assert initial_vebo_consensus_version < vebo_consensus_version
    # Check initial VEBO configuration
    try:
        assert contracts.validators_exit_bus_oracle.getMaxValidatorsPerReport() != 600
    except Exception:
        pass  # Function might not exist yet

    # Assert Withdrawal Vault implementation initial state
    assert withdrawal_vault_impl_before != WITHDRAWAL_VAULT_IMPL

    # Assert Accounting Oracle implementation and configuration
    initial_ao_consensus_version = contracts.accounting_oracle.getConsensusVersion()
    assert initial_ao_consensus_version < ao_consensus_version
    assert accounting_oracle_impl_before != ACCOUNTING_ORACLE_IMPL
    # Check that AGENT doesn't have MANAGE_CONSENSUS_VERSION_ROLE on AO yet
    assert not contracts.accounting_oracle.hasRole(contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent)

    # Assert Staking Router implementation
    assert staking_router_impl_before != STAKING_ROUTER_IMPL

    # Check Oracle Daemon Config initial state
    config_manager_role = contracts.oracle_daemon_config.CONFIG_MANAGER_ROLE()
    assert not contracts.oracle_daemon_config.hasRole(config_manager_role, contracts.agent)
    # Check that variables to be removed exist initially
    try:
        contracts.oracle_daemon_config.get('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP')
        contracts.oracle_daemon_config.get('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS')
        contracts.oracle_daemon_config.get('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS')
    except Exception as e:
        assert False, f"Expected variables to exist before removal: {e}"
    # Check that EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS doesn't exist yet
    try:
        contracts.oracle_daemon_config.get('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')
        assert False, "EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS should not exist before vote"
    except Exception:
        pass  # Expected to fail

    # Assert TWG role assignments initial state
    add_full_withdrawal_request_role = contracts.triggerable_withdrawals_gateway.ADD_FULL_WITHDRAWAL_REQUEST_ROLE()
    assert not contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.cs_ejector)
    assert not contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle)

    # Assert Staking Router permissions
    try:
        report_validator_exiting_status_role = contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE()
        report_validator_exit_triggered_role = contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE()
    except Exception as e:
        assert "Unknown typed error: 0x" in str(e), f"Unexpected error: {e}"
        report_validator_exiting_status_role = ZERO_ADDRESS
        report_validator_exit_triggered_role = ZERO_ADDRESS

    assert report_validator_exiting_status_role == ZERO_ADDRESS
    assert report_validator_exit_triggered_role == ZERO_ADDRESS

    # Assert APP_MANAGER_ROLE setting
    assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel, app_manager_role)

    # Assert Node Operator Registry and sDVT configuration

    assert contracts.node_operators_registry.getContractVersion() == 3
    assert contracts.simple_dvt.getContractVersion() == 3

    # CSM Steps 28: Check CSM implementation (pre-vote state)
    assert csm_impl_before != CSM_IMPL_V2_ADDRESS, "CSM implementation should be different before vote"

    # CSM Step 29: Check CSM finalizeUpgradeV2 was not called (pre-vote state)
    # assert contracts.csm.getInitializedVersion() < CSM_V2_VERSION, f"CSM version should be less than {CSM_V2_VERSION} before vote"

    # CSM Step 30: Check CSAccounting implementation (pre-vote state)
    assert cs_accounting_impl_before != CS_ACCOUNTING_IMPL_V2_ADDRESS, "CSAccounting implementation should be different before vote"

    # CSM Step 31: Check CSAccounting finalizeUpgradeV2 was not called (pre-vote state)
    # assert contracts.cs_accounting.getInitializedVersion() < CS_ACCOUNTING_V2_VERSION, f"CSAccounting version should be less than {CS_ACCOUNTING_V2_VERSION} before vote"

    # CSM Step 32: Check CSFeeOracle implementation (pre-vote state)
    assert cs_fee_oracle_impl_before != CS_FEE_ORACLE_IMPL_V2_ADDRESS, "CSFeeOracle implementation should be different before vote"

    # CSM Step 33: Check CSFeeOracle finalizeUpgradeV2 was not called (pre-vote state)
    assert contracts.cs_fee_oracle.getContractVersion() < CS_FEE_ORACLE_V2_VERSION, f"CSFeeOracle version should be less than {CS_FEE_ORACLE_V2_VERSION} before vote"
    assert contracts.cs_fee_oracle.getConsensusVersion() < 3, "CSFeeOracle consensus version should be less than 3 before vote"

    # CSM Step 34: Check CSFeeDistributor implementation (pre-vote state)
    assert cs_fee_distributor_impl_before != CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS, "CSFeeDistributor implementation should be different before vote"

    # CSM Step 35: Check CSFeeDistributor finalizeUpgradeV2 was not called (pre-vote state)
    # assert contracts.cs_fee_distributor.getInitializedVersion() < CS_FEE_DISTRIBUTOR_V2_VERSION, f"CSFeeDistributor version should be less than {CS_FEE_DISTRIBUTOR_V2_VERSION} before vote"

    # CSM Steps 36-38: CSAccounting roles (pre-vote state)
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.csm.address), "CSM should have SET_BOND_CURVE_ROLE on CSAccounting before vote"
    assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), contracts.csm.address), "CSM should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"
    assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), CSM_COMMITTEE_MS), "CSM committee should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"

    # CSM Steps 39-40: CSM roles (pre-vote state)
    assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), contracts.cs_permissionless_gate.address), "Permissionless gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"
    assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), contracts.cs_vetted_gate.address), "Vetted gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"

    # CSM Step 41: CSAccounting bond curve role for vetted gate (pre-vote state)
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should not have SET_BOND_CURVE_ROLE on CSAccounting before vote"

    # CSM Steps 42-43: Verifier roles (pre-vote state)
    assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier.address), "Old verifier should have VERIFIER_ROLE on CSM before vote"
    assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier_v2.address), "New verifier should not have VERIFIER_ROLE on CSM before vote"

    # CSM Steps 44-49: GateSeal roles (pre-vote state)
    assert contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSM before vote"
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSAccounting before vote"
    assert contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSFeeOracle before vote"

    assert not contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSM before vote"
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSAccounting before vote"
    assert not contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSFeeOracle before vote"

    # CSM Step 50: Staking Router CSM module state before vote (pre-vote state)
    csm_module_before = contracts.staking_router.getStakingModule(CS_MODULE_ID)
    csm_share_before = csm_module_before['stakeShareLimit']
    csm_priority_exit_threshold_before = csm_module_before['priorityExitShareThreshold']
    assert csm_share_before != CS_MODULE_NEW_TARGET_SHARE_BP, f"CSM share should not be {CS_MODULE_NEW_TARGET_SHARE_BP} before vote, current: {csm_share_before}"
    assert csm_priority_exit_threshold_before != CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, f"CSM priority exit threshold should not be {CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP} before vote, current: {csm_priority_exit_threshold_before}"

    # CSM Step 51: EasyTrack factories before vote (pre-vote state)
    initial_factories = contracts.easy_track.getEVMScriptFactories()
    assert CSM_SET_VETTED_GATE_TREE_FACTORY not in initial_factories, "EasyTrack should not have CSMSetVettedGateTree factory before vote"

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id = create_tw_vote(tx_params, silent=True)

    print(f"voteId = {vote_id}")

    # --- VALIDATE EXECUTION RESULTS ---

    # 1. Validate Lido Locator implementation was updated
    assert interface.OssifiableProxy(contracts.lido_locator).proxy__getImplementation() == LIDO_LOCATOR_IMPL

    # 2-3. Validate VEBO implementation was updated and configured
    assert interface.OssifiableProxy(contracts.validators_exit_bus_oracle).proxy__getImplementation() == VALIDATORS_EXIT_BUS_ORACLE_IMPL
    assert contracts.validators_exit_bus_oracle.getMaxValidatorsPerReport() == 600

    # Validate exit request limit parameters using the correct getter method
    exit_request_limits = contracts.validators_exit_bus_oracle.getExitRequestLimitFullInfo()
    assert exit_request_limits[0] == 13000, "maxExitRequestsLimit should be 13000"
    assert exit_request_limits[1] == 1, "exitsPerFrame should be 1"
    assert exit_request_limits[2] == 48, "frameDurationInSec should be 48 hours in seconds"

    # 4-5. Validate VEBO consensus version management
    assert contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent)
    assert contracts.validators_exit_bus_oracle.getConsensusVersion() == vebo_consensus_version

    # # 7-8. Validate TWG roles
    assert contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.cs_ejector)
    assert contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle)

    # # 9-10. Validate Withdrawal Vault upgrade
    assert interface.WithdrawalContractProxy(contracts.withdrawal_vault).implementation() == WITHDRAWAL_VAULT_IMPL
    # Validate finalizeUpgrade_v2() was called (check version or new functionality)
    assert contracts.withdrawal_vault.getContractVersion() == 2, "Withdrawal Vault finalization check failed"

    # # 11-13. Validate Accounting Oracle upgrade
    assert interface.OssifiableProxy(contracts.accounting_oracle).proxy__getImplementation() == ACCOUNTING_ORACLE_IMPL
    assert contracts.accounting_oracle.hasRole(contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent)
    assert contracts.accounting_oracle.getConsensusVersion() == ao_consensus_version

    # # 14-16. Validate Staking Router upgrade
    assert interface.OssifiableProxy(contracts.staking_router).proxy__getImplementation() == STAKING_ROUTER_IMPL
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE(), contracts.validator_exit_verifier)
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE(), contracts.triggerable_withdrawals_gateway)

    # # Check NOR and sDVT updates

    assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel, app_manager_role)

    assert contracts.node_operators_registry.getContractVersion() == 4
    assert contracts.simple_dvt.getContractVersion() == 4

    assert contracts.node_operators_registry.exitDeadlineThreshold(0) == nor_exit_deadline_in_sec
    assert contracts.simple_dvt.exitDeadlineThreshold(0) == nor_exit_deadline_in_sec

    # 23-27. Validate Oracle Daemon Config changes
    assert contracts.oracle_daemon_config.hasRole(config_manager_role, contracts.agent)
    # Check that variables were removed
    for var_name in ['NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP', 'VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS', 'VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS']:
        try:
            contracts.oracle_daemon_config.get(var_name)
            assert False, f"Variable {var_name} should have been removed"
        except Exception:
            pass  # Expected to fail - variable should be removed
    # Check new variable was added
    assert convert.to_uint(contracts.oracle_daemon_config.get('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')) == exit_events_lookback_window_in_slots

    # CSM Step 28: Check CSM implementation upgrade
    check_proxy_implementation(contracts.csm.address, CSM_IMPL_V2_ADDRESS)

    # CSM Step 29: Check CSM finalizeUpgradeV2 was called
    assert contracts.csm.getInitializedVersion() == CSM_V2_VERSION, f"CSM version should be {CSM_V2_VERSION} after vote"

    # CSM Step 30: Check CSAccounting implementation upgrade
    check_proxy_implementation(contracts.cs_accounting.address, CS_ACCOUNTING_IMPL_V2_ADDRESS)

    # CSM Step 31: Check CSAccounting finalizeUpgradeV2 was called with bond curves
    assert contracts.cs_accounting.getInitializedVersion() == CS_ACCOUNTING_V2_VERSION, f"CSAccounting version should be {CS_ACCOUNTING_V2_VERSION} after vote"

    # CSM Step 32: Check CSFeeOracle implementation upgrade
    check_proxy_implementation(contracts.cs_fee_oracle.address, CS_FEE_ORACLE_IMPL_V2_ADDRESS)

    # CSM Step 33: Check CSFeeOracle finalizeUpgradeV2 was called with consensus version 3
    assert contracts.cs_fee_oracle.getContractVersion() == CS_FEE_ORACLE_V2_VERSION, f"CSFeeOracle version should be {CS_FEE_ORACLE_V2_VERSION} after vote"
    assert contracts.cs_fee_oracle.getConsensusVersion() == 3, "CSFeeOracle consensus version should be 3 after vote"

    # CSM Step 34: Check CSFeeDistributor implementation upgrade
    check_proxy_implementation(contracts.cs_fee_distributor.address, CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS)

    # CSM Step 35: Check CSFeeDistributor finalizeUpgradeV2 was called
    assert contracts.cs_fee_distributor.getInitializedVersion() == CS_FEE_DISTRIBUTOR_V2_VERSION, f"CSFeeDistributor version should be {CS_FEE_DISTRIBUTOR_V2_VERSION} after vote"

    # CSM Step 36: Revoke SET_BOND_CURVE_ROLE from CSM on CSAccounting
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.csm.address), "CSM should not have SET_BOND_CURVE_ROLE on CSAccounting after vote"

    # CSM Step 37: Revoke RESET_BOND_CURVE_ROLE from CSM on CSAccounting
    assert not contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), contracts.csm.address), "CSM should not have RESET_BOND_CURVE_ROLE on CSAccounting after vote"

    # CSM Step 38: Revoke RESET_BOND_CURVE_ROLE from CSM committee on CSAccounting
    assert not contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), CSM_COMMITTEE_MS), "CSM committee should not have RESET_BOND_CURVE_ROLE on CSAccounting after vote"

    # CSM Step 39: Grant CREATE_NODE_OPERATOR_ROLE to permissionless gate on CSM
    assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(), contracts.cs_permissionless_gate.address), "Permissionless gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

    # CSM Step 40: Grant CREATE_NODE_OPERATOR_ROLE to vetted gate on CSM
    assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

    # CSM Step 41: Grant SET_BOND_CURVE_ROLE to vetted gate on CSAccounting
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should have SET_BOND_CURVE_ROLE on CSAccounting after vote"

    # CSM Step 42: Revoke VERIFIER_ROLE from old verifier on CSM
    assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier.address), "Old verifier should not have VERIFIER_ROLE on CSM after vote"

    # CSM Step 43: Grant VERIFIER_ROLE to new verifier on CSM
    assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier_v2.address), "New verifier should have VERIFIER_ROLE on CSM after vote"

    # CSM Step 44: Revoke PAUSE_ROLE from old GateSeal on CSM
    assert not contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSM after vote"

    # CSM Step 45: Revoke PAUSE_ROLE from old GateSeal on CSAccounting
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSAccounting after vote"

    # CSM Step 46: Revoke PAUSE_ROLE from old GateSeal on CSFeeOracle
    assert not contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSFeeOracle after vote"

    # CSM Step 47: Grant PAUSE_ROLE to new GateSeal on CSM
    assert contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSM after vote"

    # CSM Step 48: Grant PAUSE_ROLE to new GateSeal on CSAccounting
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSAccounting after vote"

    # CSM Step 49: Grant PAUSE_ROLE to new GateSeal on CSFeeOracle
    assert contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSFeeOracle after vote"

    # CSM Step 50: Increase CSM share in Staking Router
    csm_module_after = contracts.staking_router.getStakingModule(CS_MODULE_ID)
    csm_share_after = csm_module_after['stakeShareLimit']
    assert csm_share_after == CS_MODULE_NEW_TARGET_SHARE_BP, f"CSM share should be {CS_MODULE_NEW_TARGET_SHARE_BP} after vote, but got {csm_share_after}"

    csm_priority_exit_threshold_after = csm_module_after['priorityExitShareThreshold']
    assert csm_priority_exit_threshold_after == CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, f"CSM priority exit threshold should be {CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP} after vote, but got {csm_priority_exit_threshold_after}"

    # CSM Step 51: Add EasyTrack factory for CSMSetVettedGateTree
    new_factories = contracts.easy_track.getEVMScriptFactories()
    assert CSM_SET_VETTED_GATE_TREE_FACTORY in new_factories, "EasyTrack should have CSMSetVettedGateTree factory after vote"
