from typing import NamedTuple, Optional

import pytest

from brownie import chain, convert, interface, web3
from brownie.network.event import EventDict
from brownie.network.transaction import TransactionReceipt

from utils.config import network_name
from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_dg_events,
    display_voting_events,
    group_dg_events_from_receipt,
    group_voting_events_from_receipt,
)
from utils.tx_tracing import tx_events_from_receipt
from utils.evm_script import encode_call_script
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.aragon import (
    validate_aragon_grant_permission_event,
    validate_aragon_revoke_permission_event,
    validate_aragon_set_app_event,
)
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import calculate_vote_ipfs_description, get_lido_vote_cid_from_str


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_2026_04_14_hoodi_protocol_upgrade import (
    get_ipfs_description,
    start_vote,
    get_vote_items,
    get_dg_items,
    DG_PROPOSAL_METADATA,
    UPGRADE_VOTE_SCRIPT,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
EMERGENCY_PROTECTED_TIMELOCK = "0x0A5E22782C0Bd4AddF10D771f0bF0406B038282d"
HOODI_LEGACY_STAKING_MODULE_MANAGER = "0xE28f573b732632fdE03BD5507A7d475383e8512E"
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"
APP_MANAGER_ROLE = web3.keccak(text="APP_MANAGER_ROLE").hex()
BUFFER_RESERVE_MANAGER_ROLE = web3.keccak(text="BUFFER_RESERVE_MANAGER_ROLE").hex()
STAKING_MODULE_MANAGE_ROLE = web3.keccak(text="STAKING_MODULE_MANAGE_ROLE").hex()
STAKING_MODULE_UNVETTING_ROLE = web3.keccak(text="STAKING_MODULE_UNVETTING_ROLE").hex()
STAKING_MODULE_SHARE_MANAGE_ROLE = web3.keccak(text="STAKING_MODULE_SHARE_MANAGE_ROLE").hex()
REPORT_EXITED_VALIDATORS_ROLE = web3.keccak(text="REPORT_EXITED_VALIDATORS_ROLE").hex()
REPORT_VALIDATOR_EXITING_STATUS_ROLE = web3.keccak(text="REPORT_VALIDATOR_EXITING_STATUS_ROLE").hex()
REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE = web3.keccak(text="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE").hex()
REPORT_REWARDS_MINTED_ROLE = web3.keccak(text="REPORT_REWARDS_MINTED_ROLE").hex()
TW_EXIT_LIMIT_MANAGER_ROLE = web3.keccak(text="TW_EXIT_LIMIT_MANAGER_ROLE").hex()
REPORT_GENERAL_DELAYED_PENALTY_ROLE = web3.keccak(text="REPORT_GENERAL_DELAYED_PENALTY_ROLE").hex()
SETTLE_GENERAL_DELAYED_PENALTY_ROLE = web3.keccak(text="SETTLE_GENERAL_DELAYED_PENALTY_ROLE").hex()
REPORT_EL_REWARDS_STEALING_PENALTY_ROLE = web3.keccak(text="REPORT_EL_REWARDS_STEALING_PENALTY_ROLE").hex()
SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE = web3.keccak(text="SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE").hex()
VERIFIER_ROLE = web3.keccak(text="VERIFIER_ROLE").hex()
REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE = web3.keccak(text="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE").hex()
REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE = web3.keccak(text="REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE").hex()
CREATE_NODE_OPERATOR_ROLE = web3.keccak(text="CREATE_NODE_OPERATOR_ROLE").hex()
RESUME_ROLE = web3.keccak(text="RESUME_ROLE").hex()
START_REFERRAL_SEASON_ROLE = web3.keccak(text="START_REFERRAL_SEASON_ROLE").hex()
END_REFERRAL_SEASON_ROLE = web3.keccak(text="END_REFERRAL_SEASON_ROLE").hex()
MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE = web3.keccak(text="MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE").hex()
REQUEST_BURN_SHARES_ROLE = web3.keccak(text="REQUEST_BURN_SHARES_ROLE").hex()
REQUEST_BURN_MY_STETH_ROLE = web3.keccak(text="REQUEST_BURN_MY_STETH_ROLE").hex()
ADD_FULL_WITHDRAWAL_REQUEST_ROLE = web3.keccak(text="ADD_FULL_WITHDRAWAL_REQUEST_ROLE").hex()
EXIT_BALANCE_LIMIT_SET_TOPIC = web3.keccak(text="ExitBalanceLimitSet(uint256,uint256,uint256)").hex()
CIRCUIT_BREAKER_PAUSER_SET_TOPIC = web3.keccak(text="PauserSet(address,address,address)").hex()
CIRCUIT_BREAKER_HEARTBEAT_UPDATED_TOPIC = web3.keccak(text="HeartbeatUpdated(address,uint256)").hex()
AO_CONTRACT_VERSION = 5
AO_CONSENSUS_VERSION = 6
AO_PREV_CONSENSUS_VERSION = 5
VEBO_CONTRACT_VERSION = 3
VEBO_CONSENSUS_VERSION = 5
VEBO_PREV_CONSENSUS_VERSION = 4
VEBO_MAX_VALIDATORS_PER_REPORT = 600
VALIDATORS_EXIT_BUS_MAX_EXIT_BALANCE_ETH = 416000
VALIDATORS_EXIT_BUS_BALANCE_PER_FRAME_ETH = 32
VALIDATORS_EXIT_BUS_FRAME_DURATION_IN_SEC = 48
WITHDRAWAL_VAULT_CONTRACT_VERSION = 3
LIDO_CONTRACT_VERSION = 4
TW_MAX_EXIT_REQUESTS = 250
TW_EXITS_PER_FRAME = 1
TW_FRAME_DURATION_IN_SEC = 240
CURATED_MODULE_ID = 5
CURATED_INITIAL_EPOCH = 47480
CURATED_EPOCHS_PER_FRAME = 1575
# TODO: restore Easy Track checks when full ET flow is enabled again.
# EASYTRACK = "0x284D91a7D47850d21A6DEaaC6E538AC7E5E6fc2a"
# STAKING_ROUTER = "0xCc820558B39ee15C7C45B59390B503b83fb499A8"
# UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x0000000000000000000000000000000000000000"
# ALLOW_CONSOLIDATION_PAIR_FACTORY = "0x0000000000000000000000000000000000000000"
# CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY = "0x0000000000000000000000000000000000000000"
# CONSOLIDATION_MIGRATOR = "0x0000000000000000000000000000000000000000"
# META_REGISTRY = "0x0000000000000000000000000000000000000000"


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = None
EXPECTED_DG_EVENTS_FROM_AGENT = 60
EXPECTED_DG_EVENTS_COUNT = 60
IPFS_DESCRIPTION_HASH = None
DG_ONLY_MODE = True


class StakingModuleItem(NamedTuple):
    id: int
    staking_module_address: str
    name: str
    staking_module_fee: int
    stake_share_limit: int
    treasury_fee: int
    priority_exit_share_threshold: int
    max_deposits_per_block: int
    min_deposit_block_distance: int


def _is_placeholder_address(value: str) -> bool:
    normalized = str(value).lower()
    return normalized in ("", "0x0000000000000000000000000000000000000000")


def _is_placeholder_text(value: str) -> bool:
    return "TODO:" in value


def _event_list(events: EventDict, name: str):
    return [event_item for event_item in events if event_item.name == name]


def _single_event(events: EventDict, name: str):
    items = _event_list(events, name)
    assert len(items) == 1, f"Expected exactly one {name} event, got {len(items)}"
    return items[0]


def _normalize_role(role_value) -> str:
    if isinstance(role_value, bytes):
        return role_value.hex().replace("0x", "")

    if hasattr(role_value, "hex") and callable(role_value.hex):
        return role_value.hex().replace("0x", "")

    return str(role_value).replace("0x", "")


def _assert_emitted_by(event_item, emitted_by: str) -> None:
    assert convert.to_address(event_item["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}, got {event_item['_emitted_by']}"


def _address_to_topic(address: str) -> str:
    return "0x" + "0" * 24 + address.lower().replace("0x", "")


def _raw_event_values(raw_event: dict) -> dict:
    return {item["name"]: item["value"] for item in raw_event["data"]}


def _decode_uint256_words(data_hex) -> list[int]:
    normalized = _normalize_hex_data(data_hex)
    return [int(normalized[i : i + 64], 16) for i in range(0, len(normalized), 64) if normalized[i : i + 64]]


def _normalize_hex_data(data_hex) -> str:
    if isinstance(data_hex, bytes):
        normalized = data_hex.hex()
    elif hasattr(data_hex, "hex") and callable(data_hex.hex):
        normalized = data_hex.hex()
    else:
        normalized = str(data_hex)

    return normalized.replace("0x", "")


def _group_raw_dg_events_from_receipt(
    receipt: TransactionReceipt,
    timelock: str,
    admin_executor: str,
) -> list[list[dict]]:
    events = tx_events_from_receipt(receipt)

    assert len(events) >= 1, "Unexpected raw DG events count"
    assert (
        convert.to_address(events[-1]["address"]) == convert.to_address(timelock)
        and events[-1]["name"] == "ProposalExecuted"
    ), "Unexpected raw DG service event"

    groups = []
    current_group = []

    for event in events[:-1]:
        current_group.append(event)

        is_end_of_group = event["name"] == "Executed" and convert.to_address(event["address"]) == convert.to_address(
            admin_executor
        )
        if is_end_of_group:
            groups.append(current_group)
            current_group = []

    return groups


def validate_proxy_upgrade_event(
    event: EventDict,
    implementation: str,
    emitted_by: Optional[str] = None,
    events_chain: Optional[list[str]] = None,
) -> None:
    _events_chain = events_chain or ["LogScriptCall", "Upgraded", "ScriptResult", "Executed"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("Upgraded") == 1

    upgraded_event = _single_event(event, "Upgraded")
    assert convert.to_address(upgraded_event["implementation"]) == convert.to_address(implementation), "Wrong implementation address"

    if emitted_by is not None:
        _assert_emitted_by(upgraded_event, emitted_by)


def validate_contract_version_set_event(
    event: EventDict,
    version: int,
    emitted_by: Optional[str] = None,
    events_chain: Optional[list[str]] = None,
) -> None:
    _events_chain = events_chain or ["LogScriptCall", "ContractVersionSet", "ScriptResult", "Executed"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ContractVersionSet") == 1
    contract_version_event = _single_event(event, "ContractVersionSet")
    assert contract_version_event["version"] == version, "Wrong contract version"

    if emitted_by is not None:
        _assert_emitted_by(contract_version_event, emitted_by)


def validate_consensus_version_set_event(
    event: EventDict,
    new_version: int,
    prev_version: int,
    emitted_by: Optional[str] = None,
    events_chain: Optional[list[str]] = None,
) -> None:
    _events_chain = events_chain or ["LogScriptCall", "ConsensusVersionSet", "ScriptResult", "Executed"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ConsensusVersionSet") == 1
    consensus_version_event = _single_event(event, "ConsensusVersionSet")
    assert consensus_version_event["version"] == new_version, "Wrong new consensus version"
    assert consensus_version_event["prevVersion"] == prev_version, "Wrong previous consensus version"

    if emitted_by is not None:
        _assert_emitted_by(consensus_version_event, emitted_by)


def validate_role_grant_event(
    event: EventDict,
    role_hash: str,
    account: str,
    sender: str,
    emitted_by: Optional[str] = None,
) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"])

    assert event.count("RoleGranted") == 1
    role_granted_event = _single_event(event, "RoleGranted")
    assert _normalize_role(role_granted_event["role"]) == role_hash.replace("0x", ""), "Wrong role hash"
    assert convert.to_address(role_granted_event["account"]) == convert.to_address(account), "Wrong granted account"
    assert convert.to_address(role_granted_event["sender"]) == convert.to_address(sender), "Wrong role grant sender"

    if emitted_by is not None:
        _assert_emitted_by(role_granted_event, emitted_by)


def validate_role_revoke_event(
    event: EventDict,
    role_hash: str,
    account: str,
    sender: str,
    emitted_by: Optional[str] = None,
) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "RoleRevoked", "ScriptResult", "Executed"])

    assert event.count("RoleRevoked") == 1
    role_revoked_event = _single_event(event, "RoleRevoked")
    assert _normalize_role(role_revoked_event["role"]) == role_hash.replace("0x", ""), "Wrong role hash"
    assert convert.to_address(role_revoked_event["account"]) == convert.to_address(account), "Wrong revoked account"
    assert convert.to_address(role_revoked_event["sender"]) == convert.to_address(sender), "Wrong role revoke sender"

    if emitted_by is not None:
        _assert_emitted_by(role_revoked_event, emitted_by)

def validate_dg_noop_event(event: EventDict) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "ScriptResult", "Executed"])
    assert event.count("LogScriptCall") == 1
    assert event.count("ScriptResult") == 1
    assert event.count("Executed") == 1

def validate_module_add(event: EventDict, module: StakingModuleItem, emitted_by: str, sender: str) -> None:
    validate_events_chain(
        [e.name for e in event],
        [
            "LogScriptCall",
            "StakingModuleAdded",
            "StakingModuleShareLimitSet",
            "StakingModuleFeesSet",
            "StakingModuleMaxDepositsPerBlockSet",
            "StakingModuleMinDepositBlockDistanceSet",
            "StakingRouterETHDeposited",
            "ScriptResult",
            "Executed",
        ],
    )

    module_added_event = _single_event(event, "StakingModuleAdded")
    assert module_added_event["stakingModuleId"] == module.id
    assert convert.to_address(module_added_event["stakingModule"]) == convert.to_address(module.staking_module_address)
    assert module_added_event["name"] == module.name
    assert convert.to_address(module_added_event["createdBy"]) == convert.to_address(sender)
    _assert_emitted_by(module_added_event, emitted_by)

    module_share_limit_event = _single_event(event, "StakingModuleShareLimitSet")
    assert module_share_limit_event["stakingModuleId"] == module.id
    assert module_share_limit_event["stakeShareLimit"] == module.stake_share_limit
    assert module_share_limit_event["priorityExitShareThreshold"] == module.priority_exit_share_threshold
    assert convert.to_address(module_share_limit_event["setBy"]) == convert.to_address(sender)
    _assert_emitted_by(module_share_limit_event, emitted_by)

    module_fees_event = _single_event(event, "StakingModuleFeesSet")
    assert module_fees_event["stakingModuleId"] == module.id
    assert module_fees_event["stakingModuleFee"] == module.staking_module_fee
    assert module_fees_event["treasuryFee"] == module.treasury_fee
    assert convert.to_address(module_fees_event["setBy"]) == convert.to_address(sender)
    _assert_emitted_by(module_fees_event, emitted_by)

    max_deposits_event = _single_event(event, "StakingModuleMaxDepositsPerBlockSet")
    assert max_deposits_event["stakingModuleId"] == module.id
    assert max_deposits_event["maxDepositsPerBlock"] == module.max_deposits_per_block
    assert convert.to_address(max_deposits_event["setBy"]) == convert.to_address(sender)
    _assert_emitted_by(max_deposits_event, emitted_by)

    min_distance_event = _single_event(event, "StakingModuleMinDepositBlockDistanceSet")
    assert min_distance_event["stakingModuleId"] == module.id
    assert min_distance_event["minDepositBlockDistance"] == module.min_deposit_block_distance
    assert convert.to_address(min_distance_event["setBy"]) == convert.to_address(sender)
    _assert_emitted_by(min_distance_event, emitted_by)

    deposited_event = _single_event(event, "StakingRouterETHDeposited")
    assert deposited_event["stakingModuleId"] == module.id
    assert deposited_event["amount"] == 0
    _assert_emitted_by(deposited_event, emitted_by)


def validate_exit_balance_limit_set_raw_group(raw_group: list[dict], validators_exit_bus_oracle: str) -> None:
    validate_events_chain(
        [event["name"] for event in raw_group],
        [
            "LogScriptCall",
            "Upgraded",
            "ContractVersionSet",
            "ConsensusVersionSet",
            "SetMaxValidatorsPerReport",
            "(unknown)",
            "ScriptResult",
            "Executed",
        ],
    )

    unknown_event = raw_group[5]
    unknown_event_values = _raw_event_values(unknown_event)
    assert convert.to_address(unknown_event["address"]) == convert.to_address(validators_exit_bus_oracle)
    assert unknown_event_values["topic1"] == EXIT_BALANCE_LIMIT_SET_TOPIC

    decoded_words = _decode_uint256_words(unknown_event_values["data"])
    assert decoded_words == [
        VALIDATORS_EXIT_BUS_MAX_EXIT_BALANCE_ETH,
        VALIDATORS_EXIT_BUS_BALANCE_PER_FRAME_ETH,
        VALIDATORS_EXIT_BUS_FRAME_DURATION_IN_SEC,
    ]


def validate_circuit_breaker_registration_raw_group(
    raw_group: list[dict],
    circuit_breaker: str,
    consolidation_gateway: str,
    curated_module_committee: str,
) -> None:
    validate_events_chain(
        [event["name"] for event in raw_group],
        ["LogScriptCall", "(unknown)", "(unknown)", "ScriptResult", "Executed"],
    )

    first_unknown_event = raw_group[1]
    second_unknown_event = raw_group[2]

    assert convert.to_address(first_unknown_event["address"]) == convert.to_address(circuit_breaker)
    first_unknown_event_values = _raw_event_values(first_unknown_event)
    assert first_unknown_event_values["topic1"] == CIRCUIT_BREAKER_PAUSER_SET_TOPIC
    assert first_unknown_event_values["topic2"] == _address_to_topic(consolidation_gateway)
    assert first_unknown_event_values["topic3"] == _address_to_topic("0x0000000000000000000000000000000000000000")
    assert first_unknown_event_values["topic4"] == _address_to_topic(curated_module_committee)
    assert _normalize_hex_data(first_unknown_event_values["data"]) == "00"

    assert convert.to_address(second_unknown_event["address"]) == convert.to_address(circuit_breaker)
    second_unknown_event_values = _raw_event_values(second_unknown_event)
    assert second_unknown_event_values["topic1"] == CIRCUIT_BREAKER_HEARTBEAT_UPDATED_TOPIC
    assert second_unknown_event_values["topic2"] == _address_to_topic(curated_module_committee)
    assert int(_normalize_hex_data(second_unknown_event_values["data"]), 16) > 0


@pytest.fixture(scope="module")
def runtime_upgrade_context():
    if network_name() != "hoodi-fork":
        pytest.skip("Run the dedicated Hoodi upgrade test on --network hoodi-fork.")

    upgrade_vote_script = UPGRADE_VOTE_SCRIPT

    if (
        _is_placeholder_address(upgrade_vote_script)
        or _is_placeholder_text(DG_PROPOSAL_METADATA)
        or _is_placeholder_text(get_ipfs_description(dg_only=DG_ONLY_MODE))
    ):
        pytest.skip(
            "Upgrade vote script address is missing. Set UPGRADE_VOTE_SCRIPT in "
            "scripts/upgrade_2026_04_14_hoodi_protocol_upgrade.py first."
        )

    vote_script = interface.UpgradeVoteScript(upgrade_vote_script)
    upgrade_template = vote_script.TEMPLATE()
    upgrade_config = interface.UpgradeConfig(vote_script.CONFIG())
    locator_impl = interface.LidoLocator(upgrade_config.getCoreUpgradeConfig()["newLocatorImpl"])

    global_config = upgrade_config.getGlobalConfig()
    core_config = upgrade_config.getCoreUpgradeConfig()
    csm_config = upgrade_config.getCSMUpgradeConfig()
    curated_config = upgrade_config.getCuratedModuleConfig()
    easy_track_new_factories, _ = upgrade_config.getEasyTrackConfig()

    dual_governance = interface.DualGovernance(upgrade_config.DUAL_GOVERNANCE())
    dual_governance_admin_executor = None
    for proposer in dual_governance.getProposers():
        try:
            proposer_account = proposer["account"]
            proposer_executor = proposer["executor"]
        except (KeyError, TypeError):
            proposer_account = proposer[0]
            proposer_executor = proposer[1]

        if convert.to_address(proposer_account) == convert.to_address(upgrade_config.VOTING()):
            dual_governance_admin_executor = proposer_executor
            break

    assert dual_governance_admin_executor is not None, "Voting proposer is not registered in Dual Governance"

    validator_strikes = interface.IValidatorStrikesV3(csm_config["strikes"])
    old_csm_ejector = validator_strikes.ejector()

    return {
        "upgrade_vote_script": upgrade_vote_script,
        "upgrade_template": upgrade_template,
        "voting": upgrade_config.VOTING(),
        "agent": upgrade_config.AGENT(),
        "dual_governance": upgrade_config.DUAL_GOVERNANCE(),
        "dual_governance_admin_executor": dual_governance_admin_executor,
        "acl": core_config["acl"],
        "aragon_kernel": core_config["kernel"],
        "lido": global_config["lido"],
        "lido_app_id": core_config["lidoAppId"],
        "lido_impl": core_config["newLidoImpl"],
        "lido_locator": core_config["locator"],
        "lido_locator_impl": core_config["newLocatorImpl"],
        "staking_router": global_config["stakingRouter"],
        "staking_router_impl": core_config["newStakingRouterImpl"],
        "accounting_oracle": core_config["accountingOracle"],
        "accounting_oracle_impl": core_config["newAccountingOracleImpl"],
        "validators_exit_bus_oracle": core_config["validatorsExitBusOracle"],
        "validators_exit_bus_oracle_impl": core_config["newValidatorsExitBusOracleImpl"],
        "accounting": core_config["accounting"],
        "accounting_impl": core_config["newAccountingImpl"],
        "withdrawal_vault": core_config["withdrawalVault"],
        "withdrawal_vault_impl": core_config["newWithdrawalVaultImpl"],
        "validator_exit_delay_verifier": locator_impl.validatorExitDelayVerifier(),
        "easytrack_evm_script_executor": global_config["easyTrackEVMScriptExecutor"],
        "circuit_breaker": global_config["circuitBreaker"],
        "consolidation_gateway": core_config["consolidationGateway"],
        "curated_module_committee": core_config["curatedModuleCommittee"],
        "old_deposit_security_module": core_config["oldDepositSecurityModule"],
        "new_deposit_security_module": core_config["newDepositSecurityModule"],
        "triggerable_withdrawals_gateway": global_config["triggerableWithdrawalsGateway"],
        "burner": global_config["burner"],
        "csm": csm_config["csm"],
        "csm_impl": csm_config["csmImpl"],
        "cs_parameters_registry": csm_config["parametersRegistry"],
        "cs_parameters_registry_impl": csm_config["parametersRegistryImpl"],
        "cs_fee_oracle": csm_config["feeOracle"],
        "cs_fee_oracle_impl": csm_config["feeOracleImpl"],
        "cs_vetted_gate": csm_config["vettedGate"],
        "cs_vetted_gate_impl": csm_config["vettedGateImpl"],
        "cs_accounting": csm_config["accounting"],
        "cs_accounting_impl": csm_config["accountingImpl"],
        "cs_fee_distributor": csm_config["feeDistributor"],
        "cs_fee_distributor_impl": csm_config["feeDistributorImpl"],
        "cs_exit_penalties": csm_config["exitPenalties"],
        "cs_exit_penalties_impl": csm_config["exitPenaltiesImpl"],
        "cs_validator_strikes": csm_config["strikes"],
        "cs_validator_strikes_impl": csm_config["strikesImpl"],
        "old_verifier": csm_config["verifier"],
        "verifier_v3": csm_config["verifierV3"],
        "old_permissionless_gate": csm_config["oldPermissionlessGate"],
        "new_permissionless_gate": csm_config["permissionlessGate"],
        "ics_manager": csm_config["identifiedCommunityStakersGateManager"],
        "csm_general_delayed_penalty_reporter": csm_config["generalDelayedPenaltyReporter"],
        "csm_penalties_manager": csm_config["penaltiesManager"],
        "old_csm_ejector": old_csm_ejector,
        "csm_ejector": csm_config["ejector"],
        "curated_module": curated_config["module"],
        "curated_accounting": curated_config["accounting"],
        "curated_ejector": curated_config["ejector"],
        "curated_hash_consensus": curated_config["hashConsensus"],
        "curated_module_item": StakingModuleItem(
            id=CURATED_MODULE_ID,
            staking_module_address=curated_config["module"],
            name=curated_config["moduleName"],
            staking_module_fee=curated_config["stakingModuleFee"],
            stake_share_limit=curated_config["stakeShareLimit"],
            treasury_fee=curated_config["treasuryFee"],
            priority_exit_share_threshold=curated_config["priorityExitShareThreshold"],
            max_deposits_per_block=curated_config["maxDepositsPerBlock"],
            min_deposit_block_distance=curated_config["minDepositBlockDistance"],
        ),
        "update_staking_module_share_limits_factory": easy_track_new_factories["UpdateStakingModuleShareLimits"],
        "allow_consolidation_pair_factory": easy_track_new_factories["AllowConsolidationPair"],
        "create_or_update_operator_group_factory": easy_track_new_factories["CreateOrUpdateOperatorGroup"],
        "consolidation_migrator": core_config["consolidationMigrator"],
        "meta_registry": curated_config["metaRegistry"],
    }


@pytest.fixture(scope="module")
def dual_governance_proposal_calls(runtime_upgrade_context):
    dg_items = get_dg_items(runtime_upgrade_context["upgrade_vote_script"])

    proposal_calls = []
    for target, data in dg_items:
        proposal_calls.append(
            {
                "target": target,
                "value": 0,
                "data": data,
            }
        )

    return proposal_calls


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls, runtime_upgrade_context):
    ctx = runtime_upgrade_context

    voting = interface.Voting(ctx["voting"])
    agent = interface.Agent(ctx["agent"])
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(ctx["dual_governance"])
    # TODO: restore once Easy Track items are enabled in the vote again.
    # easy_track = interface.EasyTrack(EASYTRACK)
    # staking_router = interface.StakingRouter(STAKING_ROUTER)
    # consolidation_migrator = interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR)
    # meta_registry = interface.IMetaRegistry(META_REGISTRY)

    vote_desc_items, call_script_items = get_vote_items(
        dg_only=DG_ONLY_MODE,
        upgrade_vote_script=ctx["upgrade_vote_script"],
    )
    dg_items = get_dg_items(ctx["upgrade_vote_script"])
    upgrade_template = ctx["upgrade_template"]

    expected_vote_events_count = EXPECTED_VOTE_EVENTS_COUNT or len(call_script_items)
    expected_dg_events_from_agent = EXPECTED_DG_EVENTS_FROM_AGENT or len(dg_items)
    expected_dg_events_count = EXPECTED_DG_EVENTS_COUNT or len(dg_items)
    expected_ipfs_description_hash = IPFS_DESCRIPTION_HASH or calculate_vote_ipfs_description(
        get_ipfs_description(dg_only=DG_ONLY_MODE)
    )["cid"]

    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        if EXPECTED_VOTE_ID is not None:
            assert vote_id == EXPECTED_VOTE_ID
    elif EXPECTED_VOTE_ID is not None and voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        vote_id, _ = start_vote(
            {"from": ldo_holder},
            silent=True,
            dg_only=DG_ONLY_MODE,
            upgrade_vote_script=ctx["upgrade_vote_script"],
        )

    onchain_script = voting.getVote(vote_id)["script"]
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()

    expected_dg_proposal_id = EXPECTED_DG_PROPOSAL_ID
    dg_proposals_count_before_vote_execution = timelock.getProposalsCount()

    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        # TODO: restore Easy Track pre-vote checks together with full ET flow.
        # initial_factories = easy_track.getEVMScriptFactories()
        # assert UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY not in initial_factories
        # assert ALLOW_CONSOLIDATION_PAIR_FACTORY not in initial_factories
        # assert CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY not in initial_factories

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == expected_ipfs_description_hash

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        # TODO: restore Easy Track post-vote checks together with full ET flow.
        # new_factories = easy_track.getEVMScriptFactories()
        # assert UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY in new_factories
        # assert ALLOW_CONSOLIDATION_PAIR_FACTORY in new_factories
        # assert CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY in new_factories

        assert len(vote_events) == expected_vote_events_count
        assert count_vote_items_by_events(vote_tx, voting.address) == expected_vote_events_count

        if expected_dg_proposal_id is None:
            expected_dg_proposal_id = dg_proposals_count_before_vote_execution + 1

        assert expected_dg_proposal_id == timelock.getProposalsCount()

        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=expected_dg_proposal_id,
            proposer=ctx["voting"],
            executor=ctx["dual_governance_admin_executor"],
            metadata=DG_PROPOSAL_METADATA,
            proposal_calls=dual_governance_proposal_calls,
        )

        # TODO: restore ET event validation when full ET flow is enabled again.
        # validate_evmscript_factory_added_event(
        #     event=vote_events[1],
        #     p=EVMScriptFactoryAdded(
        #         factory_addr=UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
        #         permissions=create_permissions(staking_router, "updateModuleShares"),
        #     ),
        #     emitted_by=easy_track,
        # )
        #
        # validate_evmscript_factory_added_event(
        #     event=vote_events[2],
        #     p=EVMScriptFactoryAdded(
        #         factory_addr=ALLOW_CONSOLIDATION_PAIR_FACTORY,
        #         permissions=create_permissions(consolidation_migrator, "allowPair"),
        #     ),
        #     emitted_by=easy_track,
        # )
        #
        # validate_evmscript_factory_added_event(
        #     event=vote_events[3],
        #     p=EVMScriptFactoryAdded(
        #         factory_addr=CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY,
        #         permissions=create_permissions(meta_registry, "createOrUpdateOperatorGroup"),
        #     ),
        #     emitted_by=easy_track,
        # )
    elif expected_dg_proposal_id is None:
        pytest.skip("Fill EXPECTED_DG_PROPOSAL_ID to run the DG part against an already executed live Hoodi vote.")

    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if expected_dg_proposal_id is not None:
        details = timelock.getProposalDetails(expected_dg_proposal_id)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================

            # TODO Acceptance tests (before DG state)

            # TODO Scenario tests (before DG state)

            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(expected_dg_proposal_id, {"from": stranger})

            if timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)

                dg_tx: TransactionReceipt = timelock.execute(expected_dg_proposal_id, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=ctx["dual_governance_admin_executor"],
                )
                raw_dg_events = _group_raw_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=ctx["dual_governance_admin_executor"],
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == expected_dg_events_from_agent
                assert len(dg_events) == expected_dg_events_count
                assert len(raw_dg_events) == expected_dg_events_count

                # === DG EXECUTION EVENTS VALIDATION ===

                # 1. Call UpgradeTemplate.startUpgrade
                validate_events_chain([e.name for e in dg_events[0]], ["LogScriptCall", "UpgradeStarted", "ScriptResult", "Executed"])
                upgrade_started_event = _single_event(dg_events[0], "UpgradeStarted")
                _assert_emitted_by(upgrade_started_event, upgrade_template)

                # 2. Upgrade LidoLocator proxy
                validate_proxy_upgrade_event(dg_events[1], ctx["lido_locator_impl"], emitted_by=ctx["lido_locator"])

                # 3. Upgrade and finalize StakingRouter
                validate_proxy_upgrade_event(
                    dg_events[2],
                    ctx["staking_router_impl"],
                    emitted_by=ctx["staking_router"],
                    events_chain=[
                        "LogScriptCall",
                        "Upgraded",
                        "RoleGranted",
                        "RoleGranted",
                        "RoleGranted",
                        "RoleGranted",
                        "RoleGranted",
                        "RoleGranted",
                        "RoleGranted",
                        "RoleGranted",
                        "Initialized",
                        "ScriptResult",
                        "Executed",
                    ],
                )
                role_grants = _event_list(dg_events[2], "RoleGranted")
                assert len(role_grants) == 8
                for role_granted_event, (role_hash, account) in zip(
                    role_grants,
                    [
                        (DEFAULT_ADMIN_ROLE, ctx["agent"]),
                        (STAKING_MODULE_MANAGE_ROLE, ctx["agent"]),
                        (STAKING_MODULE_MANAGE_ROLE, HOODI_LEGACY_STAKING_MODULE_MANAGER),
                        (STAKING_MODULE_UNVETTING_ROLE, ctx["old_deposit_security_module"]),
                        (REPORT_EXITED_VALIDATORS_ROLE, ctx["accounting_oracle"]),
                        (REPORT_VALIDATOR_EXITING_STATUS_ROLE, ctx["validator_exit_delay_verifier"]),
                        (REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE, ctx["triggerable_withdrawals_gateway"]),
                        (REPORT_REWARDS_MINTED_ROLE, ctx["accounting"]),
                    ],
                ):
                    assert _normalize_role(role_granted_event["role"]) == role_hash.replace("0x", "")
                    assert convert.to_address(role_granted_event["account"]) == convert.to_address(account)
                    assert convert.to_address(role_granted_event["sender"]) == convert.to_address(ctx["agent"])
                    _assert_emitted_by(role_granted_event, ctx["staking_router"])
                initialized_event = _single_event(dg_events[2], "Initialized")
                assert initialized_event["version"] == 4
                _assert_emitted_by(initialized_event, ctx["staking_router"])

                # 4. Upgrade and finalize AccountingOracle
                validate_proxy_upgrade_event(
                    dg_events[3],
                    ctx["accounting_oracle_impl"],
                    emitted_by=ctx["accounting_oracle"],
                    events_chain=[
                        "LogScriptCall",
                        "Upgraded",
                        "ContractVersionSet",
                        "ConsensusVersionSet",
                        "ScriptResult",
                        "Executed",
                    ],
                )
                validate_contract_version_set_event(
                    dg_events[3],
                    AO_CONTRACT_VERSION,
                    emitted_by=ctx["accounting_oracle"],
                    events_chain=[
                        "LogScriptCall",
                        "Upgraded",
                        "ContractVersionSet",
                        "ConsensusVersionSet",
                        "ScriptResult",
                        "Executed",
                    ],
                )
                validate_consensus_version_set_event(
                    dg_events[3],
                    AO_CONSENSUS_VERSION,
                    AO_PREV_CONSENSUS_VERSION,
                    emitted_by=ctx["accounting_oracle"],
                    events_chain=[
                        "LogScriptCall",
                        "Upgraded",
                        "ContractVersionSet",
                        "ConsensusVersionSet",
                        "ScriptResult",
                        "Executed",
                    ],
                )

                # 5. Upgrade and finalize ValidatorsExitBusOracle
                validate_proxy_upgrade_event(
                    dg_events[4],
                    ctx["validators_exit_bus_oracle_impl"],
                    emitted_by=ctx["validators_exit_bus_oracle"],
                    events_chain=[
                        "LogScriptCall",
                        "Upgraded",
                        "ContractVersionSet",
                        "ConsensusVersionSet",
                        "SetMaxValidatorsPerReport",
                        "(unknown)",
                        "ScriptResult",
                        "Executed",
                    ],
                )
                validate_contract_version_set_event(
                    dg_events[4],
                    VEBO_CONTRACT_VERSION,
                    emitted_by=ctx["validators_exit_bus_oracle"],
                    events_chain=[
                        "LogScriptCall",
                        "Upgraded",
                        "ContractVersionSet",
                        "ConsensusVersionSet",
                        "SetMaxValidatorsPerReport",
                        "(unknown)",
                        "ScriptResult",
                        "Executed",
                    ],
                )
                validate_consensus_version_set_event(
                    dg_events[4],
                    VEBO_CONSENSUS_VERSION,
                    VEBO_PREV_CONSENSUS_VERSION,
                    emitted_by=ctx["validators_exit_bus_oracle"],
                    events_chain=[
                        "LogScriptCall",
                        "Upgraded",
                        "ContractVersionSet",
                        "ConsensusVersionSet",
                        "SetMaxValidatorsPerReport",
                        "(unknown)",
                        "ScriptResult",
                        "Executed",
                    ],
                )
                set_max_validators_event = _single_event(dg_events[4], "SetMaxValidatorsPerReport")
                assert set_max_validators_event["maxValidatorsPerReport"] == VEBO_MAX_VALIDATORS_PER_REPORT
                _assert_emitted_by(set_max_validators_event, ctx["validators_exit_bus_oracle"])
                validate_exit_balance_limit_set_raw_group(raw_dg_events[4], ctx["validators_exit_bus_oracle"])

                # 6. Upgrade Accounting implementation
                validate_proxy_upgrade_event(dg_events[5], ctx["accounting_impl"], emitted_by=ctx["accounting"])

                # 7. Upgrade and finalize WithdrawalVault
                validate_proxy_upgrade_event(
                    dg_events[6],
                    ctx["withdrawal_vault_impl"],
                    emitted_by=ctx["withdrawal_vault"],
                    events_chain=["LogScriptCall", "Upgraded", "ContractVersionSet", "ScriptResult", "Executed"],
                )
                validate_contract_version_set_event(
                    dg_events[6],
                    WITHDRAWAL_VAULT_CONTRACT_VERSION,
                    emitted_by=ctx["withdrawal_vault"],
                    events_chain=["LogScriptCall", "Upgraded", "ContractVersionSet", "ScriptResult", "Executed"],
                )

                # 8. Grant APP_MANAGER_ROLE on Kernel to Agent
                validate_aragon_grant_permission_event(
                    dg_events[7],
                    entity=ctx["agent"],
                    app=ctx["aragon_kernel"],
                    role=APP_MANAGER_ROLE,
                    emitted_by=ctx["acl"],
                )

                # 9. Set new Lido implementation in Kernel
                validate_aragon_set_app_event(
                    dg_events[8],
                    app_id=ctx["lido_app_id"],
                    app=ctx["lido_impl"],
                    emitted_by=ctx["aragon_kernel"],
                )

                # 10. Revoke APP_MANAGER_ROLE on Kernel from Agent
                validate_aragon_revoke_permission_event(
                    dg_events[9],
                    entity=ctx["agent"],
                    app=ctx["aragon_kernel"],
                    role=APP_MANAGER_ROLE,
                    emitted_by=ctx["acl"],
                )

                # 11. Grant BUFFER_RESERVE_MANAGER_ROLE on Lido and transfer permission manager to Agent
                validate_events_chain(
                    [e.name for e in dg_events[10]],
                    ["LogScriptCall", "SetPermission", "ChangePermissionManager", "ScriptResult", "Executed"],
                )
                set_permission_event = _single_event(dg_events[10], "SetPermission")
                assert convert.to_address(set_permission_event["entity"]) == convert.to_address(ctx["agent"])
                assert convert.to_address(set_permission_event["app"]) == convert.to_address(ctx["lido"])
                assert set_permission_event["role"] == BUFFER_RESERVE_MANAGER_ROLE
                assert set_permission_event["allowed"] is True
                _assert_emitted_by(set_permission_event, ctx["acl"])
                change_permission_manager_event = _single_event(dg_events[10], "ChangePermissionManager")
                assert convert.to_address(change_permission_manager_event["app"]) == convert.to_address(ctx["lido"])
                assert change_permission_manager_event["role"] == BUFFER_RESERVE_MANAGER_ROLE
                assert convert.to_address(change_permission_manager_event["manager"]) == convert.to_address(ctx["agent"])
                _assert_emitted_by(change_permission_manager_event, ctx["acl"])

                # 12. Finalize Lido contract version
                validate_contract_version_set_event(dg_events[11], LIDO_CONTRACT_VERSION, emitted_by=ctx["lido"])

                # 13. Grant STAKING_MODULE_SHARE_MANAGE_ROLE to EasyTrack executor
                validate_role_grant_event(
                    dg_events[12],
                    STAKING_MODULE_SHARE_MANAGE_ROLE,
                    ctx["easytrack_evm_script_executor"],
                    sender=ctx["agent"],
                    emitted_by=ctx["staking_router"],
                )

                # 14. Revoke STAKING_MODULE_UNVETTING_ROLE from old DSM
                validate_role_revoke_event(
                    dg_events[13],
                    STAKING_MODULE_UNVETTING_ROLE,
                    ctx["old_deposit_security_module"],
                    sender=ctx["agent"],
                    emitted_by=ctx["staking_router"],
                )

                # 15. Grant STAKING_MODULE_UNVETTING_ROLE to new DSM
                validate_role_grant_event(
                    dg_events[14],
                    STAKING_MODULE_UNVETTING_ROLE,
                    ctx["new_deposit_security_module"],
                    sender=ctx["agent"],
                    emitted_by=ctx["staking_router"],
                )

                # 16. Grant TW_EXIT_LIMIT_MANAGER_ROLE to Agent
                validate_role_grant_event(
                    dg_events[15],
                    TW_EXIT_LIMIT_MANAGER_ROLE,
                    ctx["agent"],
                    sender=ctx["agent"],
                    emitted_by=ctx["triggerable_withdrawals_gateway"],
                )

                # 17. Set TWG exit limits
                validate_events_chain(
                    [e.name for e in dg_events[16]],
                    ["LogScriptCall", "ExitRequestsLimitSet", "ScriptResult", "Executed"],
                )
                exit_requests_limit_set_event = _single_event(dg_events[16], "ExitRequestsLimitSet")
                assert exit_requests_limit_set_event["maxExitRequestsLimit"] == TW_MAX_EXIT_REQUESTS
                assert exit_requests_limit_set_event["exitsPerFrame"] == TW_EXITS_PER_FRAME
                assert exit_requests_limit_set_event["frameDurationInSec"] == TW_FRAME_DURATION_IN_SEC
                _assert_emitted_by(exit_requests_limit_set_event, ctx["triggerable_withdrawals_gateway"])

                # 18. Register CircuitBreaker integration
                validate_circuit_breaker_registration_raw_group(
                    raw_dg_events[17],
                    circuit_breaker=ctx["circuit_breaker"],
                    consolidation_gateway=ctx["consolidation_gateway"],
                    curated_module_committee=ctx["curated_module_committee"],
                )

                # 19. Upgrade and initialize CSM
                validate_proxy_upgrade_event(
                    dg_events[18],
                    ctx["csm_impl"],
                    emitted_by=ctx["csm"],
                    events_chain=["LogScriptCall", "Upgraded", "Initialized", "ScriptResult", "Executed"],
                )
                initialized_event = _single_event(dg_events[18], "Initialized")
                assert initialized_event["version"] == 3
                _assert_emitted_by(initialized_event, ctx["csm"])

                # 20. Upgrade and initialize CSParametersRegistry
                validate_proxy_upgrade_event(
                    dg_events[19],
                    ctx["cs_parameters_registry_impl"],
                    emitted_by=ctx["cs_parameters_registry"],
                    events_chain=["LogScriptCall", "Upgraded", "Initialized", "ScriptResult", "Executed"],
                )
                initialized_event = _single_event(dg_events[19], "Initialized")
                assert initialized_event["version"] == 3
                _assert_emitted_by(initialized_event, ctx["cs_parameters_registry"])

                # 21. Upgrade and finalize CSFeeOracle
                validate_proxy_upgrade_event(
                    dg_events[20],
                    ctx["cs_fee_oracle_impl"],
                    emitted_by=ctx["cs_fee_oracle"],
                    events_chain=["LogScriptCall", "Upgraded", "ConsensusVersionSet", "ContractVersionSet", "ScriptResult", "Executed"],
                )
                validate_consensus_version_set_event(
                    dg_events[20],
                    4,
                    3,
                    emitted_by=ctx["cs_fee_oracle"],
                    events_chain=["LogScriptCall", "Upgraded", "ConsensusVersionSet", "ContractVersionSet", "ScriptResult", "Executed"],
                )
                validate_contract_version_set_event(
                    dg_events[20],
                    3,
                    emitted_by=ctx["cs_fee_oracle"],
                    events_chain=["LogScriptCall", "Upgraded", "ConsensusVersionSet", "ContractVersionSet", "ScriptResult", "Executed"],
                )

                # 22. Upgrade CSVettedGate
                validate_proxy_upgrade_event(dg_events[21], ctx["cs_vetted_gate_impl"], emitted_by=ctx["cs_vetted_gate"])

                # 23. Upgrade and initialize CSAccounting
                validate_proxy_upgrade_event(
                    dg_events[22],
                    ctx["cs_accounting_impl"],
                    emitted_by=ctx["cs_accounting"],
                    events_chain=["LogScriptCall", "Upgraded", "Initialized", "ScriptResult", "Executed"],
                )
                initialized_event = _single_event(dg_events[22], "Initialized")
                assert initialized_event["version"] == 3
                _assert_emitted_by(initialized_event, ctx["cs_accounting"])

                # 24. Upgrade and initialize CSFeeDistributor
                validate_proxy_upgrade_event(
                    dg_events[23],
                    ctx["cs_fee_distributor_impl"],
                    emitted_by=ctx["cs_fee_distributor"],
                    events_chain=["LogScriptCall", "Upgraded", "Initialized", "ScriptResult", "Executed"],
                )
                initialized_event = _single_event(dg_events[23], "Initialized")
                assert initialized_event["version"] == 3
                _assert_emitted_by(initialized_event, ctx["cs_fee_distributor"])

                # 25. Upgrade CSExitPenalties
                validate_proxy_upgrade_event(dg_events[24], ctx["cs_exit_penalties_impl"], emitted_by=ctx["cs_exit_penalties"])

                # 26. Upgrade CSValidatorStrikes
                validate_proxy_upgrade_event(dg_events[25], ctx["cs_validator_strikes_impl"], emitted_by=ctx["cs_validator_strikes"])

                # 27. Set CSM ejector
                validate_events_chain([e.name for e in dg_events[26]], ["LogScriptCall", "EjectorSet", "ScriptResult", "Executed"])
                ejector_set_event = _single_event(dg_events[26], "EjectorSet")
                assert convert.to_address(ejector_set_event["ejector"]) == convert.to_address(ctx["csm_ejector"])
                _assert_emitted_by(ejector_set_event, ctx["cs_validator_strikes"])

                # 28. Grant REPORT_GENERAL_DELAYED_PENALTY_ROLE
                validate_role_grant_event(
                    dg_events[27],
                    REPORT_GENERAL_DELAYED_PENALTY_ROLE,
                    ctx["csm_general_delayed_penalty_reporter"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 29. Grant SETTLE_GENERAL_DELAYED_PENALTY_ROLE
                validate_role_grant_event(
                    dg_events[28],
                    SETTLE_GENERAL_DELAYED_PENALTY_ROLE,
                    ctx["easytrack_evm_script_executor"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 30. Revoke REPORT_EL_REWARDS_STEALING_PENALTY_ROLE
                validate_role_revoke_event(
                    dg_events[29],
                    REPORT_EL_REWARDS_STEALING_PENALTY_ROLE,
                    ctx["csm_general_delayed_penalty_reporter"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 31. Revoke SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE
                validate_role_revoke_event(
                    dg_events[30],
                    SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE,
                    ctx["easytrack_evm_script_executor"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 32. Revoke VERIFIER_ROLE from old verifier
                validate_role_revoke_event(
                    dg_events[31],
                    VERIFIER_ROLE,
                    ctx["old_verifier"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 33. Grant VERIFIER_ROLE to verifier v3
                validate_role_grant_event(
                    dg_events[32],
                    VERIFIER_ROLE,
                    ctx["verifier_v3"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 34. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE
                validate_role_grant_event(
                    dg_events[33],
                    REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE,
                    ctx["verifier_v3"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 35. Grant REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE
                validate_role_grant_event(
                    dg_events[34],
                    REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE,
                    ctx["easytrack_evm_script_executor"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 36. Revoke CREATE_NODE_OPERATOR_ROLE from old permissionless gate
                validate_role_revoke_event(
                    dg_events[35],
                    CREATE_NODE_OPERATOR_ROLE,
                    ctx["old_permissionless_gate"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 37. Grant CREATE_NODE_OPERATOR_ROLE to new permissionless gate
                validate_role_grant_event(
                    dg_events[36],
                    CREATE_NODE_OPERATOR_ROLE,
                    ctx["new_permissionless_gate"],
                    sender=ctx["agent"],
                    emitted_by=ctx["csm"],
                )

                # 38. No-op DG item
                validate_dg_noop_event(dg_events[37])

                # 39. No-op DG item
                validate_dg_noop_event(dg_events[38])

                # 40. No-op DG item
                validate_dg_noop_event(dg_events[39])

                # 41. No-op DG item
                validate_dg_noop_event(dg_events[40])

                # 42. Revoke START_REFERRAL_SEASON_ROLE from Agent
                validate_role_revoke_event(
                    dg_events[41],
                    START_REFERRAL_SEASON_ROLE,
                    ctx["agent"],
                    sender=ctx["agent"],
                    emitted_by=ctx["cs_vetted_gate"],
                )

                # 43. Revoke END_REFERRAL_SEASON_ROLE from ICS manager
                validate_role_revoke_event(
                    dg_events[42],
                    END_REFERRAL_SEASON_ROLE,
                    ctx["ics_manager"],
                    sender=ctx["agent"],
                    emitted_by=ctx["cs_vetted_gate"],
                )

                # 44. No-op DG item
                validate_dg_noop_event(dg_events[43])

                # 45. No-op DG item
                validate_dg_noop_event(dg_events[44])

                # 46. No-op DG item
                validate_dg_noop_event(dg_events[45])

                # 47. No-op DG item
                validate_dg_noop_event(dg_events[46])

                # 48. Grant MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE
                validate_role_grant_event(
                    dg_events[47],
                    MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE,
                    ctx["csm_penalties_manager"],
                    sender=ctx["agent"],
                    emitted_by=ctx["cs_parameters_registry"],
                )

                # 49. Revoke REQUEST_BURN_SHARES_ROLE from CSAccounting
                validate_role_revoke_event(
                    dg_events[48],
                    REQUEST_BURN_SHARES_ROLE,
                    ctx["cs_accounting"],
                    sender=ctx["agent"],
                    emitted_by=ctx["burner"],
                )

                # 50. Grant REQUEST_BURN_MY_STETH_ROLE to CSAccounting
                validate_role_grant_event(
                    dg_events[49],
                    REQUEST_BURN_MY_STETH_ROLE,
                    ctx["cs_accounting"],
                    sender=ctx["agent"],
                    emitted_by=ctx["burner"],
                )

                # 51. Revoke ADD_FULL_WITHDRAWAL_REQUEST_ROLE from old CSM ejector
                validate_role_revoke_event(
                    dg_events[50],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    ctx["old_csm_ejector"],
                    sender=ctx["agent"],
                    emitted_by=ctx["triggerable_withdrawals_gateway"],
                )

                # 52. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to CSM ejector
                validate_role_grant_event(
                    dg_events[51],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    ctx["csm_ejector"],
                    sender=ctx["agent"],
                    emitted_by=ctx["triggerable_withdrawals_gateway"],
                )

                # 53. Add curated-onchain-v2 module
                validate_module_add(dg_events[52], ctx["curated_module_item"], emitted_by=ctx["staking_router"], sender=ctx["agent"])

                # 54. Grant REQUEST_BURN_MY_STETH_ROLE to curated accounting
                validate_role_grant_event(
                    dg_events[53],
                    REQUEST_BURN_MY_STETH_ROLE,
                    ctx["curated_accounting"],
                    sender=ctx["agent"],
                    emitted_by=ctx["burner"],
                )

                # 55. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to curated ejector
                validate_role_grant_event(
                    dg_events[54],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    ctx["curated_ejector"],
                    sender=ctx["agent"],
                    emitted_by=ctx["triggerable_withdrawals_gateway"],
                )

                # 56. Grant RESUME_ROLE on curated module to Agent
                validate_role_grant_event(
                    dg_events[55],
                    RESUME_ROLE,
                    ctx["agent"],
                    sender=ctx["agent"],
                    emitted_by=ctx["curated_module"],
                )

                # 57. Resume curated module
                validate_events_chain([e.name for e in dg_events[56]], ["LogScriptCall", "Resumed", "ScriptResult", "Executed"])
                resumed_event = _single_event(dg_events[56], "Resumed")
                _assert_emitted_by(resumed_event, ctx["curated_module"])

                # 58. Revoke RESUME_ROLE from Agent
                validate_role_revoke_event(
                    dg_events[57],
                    RESUME_ROLE,
                    ctx["agent"],
                    sender=ctx["agent"],
                    emitted_by=ctx["curated_module"],
                )

                # 59. Set curated HashConsensus frame config
                validate_events_chain([e.name for e in dg_events[58]], ["LogScriptCall", "FrameConfigSet", "ScriptResult", "Executed"])
                frame_config_set_event = _single_event(dg_events[58], "FrameConfigSet")
                assert frame_config_set_event["newInitialEpoch"] == CURATED_INITIAL_EPOCH
                assert frame_config_set_event["newEpochsPerFrame"] == CURATED_EPOCHS_PER_FRAME
                _assert_emitted_by(frame_config_set_event, ctx["curated_hash_consensus"])

                # 60. Call UpgradeTemplate.finishUpgrade
                validate_events_chain([e.name for e in dg_events[59]], ["LogScriptCall", "UpgradeFinished", "ScriptResult", "Executed"])
                upgrade_finished_event = _single_event(dg_events[59], "UpgradeFinished")
                _assert_emitted_by(upgrade_finished_event, upgrade_template)

        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # TODO Acceptance tests (after DG state)

        # TODO Scenario tests (after DG state)
