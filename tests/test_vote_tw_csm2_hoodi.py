from typing import Optional
from scripts.vote_tw_csm2_hoodi import start_vote
from brownie import interface, reverts, chain, convert, web3, ZERO_ADDRESS  # type: ignore
from brownie.network.event import EventDict
from utils.easy_track import create_permissions
from utils.test.tx_tracing_helpers import group_voting_events_from_receipt, group_dg_events_from_receipt
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.dual_governance import wait_for_noon_utc_to_satisfy_time_constrains
from utils.config import (
    DUAL_GOVERNANCE,
    TIMELOCK,
    DUAL_GOVERNANCE_EXECUTORS,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    CS_MODULE_ID,
    CS_MODULE_MODULE_FEE_BP,
    CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
    CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
    CS_MODULE_TREASURY_FEE_BP,
    CS_GATE_SEAL_ADDRESS,
    CSM_COMMITTEE_MS,
    ARAGON_KERNEL,
    AGENT,
    VOTING,
    contracts,
)


def validate_proxy_upgrade_event(event: EventDict, implementation: str, emitted_by: Optional[str] = None):
    assert "Upgraded" in event, "No Upgraded event found"

    assert event["Upgraded"][0]["implementation"] == implementation, "Wrong implementation address"

    if emitted_by is not None:
        assert convert.to_address(event["Upgraded"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_consensus_version_set_event(event: EventDict, new_version: int, prev_version: int, emitted_by: Optional[str] = None):
    assert "ConsensusVersionSet" in event, "No ConsensusVersionSet event found"

    assert event["ConsensusVersionSet"][0]["version"] == new_version, "Wrong new version"

    assert event["ConsensusVersionSet"][0]["prevVersion"] == prev_version, "Wrong previous version"

    if emitted_by is not None:
        assert convert.to_address(event["ConsensusVersionSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_role_grant_event(event: EventDict, role_hash: str, account: str, emitted_by: Optional[str] = None):
    assert "RoleGranted" in event, "No RoleGranted event found"

    # Strip 0x prefix for consistent comparison
    expected_role_hash = role_hash.replace('0x', '')
    actual_role_hash = event["RoleGranted"][0]["role"].hex().replace('0x', '')

    assert actual_role_hash == expected_role_hash, "Wrong role hash"

    assert convert.to_address(event["RoleGranted"][0]["account"]) == convert.to_address(account), "Wrong account"

    if emitted_by is not None:
        assert convert.to_address(event["RoleGranted"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_role_revoke_event(event: EventDict, role_hash: str, account: str, emitted_by: Optional[str] = None):
    assert "RoleRevoked" in event, "No RoleRevoked event found"

    # Strip 0x prefix for consistent comparison
    expected_role_hash = role_hash.replace('0x', '')
    actual_role_hash = event["RoleRevoked"][0]["role"].hex().replace('0x', '')

    assert actual_role_hash == expected_role_hash, "Wrong role hash"

    assert convert.to_address(event["RoleRevoked"][0]["account"]) == convert.to_address(account), "Wrong account"

    if emitted_by is not None:
        assert convert.to_address(event["RoleRevoked"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_contract_version_set_event(event: EventDict, version: int, emitted_by: Optional[str] = None):
    assert "ContractVersionSet" in event, "No ContractVersionSet event found"

    assert event["ContractVersionSet"][0]["version"] == version, "Wrong version"

    if emitted_by is not None:
        assert convert.to_address(event["ContractVersionSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_bond_curve_added_event(event: EventDict, curve_id: int, emitted_by: Optional[str] = None):
    assert "BondCurveAdded" in event, "No BondCurveAdded event found"

    assert event["BondCurveAdded"][0]["curveId"] == curve_id, "Wrong curve ID"

    if emitted_by is not None:
        assert convert.to_address(event["BondCurveAdded"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_staking_module_update_event(
    event: EventDict,
    module_id: int,
    share_limit: int,
    priority_share_threshold: int,
    module_fee_points_bp: int,
    treasury_fee_points_bp: int,
    max_deposits_per_block: int,
    min_deposit_block_distance: int,
    emitted_by: Optional[str] = None
):
    assert "StakingModuleShareLimitSet" in event, "No StakingModuleShareLimitSet event found"
    assert "StakingModuleFeesSet" in event, "No StakingModuleFeesSet event found"
    assert "StakingModuleMaxDepositsPerBlockSet" in event, "No StakingModuleMaxDepositsPerBlockSet event found"
    assert "StakingModuleMinDepositBlockDistanceSet" in event, "No StakingModuleMinDepositBlockDistanceSet event found"

    assert len(event["StakingModuleShareLimitSet"]) == 1, "Multiple StakingModuleShareLimitSet events found"
    assert len(event["StakingModuleFeesSet"]) == 1, "Multiple StakingModuleFeesSet events found"
    assert len(event["StakingModuleMaxDepositsPerBlockSet"]) == 1, "Multiple StakingModuleMaxDepositsPerBlockSet events found"
    assert len(event["StakingModuleMinDepositBlockDistanceSet"]) == 1, "Multiple StakingModuleMinDepositBlockDistanceSet events found"

    assert event["StakingModuleShareLimitSet"][0]["stakingModuleId"] == module_id, "Wrong module ID"
    assert event["StakingModuleShareLimitSet"][0]["stakeShareLimit"] == share_limit, "Wrong share limit"
    assert event["StakingModuleShareLimitSet"][0]["priorityExitShareThreshold"] == priority_share_threshold, "Wrong priority threshold"

    assert event["StakingModuleFeesSet"][0]["stakingModuleFee"] == module_fee_points_bp, "Wrong fee points"
    assert event["StakingModuleFeesSet"][0]["treasuryFee"] == treasury_fee_points_bp, "Wrong treasury fee points"

    assert event["StakingModuleMaxDepositsPerBlockSet"][0]["maxDepositsPerBlock"] == max_deposits_per_block, "Wrong max deposits"

    assert event["StakingModuleMinDepositBlockDistanceSet"][0]["minDepositBlockDistance"] == min_deposit_block_distance, "Wrong min distance"

    if emitted_by is not None:
        assert convert.to_address(event["StakingModuleShareLimitSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"
        assert convert.to_address(event["StakingModuleFeesSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"
        assert convert.to_address(event["StakingModuleMaxDepositsPerBlockSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"
        assert convert.to_address(event["StakingModuleMinDepositBlockDistanceSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


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


# New core contracts implementations
LIDO_LOCATOR_IMPL = "0x003f20CD17e7683A7F88A7AfF004f0C44F0cfB31"
ACCOUNTING_ORACLE_IMPL = "0x2341c9BE0E639f262f8170f9ef1efeCC92cCF617"
VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0x7E6d9C9C44417bf2EaF69685981646e9752D623A"
WITHDRAWAL_VAULT_IMPL = "0xfe7A58960Af333eAdeAeC39149F9d6A71dc3E668"
STAKING_ROUTER_IMPL = "0xd5F04A81ac472B2cB32073CE9dDABa6FaF022827"
NODE_OPERATORS_REGISTRY_IMPL = "0x95F00b016bB31b7182D96D25074684518246E42a"

TRIGGERABLE_WITHDRAWALS_GATEWAY = "0x6679090D92b08a2a686eF8614feECD8cDFE209db"
VALIDATOR_EXIT_VERIFIER = "0xFd4386A8795956f4B6D01cbb6dB116749731D7bD"

# Add missing constants
OLD_GATE_SEAL_ADDRESS = "0x2168Ea6D948Ab49c3D34c667A7e02F92369F3A9C"
NEW_WQ_GATE_SEAL = "0x73d76Bd3D589B2b2185c402da82cdAfbc18b958D"
NEW_TW_GATE_SEAL = "0x368f2fcb593170823cc844F1B29e75E3d26879A1"
RESEAL_MANAGER = "0x05172CbCDb7307228F781436b327679e4DAE166B"

# Add EasyTrack constants
EASYTRACK_EVMSCRIPT_EXECUTOR = "0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E"
EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0xAa3D6A8B52447F272c1E8FAaA06EA06658bd95E2"
EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x397206ecdbdcb1A55A75e60Fc4D054feC72E5f63"

# Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4
CSM_CONSENSUS_VERSION = 3

EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 50400

NOR_EXIT_DEADLINE_IN_SEC = 172800

# CSM
CS_MODULE_NEW_TARGET_SHARE_BP = 1600  # 16%
CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 2100  # 21%

CS_ACCOUNTING_IMPL_V2_ADDRESS = "0x9483b34504292a0E4f6509e5887D2c68f7129638"
CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS = "0xe05F7Aab7177D73f26e62a5296120583F5F18031"
CS_FEE_ORACLE_IMPL_V2_ADDRESS = "0x752fF00fcacdB66Bc512a067F15A5E0B0b50EADB"
CSM_IMPL_V2_ADDRESS = "0x9aE387EB2abA80B9B1ebc145597D593EFAE61f31"

CS_GATE_SEAL_V2_ADDRESS = "0x94a3aEB0E9148F64CB453Be2BDe2Bc0148f6AC24"
CS_EJECTOR_ADDRESS = "0x21e271cBa32672B106737AbeB3a45E53Fe9a0df4"
CS_PERMISSIONLESS_GATE_ADDRESS = "0x5553077102322689876A6AdFd48D75014c28acfb"
CS_VETTED_GATE_ADDRESS = "0x10a254E724fe2b7f305F76f3F116a3969c53845f"
CS_VERIFIER_V2_ADDRESS = "0xf805b3711cBB48F15Ae2bb27095ddC38c5339968"

CS_CURVES = [
    ([1, 2.4 * 10**18], [2, 1.3 * 10**18]),  # Default Curve
    ([1, 1.5 * 10**18], [2, 1.3 * 10**18]),  # Legacy EA Curve
]
CS_ICS_GATE_BOND_CURVE = ([1, 1.5 * 10**18], [2, 1.3 * 10**18])  # Identified Community Stakers Gate Bond Curve

# Contract versions expected after upgrade
CSM_V2_VERSION = 2
CS_ACCOUNTING_V2_VERSION = 2
CS_FEE_ORACLE_V2_VERSION = 2
CS_FEE_DISTRIBUTOR_V2_VERSION = 2

EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY = "0xa890fc73e1b771Ee6073e2402E631c312FF92Cd9"


def test_tw_vote(helpers, accounts, vote_ids_from_env, stranger):
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

    # Not yet used by the protocol, but needed for the test
    triggerable_withdrawals_gateway = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)
    cs_ejector = interface.CSEjector(CS_EJECTOR_ADDRESS)
    cs_permissionless_gate = interface.CSPermissionlessGate(CS_PERMISSIONLESS_GATE_ADDRESS)
    cs_vetted_gate = interface.CSVettedGate(CS_VETTED_GATE_ADDRESS)
    cs_verifier_v2 = interface.CSVerifierV2(CS_VERIFIER_V2_ADDRESS)

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
    assert initial_vebo_consensus_version < VEBO_CONSENSUS_VERSION, f"VEBO consensus version should be less than {VEBO_CONSENSUS_VERSION}"

    # Step 7: Check TWG role for CS Ejector initial state
    add_full_withdrawal_request_role = triggerable_withdrawals_gateway.ADD_FULL_WITHDRAWAL_REQUEST_ROLE()
    assert not triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, cs_ejector), "CS Ejector should not have ADD_FULL_WITHDRAWAL_REQUEST_ROLE before upgrade"

    # Step 8: Check TWG role for VEB initial state
    assert not triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle), "VEBO should not have ADD_FULL_WITHDRAWAL_REQUEST_ROLE before upgrade"

    # Step 9: Check EasyTrack VEB SUBMIT_REPORT_HASH_ROLE initial state
    submit_report_hash_role = web3.keccak(text="SUBMIT_REPORT_HASH_ROLE")
    assert not contracts.validators_exit_bus_oracle.hasRole(submit_report_hash_role, EASYTRACK_EVMSCRIPT_EXECUTOR), "EasyTrack executor should not have SUBMIT_REPORT_HASH_ROLE on VEBO before upgrade"

    # Step 10: Check DualGovernance tiebreaker initial state
    tiebreaker_details = contracts.dual_governance.getTiebreakerDetails()
    initial_tiebreakers = tiebreaker_details[3]  # sealableWithdrawalBlockers
    assert TRIGGERABLE_WITHDRAWALS_GATEWAY not in initial_tiebreakers, "TWG should not be in tiebreaker list before upgrade"

    # Step 9: Check Withdrawal Vault implementation initial state
    assert withdrawal_vault_impl_before != WITHDRAWAL_VAULT_IMPL, "Withdrawal Vault implementation should be different before upgrade"

    # Step 10: Withdrawal Vault finalizeUpgrade_v2 check is done post-execution
    assert contracts.withdrawal_vault.getContractVersion()  == 1, "Withdrawal Vault version should be 1 before upgrade"

    # Step 11: Check Accounting Oracle implementation initial state
    assert accounting_oracle_impl_before != ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be different before upgrade"

    # Steps 12-14: Check AO consensus version management
    initial_ao_consensus_version = contracts.accounting_oracle.getConsensusVersion()
    assert initial_ao_consensus_version < AO_CONSENSUS_VERSION, f"AO consensus version should be less than {AO_CONSENSUS_VERSION}"
    assert not contracts.accounting_oracle.hasRole(contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent), "Agent should not have MANAGE_CONSENSUS_VERSION_ROLE on AO before upgrade"

    # Step 17: Check AO version before finalizeUpgrade_v3
    assert contracts.accounting_oracle.getContractVersion() == 2, "AO contract version should be 2 before finalizeUpgrade_v3"

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
    with reverts():
        # The function should not exist yet
        contracts.csm.getInitializedVersion()

    # CSM Step 32: Check CSAccounting implementation (pre-vote state)
    assert cs_accounting_impl_before != CS_ACCOUNTING_IMPL_V2_ADDRESS, "CSAccounting implementation should be different before vote"

    # CSM Step 33: Check CSAccounting finalizeUpgradeV2 was not called (pre-vote state)
    with reverts():
        # The function should not exist yet
        contracts.cs_accounting.getInitializedVersion()

    # CSM Step 34: Check CSFeeOracle implementation (pre-vote state)
    assert cs_fee_oracle_impl_before != CS_FEE_ORACLE_IMPL_V2_ADDRESS, "CSFeeOracle implementation should be different before vote"

    # CSM Step 35: Check CSFeeOracle finalizeUpgradeV2 was not called (pre-vote state)
    assert contracts.cs_fee_oracle.getContractVersion() < CS_FEE_ORACLE_V2_VERSION, f"CSFeeOracle version should be less than {CS_FEE_ORACLE_V2_VERSION} before vote"
    assert contracts.cs_fee_oracle.getConsensusVersion() < 3, "CSFeeOracle consensus version should be less than 3 before vote"

    # CSM Step 36: Check CSFeeDistributor implementation (pre-vote state)
    assert cs_fee_distributor_impl_before != CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS, "CSFeeDistributor implementation should be different before vote"

    # CSM Step 37: Check CSFeeDistributor finalizeUpgradeV2 was not called (pre-vote state)
    with reverts():
        # The function should not exist yet
        contracts.cs_fee_distributor.getInitializedVersion()

    # CSM Steps 38-40: CSAccounting roles (pre-vote state)
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.csm.address), "CSM should have SET_BOND_CURVE_ROLE on CSAccounting before vote"
    assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), contracts.csm.address), "CSM should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"
    assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), CSM_COMMITTEE_MS), "CSM committee should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"

    # CSM Steps 41-42: CSM roles (pre-vote state)
    assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), cs_permissionless_gate.address), "Permissionless gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"
    assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), cs_vetted_gate.address), "Vetted gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"

    # CSM Step 43: CSAccounting bond curve role for vetted gate (pre-vote state)
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), cs_vetted_gate.address), "Vetted gate should not have SET_BOND_CURVE_ROLE on CSAccounting before vote"

    # CSM Steps 44-45: Verifier roles (pre-vote state)
    assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier.address), "Old verifier should have VERIFIER_ROLE on CSM before vote"
    assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), cs_verifier_v2.address), "New verifier should not have VERIFIER_ROLE on CSM before vote"

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

    # CSM Step 65: EasyTrack factories before vote (pre-vote state)
    initial_factories = contracts.easy_track.getEVMScriptFactories()
    assert EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY not in initial_factories, "EasyTrack should not have CSMSetVettedGateTree factory before vote"
    assert EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY not in initial_factories, "EasyTrack should not have SDVT validator exit request hashes factory before vote"
    assert EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY not in initial_factories, "EasyTrack should not have Curated validator exit request hashes factory before vote"

    # Gate Seals: Check initial states before vote
    assert contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), OLD_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on WithdrawalQueue before vote"
    assert contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.PAUSE_ROLE(), OLD_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on VEBO before vote"
    assert not contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), NEW_WQ_GATE_SEAL), "New WQ GateSeal should not have PAUSE_ROLE on WithdrawalQueue before vote"
    assert not contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.PAUSE_ROLE(), NEW_TW_GATE_SEAL), "New TW GateSeal should not have PAUSE_ROLE on VEBO before vote"
    assert not triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.PAUSE_ROLE(), NEW_TW_GATE_SEAL), "New TW GateSeal should not have PAUSE_ROLE on TWG before vote"

    # ResealManager: Check initial states before vote
    assert not triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.PAUSE_ROLE(), RESEAL_MANAGER), "ResealManager should not have PAUSE_ROLE on TWG before vote"
    assert not triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.RESUME_ROLE(), RESEAL_MANAGER), "ResealManager should not have RESUME_ROLE on TWG before vote"

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}")

    proposal_id = vote_tx.events["ProposalSubmitted"][1]["proposalId"]
    print(f"proposalId = {proposal_id}")

    chain.sleep(timelock.getAfterSubmitDelay() + 1)
    dual_governance.scheduleProposal(proposal_id, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)
    wait_for_noon_utc_to_satisfy_time_constrains()

    dg_tx = timelock.execute(proposal_id, {"from": stranger})

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
    assert contracts.validators_exit_bus_oracle.getConsensusVersion() == VEBO_CONSENSUS_VERSION, f"VEBO consensus version should be set to {VEBO_CONSENSUS_VERSION}"

    # Steps 7-8: Validate TWG roles
    assert triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, cs_ejector), "CS Ejector should have ADD_FULL_WITHDRAWAL_REQUEST_ROLE on TWG"
    assert triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle), "VEBO should have ADD_FULL_WITHDRAWAL_REQUEST_ROLE on TWG"

    # Step 9: Validate EasyTrack VEB SUBMIT_REPORT_HASH_ROLE
    assert contracts.validators_exit_bus_oracle.hasRole(submit_report_hash_role, EASYTRACK_EVMSCRIPT_EXECUTOR), "EasyTrack executor should have SUBMIT_REPORT_HASH_ROLE on VEBO"

    # Step 10: Validate DualGovernance tiebreaker connection
    final_tiebreaker_details = contracts.dual_governance.getTiebreakerDetails()
    final_tiebreakers = final_tiebreaker_details[3]  # sealableWithdrawalBlockers
    assert TRIGGERABLE_WITHDRAWALS_GATEWAY in final_tiebreakers, "TWG should be in tiebreaker list after upgrade"

    # Steps 9-10: Validate Withdrawal Vault upgrade
    assert get_wv_contract_proxy_impl(contracts.withdrawal_vault) == WITHDRAWAL_VAULT_IMPL, "Withdrawal Vault implementation should be updated"
    assert contracts.withdrawal_vault.getContractVersion() == 2, "Withdrawal Vault version should be 2 after finalizeUpgrade_v2"

    # Steps 11-14: Validate Accounting Oracle upgrade
    assert get_ossifiable_proxy_impl(contracts.accounting_oracle) == ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be updated"
    assert not contracts.accounting_oracle.hasRole(contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent), "Agent should not have MANAGE_CONSENSUS_VERSION_ROLE on AO"
    assert contracts.accounting_oracle.getConsensusVersion() == AO_CONSENSUS_VERSION, f"AO consensus version should be set to {AO_CONSENSUS_VERSION}"

    # Step 17: Validate AO finalizeUpgrade_v3
    assert contracts.accounting_oracle.getContractVersion() == 3, "AO contract version should be 3 after finalizeUpgrade_v3"

    # Steps 15-17: Validate Staking Router upgrade
    assert get_ossifiable_proxy_impl(contracts.staking_router) == STAKING_ROUTER_IMPL, "Staking Router implementation should be updated"
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE(), VALIDATOR_EXIT_VERIFIER), "ValidatorExitVerifier should have REPORT_VALIDATOR_EXITING_STATUS_ROLE on SR"
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE(), triggerable_withdrawals_gateway), "TWG should have REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE on SR"

    # Steps 18-23: Validate NOR and sDVT updates
    assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel, app_manager_role), "Agent should not have APP_MANAGER_ROLE after vote"
    assert contracts.node_operators_registry.getContractVersion() == 4, "Node Operators Registry version should be updated to 4"
    assert contracts.simple_dvt.getContractVersion() == 4, "Simple DVT version should be updated to 4"
    assert contracts.node_operators_registry.exitDeadlineThreshold(0) == NOR_EXIT_DEADLINE_IN_SEC, "NOR exit deadline threshold should be set correctly"
    assert contracts.simple_dvt.exitDeadlineThreshold(0) == NOR_EXIT_DEADLINE_IN_SEC, "sDVT exit deadline threshold should be set correctly"

    # Steps 24-28: Validate Oracle Daemon Config changes
    assert contracts.oracle_daemon_config.hasRole(config_manager_role, contracts.agent), "Agent should have CONFIG_MANAGER_ROLE on Oracle Daemon Config"
    for var_name in ['NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP', 'VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS', 'VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS']:
        try:
            contracts.oracle_daemon_config.get(var_name)
            assert False, f"Variable {var_name} should have been removed"
        except Exception:
            pass  # Expected to fail - variable should be removed
    assert convert.to_uint(contracts.oracle_daemon_config.get('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')) == EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS, f"EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS should be set to {EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS}"

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
    assert contracts.cs_fee_oracle.getConsensusVersion() == CSM_CONSENSUS_VERSION, "CSFeeOracle consensus version should be 3 after vote"

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
    assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(), cs_permissionless_gate.address), "Permissionless gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

    # Step 41: Validate CREATE_NODE_OPERATOR_ROLE was granted to vetted gate on CSM
    assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(), cs_vetted_gate.address), "Vetted gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

    # Step 42: Validate SET_BOND_CURVE_ROLE was granted to vetted gate on CSAccounting
    assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), cs_vetted_gate.address), "Vetted gate should have SET_BOND_CURVE_ROLE on CSAccounting after vote"

    # Step 43: Validate VERIFIER_ROLE was revoked from old verifier on CSM
    assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), contracts.cs_verifier.address), "Old verifier should not have VERIFIER_ROLE on CSM after vote"

    # Step 44: Validate VERIFIER_ROLE was granted to new verifier on CSM
    assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), cs_verifier_v2.address), "New verifier should have VERIFIER_ROLE on CSM after vote"

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

    # Step 50-52: Check add ICS Bond Curve to CSAccounting
    assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.MANAGE_BOND_CURVES_ROLE(), contracts.agent), "Agent should not have MANAGE_BOND_CURVES_ROLE on CSAccounting after vote"
    assert contracts.cs_accounting.getCurvesCount() == len(CS_CURVES) + 1, "CSAccounting should have legacy bond curves and ICS Bond Curve after vote"

    # Step 53: Increase CSM share in Staking Router
    csm_module_after = contracts.staking_router.getStakingModule(CS_MODULE_ID)
    csm_share_after = csm_module_after['stakeShareLimit']
    assert csm_share_after == CS_MODULE_NEW_TARGET_SHARE_BP, f"CSM share should be {CS_MODULE_NEW_TARGET_SHARE_BP} after vote, but got {csm_share_after}"

    csm_priority_exit_threshold_after = csm_module_after['priorityExitShareThreshold']
    assert csm_priority_exit_threshold_after == CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, f"CSM priority exit threshold should be {CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP} after vote, but got {csm_priority_exit_threshold_after}"


    # Steps 58-62: Validate Gate Seals updates
    assert not contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), OLD_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on WithdrawalQueue after vote"
    assert not contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.PAUSE_ROLE(), OLD_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on VEBO after vote"
    assert contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), NEW_WQ_GATE_SEAL), "New WQ GateSeal should have PAUSE_ROLE on WithdrawalQueue after vote"
    assert contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.PAUSE_ROLE(), NEW_TW_GATE_SEAL), "New TW GateSeal should have PAUSE_ROLE on VEBO after vote"
    assert triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.PAUSE_ROLE(), NEW_TW_GATE_SEAL), "New TW GateSeal should have PAUSE_ROLE on TWG after vote"

    # Steps 63-64: Validate ResealManager roles
    assert triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.PAUSE_ROLE(), RESEAL_MANAGER), "ResealManager should have PAUSE_ROLE on TWG after vote"
    assert triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.RESUME_ROLE(), RESEAL_MANAGER), "ResealManager should have RESUME_ROLE on TWG after vote"

    # Step 65: Add EasyTrack factory for CSSetVettedGateTree
    new_factories = contracts.easy_track.getEVMScriptFactories()
    assert EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY in new_factories, "EasyTrack should have CSSetVettedGateTree factory after vote"

    # Steps 66-67: Validate EasyTrack factories for validator exit request hashes
    assert EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY in new_factories, "EasyTrack should have SDVT validator exit request hashes factory after vote"
    assert EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY in new_factories, "EasyTrack should have Curated validator exit request hashes factory after vote"

    # --- VALIDATE EVENTS ---

    voting_events = group_voting_events_from_receipt(vote_tx)
    dg_execution_events = group_dg_events_from_receipt(dg_tx, timelock=TIMELOCK, admin_executor=DUAL_GOVERNANCE_EXECUTORS[0])

    # Validate voting events structure
    assert len(voting_events) == 4, "Unexpected number of voting events"
    dg_voting_event, dg_bypass_voting_event1, dg_bypass_voting_event2, dg_bypass_voting_event3 = voting_events

    # Validate DG execution events structure
    assert len(dg_execution_events) == 64, "Unexpected number of dual governance events"

    # Main DG voting event validation
    validate_dual_governance_submit_event(
        dg_voting_event,
        proposal_id,
        proposer=VOTING,
        executor=DUAL_GOVERNANCE_EXECUTORS[0],
    )

    # Validate EasyTrack bypass events for new factories
    validate_evmscript_factory_added_event(
        event=dg_bypass_voting_event1,
        p=EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY,
            permissions=create_permissions(interface.CSVettedGate(CS_VETTED_GATE_ADDRESS), "setTreeParams")
        ),
        emitted_by=contracts.easy_track,
    )

    validate_evmscript_factory_added_event(
        event=dg_bypass_voting_event2,
        p=EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
            permissions=create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")
        ),
        emitted_by=contracts.easy_track,
    )

    validate_evmscript_factory_added_event(
        event=dg_bypass_voting_event3,
        p=EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
            permissions=create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")
        ),
        emitted_by=contracts.easy_track,
    )

    # === DG EXECUTION EVENTS VALIDATION ===

    # 0. Lido Locator upgrade events
    validate_proxy_upgrade_event(dg_execution_events[0], LIDO_LOCATOR_IMPL, emitted_by=contracts.lido_locator)

    # 1. VEBO upgrade events
    validate_proxy_upgrade_event(dg_execution_events[1], VALIDATORS_EXIT_BUS_ORACLE_IMPL, emitted_by=contracts.validators_exit_bus_oracle)

    # 2. VEBO finalize upgrade events
    validate_contract_version_set_event(dg_execution_events[2], version=2, emitted_by=contracts.validators_exit_bus_oracle)
    assert 'ExitRequestsLimitSet' in dg_execution_events[2], "ExitRequestsLimitSet event not found"
    assert dg_execution_events[2]['ExitRequestsLimitSet'][0]['maxExitRequestsLimit'] == 13000, "Wrong maxExitRequestsLimit"
    assert dg_execution_events[2]['ExitRequestsLimitSet'][0]['exitsPerFrame'] == 1, "Wrong exitsPerFrame"
    assert dg_execution_events[2]['ExitRequestsLimitSet'][0]['frameDurationInSec'] == 48, "Wrong frameDurationInSec"

    # 3. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to Agent
    validate_role_grant_event(
        dg_execution_events[3],
        role_hash=web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex(),
        account=contracts.agent.address,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    # 4. Set VEBO consensus version to 4
    validate_consensus_version_set_event(
        dg_execution_events[4],
        new_version=4,
        prev_version=3,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    # 5. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from Agent
    validate_role_revoke_event(
        dg_execution_events[5],
        role_hash=web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex(),
        account=contracts.agent.address,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    # 6. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to CS Ejector
    validate_role_grant_event(
        dg_execution_events[6],
        role_hash=web3.keccak(text="ADD_FULL_WITHDRAWAL_REQUEST_ROLE").hex(),
        account=CS_EJECTOR_ADDRESS,
        emitted_by=triggerable_withdrawals_gateway
    )

    # 7. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to VEBO
    validate_role_grant_event(
        dg_execution_events[7],
        role_hash=web3.keccak(text="ADD_FULL_WITHDRAWAL_REQUEST_ROLE").hex(),
        account=contracts.validators_exit_bus_oracle.address,
        emitted_by=triggerable_withdrawals_gateway
    )

    # 8. Grant VEBO SUBMIT_REPORT_HASH_ROLE to EasyTrack executor
    validate_role_grant_event(
        dg_execution_events[8],
        role_hash=web3.keccak(text="SUBMIT_REPORT_HASH_ROLE").hex(),
        account=EASYTRACK_EVMSCRIPT_EXECUTOR,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    # 9. Connect TWG to Dual Governance tiebreaker
    assert 'SealableWithdrawalBlockerAdded' in dg_execution_events[9], "SealableWithdrawalBlockerAdded event not found"
    assert dg_execution_events[9]['SealableWithdrawalBlockerAdded'][0]['sealable'] == TRIGGERABLE_WITHDRAWALS_GATEWAY, "Wrong sealableWithdrawalBlocker"

    # 10. Update WithdrawalVault implementation
    validate_proxy_upgrade_event(dg_execution_events[10], WITHDRAWAL_VAULT_IMPL, emitted_by=contracts.withdrawal_vault)

    # 11. Call finalizeUpgrade_v2 on WithdrawalVault
    validate_contract_version_set_event(dg_execution_events[11], version=2, emitted_by=contracts.withdrawal_vault)

    # 12. Update AO implementation
    validate_proxy_upgrade_event(dg_execution_events[12], ACCOUNTING_ORACLE_IMPL, emitted_by=contracts.accounting_oracle)

    # 13. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
    validate_role_grant_event(
        dg_execution_events[13],
        role_hash=web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex(),
        account=contracts.agent.address,
        emitted_by=contracts.accounting_oracle
    )

    # 14. Bump AO consensus version to 4
    validate_consensus_version_set_event(
        dg_execution_events[14],
        new_version=4,
        prev_version=3,
        emitted_by=contracts.accounting_oracle
    )

    # 15. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
    validate_role_revoke_event(
        dg_execution_events[15],
        role_hash=web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex(),
        account=contracts.agent.address,
        emitted_by=contracts.accounting_oracle
    )

    # 16. Call finalizeUpgrade_v3() on AO
    validate_contract_version_set_event(dg_execution_events[16], version=3, emitted_by=contracts.accounting_oracle)

    # 17. Update SR implementation
    validate_proxy_upgrade_event(dg_execution_events[17], STAKING_ROUTER_IMPL, emitted_by=contracts.staking_router)

    # 18. Grant SR REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
    validate_role_grant_event(
        dg_execution_events[18],
        role_hash=web3.keccak(text="REPORT_VALIDATOR_EXITING_STATUS_ROLE").hex(),
        account=VALIDATOR_EXIT_VERIFIER,
        emitted_by=contracts.staking_router
    )

    # 19. Grant SR REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
    validate_role_grant_event(
        dg_execution_events[19],
        role_hash=web3.keccak(text="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE").hex(),
        account=triggerable_withdrawals_gateway.address,
        emitted_by=contracts.staking_router
    )

    # 20. Grant APP_MANAGER_ROLE on Kernel to Voting
    assert 'SetPermission' in dg_execution_events[20]
    assert dg_execution_events[20]['SetPermission'][0]['allowed'] is True

    # 21. Set new implementation for NOR
    assert 'SetApp' in dg_execution_events[21]

    # 22. Finalize upgrade for NOR
    validate_contract_version_set_event(dg_execution_events[22], version=4, emitted_by=contracts.node_operators_registry)
    assert 'ExitDeadlineThresholdChanged' in dg_execution_events[22]
    assert dg_execution_events[22]['ExitDeadlineThresholdChanged'][0]['threshold'] == NOR_EXIT_DEADLINE_IN_SEC

    # 23. Set new implementation for sDVT
    assert 'SetApp' in dg_execution_events[23]

    # 24. Finalize upgrade for sDVT
    validate_contract_version_set_event(dg_execution_events[24], version=4, emitted_by=contracts.simple_dvt)
    assert 'ExitDeadlineThresholdChanged' in dg_execution_events[24]
    assert dg_execution_events[24]['ExitDeadlineThresholdChanged'][0]['threshold'] == NOR_EXIT_DEADLINE_IN_SEC

    # 25. Revoke APP_MANAGER_ROLE on Kernel from Voting
    assert 'SetPermission' in dg_execution_events[25]
    assert dg_execution_events[25]['SetPermission'][0]['allowed'] is False

    # 26. Grant CONFIG_MANAGER_ROLE on OracleDaemonConfig to Agent
    validate_role_grant_event(
        dg_execution_events[26],
        role_hash=contracts.oracle_daemon_config.CONFIG_MANAGER_ROLE().hex(),
        account=contracts.agent.address,
        emitted_by=contracts.oracle_daemon_config
    )

    # 27. Unset NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP
    assert 'ConfigValueUnset' in dg_execution_events[27]
    assert 'NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP' in dg_execution_events[27]['ConfigValueUnset'][0]['key']

    # 28. Unset VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS
    assert 'ConfigValueUnset' in dg_execution_events[28]
    assert 'VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS' in dg_execution_events[28]['ConfigValueUnset'][0]['key']

    # 29. Unset VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS
    assert 'ConfigValueUnset' in dg_execution_events[29]
    assert 'VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS' in dg_execution_events[29]['ConfigValueUnset'][0]['key']

    # 30. Set EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS
    assert 'ConfigValueSet' in dg_execution_events[30]
    assert 'EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS' in dg_execution_events[30]['ConfigValueSet'][0]['key']
    assert convert.to_int(dg_execution_events[30]['ConfigValueSet'][0]['value']) == EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS

    # 31. CSM implementation upgrade
    validate_proxy_upgrade_event(dg_execution_events[31], CSM_IMPL_V2_ADDRESS, emitted_by=contracts.csm)

    # 32. CSM finalize upgrade validation
    assert 'Initialized' in dg_execution_events[32]
    assert dg_execution_events[32]['Initialized'][0]['version'] == CSM_V2_VERSION

    # 33. CSAccounting implementation upgrade
    validate_proxy_upgrade_event(dg_execution_events[33], CS_ACCOUNTING_IMPL_V2_ADDRESS, emitted_by=contracts.cs_accounting)

    # 34. CSAccounting finalize upgrade with bond curves
    assert 'BondCurveAdded' in dg_execution_events[34]
    assert len(dg_execution_events[34]['BondCurveAdded']) == len(CS_CURVES)
    assert 'Initialized' in dg_execution_events[34]
    assert dg_execution_events[34]['Initialized'][0]['version'] == CS_ACCOUNTING_V2_VERSION

    # 35. CSFeeOracle implementation upgrade
    validate_proxy_upgrade_event(dg_execution_events[35], CS_FEE_ORACLE_IMPL_V2_ADDRESS, emitted_by=contracts.cs_fee_oracle)

    # 36. CSFeeOracle finalize upgrade with consensus version
    validate_consensus_version_set_event(dg_execution_events[36], new_version=3, prev_version=2, emitted_by=contracts.cs_fee_oracle)
    validate_contract_version_set_event(dg_execution_events[36], version=CS_FEE_ORACLE_V2_VERSION, emitted_by=contracts.cs_fee_oracle)

    # 37. CSFeeDistributor implementation upgrade
    validate_proxy_upgrade_event(dg_execution_events[37], CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS, emitted_by=contracts.cs_fee_distributor)

    # 38. CSFeeDistributor finalize upgrade
    assert 'RebateRecipientSet' in dg_execution_events[38]
    assert 'Initialized' in dg_execution_events[38]
    assert dg_execution_events[38]['Initialized'][0]['version'] == CS_FEE_DISTRIBUTOR_V2_VERSION

    # 39. Revoke SET_BOND_CURVE_ROLE from CSM on CSAccounting
    validate_role_revoke_event(
        dg_execution_events[39],
        role_hash=contracts.cs_accounting.SET_BOND_CURVE_ROLE().hex(),
        account=contracts.csm.address,
        emitted_by=contracts.cs_accounting
    )

    # 40. Revoke RESET_BOND_CURVE_ROLE from CSM on CSAccounting
    validate_role_revoke_event(
        dg_execution_events[40],
        role_hash=web3.keccak(text="RESET_BOND_CURVE_ROLE").hex(),
        account=contracts.csm.address,
        emitted_by=contracts.cs_accounting
    )

    # 41. Revoke RESET_BOND_CURVE_ROLE from CSM committee on CSAccounting
    validate_role_revoke_event(
        dg_execution_events[41],
        role_hash=web3.keccak(text="RESET_BOND_CURVE_ROLE").hex(),
        account=CSM_COMMITTEE_MS,
        emitted_by=contracts.cs_accounting
    )

    # 42. Grant CREATE_NODE_OPERATOR_ROLE to permissionless gate on CSM
    validate_role_grant_event(
        dg_execution_events[42],
        role_hash=contracts.csm.CREATE_NODE_OPERATOR_ROLE().hex(),
        account=CS_PERMISSIONLESS_GATE_ADDRESS,
        emitted_by=contracts.csm
    )

    # 43. Grant CREATE_NODE_OPERATOR_ROLE to vetted gate on CSM
    validate_role_grant_event(
        dg_execution_events[43],
        role_hash=contracts.csm.CREATE_NODE_OPERATOR_ROLE().hex(),
        account=CS_VETTED_GATE_ADDRESS,
        emitted_by=contracts.csm
    )

    # 44. Grant SET_BOND_CURVE_ROLE to vetted gate on CSAccounting
    validate_role_grant_event(
        dg_execution_events[44],
        role_hash=contracts.cs_accounting.SET_BOND_CURVE_ROLE().hex(),
        account=CS_VETTED_GATE_ADDRESS,
        emitted_by=contracts.cs_accounting
    )

    # 45. Revoke VERIFIER_ROLE from old verifier on CSM
    validate_role_revoke_event(
        dg_execution_events[45],
        role_hash=contracts.csm.VERIFIER_ROLE().hex(),
        account=contracts.cs_verifier.address,
        emitted_by=contracts.csm
    )

    # 46. Grant VERIFIER_ROLE to new verifier on CSM
    validate_role_grant_event(
        dg_execution_events[46],
        role_hash=contracts.csm.VERIFIER_ROLE().hex(),
        account=CS_VERIFIER_V2_ADDRESS,
        emitted_by=contracts.csm
    )

    # 47. Revoke PAUSE_ROLE from old GateSeal on CSM
    validate_role_revoke_event(
        dg_execution_events[47],
        role_hash=contracts.csm.PAUSE_ROLE().hex(),
        account=CS_GATE_SEAL_ADDRESS,
        emitted_by=contracts.csm
    )

    # 48. Revoke PAUSE_ROLE from old GateSeal on CSAccounting
    validate_role_revoke_event(
        dg_execution_events[48],
        role_hash=contracts.cs_accounting.PAUSE_ROLE().hex(),
        account=CS_GATE_SEAL_ADDRESS,
        emitted_by=contracts.cs_accounting
    )

    # 49. Revoke PAUSE_ROLE from old GateSeal on CSFeeOracle
    validate_role_revoke_event(
        dg_execution_events[49],
        role_hash=contracts.cs_fee_oracle.PAUSE_ROLE().hex(),
        account=CS_GATE_SEAL_ADDRESS,
        emitted_by=contracts.cs_fee_oracle
    )

    # 50. Grant PAUSE_ROLE to new GateSeal on CSM
    validate_role_grant_event(
        dg_execution_events[50],
        role_hash=contracts.csm.PAUSE_ROLE().hex(),
        account=CS_GATE_SEAL_V2_ADDRESS,
        emitted_by=contracts.csm
    )

    # 51. Grant PAUSE_ROLE to new GateSeal on CSAccounting
    validate_role_grant_event(
        dg_execution_events[51],
        role_hash=contracts.cs_accounting.PAUSE_ROLE().hex(),
        account=CS_GATE_SEAL_V2_ADDRESS,
        emitted_by=contracts.cs_accounting
    )

    # 52. Grant PAUSE_ROLE to new GateSeal on CSFeeOracle
    validate_role_grant_event(
        dg_execution_events[52],
        role_hash=contracts.cs_fee_oracle.PAUSE_ROLE().hex(),
        account=CS_GATE_SEAL_V2_ADDRESS,
        emitted_by=contracts.cs_fee_oracle
    )

    # 53. Grant MANAGE_BOND_CURVES_ROLE to agent on CSAccounting
    validate_role_grant_event(
        dg_execution_events[53],
        role_hash=contracts.cs_accounting.MANAGE_BOND_CURVES_ROLE().hex(),
        account=contracts.agent.address,
        emitted_by=contracts.cs_accounting
    )

    # 54. Add ICS bond curve
    ics_curve_id = len(CS_CURVES)
    validate_bond_curve_added_event(dg_execution_events[54], curve_id=ics_curve_id, emitted_by=contracts.cs_accounting)

    # 55. Revoke MANAGE_BOND_CURVES_ROLE from agent on CSAccounting
    validate_role_revoke_event(
        dg_execution_events[55],
        role_hash=contracts.cs_accounting.MANAGE_BOND_CURVES_ROLE().hex(),
        account=contracts.agent.address,
        emitted_by=contracts.cs_accounting
    )

    # 56. Increase CSM share in Staking Router
    validate_staking_module_update_event(
        dg_execution_events[56],
        module_id=CS_MODULE_ID,
        share_limit=CS_MODULE_NEW_TARGET_SHARE_BP,
        priority_share_threshold=CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
        module_fee_points_bp=CS_MODULE_MODULE_FEE_BP,
        treasury_fee_points_bp=CS_MODULE_TREASURY_FEE_BP,
        max_deposits_per_block=CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
        min_deposit_block_distance=CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
        emitted_by=contracts.staking_router
    )

    # 57-63. Gate Seals and ResealManager role updates
    # 57. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
    validate_role_revoke_event(
        dg_execution_events[57],
        role_hash=contracts.withdrawal_queue.PAUSE_ROLE().hex(),
        account=OLD_GATE_SEAL_ADDRESS,
        emitted_by=contracts.withdrawal_queue
    )

    # 58. Revoke PAUSE_ROLE on ValidatorsExitBusOracle from the old GateSeal
    validate_role_revoke_event(
        dg_execution_events[58],
        role_hash=contracts.validators_exit_bus_oracle.PAUSE_ROLE().hex(),
        account=OLD_GATE_SEAL_ADDRESS,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    # 59. Grant PAUSE_ROLE on WithdrawalQueue to the new WithdrawalQueue GateSeal
    validate_role_grant_event(
        dg_execution_events[59],
        role_hash=contracts.withdrawal_queue.PAUSE_ROLE().hex(),
        account=NEW_WQ_GATE_SEAL,
        emitted_by=contracts.withdrawal_queue
    )

    # 60. Grant PAUSE_ROLE on ValidatorsExitBusOracle to the new Triggerable Withdrawals GateSeal
    validate_role_grant_event(
        dg_execution_events[60],
        role_hash=contracts.validators_exit_bus_oracle.PAUSE_ROLE().hex(),
        account=NEW_TW_GATE_SEAL,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    # 61. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to the new Triggerable Withdrawals GateSeal
    validate_role_grant_event(
        dg_execution_events[61],
        role_hash=triggerable_withdrawals_gateway.PAUSE_ROLE().hex(),
        account=NEW_TW_GATE_SEAL,
        emitted_by=triggerable_withdrawals_gateway
    )

    # 62. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to ResealManager
    validate_role_grant_event(
        dg_execution_events[62],
        role_hash=triggerable_withdrawals_gateway.PAUSE_ROLE().hex(),
        account=RESEAL_MANAGER,
        emitted_by=triggerable_withdrawals_gateway
    )

    # 63. Grant RESUME_ROLE on TriggerableWithdrawalsGateway to ResealManager
    validate_role_grant_event(
        dg_execution_events[63],
        role_hash=triggerable_withdrawals_gateway.RESUME_ROLE().hex(),
        account=RESEAL_MANAGER,
        emitted_by=triggerable_withdrawals_gateway
    )
