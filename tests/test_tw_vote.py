"""
Tests for triggerable withdrawals voting.
"""

from typing import Dict, Tuple, List, NamedTuple
from scripts.tw_vote import create_tw_vote
from brownie import interface, convert, web3, ZERO_ADDRESS
from utils.test.tx_tracing_helpers import *
from utils.config import (
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    WITHDRAWAL_VAULT_IMPL,
    LIDO_LOCATOR_IMPL,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    CSM_MODULE_ID,
    CS_ACCOUNTING_IMPL_V2_ADDRESS,
    CS_CURVES,
    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
    CS_FEE_ORACLE_IMPL_V2_ADDRESS,
    CS_GATE_SEAL_ADDRESS,
    CS_GATE_SEAL_V2_ADDRESS,
    CSM_COMMITTEE_MS,
    CSM_IMPL_V2_ADDRESS,
    CSM_SET_VETTED_GATE_TREE_FACTORY,
    contracts,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


# CSM share constants
CSM_NEW_TARGET_SHARE_BP = 300  # 3%
CSM_NEW_PRIORITY_EXIT_THRESHOLD_BP = 375  # 3.75%

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

    csm_impl_before = get_ossifiable_proxy_impl(contracts.csm.address)
    cs_accounting_impl_before = get_ossifiable_proxy_impl(contracts.cs_accounting.address)
    cs_fee_oracle_impl_before = get_ossifiable_proxy_impl(contracts.cs_fee_oracle.address)
    cs_fee_distributor_impl_before = get_ossifiable_proxy_impl(contracts.cs_fee_distributor.address)

    # --- Initial state checks ---

    # Assert VEBO implementation and configuration
    initial_vebo_consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    assert initial_vebo_consensus_version < vebo_consensus_version

    # Assert Accounting Oracle implementation and configuration
    initial_ao_consensus_version = contracts.accounting_oracle.getConsensusVersion()
    assert initial_ao_consensus_version < ao_consensus_version


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

     # CSAccounting roles
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.csm.address), "CSM should have SET_BOND_CURVE_ROLE on CSAccounting before vote"
    assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), contracts.csm.address), "CSM should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"
    assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), CSM_COMMITTEE_MS), "CSM committee should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"

    # CSM roles
    assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), contracts.cs_permissionless_gate.address), "Permissionless gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"
    assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), contracts.cs_vetted_gate.address), "Vetted gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"
    assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier.address), "Old verifier should have VERIFIER_ROLE on CSM before vote"
    assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier_v2.address), "New verifier should not have VERIFIER_ROLE on CSM before vote"

    # CSAccounting bond curve role for vetted gate
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should not have SET_BOND_CURVE_ROLE on CSAccounting before vote"
    
    # GateSeal roles
    assert contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSM before vote"
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSAccounting before vote"
    assert contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSFeeOracle before vote"

    assert not contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSM before vote"
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSAccounting before vote"
    assert not contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSFeeOracle before vote"

    # Staking Router CSM module state before vote
    csm_module_before = contracts.staking_router.getStakingModule(CSM_MODULE_ID)
    csm_share_before = csm_module_before['stakeShareLimit']
    assert csm_share_before != CSM_NEW_TARGET_SHARE_BP, f"CSM share should not be {CSM_NEW_TARGET_SHARE_BP} before vote, current: {csm_share_before}"
    
    # Check that implementations are different from target ones
    assert csm_impl_before != CSM_IMPL_V2_ADDRESS, "CSM implementation should be different before vote"
    assert cs_accounting_impl_before != CS_ACCOUNTING_IMPL_V2_ADDRESS, "CSAccounting implementation should be different before vote"
    assert cs_fee_oracle_impl_before != CS_FEE_ORACLE_IMPL_V2_ADDRESS, "CSFeeOracle implementation should be different before vote"
    assert cs_fee_distributor_impl_before != CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS, "CSFeeDistributor implementation should be different before vote"

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

    # # 4-5. Validate VEBO consensus version management
    assert contracts.validators_exit_bus_oracle.getConsensusVersion() == vebo_consensus_version

    # # 7-8. Validate TWG roles
    assert contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.cs_ejector)
    assert contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle)

    # # 9-10. Validate Withdrawal Vault upgrade
    assert interface.WithdrawalContractProxy(contracts.withdrawal_vault).implementation() == WITHDRAWAL_VAULT_IMPL

    # # 11-13. Validate Accounting Oracle upgrade
    assert contracts.accounting_oracle.getConsensusVersion() == ao_consensus_version

    # # 14-16. Validate Staking Router upgrade
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE(), contracts.validator_exit_verifier)
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE(), contracts.triggerable_withdrawals_gateway)

    # # Check NOR and sDVT updates

    assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel, app_manager_role)

    assert contracts.node_operators_registry.getContractVersion() == 4
    assert contracts.simple_dvt.getContractVersion() == 4

    assert contracts.node_operators_registry.exitDeadlineThreshold(0) == nor_exit_deadline_in_sec
    assert contracts.simple_dvt.exitDeadlineThreshold(0) == nor_exit_deadline_in_sec

    # 23-27. Validate Oracle Daemon Config changes
    assert convert.to_uint(contracts.oracle_daemon_config.get('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')) == exit_events_lookback_window_in_slots

    # Check implementations are upgraded
    check_proxy_implementation(contracts.csm.address, CSM_IMPL_V2_ADDRESS)
    check_proxy_implementation(contracts.cs_accounting.address, CS_ACCOUNTING_IMPL_V2_ADDRESS)
    check_proxy_implementation(contracts.cs_fee_oracle.address, CS_FEE_ORACLE_IMPL_V2_ADDRESS)
    check_proxy_implementation(contracts.cs_fee_distributor.address, CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS)

    # Check contract versions are updated (finalizeUpgradeV2 was called)
    assert contracts.csm.getInitializedVersion() == CSM_V2_VERSION, f"CSM version should be {CSM_V2_VERSION} after vote"
    assert contracts.cs_accounting.getInitializedVersion() == CS_ACCOUNTING_V2_VERSION, f"CSAccounting version should be {CS_ACCOUNTING_V2_VERSION} after vote"
    assert contracts.cs_fee_oracle.getContractVersion() == CS_FEE_ORACLE_V2_VERSION, f"CSFeeOracle version should be {CS_FEE_ORACLE_V2_VERSION} after vote"
    assert contracts.cs_fee_distributor.getInitializedVersion() == CS_FEE_DISTRIBUTOR_V2_VERSION, f"CSFeeDistributor version should be {CS_FEE_DISTRIBUTOR_V2_VERSION} after vote"

    # Check CSAccounting finalizeUpgradeV2 was called with bond curves
    # This is verified by checking that the contract version was updated
    
    # Check CSFeeOracle finalizeUpgradeV2 was called with consensus version 3
    assert contracts.cs_fee_oracle.getConsensusVersion() == 3, "CSFeeOracle consensus version should be 3 after vote"

    # Check role changes
    
    # CSAccounting roles revoked from CSM
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.csm.address), "CSM should not have SET_BOND_CURVE_ROLE on CSAccounting after vote"
    assert not contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), contracts.csm.address), "CSM should not have RESET_BOND_CURVE_ROLE on CSAccounting after vote"
    assert not contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), CSM_COMMITTEE_MS), "CSM committee should not have RESET_BOND_CURVE_ROLE on CSAccounting after vote"

    # CSM roles granted to gates
    assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(), contracts.cs_permissionless_gate.address), "Permissionless gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"
    assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

    # CSAccounting bond curve role granted to vetted gate
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should have SET_BOND_CURVE_ROLE on CSAccounting after vote"

    # Verifier role changes
    assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier.address), "Old verifier should not have VERIFIER_ROLE on CSM after vote"
    assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier_v2.address), "New verifier should have VERIFIER_ROLE on CSM after vote"

    # GateSeal role changes
    assert not contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSM after vote"
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSAccounting after vote"
    assert not contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSFeeOracle after vote"

    assert contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSM after vote"
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSAccounting after vote"
    assert contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSFeeOracle after vote"

    # Check CSM share increase in Staking Router
    csm_module_after = contracts.staking_router.getStakingModule(CSM_MODULE_ID)
    csm_share_after = csm_module_after['stakeShareLimit']
    assert csm_share_after == CSM_NEW_TARGET_SHARE_BP, f"CSM share should be {CSM_NEW_TARGET_SHARE_BP} after vote, but got {csm_share_after}"

    csm_priority_exit_threshold_after = csm_module_after['priorityExitShareThreshold']
    assert csm_priority_exit_threshold_after == CSM_NEW_PRIORITY_EXIT_THRESHOLD_BP, f"CSM priority exit threshold should be {CSM_NEW_PRIORITY_EXIT_THRESHOLD_BP} after vote, but got {csm_priority_exit_threshold_after}"

    # Check EasyTrack factory addition
    new_factories = contracts.easy_track.getEVMScriptFactories()
    assert CSM_SET_VETTED_GATE_TREE_FACTORY in new_factories, "EasyTrack should have CSMSetVettedGateTree factory after vote"
