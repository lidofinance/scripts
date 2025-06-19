"""
Tests for triggerable withdrawals voting.
"""

from scripts.vote_tw_csm2 import create_tw_vote
from brownie import interface, chain, convert, web3, ZERO_ADDRESS
from utils.test.tx_tracing_helpers import group_voting_events_from_receipt, group_dg_events_from_receipt
from utils.dual_governance import wait_for_noon_utc_to_satisfy_time_constrains
from utils.config import (
    DUAL_GOVERNANCE,
    TIMELOCK,
    DUAL_GOVERNANCE_ADMIN_EXECUTOR,
    CS_CURVES,
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
    CS_SET_VETTED_GATE_TREE_FACTORY,
    ACCOUNTING_ORACLE_IMPL,
    STAKING_ROUTER_IMPL,
    ARAGON_KERNEL,
    AGENT,
    VOTING,
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


def get_wv_contract_proxy_impl(proxy_address):
    """Get implementation address from an WithdrawalContractProxy"""
    proxy = interface.WithdrawalContractProxy(proxy_address)
    return proxy.implementation()


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
    locator_impl_before = get_ossifiable_proxy_impl(contracts.lido_locator)
    accounting_oracle_impl_before = get_ossifiable_proxy_impl(contracts.accounting_oracle)
    vebo_impl_before = get_ossifiable_proxy_impl(contracts.validators_exit_bus_oracle)
    withdrawal_vault_impl_before = get_wv_contract_proxy_impl(contracts.withdrawal_vault)
    staking_router_impl_before = get_ossifiable_proxy_impl(contracts.staking_router)

    csm_impl_before = get_ossifiable_proxy_impl(contracts.csm.address)
    cs_accounting_impl_before = get_ossifiable_proxy_impl(contracts.cs_accounting.address)
    cs_fee_oracle_impl_before = get_ossifiable_proxy_impl(contracts.cs_fee_oracle.address)
    cs_fee_distributor_impl_before = get_ossifiable_proxy_impl(contracts.cs_fee_distributor.address)

    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

    # --- Initial state checks ---

    # Step 1: Check Lido Locator implementation initial state
    assert locator_impl_before != LIDO_LOCATOR_IMPL, "Locator implementation should be different before upgrade"

    # Step 2: Check VEBO implementation initial state
    assert vebo_impl_before != VALIDATORS_EXIT_BUS_ORACLE_IMPL, "VEBO implementation should be different before upgrade"

    # Step 3: Check VEBO finalizeUpgrade_v2 state
    try:
        assert contracts.validators_exit_bus_oracle.getMaxValidatorsPerReport() != 600, "VEBO max validators per report should not be 600 before upgrade"
    except Exception:
        pass  # Function might not exist yet

    # Steps 4-6: Check VEBO consensus version management
    initial_vebo_consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    assert initial_vebo_consensus_version < vebo_consensus_version, f"VEBO consensus version should be less than {vebo_consensus_version}"

    # Step 7: Check TWG role for CS Ejector initial state
    add_full_withdrawal_request_role = contracts.triggerable_withdrawals_gateway.ADD_FULL_WITHDRAWAL_REQUEST_ROLE()
    assert not contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.cs_ejector), "CS Ejector should not have ADD_FULL_WITHDRAWAL_REQUEST_ROLE before upgrade"

    # Step 8: Check TWG role for VEB initial state
    assert not contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle), "VEBO should not have ADD_FULL_WITHDRAWAL_REQUEST_ROLE before upgrade"

    # Step 9: Check Withdrawal Vault implementation initial state
    assert withdrawal_vault_impl_before != WITHDRAWAL_VAULT_IMPL, "Withdrawal Vault implementation should be different before upgrade"

    # Step 10: Withdrawal Vault finalizeUpgrade_v2 check is done post-execution
    assert contracts.withdrawal_vault.getContractVersion()  == 1, "Withdrawal Vault version should be 1 before upgrade"

    # Step 11: Check Accounting Oracle implementation initial state
    assert accounting_oracle_impl_before != ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be different before upgrade"

    # Steps 12-14: Check AO consensus version management
    initial_ao_consensus_version = contracts.accounting_oracle.getConsensusVersion()
    assert initial_ao_consensus_version < ao_consensus_version, f"AO consensus version should be less than {ao_consensus_version}"
    assert not contracts.accounting_oracle.hasRole(contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent), "Agent should not have MANAGE_CONSENSUS_VERSION_ROLE on AO before upgrade"

    # Step 15: Check Staking Router implementation initial state
    assert staking_router_impl_before != STAKING_ROUTER_IMPL, "Staking Router implementation should be different before upgrade"

    # Steps 16-17: Check SR roles initial state
    try:
        report_validator_exiting_status_role = contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE()
        report_validator_exit_triggered_role = contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE()
    except Exception as e:
        assert "Unknown typed error: 0x" in str(e), f"Unexpected error: {e}"
        report_validator_exiting_status_role = ZERO_ADDRESS
        report_validator_exit_triggered_role = ZERO_ADDRESS

    assert report_validator_exiting_status_role == ZERO_ADDRESS, "REPORT_VALIDATOR_EXITING_STATUS_ROLE should not exist before upgrade"
    assert report_validator_exit_triggered_role == ZERO_ADDRESS, "REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE should not exist before upgrade"

    # Step 18: Check APP_MANAGER_ROLE initial state
    app_manager_role = web3.keccak(text="APP_MANAGER_ROLE")
    assert contracts.acl.getPermissionManager(ARAGON_KERNEL, app_manager_role) == AGENT, "AGENT should be the permission manager for APP_MANAGER_ROLE"
    assert contracts.node_operators_registry.kernel() == ARAGON_KERNEL, "Node Operators Registry must use the correct kernel"
    assert not contracts.acl.hasPermission(VOTING, ARAGON_KERNEL, app_manager_role), "VOTING should not have APP_MANAGER_ROLE before the upgrade"
    assert not contracts.acl.hasPermission(AGENT, ARAGON_KERNEL, app_manager_role), "AGENT should not have APP_MANAGER_ROLE before the upgrade"

    # Steps 19-23: Check NOR and sDVT initial state
    assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel, app_manager_role), "Agent should not have APP_MANAGER_ROLE before upgrade"
    assert contracts.node_operators_registry.getContractVersion() == 3, "Node Operators Registry version should be 3 before upgrade"
    assert contracts.simple_dvt.getContractVersion() == 3, "Simple DVT version should be 3 before upgrade"

    # Step 24: Check CONFIG_MANAGER_ROLE initial state
    config_manager_role = contracts.oracle_daemon_config.CONFIG_MANAGER_ROLE()
    assert not contracts.oracle_daemon_config.hasRole(config_manager_role, contracts.agent), "Agent should not have CONFIG_MANAGER_ROLE on Oracle Daemon Config before upgrade"

    # Steps 25-27: Check Oracle Daemon Config variables to be removed
    try:
        contracts.oracle_daemon_config.get('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP')
        contracts.oracle_daemon_config.get('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS')
        contracts.oracle_daemon_config.get('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS')
    except Exception as e:
        assert False, f"Expected variables to exist before removal: {e}"

    # Step 28: Check that EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS doesn't exist yet
    try:
        contracts.oracle_daemon_config.get('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')
        assert False, "EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS should not exist before vote"
    except Exception:
        pass  # Expected to fail

    # Step 29: Check CSM implementation initial state
    assert csm_impl_before != CSM_IMPL_V2_ADDRESS, "CSM implementation should be different before vote"

    # Step 30: Check CSM finalizeUpgradeV2 initial state
    try:
        version = contracts.csm.getInitializedVersion()
        assert version < CSM_V2_VERSION, f"CSM version should be less than {CSM_V2_VERSION} before vote"
    except Exception:
        pass  # Function might not exist yet

    # CSM Step 32: Check CSAccounting implementation (pre-vote state)
    assert cs_accounting_impl_before != CS_ACCOUNTING_IMPL_V2_ADDRESS, "CSAccounting implementation should be different before vote"

    # CSM Step 33: Check CSAccounting finalizeUpgradeV2 was not called (pre-vote state)
    # assert contracts.cs_accounting.getInitializedVersion() < CS_ACCOUNTING_V2_VERSION, f"CSAccounting version should be less than {CS_ACCOUNTING_V2_VERSION} before vote"

    # CSM Step 34: Check CSFeeOracle implementation (pre-vote state)
    assert cs_fee_oracle_impl_before != CS_FEE_ORACLE_IMPL_V2_ADDRESS, "CSFeeOracle implementation should be different before vote"

    # CSM Step 35: Check CSFeeOracle finalizeUpgradeV2 was not called (pre-vote state)
    assert contracts.cs_fee_oracle.getContractVersion() < CS_FEE_ORACLE_V2_VERSION, f"CSFeeOracle version should be less than {CS_FEE_ORACLE_V2_VERSION} before vote"
    assert contracts.cs_fee_oracle.getConsensusVersion() < 3, "CSFeeOracle consensus version should be less than 3 before vote"

    # CSM Step 36: Check CSFeeDistributor implementation (pre-vote state)
    assert cs_fee_distributor_impl_before != CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS, "CSFeeDistributor implementation should be different before vote"

    # CSM Step 37: Check CSFeeDistributor finalizeUpgradeV2 was not called (pre-vote state)
    # assert contracts.cs_fee_distributor.getInitializedVersion() < CS_FEE_DISTRIBUTOR_V2_VERSION, f"CSFeeDistributor version should be less than {CS_FEE_DISTRIBUTOR_V2_VERSION} before vote"

    # CSM Steps 38-40: CSAccounting roles (pre-vote state)
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.csm.address), "CSM should have SET_BOND_CURVE_ROLE on CSAccounting before vote"
    assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), contracts.csm.address), "CSM should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"
    assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), CSM_COMMITTEE_MS), "CSM committee should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"

    # CSM Steps 41-42: CSM roles (pre-vote state)
    assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), contracts.cs_permissionless_gate.address), "Permissionless gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"
    assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), contracts.cs_vetted_gate.address), "Vetted gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"

    # CSM Step 43: CSAccounting bond curve role for vetted gate (pre-vote state)
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should not have SET_BOND_CURVE_ROLE on CSAccounting before vote"

    # CSM Steps 44-45: Verifier roles (pre-vote state)
    assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier.address), "Old verifier should have VERIFIER_ROLE on CSM before vote"
    assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier_v2.address), "New verifier should not have VERIFIER_ROLE on CSM before vote"

    # CSM Steps 46-51: GateSeal roles (pre-vote state)
    assert contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSM before vote"
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSAccounting before vote"
    assert contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSFeeOracle before vote"

    assert not contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSM before vote"
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSAccounting before vote"
    assert not contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSFeeOracle before vote"

    # CSM Step 52: Staking Router CSM module state before vote (pre-vote state)
    csm_module_before = contracts.staking_router.getStakingModule(CS_MODULE_ID)
    csm_share_before = csm_module_before['stakeShareLimit']
    csm_priority_exit_threshold_before = csm_module_before['priorityExitShareThreshold']
    assert csm_share_before != CS_MODULE_NEW_TARGET_SHARE_BP, f"CSM share should not be {CS_MODULE_NEW_TARGET_SHARE_BP} before vote, current: {csm_share_before}"
    assert csm_priority_exit_threshold_before != CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, f"CSM priority exit threshold should not be {CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP} before vote, current: {csm_priority_exit_threshold_before}"

    # CSM Step 53: EasyTrack factories before vote (pre-vote state)
    initial_factories = contracts.easy_track.getEVMScriptFactories()
    assert CS_SET_VETTED_GATE_TREE_FACTORY not in initial_factories, "EasyTrack should not have CSMSetVettedGateTree factory before vote"

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = create_tw_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}")

    proposal_id = vote_tx.events["ProposalSubmitted"][1]["proposalId"]
    print(f"proposalId = {proposal_id}")

    chain.sleep(timelock.getAfterSubmitDelay() + 1)
    dual_governance.scheduleProposal(proposal_id, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)
    wait_for_noon_utc_to_satisfy_time_constrains()

    dg_tx = timelock.execute(proposal_id, {"from": stranger})

    voting_events = group_voting_events_from_receipt(vote_tx)
    dg_events = group_dg_events_from_receipt(dg_tx, timelock=TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR)

    # --- VALIDATE EXECUTION RESULTS ---

    # Step 1: Validate Lido Locator implementation was updated
    assert get_ossifiable_proxy_impl(contracts.lido_locator) == LIDO_LOCATOR_IMPL, "Locator implementation should be updated to the new value"

    # Step 2-3: Validate VEBO implementation was updated and configured
    assert get_ossifiable_proxy_impl(contracts.validators_exit_bus_oracle) == VALIDATORS_EXIT_BUS_ORACLE_IMPL, "VEBO implementation should be updated"
    assert contracts.validators_exit_bus_oracle.getMaxValidatorsPerReport() == 600, "VEBO max validators per report should be set to 600"

    # Validate exit request limit parameters from finalizeUpgrade_v2 call
    exit_request_limits = contracts.validators_exit_bus_oracle.getExitRequestLimitFullInfo()
    assert exit_request_limits[0] == 13000, "maxExitRequestsLimit should be 13000"
    assert exit_request_limits[1] == 1, "exitsPerFrame should be 1"
    assert exit_request_limits[2] == 48, "frameDurationInSec should be 48 hours in seconds"

    # Steps 4-6: Validate VEBO consensus version management
    assert not contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent), "Agent should not have MANAGE_CONSENSUS_VERSION_ROLE on VEBO"
    assert contracts.validators_exit_bus_oracle.getConsensusVersion() == vebo_consensus_version, f"VEBO consensus version should be set to {vebo_consensus_version}"

    # Steps 7-8: Validate TWG roles
    assert contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.cs_ejector), "CS Ejector should have ADD_FULL_WITHDRAWAL_REQUEST_ROLE on TWG"
    assert contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle), "VEBO should have ADD_FULL_WITHDRAWAL_REQUEST_ROLE on TWG"

    # Steps 9-10: Validate Withdrawal Vault upgrade
    assert get_wv_contract_proxy_impl(contracts.withdrawal_vault) == WITHDRAWAL_VAULT_IMPL, "Withdrawal Vault implementation should be updated"
    assert contracts.withdrawal_vault.getContractVersion() == 2, "Withdrawal Vault version should be 2 after finalizeUpgrade_v2"

    # Steps 11-14: Validate Accounting Oracle upgrade
    assert get_ossifiable_proxy_impl(contracts.accounting_oracle) == ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be updated"
    assert not contracts.accounting_oracle.hasRole(contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent), "Agent should not have MANAGE_CONSENSUS_VERSION_ROLE on AO"
    assert contracts.accounting_oracle.getConsensusVersion() == ao_consensus_version, f"AO consensus version should be set to {ao_consensus_version}"

    # Steps 15-17: Validate Staking Router upgrade
    assert get_ossifiable_proxy_impl(contracts.staking_router) == STAKING_ROUTER_IMPL, "Staking Router implementation should be updated"
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE(), contracts.validator_exit_verifier), "ValidatorExitVerifier should have REPORT_VALIDATOR_EXITING_STATUS_ROLE on SR"
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE(), contracts.triggerable_withdrawals_gateway), "TWG should have REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE on SR"

    # Steps 18-23: Validate NOR and sDVT updates
    assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel, app_manager_role), "Agent should not have APP_MANAGER_ROLE after vote"
    assert contracts.node_operators_registry.getContractVersion() == 4, "Node Operators Registry version should be updated to 4"
    assert contracts.simple_dvt.getContractVersion() == 4, "Simple DVT version should be updated to 4"
    assert contracts.node_operators_registry.exitDeadlineThreshold(0) == nor_exit_deadline_in_sec, "NOR exit deadline threshold should be set correctly"
    assert contracts.simple_dvt.exitDeadlineThreshold(0) == nor_exit_deadline_in_sec, "sDVT exit deadline threshold should be set correctly"

    # Steps 24-28: Validate Oracle Daemon Config changes
    assert contracts.oracle_daemon_config.hasRole(config_manager_role, contracts.agent), "Agent should have CONFIG_MANAGER_ROLE on Oracle Daemon Config"

    # Check that variables were removed
    for var_name in ['NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP', 'VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS', 'VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS']:
        try:
            contracts.oracle_daemon_config.get(var_name)
            assert False, f"Variable {var_name} should have been removed"
        except Exception:
            pass  # Expected to fail - variable should be removed

    # Check new variable was added
    assert convert.to_uint(contracts.oracle_daemon_config.get('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')) == exit_events_lookback_window_in_slots, f"EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS should be set to {exit_events_lookback_window_in_slots}"

    # Step 29: Validate CSM implementation upgrade
    check_proxy_implementation(contracts.csm.address, CSM_IMPL_V2_ADDRESS)

    # Step 30: Validate CSM finalizeUpgradeV2 was called
    assert contracts.csm.getInitializedVersion() == CSM_V2_VERSION, f"CSM version should be {CSM_V2_VERSION} after vote"

    # Step 31: Validate CSAccounting implementation upgrade
    check_proxy_implementation(contracts.cs_accounting.address, CS_ACCOUNTING_IMPL_V2_ADDRESS)

    # Step 32: Validate CSAccounting finalizeUpgradeV2 was called with bond curves
    assert contracts.cs_accounting.getInitializedVersion() == CS_ACCOUNTING_V2_VERSION, f"CSAccounting version should be {CS_ACCOUNTING_V2_VERSION} after vote"

    # Step 33: Validate CSFeeOracle implementation upgrade
    check_proxy_implementation(contracts.cs_fee_oracle.address, CS_FEE_ORACLE_IMPL_V2_ADDRESS)

    # Step 34: Validate CSFeeOracle finalizeUpgradeV2 was called with consensus version 3
    assert contracts.cs_fee_oracle.getContractVersion() == CS_FEE_ORACLE_V2_VERSION, f"CSFeeOracle version should be {CS_FEE_ORACLE_V2_VERSION} after vote"
    assert contracts.cs_fee_oracle.getConsensusVersion() == 3, "CSFeeOracle consensus version should be 3 after vote"

    # Step 35: Validate CSFeeDistributor implementation upgrade
    check_proxy_implementation(contracts.cs_fee_distributor.address, CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS)

    # Step 36: Validate CSFeeDistributor finalizeUpgradeV2 was called
    assert contracts.cs_fee_distributor.getInitializedVersion() == CS_FEE_DISTRIBUTOR_V2_VERSION, f"CSFeeDistributor version should be {CS_FEE_DISTRIBUTOR_V2_VERSION} after vote"

    # Step 37: Validate SET_BOND_CURVE_ROLE was revoked from CSM on CSAccounting
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.csm.address), "CSM should not have SET_BOND_CURVE_ROLE on CSAccounting after vote"

    # Step 38: Validate RESET_BOND_CURVE_ROLE was revoked from CSM on CSAccounting
    assert not contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), contracts.csm.address), "CSM should not have RESET_BOND_CURVE_ROLE on CSAccounting after vote"

    # Step 39: Validate RESET_BOND_CURVE_ROLE was revoked from CSM committee on CSAccounting
    assert not contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), CSM_COMMITTEE_MS), "CSM committee should not have RESET_BOND_CURVE_ROLE on CSAccounting after vote"

    # Step 40: Validate CREATE_NODE_OPERATOR_ROLE was granted to permissionless gate on CSM
    assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(), contracts.cs_permissionless_gate.address), "Permissionless gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

    # Step 41: Validate CREATE_NODE_OPERATOR_ROLE was granted to vetted gate on CSM
    assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

    # Step 42: Validate SET_BOND_CURVE_ROLE was granted to vetted gate on CSAccounting
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.cs_vetted_gate.address), "Vetted gate should have SET_BOND_CURVE_ROLE on CSAccounting after vote"

    # Step 43: Validate VERIFIER_ROLE was revoked from old verifier on CSM
    assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier.address), "Old verifier should not have VERIFIER_ROLE on CSM after vote"

    # Step 44: Validate VERIFIER_ROLE was granted to new verifier on CSM
    assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier_v2.address), "New verifier should have VERIFIER_ROLE on CSM after vote"

    # Step 45: Validate PAUSE_ROLE was revoked from old GateSeal on CSM
    assert not contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSM after vote"

    # Step 46: Validate PAUSE_ROLE was revoked from old GateSeal on CSAccounting
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSAccounting after vote"

    # Step 47: Validate PAUSE_ROLE was revoked from old GateSeal on CSFeeOracle
    assert not contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSFeeOracle after vote"

    # Step 48: Validate PAUSE_ROLE was granted to new GateSeal on CSM
    assert contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSM after vote"

    # Step 49: Validate PAUSE_ROLE was granted to new GateSeal on CSAccounting
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSAccounting after vote"

    # Step 50: Validate PAUSE_ROLE was granted to new GateSeal on CSFeeOracle
    assert contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSFeeOracle after vote"

    # CSM Step 50-52: Check add ICS Bond Curve to CSAccounting
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.MANAGE_BOND_CURVES_ROLE(), contracts.agent), "Agent should not have MANAGE_BOND_CURVES_ROLE on CSAccounting after vote"
    assert contracts.cs_accounting.getCurvesCount() == len(CS_CURVES) + 1, "CSAccounting should have legacy bond curves and ICS Bond Curve after vote"

    # CSM Step 53: Increase CSM share in Staking Router
    csm_module_after = contracts.staking_router.getStakingModule(CS_MODULE_ID)
    csm_share_after = csm_module_after['stakeShareLimit']
    assert csm_share_after == CS_MODULE_NEW_TARGET_SHARE_BP, f"CSM share should be {CS_MODULE_NEW_TARGET_SHARE_BP} after vote, but got {csm_share_after}"

    csm_priority_exit_threshold_after = csm_module_after['priorityExitShareThreshold']
    assert csm_priority_exit_threshold_after == CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, f"CSM priority exit threshold should be {CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP} after vote, but got {csm_priority_exit_threshold_after}"

    # CSM Step 54: Add EasyTrack factory for CSSetVettedGateTree
    new_factories = contracts.easy_track.getEVMScriptFactories()
    assert CS_SET_VETTED_GATE_TREE_FACTORY in new_factories, "EasyTrack should have CSSetVettedGateTree factory after vote"


