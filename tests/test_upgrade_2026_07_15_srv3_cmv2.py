"""
Acceptance test for vote 2026_07_15 — Staking Router v3 + Curated Module v2 + Community Staking Module v3.

Structure follows tests/_test_2026_MM_DD.py:
  * Arrange variables
  * Identify or create vote
  * Execute vote (before / after voting checks)
  * Execute Dual Governance proposal (before / after DG checks)

All protocol addresses are resolved at runtime from the on-chain UpgradeConfig
(referenced by the deployed UpgradeVoteScript) so the test tracks the deployed
artefacts without a hand-maintained address list.

Run:
    ETHERSCAN_TOKEN=<token> \
    poetry run brownie test tests/test_upgrade_2026_07_15_srv3_cmv2.py --network=mfh-1 -v
"""

import os

from typing import NamedTuple, Optional

import pytest

from brownie import chain, convert, history, interface, web3
from brownie.network.contract import Contract
from brownie.network.event import EventDict
from brownie.network.transaction import TransactionReceipt

from utils.config import network_name, TIMELOCK
from utils.test.tx_tracing_helpers import (
    add_event_emitter,
    count_vote_items_by_events,
    display_dg_events,
    display_voting_events,
    group_dg_events_from_receipt,
    group_voting_events_from_receipt,
)
from utils.tx_tracing import tx_events_from_receipt
from utils.evm_script import encode_call_script
from utils.dual_governance import PROPOSAL_STATUS, process_proposals
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.easy_track import (
    EVMScriptFactoryAdded,
    validate_evmscript_factory_added_event,
    validate_evmscript_factory_removed_event,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import calculate_vote_ipfs_description, get_lido_vote_cid_from_str

# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_2026_07_15_srv3_cmv2 import (
    IPFS_DESCRIPTION,
    start_vote,
    get_vote_items,
    get_dg_items,
    DG_PROPOSAL_METADATA,
    UPGRADE_VOTE_SCRIPT,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
def _selector(signature: str) -> str:
    return web3.keccak(text=signature).hex()[:10]


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"

# --- Aragon roles ---
APP_MANAGER_ROLE = web3.keccak(text="APP_MANAGER_ROLE").hex()
BUFFER_RESERVE_MANAGER_ROLE = web3.keccak(text="BUFFER_RESERVE_MANAGER_ROLE").hex()

# --- StakingRouter roles (finalizeUpgrade_v4 migrates these, in this exact order) ---
MANAGE_WITHDRAWAL_CREDENTIALS_ROLE = web3.keccak(text="MANAGE_WITHDRAWAL_CREDENTIALS_ROLE").hex()
STAKING_MODULE_MANAGE_ROLE = web3.keccak(text="STAKING_MODULE_MANAGE_ROLE").hex()
STAKING_MODULE_UNVETTING_ROLE = web3.keccak(text="STAKING_MODULE_UNVETTING_ROLE").hex()
STAKING_MODULE_SHARE_MANAGE_ROLE = web3.keccak(text="STAKING_MODULE_SHARE_MANAGE_ROLE").hex()
REPORT_EXITED_VALIDATORS_ROLE = web3.keccak(text="REPORT_EXITED_VALIDATORS_ROLE").hex()
REPORT_VALIDATOR_EXITING_STATUS_ROLE = web3.keccak(text="REPORT_VALIDATOR_EXITING_STATUS_ROLE").hex()
REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE = web3.keccak(text="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE").hex()
UNSAFE_SET_EXITED_VALIDATORS_ROLE = web3.keccak(text="UNSAFE_SET_EXITED_VALIDATORS_ROLE").hex()
REPORT_REWARDS_MINTED_ROLE = web3.keccak(text="REPORT_REWARDS_MINTED_ROLE").hex()

# StakingRouter.finalizeUpgrade_v4 migration order (see StakingRouter.sol finalizeUpgrade_v4).
SR_MIGRATED_ROLES_ORDER = [
    DEFAULT_ADMIN_ROLE,
    MANAGE_WITHDRAWAL_CREDENTIALS_ROLE,
    STAKING_MODULE_MANAGE_ROLE,
    STAKING_MODULE_UNVETTING_ROLE,
    REPORT_EXITED_VALIDATORS_ROLE,
    REPORT_VALIDATOR_EXITING_STATUS_ROLE,
    REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE,
    UNSAFE_SET_EXITED_VALIDATORS_ROLE,
    REPORT_REWARDS_MINTED_ROLE,
]

# --- Triggerable withdrawals gateway ---
TW_EXIT_LIMIT_MANAGER_ROLE = web3.keccak(text="TW_EXIT_LIMIT_MANAGER_ROLE").hex()
ADD_FULL_WITHDRAWAL_REQUEST_ROLE = web3.keccak(text="ADD_FULL_WITHDRAWAL_REQUEST_ROLE").hex()

# --- CSM roles ---
REPORT_GENERAL_DELAYED_PENALTY_ROLE = web3.keccak(text="REPORT_GENERAL_DELAYED_PENALTY_ROLE").hex()
SETTLE_GENERAL_DELAYED_PENALTY_ROLE = web3.keccak(text="SETTLE_GENERAL_DELAYED_PENALTY_ROLE").hex()
REPORT_EL_REWARDS_STEALING_PENALTY_ROLE = web3.keccak(text="REPORT_EL_REWARDS_STEALING_PENALTY_ROLE").hex()
SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE = web3.keccak(text="SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE").hex()
VERIFIER_ROLE = web3.keccak(text="VERIFIER_ROLE").hex()
REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE = web3.keccak(text="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE").hex()
REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE = web3.keccak(text="REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE").hex()
CREATE_NODE_OPERATOR_ROLE = web3.keccak(text="CREATE_NODE_OPERATOR_ROLE").hex()
SET_BOND_CURVE_ROLE = web3.keccak(text="SET_BOND_CURVE_ROLE").hex()
MANAGE_BOND_CURVES_ROLE = web3.keccak(text="MANAGE_BOND_CURVES_ROLE").hex()
MANAGE_CURVE_PARAMETERS_ROLE = web3.keccak(text="MANAGE_CURVE_PARAMETERS_ROLE").hex()
MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE = web3.keccak(text="MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE").hex()
START_REFERRAL_SEASON_ROLE = web3.keccak(text="START_REFERRAL_SEASON_ROLE").hex()
END_REFERRAL_SEASON_ROLE = web3.keccak(text="END_REFERRAL_SEASON_ROLE").hex()

# --- Burner / Curated module roles ---
REQUEST_BURN_SHARES_ROLE = web3.keccak(text="REQUEST_BURN_SHARES_ROLE").hex()
REQUEST_BURN_MY_STETH_ROLE = web3.keccak(text="REQUEST_BURN_MY_STETH_ROLE").hex()
RESUME_ROLE = web3.keccak(text="RESUME_ROLE").hex()

# --- EasyTrack factory permission selectors ---
VALIDATE_STAKING_MODULE_SHARE_PARAMS_SELECTOR = _selector("validateParams((uint16,uint16,uint16,uint16))")
UPDATE_MODULE_SHARES_SELECTOR = _selector("updateModuleShares(uint256,uint16,uint16)")
ALLOW_CONSOLIDATION_PAIR_SELECTOR = _selector("allowPair(uint256,uint256,address)")
SET_MERKLE_GATE_TREE_VALIDATE_INPUT_DATA_SELECTOR = _selector(
    "validateInputData(address,bytes32,string,bytes32,string)"
)
SET_TREE_PARAMS_SELECTOR = _selector("setTreeParams(bytes32,string)")
REPORT_SLASHED_WITHDRAWN_VALIDATORS_SELECTOR = _selector(
    "reportSlashedWithdrawnValidators((uint256,uint256,uint256,uint256,bool)[])"
)
SETTLE_GENERAL_DELAYED_PENALTY_SELECTOR = _selector("settleGeneralDelayedPenalty(uint256[],uint256[])")
CREATE_OR_UPDATE_OPERATOR_GROUP_VALIDATE_INPUT_DATA_SELECTOR = _selector(
    "validateInputData(uint256,(string,(uint64,uint16)[],(bytes)[]),(string,(uint64,uint16)[],(bytes)[]))"
)
CREATE_OR_UPDATE_OPERATOR_GROUP_SELECTOR = _selector(
    "createOrUpdateOperatorGroup(uint256,(string,(uint64,uint16)[],(bytes)[]))"
)

# --- Contract / consensus versions ---
SR_INITIALIZED_VERSION = 4
AO_CONTRACT_VERSION = 5
AO_CONSENSUS_VERSION = 6
VEBO_CONTRACT_VERSION = 3
VEBO_CONSENSUS_VERSION = 5
VEBO_MAX_VALIDATORS_PER_REPORT = 600
VALIDATORS_EXIT_BUS_MAX_EXIT_BALANCE_ETH = 358400
VALIDATORS_EXIT_BUS_BALANCE_PER_FRAME_ETH = 32
VALIDATORS_EXIT_BUS_FRAME_DURATION_IN_SEC = 48
WITHDRAWAL_VAULT_CONTRACT_VERSION = 3
LIDO_CONTRACT_VERSION = 4
CSM_INITIALIZED_VERSION = 3
CS_FEE_ORACLE_CONTRACT_VERSION = 3

# --- Triggerable withdrawals exit-limit config ---
TW_MAX_EXIT_REQUESTS = 250
TW_EXITS_PER_FRAME = 1
TW_FRAME_DURATION_IN_SEC = 240

# --- Identified DVT cluster curve setup (baked into the OneShotCurveSetup contract) ---
IDVT_BOND_CURVE = [[1, 1500000000000000000], [2, 500000000000000000]]
IDVT_KEY_REMOVAL_CHARGE = 10000000000000000
IDVT_GENERAL_DELAYED_PENALTY_FINE = 50000000000000000
IDVT_QUEUE_PRIORITY = 1
IDVT_QUEUE_MAX_DEPOSITS = 40
IDVT_REWARD_SHARE_DATA = [[1, 5834], [65, 3334]]
IDVT_ALLOWED_EXIT_DELAY = 432000
IDVT_EXIT_DELAY_FEE = 50000000000000000

IDENTIFIED_COMMUNITY_STAKERS_GATE_NAME = "Identified Community Stakers Gate"

# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 12  # 1 DG submission + 11 Easy Track items
EXPECTED_DG_EVENTS_FROM_AGENT = 69
EXPECTED_DG_EVENTS_COUNT = 69
IPFS_DESCRIPTION_HASH = None


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


# ============================================================================
# ============================= Helpers ======================================
# ============================================================================


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


def _permission(contract_address: str, selector: str) -> str:
    return convert.to_address(contract_address).lower() + selector.lower().replace("0x", "")


def _concat_permissions(*permissions: str) -> str:
    assert permissions, "Expected at least one permission"
    return permissions[0] + "".join(permission.replace("0x", "") for permission in permissions[1:])


def _raw_event_values(raw_event: dict) -> dict:
    return {item["name"]: item["value"] for item in raw_event["data"]}


def _group_agent_dg_events_from_receipt(receipt: TransactionReceipt, timelock: str, agent: str) -> list[EventDict]:
    """Split a Dual Governance execution receipt into per-item groups.

    The whole proposal is a single Agent.forward call, so the outer DG grouping
    yields one item; we re-group by the `LogScriptCall` boundaries emitted by the
    Agent (`src == agent`) to recover the individual upgrade items.
    """
    events = tx_events_from_receipt(receipt)

    assert len(events) >= 1, "Unexpected events count"
    assert (
        convert.to_address(events[-1]["address"]) == convert.to_address(timelock)
        and events[-1]["name"] == "ProposalExecuted"
    ), "Unexpected Dual Governance service event"

    groups = []
    current_group = None

    for event in events[:-1]:
        event_values = _raw_event_values(event) if event["name"] == "LogScriptCall" else {}
        is_start_of_new_group = event["name"] == "LogScriptCall" and convert.to_address(
            event_values["src"]
        ) == convert.to_address(agent)

        if is_start_of_new_group:
            current_group = []
            groups.append(current_group)

        assert current_group is not None, "Unexpected DG events chain"
        current_group.append(add_event_emitter(event))

    return [EventDict(group) for group in groups]


# ---- event validators --------------------------------------------------------
def validate_proxy_upgrade_event(
    event: EventDict,
    implementation: str,
    emitted_by: Optional[str] = None,
    events_chain: Optional[list[str]] = None,
) -> None:
    _events_chain = events_chain or ["LogScriptCall", "Upgraded"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("Upgraded") == 1

    upgraded_event = _single_event(event, "Upgraded")
    assert convert.to_address(upgraded_event["implementation"]) == convert.to_address(
        implementation
    ), "Wrong implementation address"

    if emitted_by is not None:
        _assert_emitted_by(upgraded_event, emitted_by)


def validate_contract_version_set_event(
    event: EventDict,
    version: int,
    emitted_by: Optional[str] = None,
    events_chain: Optional[list[str]] = None,
) -> None:
    _events_chain = events_chain or ["LogScriptCall", "ContractVersionSet"]
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
    _events_chain = events_chain or ["LogScriptCall", "ConsensusVersionSet"]
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
    validate_events_chain([e.name for e in event], ["LogScriptCall", "RoleGranted"])

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
    validate_events_chain([e.name for e in event], ["LogScriptCall", "RoleRevoked"])

    assert event.count("RoleRevoked") == 1
    role_revoked_event = _single_event(event, "RoleRevoked")
    assert _normalize_role(role_revoked_event["role"]) == role_hash.replace("0x", ""), "Wrong role hash"
    assert convert.to_address(role_revoked_event["account"]) == convert.to_address(account), "Wrong revoked account"
    assert convert.to_address(role_revoked_event["sender"]) == convert.to_address(sender), "Wrong role revoke sender"

    if emitted_by is not None:
        _assert_emitted_by(role_revoked_event, emitted_by)


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


def validate_circuit_breaker_registration_event(
    event: EventDict,
    circuit_breaker: str,
    pausable: str,
    pauser: str,
) -> None:
    validate_events_chain(
        [e.name for e in event],
        ["LogScriptCall", "PauserSet", "HeartbeatUpdated"],
    )

    pauser_set_event = _single_event(event, "PauserSet")
    assert convert.to_address(pauser_set_event["pausable"]) == convert.to_address(pausable)
    assert convert.to_address(pauser_set_event["previousPauser"]) == convert.to_address(ZERO_ADDRESS)
    assert convert.to_address(pauser_set_event["newPauser"]) == convert.to_address(pauser)
    _assert_emitted_by(pauser_set_event, circuit_breaker)

    heartbeat_updated_event = _single_event(event, "HeartbeatUpdated")
    assert convert.to_address(heartbeat_updated_event["pauser"]) == convert.to_address(pauser)
    assert heartbeat_updated_event["newHeartbeatExpiry"] > 0
    _assert_emitted_by(heartbeat_updated_event, circuit_breaker)


def validate_circuit_breaker_unregistration_event(
    event: EventDict,
    circuit_breaker: str,
    pausable: str,
    previous_pauser: str,
) -> None:
    # Unregister always emits PauserSet(pausable, previousPauser, 0). It additionally emits
    # HeartbeatUpdated(previousPauser, 0) iff previousPauser no longer guards any pausable
    # afterwards — a fork-state-dependent tail that we validate only when present.
    validate_events_chain(
        [e.name for e in event],
        ["LogScriptCall", "PauserSet", "HeartbeatUpdated"],
    )

    pauser_set_event = _single_event(event, "PauserSet")
    assert convert.to_address(pauser_set_event["pausable"]) == convert.to_address(pausable)
    assert convert.to_address(pauser_set_event["previousPauser"]) == convert.to_address(previous_pauser)
    assert convert.to_address(pauser_set_event["newPauser"]) == convert.to_address(ZERO_ADDRESS)
    _assert_emitted_by(pauser_set_event, circuit_breaker)

    if event.count("HeartbeatUpdated") > 0:
        heartbeat_updated_event = _single_event(event, "HeartbeatUpdated")
        assert convert.to_address(heartbeat_updated_event["pauser"]) == convert.to_address(previous_pauser)
        assert heartbeat_updated_event["newHeartbeatExpiry"] == 0
        _assert_emitted_by(heartbeat_updated_event, circuit_breaker)


def validate_gate_name_set_event(event: EventDict, name: str, emitted_by: str) -> None:
    # NOTE: events chain confirmed against the on-chain execution dump.
    validate_events_chain([e.name for e in event], ["LogScriptCall", "NameSet"])
    name_set_event = _single_event(event, "NameSet")
    assert name_set_event["name"] == name, "Wrong gate name"
    _assert_emitted_by(name_set_event, emitted_by)


def _expected_sr_role_migration_grants(staking_router: str):
    """Read the members of every role migrated by StakingRouter.finalizeUpgrade_v4.

    finalizeUpgrade_v4 re-grants each pre-upgrade member of the migrated roles in
    role order, member index order — this is what the RoleGranted events reflect.
    """
    sr = interface.StakingRouter(staking_router)
    grants = []
    for role in SR_MIGRATED_ROLES_ORDER:
        count = sr.getRoleMemberCount(role)
        for i in range(count):
            grants.append((role, sr.getRoleMember(role, i)))
    return grants


# ============================================================================
# ============================== Fixtures ====================================
# ============================================================================
@pytest.fixture(scope="module")
def runtime_upgrade_context():
    print(f"Upgrade vote script: {UPGRADE_VOTE_SCRIPT}")
    print(f"DG_PROPOSAL_METADATA: {DG_PROPOSAL_METADATA}")
    print(f"IPFS_DESCRIPTION: {IPFS_DESCRIPTION}")

    vote_script = interface.UpgradeVoteScript(UPGRADE_VOTE_SCRIPT)
    upgrade_template = vote_script.TEMPLATE()
    upgrade_config = interface.UpgradeConfig(vote_script.CONFIG())
    locator_impl = interface.LidoLocator(upgrade_config.getCoreUpgradeConfig()["newLocatorImpl"])

    global_config = upgrade_config.getGlobalConfig()
    core_config = upgrade_config.getCoreUpgradeConfig()
    csm_config = upgrade_config.getCSMUpgradeConfig()
    curated_config = upgrade_config.getCuratedModuleConfig()
    easy_track_new_factories, easy_track_old_factories = upgrade_config.getEasyTrackConfig()

    # Load ABIs for Brownie receipt event decoding.
    interface.CircuitBreaker(global_config["circuitBreaker"])
    interface.ValidatorsExitBusOracle(core_config["validatorsExitBusOracle"])
    interface.ParametersRegistry(csm_config["parametersRegistry"])
    interface.OneShotCurveSetup(csm_config["identifiedDVTClusterCurveSetup"])
    interface.ModuleAccounting(csm_config["accounting"])  # BondCurveAdded (curve setup item)
    # ExitBalanceLimitSet exists only in the new ValidatorsExitBusOracle impl ABI (not in the
    # local interfaces/*.json), so fetch that impl from the explorer to make it decodable.
    Contract.from_explorer(convert.to_address(core_config["newValidatorsExitBusOracleImpl"]))

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

    staking_router = global_config["stakingRouter"]

    # Pre-upgrade state used to build dynamic expectations (read before the vote runs):
    #  - StakingRouter role migration performed by finalizeUpgrade_v4
    #  - new staking module id assigned to Curated Module v2
    #  - Curated HashConsensus epochsPerFrame preserved by updateInitialEpoch
    sr_role_migration_grants = _expected_sr_role_migration_grants(staking_router)
    expected_curated_module_id = interface.StakingRouter(staking_router).getStakingModulesCount() + 1
    curated_epochs_per_frame = interface.HashConsensus(curated_config["hashConsensus"]).getFrameConfig()[1]

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
        "lido_deposits_reserve_target": core_config["lidoDepositsReserveTarget"],
        "easy_track": global_config["easyTrack"],
        "lido_app_id": core_config["lidoAppId"],
        "lido_impl": core_config["newLidoImpl"],
        "lido_locator": core_config["locator"],
        "lido_locator_impl": core_config["newLocatorImpl"],
        "staking_router": staking_router,
        "staking_router_impl": core_config["newStakingRouterImpl"],
        "sr_role_migration_grants": sr_role_migration_grants,
        "max_top_up_per_block_gwei": core_config["maxTopUpPerBlockGwei"],
        "accounting_oracle": core_config["accountingOracle"],
        "accounting_oracle_impl": core_config["newAccountingOracleImpl"],
        "validators_exit_bus_oracle": core_config["validatorsExitBusOracle"],
        "validators_exit_bus_oracle_impl": core_config["newValidatorsExitBusOracleImpl"],
        "accounting": core_config["accounting"],
        "accounting_impl": core_config["newAccountingImpl"],
        "withdrawal_vault": core_config["withdrawalVault"],
        "withdrawal_vault_impl": core_config["newWithdrawalVaultImpl"],
        "oracle_report_sanity_checker": core_config["newOracleReportSanityChecker"],
        "validator_exit_delay_verifier": locator_impl.validatorExitDelayVerifier(),
        "easytrack_evm_script_executor": global_config["easyTrackEVMScriptExecutor"],
        "circuit_breaker": global_config["circuitBreaker"],
        "circuit_breaker_committee": global_config["circuitBreakerCommittee"],
        "consolidation_gateway": core_config["consolidationGateway"],
        "consolidation_committee": core_config["consolidationCommittee"],
        "top_up_gateway": core_config["topUpGateway"],
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
        "cs_fee_oracle_consensus_version": csm_config["feeOracleConsensusVersion"],
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
        "old_verifier": csm_config["oldVerifier"],
        "verifier_v3": csm_config["newVerifier"],
        "old_permissionless_gate": csm_config["oldPermissionlessGate"],
        "new_permissionless_gate": csm_config["newPermissionlessGate"],
        "identified_dvt_cluster_gate": csm_config["identifiedDVTClusterGate"],
        "identified_dvt_cluster_curve_setup": csm_config["identifiedDVTClusterCurveSetup"],
        "identified_dvt_cluster_bond_curve_id": csm_config["identifiedDVTClusterBondCurveId"],
        "old_csm_ejector": old_csm_ejector,
        "new_csm_ejector": csm_config["newEjector"],
        "config_old_csm_ejector": csm_config["oldEjector"],
        "csm_committee": csm_config["csmCommittee"],
        "curated_module": curated_config["module"],
        "curated_gates": curated_config["curatedGates"],
        "curated_accounting": curated_config["accounting"],
        "curated_ejector": curated_config["ejector"],
        "curated_fee_oracle": curated_config["feeOracle"],
        "curated_verifier": curated_config["verifier"],
        "curated_circuit_breaker_pauser": curated_config["circuitBreakerPauser"],
        "curated_strikes": curated_config["strikes"],
        "curated_hash_consensus": curated_config["hashConsensus"],
        "curated_hash_consensus_initial_epoch": curated_config["hashConsensusInitialEpoch"],
        "curated_epochs_per_frame": curated_epochs_per_frame,
        "meta_registry": curated_config["metaRegistry"],
        "curated_module_item": StakingModuleItem(
            id=expected_curated_module_id,
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
        "set_merkle_gate_tree_for_csm_factory": easy_track_new_factories["SetMerkleGateTreeForCSM"],
        "report_withdrawals_for_slashed_validators_for_csm_factory": easy_track_new_factories[
            "ReportWithdrawalsForSlashedValidatorsForCSM"
        ],
        "settle_general_delayed_penalty_for_csm_factory": easy_track_new_factories["SettleGeneralDelayedPenaltyForCSM"],
        "set_merkle_gate_tree_for_cm_factory": easy_track_new_factories["SetMerkleGateTreeForCM"],
        "report_withdrawals_for_slashed_validators_for_cm_factory": easy_track_new_factories[
            "ReportWithdrawalsForSlashedValidatorsForCM"
        ],
        "settle_general_delayed_penalty_for_cm_factory": easy_track_new_factories["SettleGeneralDelayedPenaltyForCM"],
        "create_or_update_operator_group_factory": easy_track_new_factories["CreateOrUpdateOperatorGroupForCM"],
        "old_csm_settle_el_stealing_penalty_factory": easy_track_old_factories["CSMSettleElStealingPenalty"],
        "old_csm_set_vetted_gate_tree_factory": easy_track_old_factories["CSMSetVettedGateTree"],
        "consolidation_migrator": core_config["consolidationMigrator"],
    }


@pytest.fixture(scope="module")
def dual_governance_proposal_calls(runtime_upgrade_context):
    dg_items = get_dg_items(runtime_upgrade_context["upgrade_vote_script"])

    proposal_calls = []
    for target, data in dg_items:
        # get_dg_items() returns data as HexBytes.hex(); in current hexbytes this
        # drops the "0x" prefix, which breaks Brownie's HexString comparison in the
        # submit-event validator. Normalise to a 0x-prefixed hex string.
        data_hex = data if str(data).startswith("0x") else "0x" + str(data)
        proposal_calls.append(
            {
                "target": target,
                "value": 0,
                "data": data_hex,
            }
        )

    return proposal_calls


# ============================================================================
# =============================== The test ===================================
# ============================================================================
def test_vote(
    helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls, runtime_upgrade_context
):
    # =========================================================================
    # ========================= Arrange variables =============================
    # =========================================================================
    ctx = runtime_upgrade_context

    voting = interface.Voting(ctx["voting"])
    agent = interface.Agent(ctx["agent"])
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dual_governance = interface.DualGovernance(ctx["dual_governance"])
    easy_track = interface.EasyTrack(ctx["easy_track"])
    staking_router = interface.StakingRouter(ctx["staking_router"])

    _, call_script_items = get_vote_items(upgrade_vote_script=ctx["upgrade_vote_script"])
    # NB: get_dg_items() returns the Dual Governance proposal calls — a single packed
    # `Agent.forward(...)` call. The individual upgrade actions live inside it and only
    # surface as events during DG execution, so their count comes from DG_ITEMS_COUNT().
    upgrade_template = ctx["upgrade_template"]
    vote_script = interface.UpgradeVoteScript(ctx["upgrade_vote_script"])
    onchain_dg_items_count = vote_script.DG_ITEMS_COUNT()

    expected_vote_events_count = EXPECTED_VOTE_EVENTS_COUNT or len(call_script_items)
    expected_dg_events_from_agent = EXPECTED_DG_EVENTS_FROM_AGENT or onchain_dg_items_count
    expected_dg_events_count = EXPECTED_DG_EVENTS_COUNT or onchain_dg_items_count
    expected_ipfs_description_hash = IPFS_DESCRIPTION_HASH or calculate_vote_ipfs_description(IPFS_DESCRIPTION)["cid"]

    # Guard against the deployed script drifting from the counts encoded in this test.
    assert onchain_dg_items_count == expected_dg_events_count, (
        f"On-chain DG_ITEMS_COUNT ({onchain_dg_items_count}) != EXPECTED_DG_EVENTS_COUNT ({expected_dg_events_count})"
    )
    assert len(call_script_items) == expected_vote_events_count, (
        f"On-chain voting item count ({len(call_script_items)}) != EXPECTED_VOTE_EVENTS_COUNT "
        f"({expected_vote_events_count})"
    )

    old_easy_track_factories = [
        ctx["old_csm_settle_el_stealing_penalty_factory"],
        ctx["old_csm_set_vetted_gate_tree_factory"],
    ]
    new_easy_track_factories = [
        ctx["update_staking_module_share_limits_factory"],
        ctx["allow_consolidation_pair_factory"],
        ctx["set_merkle_gate_tree_for_csm_factory"],
        ctx["report_withdrawals_for_slashed_validators_for_csm_factory"],
        ctx["settle_general_delayed_penalty_for_csm_factory"],
        ctx["set_merkle_gate_tree_for_cm_factory"],
        ctx["report_withdrawals_for_slashed_validators_for_cm_factory"],
        ctx["settle_general_delayed_penalty_for_cm_factory"],
        ctx["create_or_update_operator_group_factory"],
    ]

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
        # =====================================================================
        # ======================= Before voting checks ========================
        # =====================================================================
        initial_factories = easy_track.getEVMScriptFactories()
        for factory in old_easy_track_factories:
            assert factory in initial_factories, "Old Easy Track factory unexpectedly absent before the vote"
        for factory in new_easy_track_factories:
            assert factory not in initial_factories, "New Easy Track factory unexpectedly present before the vote"

        # Curated Module v2 is not registered in the Staking Router yet.
        assert staking_router.getStakingModulesCount() == ctx["curated_module_item"].id - 1

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == expected_ipfs_description_hash

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =====================================================================
        # ======================== After voting checks ========================
        # =====================================================================
        new_factories = easy_track.getEVMScriptFactories()
        for factory in old_easy_track_factories:
            assert factory not in new_factories, "Old Easy Track factory not removed by the vote"
        for factory in new_easy_track_factories:
            assert factory in new_factories, "New Easy Track factory not added by the vote"

        assert len(vote_events) == expected_vote_events_count
        assert count_vote_items_by_events(vote_tx, voting.address) == expected_vote_events_count

        if expected_dg_proposal_id is None:
            expected_dg_proposal_id = dg_proposals_count_before_vote_execution + 1

        assert expected_dg_proposal_id == timelock.getProposalsCount()

        # 1. Submit a Dual Governance proposal
        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=expected_dg_proposal_id,
            proposer=ctx["voting"],
            executor=ctx["dual_governance_admin_executor"],
            metadata=DG_PROPOSAL_METADATA,
            proposal_calls=dual_governance_proposal_calls,
        )

        # 2. Remove CSMSettleElStealingPenalty ET factory
        validate_evmscript_factory_removed_event(
            vote_events[1],
            factory_addr=ctx["old_csm_settle_el_stealing_penalty_factory"],
            emitted_by=easy_track,
        )

        # 3. Remove CSMSetVettedGateTree ET factory
        validate_evmscript_factory_removed_event(
            vote_events[2],
            factory_addr=ctx["old_csm_set_vetted_gate_tree_factory"],
            emitted_by=easy_track,
        )

        # 4. Add UpdateStakingModuleShareLimits ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[3],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["update_staking_module_share_limits_factory"],
                permissions=_concat_permissions(
                    _permission(
                        ctx["update_staking_module_share_limits_factory"],
                        VALIDATE_STAKING_MODULE_SHARE_PARAMS_SELECTOR,
                    ),
                    _permission(ctx["staking_router"], UPDATE_MODULE_SHARES_SELECTOR),
                ),
            ),
            emitted_by=easy_track,
        )

        # 5. Add AllowConsolidationPair ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[4],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["allow_consolidation_pair_factory"],
                permissions=_permission(ctx["consolidation_migrator"], ALLOW_CONSOLIDATION_PAIR_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 6. Add SetMerkleGateTree CSM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[5],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["set_merkle_gate_tree_for_csm_factory"],
                # SetMerkleGateTree permissions = factory.validateInputData + each gate.setTreeParams
                permissions=_concat_permissions(
                    _permission(
                        ctx["set_merkle_gate_tree_for_csm_factory"], SET_MERKLE_GATE_TREE_VALIDATE_INPUT_DATA_SELECTOR
                    ),
                    _permission(ctx["cs_vetted_gate"], SET_TREE_PARAMS_SELECTOR),
                    _permission(ctx["identified_dvt_cluster_gate"], SET_TREE_PARAMS_SELECTOR),
                ),
            ),
            emitted_by=easy_track,
        )

        # 7. Add ReportWithdrawalsForSlashedValidators CSM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[6],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["report_withdrawals_for_slashed_validators_for_csm_factory"],
                permissions=_permission(ctx["csm"], REPORT_SLASHED_WITHDRAWN_VALIDATORS_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 8. Add SettleGeneralDelayedPenalty CSM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[7],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["settle_general_delayed_penalty_for_csm_factory"],
                permissions=_permission(ctx["csm"], SETTLE_GENERAL_DELAYED_PENALTY_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 9. Add SetMerkleGateTree CM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[8],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["set_merkle_gate_tree_for_cm_factory"],
                # SetMerkleGateTree permissions = factory.validateInputData + each gate.setTreeParams
                permissions=_concat_permissions(
                    _permission(
                        ctx["set_merkle_gate_tree_for_cm_factory"], SET_MERKLE_GATE_TREE_VALIDATE_INPUT_DATA_SELECTOR
                    ),
                    *[_permission(gate, SET_TREE_PARAMS_SELECTOR) for gate in ctx["curated_gates"]],
                ),
            ),
            emitted_by=easy_track,
        )

        # 10. Add ReportWithdrawalsForSlashedValidators CM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[9],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["report_withdrawals_for_slashed_validators_for_cm_factory"],
                permissions=_permission(ctx["curated_module"], REPORT_SLASHED_WITHDRAWN_VALIDATORS_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 11. Add SettleGeneralDelayedPenalty CM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[10],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["settle_general_delayed_penalty_for_cm_factory"],
                permissions=_permission(ctx["curated_module"], SETTLE_GENERAL_DELAYED_PENALTY_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 12. Add CreateOrUpdateOperatorGroup CM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[11],
            p=EVMScriptFactoryAdded(
                factory_addr=ctx["create_or_update_operator_group_factory"],
                permissions=_concat_permissions(
                    _permission(
                        ctx["create_or_update_operator_group_factory"],
                        CREATE_OR_UPDATE_OPERATOR_GROUP_VALIDATE_INPUT_DATA_SELECTOR,
                    ),
                    _permission(ctx["meta_registry"], CREATE_OR_UPDATE_OPERATOR_GROUP_SELECTOR),
                ),
            ),
            emitted_by=easy_track,
        )
    elif expected_dg_proposal_id is None:
        pytest.skip("Fill EXPECTED_DG_PROPOSAL_ID to run the DG part against an already-executed vote.")

    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if expected_dg_proposal_id is not None:
        # --- pre-DG state snapshots used by the after-DG acceptance checks ---
        initial_cs_fee_oracle_consensus_version = interface.FeeOracle(ctx["cs_fee_oracle"]).getConsensusVersion()

        details = timelock.getProposalDetails(expected_dg_proposal_id)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =================================================================
            # ================ Before DG proposal executed checks =============
            # =================================================================
            assert interface.AccountingOracle(ctx["accounting_oracle"]).getConsensusVersion() == AO_CONSENSUS_VERSION - 1
            assert (
                interface.ValidatorsExitBusOracle(ctx["validators_exit_bus_oracle"]).getConsensusVersion()
                == VEBO_CONSENSUS_VERSION - 1
            )

            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(expected_dg_proposal_id, {"from": stranger})

            if timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["scheduled"]:
                # Delegate execution to process_proposals: it waits the schedule delay and, crucially,
                # pushes a fresh AccountingOracle report so Lido.finalizeUpgrade_v4 (DG item 1.12) does
                # not revert with "NO_REPORT" once the DG delays have rolled the oracle frame over.
                process_proposals([expected_dg_proposal_id])
                dg_tx: TransactionReceipt = history[-1]
                display_dg_events(dg_tx)
                outer_dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=TIMELOCK,
                    admin_executor=ctx["dual_governance_admin_executor"],
                )
                dg_events = _group_agent_dg_events_from_receipt(
                    dg_tx,
                    timelock=TIMELOCK,
                    agent=agent.address,
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == expected_dg_events_from_agent
                assert len(outer_dg_events) == 1
                assert len(dg_events) == expected_dg_events_count

                # =============================================================
                # ================ DG EXECUTION EVENTS VALIDATION =============
                # =============================================================

                # ------------------------ Core ------------------------------
                # 1.1. Call UpgradeTemplate.startUpgrade
                validate_events_chain([e.name for e in dg_events[0]], ["LogScriptCall", "UpgradeStarted"])
                _assert_emitted_by(_single_event(dg_events[0], "UpgradeStarted"), upgrade_template)

                # 1.2. Upgrade LidoLocator implementation
                validate_proxy_upgrade_event(dg_events[1], ctx["lido_locator_impl"], emitted_by=ctx["lido_locator"])

                # 1.3. Upgrade StakingRouter implementation and call finalizeUpgrade_v4.
                #      finalizeUpgrade_v4 sets maxTopUpPerBlockGwei and re-grants each pre-upgrade
                #      member of the migrated roles.
                sr_grants = ctx["sr_role_migration_grants"]
                validate_proxy_upgrade_event(
                    dg_events[2],
                    ctx["staking_router_impl"],
                    emitted_by=ctx["staking_router"],
                    events_chain=["LogScriptCall", "Upgraded", "MaxTopUpPerBlockGweiSet"]
                    + ["RoleGranted"] * len(sr_grants)
                    + ["Initialized"],
                )
                max_top_up_event = _single_event(dg_events[2], "MaxTopUpPerBlockGweiSet")
                assert max_top_up_event["maxTopUpPerBlockGwei"] == ctx["max_top_up_per_block_gwei"]
                assert convert.to_address(max_top_up_event["setBy"]) == convert.to_address(ctx["agent"])
                _assert_emitted_by(max_top_up_event, ctx["staking_router"])
                role_grants = _event_list(dg_events[2], "RoleGranted")
                assert len(role_grants) == len(sr_grants)
                for role_granted_event, (role_hash, account) in zip(role_grants, sr_grants):
                    assert _normalize_role(role_granted_event["role"]) == _normalize_role(role_hash)
                    assert convert.to_address(role_granted_event["account"]) == convert.to_address(account)
                    assert convert.to_address(role_granted_event["sender"]) == convert.to_address(ctx["agent"])
                    _assert_emitted_by(role_granted_event, ctx["staking_router"])
                initialized_event = _single_event(dg_events[2], "Initialized")
                assert initialized_event["version"] == SR_INITIALIZED_VERSION
                _assert_emitted_by(initialized_event, ctx["staking_router"])

                # 1.4. Upgrade AccountingOracle implementation and call finalizeUpgrade_v5
                ao_chain = ["LogScriptCall", "Upgraded", "ContractVersionSet", "ConsensusVersionSet"]
                validate_proxy_upgrade_event(
                    dg_events[3], ctx["accounting_oracle_impl"], emitted_by=ctx["accounting_oracle"], events_chain=ao_chain
                )
                validate_contract_version_set_event(
                    dg_events[3], AO_CONTRACT_VERSION, emitted_by=ctx["accounting_oracle"], events_chain=ao_chain
                )
                validate_consensus_version_set_event(
                    dg_events[3],
                    AO_CONSENSUS_VERSION,
                    AO_CONSENSUS_VERSION - 1,
                    emitted_by=ctx["accounting_oracle"],
                    events_chain=ao_chain,
                )

                # 1.5. Upgrade ValidatorsExitBusOracle implementation and call finalizeUpgrade_v3
                vebo_chain = [
                    "LogScriptCall",
                    "Upgraded",
                    "ContractVersionSet",
                    "ConsensusVersionSet",
                    "SetMaxValidatorsPerReport",
                    "ExitBalanceLimitSet",
                ]
                validate_proxy_upgrade_event(
                    dg_events[4],
                    ctx["validators_exit_bus_oracle_impl"],
                    emitted_by=ctx["validators_exit_bus_oracle"],
                    events_chain=vebo_chain,
                )
                validate_contract_version_set_event(
                    dg_events[4],
                    VEBO_CONTRACT_VERSION,
                    emitted_by=ctx["validators_exit_bus_oracle"],
                    events_chain=vebo_chain,
                )
                validate_consensus_version_set_event(
                    dg_events[4],
                    VEBO_CONSENSUS_VERSION,
                    VEBO_CONSENSUS_VERSION - 1,
                    emitted_by=ctx["validators_exit_bus_oracle"],
                    events_chain=vebo_chain,
                )
                set_max_validators_event = _single_event(dg_events[4], "SetMaxValidatorsPerReport")
                assert set_max_validators_event["maxValidatorsPerReport"] == VEBO_MAX_VALIDATORS_PER_REPORT
                _assert_emitted_by(set_max_validators_event, ctx["validators_exit_bus_oracle"])
                exit_balance_limit_event = _single_event(dg_events[4], "ExitBalanceLimitSet")
                assert exit_balance_limit_event["maxExitBalanceEth"] == VALIDATORS_EXIT_BUS_MAX_EXIT_BALANCE_ETH
                assert exit_balance_limit_event["balancePerFrameEth"] == VALIDATORS_EXIT_BUS_BALANCE_PER_FRAME_ETH
                assert exit_balance_limit_event["frameDurationInSec"] == VALIDATORS_EXIT_BUS_FRAME_DURATION_IN_SEC
                _assert_emitted_by(exit_balance_limit_event, ctx["validators_exit_bus_oracle"])

                # 1.6. Upgrade Accounting implementation
                validate_proxy_upgrade_event(dg_events[5], ctx["accounting_impl"], emitted_by=ctx["accounting"])

                # 1.7. Upgrade WithdrawalVault implementation and call finalizeUpgrade_v3
                wv_chain = ["LogScriptCall", "Upgraded", "ContractVersionSet"]
                validate_proxy_upgrade_event(
                    dg_events[6], ctx["withdrawal_vault_impl"], emitted_by=ctx["withdrawal_vault"], events_chain=wv_chain
                )
                validate_contract_version_set_event(
                    dg_events[6],
                    WITHDRAWAL_VAULT_CONTRACT_VERSION,
                    emitted_by=ctx["withdrawal_vault"],
                    events_chain=wv_chain,
                )

                # 1.8. Grant Aragon APP_MANAGER_ROLE to the AGENT
                validate_events_chain([e.name for e in dg_events[7]], ["LogScriptCall", "SetPermission"])
                set_permission_event = _single_event(dg_events[7], "SetPermission")
                assert convert.to_address(set_permission_event["entity"]) == convert.to_address(ctx["agent"])
                assert convert.to_address(set_permission_event["app"]) == convert.to_address(ctx["aragon_kernel"])
                assert set_permission_event["role"] == APP_MANAGER_ROLE
                assert set_permission_event["allowed"] is True
                _assert_emitted_by(set_permission_event, ctx["acl"])

                # 1.9. Set Lido implementation in Kernel
                validate_events_chain([e.name for e in dg_events[8]], ["LogScriptCall", "SetApp"])
                set_app_event = _single_event(dg_events[8], "SetApp")
                assert set_app_event["appId"] == ctx["lido_app_id"]
                assert convert.to_address(set_app_event["app"]) == convert.to_address(ctx["lido_impl"])
                _assert_emitted_by(set_app_event, ctx["aragon_kernel"])

                # 1.10. Revoke Aragon APP_MANAGER_ROLE from the AGENT
                validate_events_chain([e.name for e in dg_events[9]], ["LogScriptCall", "SetPermission"])
                set_permission_event = _single_event(dg_events[9], "SetPermission")
                assert convert.to_address(set_permission_event["entity"]) == convert.to_address(ctx["agent"])
                assert convert.to_address(set_permission_event["app"]) == convert.to_address(ctx["aragon_kernel"])
                assert set_permission_event["role"] == APP_MANAGER_ROLE
                assert set_permission_event["allowed"] is False
                _assert_emitted_by(set_permission_event, ctx["acl"])

                # 1.11. Create Aragon BUFFER_RESERVE_MANAGER_ROLE and grant role manager to the AGENT
                validate_events_chain(
                    [e.name for e in dg_events[10]],
                    ["LogScriptCall", "SetPermission", "ChangePermissionManager"],
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

                # 1.12. Call finalizeUpgrade_v4 on Lido
                lido_finalize_chain = ["LogScriptCall", "ContractVersionSet", "DepositsReserveTargetSet"]
                validate_contract_version_set_event(
                    dg_events[11], LIDO_CONTRACT_VERSION, emitted_by=ctx["lido"], events_chain=lido_finalize_chain
                )
                deposits_reserve_target_event = _single_event(dg_events[11], "DepositsReserveTargetSet")
                assert deposits_reserve_target_event["depositsReserveTarget"] == ctx["lido_deposits_reserve_target"]
                _assert_emitted_by(deposits_reserve_target_event, ctx["lido"])

                # 1.13. Grant Staking Router STAKING_MODULE_SHARE_MANAGE_ROLE to EasyTrack executor
                validate_role_grant_event(
                    dg_events[12],
                    STAKING_MODULE_SHARE_MANAGE_ROLE,
                    ctx["easytrack_evm_script_executor"],
                    sender=ctx["agent"],
                    emitted_by=ctx["staking_router"],
                )

                # 1.14. Revoke Staking Router STAKING_MODULE_UNVETTING_ROLE from old DSM
                validate_role_revoke_event(
                    dg_events[13],
                    STAKING_MODULE_UNVETTING_ROLE,
                    ctx["old_deposit_security_module"],
                    sender=ctx["agent"],
                    emitted_by=ctx["staking_router"],
                )

                # 1.15. Grant Staking Router STAKING_MODULE_UNVETTING_ROLE to new DSM
                validate_role_grant_event(
                    dg_events[14],
                    STAKING_MODULE_UNVETTING_ROLE,
                    ctx["new_deposit_security_module"],
                    sender=ctx["agent"],
                    emitted_by=ctx["staking_router"],
                )

                # 1.16. Grant TWG TW_EXIT_LIMIT_MANAGER_ROLE to AGENT
                validate_role_grant_event(
                    dg_events[15],
                    TW_EXIT_LIMIT_MANAGER_ROLE,
                    ctx["agent"],
                    sender=ctx["agent"],
                    emitted_by=ctx["triggerable_withdrawals_gateway"],
                )

                # 1.17. Set TWG exit request limits
                validate_events_chain([e.name for e in dg_events[16]], ["LogScriptCall", "ExitRequestsLimitSet"])
                exit_requests_limit_set_event = _single_event(dg_events[16], "ExitRequestsLimitSet")
                assert exit_requests_limit_set_event["maxExitRequestsLimit"] == TW_MAX_EXIT_REQUESTS
                assert exit_requests_limit_set_event["exitsPerFrame"] == TW_EXITS_PER_FRAME
                assert exit_requests_limit_set_event["frameDurationInSec"] == TW_FRAME_DURATION_IN_SEC
                _assert_emitted_by(exit_requests_limit_set_event, ctx["triggerable_withdrawals_gateway"])

                # 1.18. Register CircuitBreaker pauser for ConsolidationGateway
                validate_circuit_breaker_registration_event(
                    dg_events[17],
                    circuit_breaker=ctx["circuit_breaker"],
                    pausable=ctx["consolidation_gateway"],
                    pauser=ctx["circuit_breaker_committee"],
                )

                # 1.19. Register CircuitBreaker pauser for TopUpGateway
                validate_circuit_breaker_registration_event(
                    dg_events[18],
                    circuit_breaker=ctx["circuit_breaker"],
                    pausable=ctx["top_up_gateway"],
                    pauser=ctx["circuit_breaker_committee"],
                )

                # ------------------------- CSM ------------------------------
                # 1.20. Upgrade CSM to v3 and call finalizeUpgradeV3
                validate_proxy_upgrade_event(
                    dg_events[19], ctx["csm_impl"], emitted_by=ctx["csm"],
                    events_chain=["LogScriptCall", "Upgraded", "Initialized"],
                )
                assert _single_event(dg_events[19], "Initialized")["version"] == CSM_INITIALIZED_VERSION
                _assert_emitted_by(_single_event(dg_events[19], "Initialized"), ctx["csm"])

                # 1.21. Upgrade CSM ParametersRegistry to v3 and call finalizeUpgradeV3
                validate_proxy_upgrade_event(
                    dg_events[20], ctx["cs_parameters_registry_impl"], emitted_by=ctx["cs_parameters_registry"],
                    events_chain=["LogScriptCall", "Upgraded", "Initialized"],
                )
                assert _single_event(dg_events[20], "Initialized")["version"] == CSM_INITIALIZED_VERSION
                _assert_emitted_by(_single_event(dg_events[20], "Initialized"), ctx["cs_parameters_registry"])

                # 1.22. Upgrade CSM FeeOracle to v3 and call finalizeUpgradeV3
                fo_chain = ["LogScriptCall", "Upgraded", "ConsensusVersionSet", "ContractVersionSet"]
                validate_proxy_upgrade_event(
                    dg_events[21], ctx["cs_fee_oracle_impl"], emitted_by=ctx["cs_fee_oracle"], events_chain=fo_chain
                )
                validate_consensus_version_set_event(
                    dg_events[21],
                    ctx["cs_fee_oracle_consensus_version"],
                    initial_cs_fee_oracle_consensus_version,
                    emitted_by=ctx["cs_fee_oracle"],
                    events_chain=fo_chain,
                )
                validate_contract_version_set_event(
                    dg_events[21], CS_FEE_ORACLE_CONTRACT_VERSION, emitted_by=ctx["cs_fee_oracle"], events_chain=fo_chain
                )

                # 1.23. Upgrade CSM VettedGate implementation
                validate_proxy_upgrade_event(dg_events[22], ctx["cs_vetted_gate_impl"], emitted_by=ctx["cs_vetted_gate"])

                # 1.24. Upgrade CSM Accounting to v3 and call finalizeUpgradeV3
                validate_proxy_upgrade_event(
                    dg_events[23], ctx["cs_accounting_impl"], emitted_by=ctx["cs_accounting"],
                    events_chain=["LogScriptCall", "Upgraded", "Initialized"],
                )
                assert _single_event(dg_events[23], "Initialized")["version"] == CSM_INITIALIZED_VERSION
                _assert_emitted_by(_single_event(dg_events[23], "Initialized"), ctx["cs_accounting"])

                # 1.25. Upgrade CSM FeeDistributor to v3 and call finalizeUpgradeV3
                validate_proxy_upgrade_event(
                    dg_events[24], ctx["cs_fee_distributor_impl"], emitted_by=ctx["cs_fee_distributor"],
                    events_chain=["LogScriptCall", "Upgraded", "Initialized"],
                )
                assert _single_event(dg_events[24], "Initialized")["version"] == CSM_INITIALIZED_VERSION
                _assert_emitted_by(_single_event(dg_events[24], "Initialized"), ctx["cs_fee_distributor"])

                # 1.26. Upgrade CSM ExitPenalties implementation
                validate_proxy_upgrade_event(dg_events[25], ctx["cs_exit_penalties_impl"], emitted_by=ctx["cs_exit_penalties"])

                # 1.27. Upgrade CSM ValidatorStrikes implementation
                validate_proxy_upgrade_event(dg_events[26], ctx["cs_validator_strikes_impl"], emitted_by=ctx["cs_validator_strikes"])

                # 1.28. Point CSM ValidatorStrikes to the New CSM Ejector
                validate_events_chain([e.name for e in dg_events[27]], ["LogScriptCall", "EjectorSet"])
                ejector_set_event = _single_event(dg_events[27], "EjectorSet")
                assert convert.to_address(ejector_set_event["ejector"]) == convert.to_address(ctx["new_csm_ejector"])
                _assert_emitted_by(ejector_set_event, ctx["cs_validator_strikes"])

                # 1.29. Revoke CSM REPORT_EL_REWARDS_STEALING_PENALTY_ROLE from CSM Committee
                validate_role_revoke_event(
                    dg_events[28], REPORT_EL_REWARDS_STEALING_PENALTY_ROLE, ctx["csm_committee"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.30. Grant CSM REPORT_GENERAL_DELAYED_PENALTY_ROLE to CSM Committee
                validate_role_grant_event(
                    dg_events[29], REPORT_GENERAL_DELAYED_PENALTY_ROLE, ctx["csm_committee"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.31. Revoke CSM SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE from Easy Track executor
                validate_role_revoke_event(
                    dg_events[30], SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE, ctx["easytrack_evm_script_executor"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.32. Grant CSM SETTLE_GENERAL_DELAYED_PENALTY_ROLE to Easy Track executor
                validate_role_grant_event(
                    dg_events[31], SETTLE_GENERAL_DELAYED_PENALTY_ROLE, ctx["easytrack_evm_script_executor"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.33. Revoke CSM VERIFIER_ROLE from the Old CSM Verifier
                validate_role_revoke_event(
                    dg_events[32], VERIFIER_ROLE, ctx["old_verifier"], sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.34. Grant CSM VERIFIER_ROLE to the New CSM Verifier
                validate_role_grant_event(
                    dg_events[33], VERIFIER_ROLE, ctx["verifier_v3"], sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.35. Grant CSM REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE to the New CSM Verifier
                validate_role_grant_event(
                    dg_events[34], REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, ctx["verifier_v3"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.36. Grant CSM REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE to Easy Track executor
                validate_role_grant_event(
                    dg_events[35], REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE, ctx["easytrack_evm_script_executor"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.37. Revoke CSM CREATE_NODE_OPERATOR_ROLE from the Old CSM PermissionlessGate
                validate_role_revoke_event(
                    dg_events[36], CREATE_NODE_OPERATOR_ROLE, ctx["old_permissionless_gate"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.38. Grant CSM CREATE_NODE_OPERATOR_ROLE to the New CSM PermissionlessGate
                validate_role_grant_event(
                    dg_events[37], CREATE_NODE_OPERATOR_ROLE, ctx["new_permissionless_gate"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.39. Revoke VettedGate START_REFERRAL_SEASON_ROLE from AGENT
                validate_role_revoke_event(
                    dg_events[38], START_REFERRAL_SEASON_ROLE, ctx["agent"],
                    sender=ctx["agent"], emitted_by=ctx["cs_vetted_gate"],
                )

                # 1.40. Revoke VettedGate END_REFERRAL_SEASON_ROLE from CSM Committee
                validate_role_revoke_event(
                    dg_events[39], END_REFERRAL_SEASON_ROLE, ctx["csm_committee"],
                    sender=ctx["agent"], emitted_by=ctx["cs_vetted_gate"],
                )

                # 1.41. Set name Identified Community Stakers for CSM VettedGate gate
                validate_gate_name_set_event(
                    dg_events[40], IDENTIFIED_COMMUNITY_STAKERS_GATE_NAME, emitted_by=ctx["cs_vetted_gate"]
                )

                # 1.42. Unregister CircuitBreaker pauser for Old CSM Verifier
                validate_circuit_breaker_unregistration_event(
                    dg_events[41],
                    circuit_breaker=ctx["circuit_breaker"],
                    pausable=ctx["old_verifier"],
                    previous_pauser=ctx["csm_committee"],
                )

                # 1.43. Unregister CircuitBreaker pauser for Old CSM Ejector
                validate_circuit_breaker_unregistration_event(
                    dg_events[42],
                    circuit_breaker=ctx["circuit_breaker"],
                    pausable=ctx["config_old_csm_ejector"],
                    previous_pauser=ctx["csm_committee"],
                )

                # 1.44. Register CircuitBreaker pauser for New CSM Verifier
                validate_circuit_breaker_registration_event(
                    dg_events[43], circuit_breaker=ctx["circuit_breaker"], pausable=ctx["verifier_v3"],
                    pauser=ctx["csm_committee"],
                )

                # 1.45. Register CircuitBreaker pauser for New CSM Ejector
                validate_circuit_breaker_registration_event(
                    dg_events[44], circuit_breaker=ctx["circuit_breaker"], pausable=ctx["new_csm_ejector"],
                    pauser=ctx["csm_committee"],
                )

                # 1.46. Register CircuitBreaker pauser for CSM Identified DVT Cluster gate
                validate_circuit_breaker_registration_event(
                    dg_events[45], circuit_breaker=ctx["circuit_breaker"], pausable=ctx["identified_dvt_cluster_gate"],
                    pauser=ctx["csm_committee"],
                )

                # 1.47. Grant CSM CREATE_NODE_OPERATOR_ROLE to Identified DVT Cluster gate
                validate_role_grant_event(
                    dg_events[46], CREATE_NODE_OPERATOR_ROLE, ctx["identified_dvt_cluster_gate"],
                    sender=ctx["agent"], emitted_by=ctx["csm"],
                )

                # 1.48. Grant CSM Accounting SET_BOND_CURVE_ROLE to Identified DVT Cluster gate
                validate_role_grant_event(
                    dg_events[47], SET_BOND_CURVE_ROLE, ctx["identified_dvt_cluster_gate"],
                    sender=ctx["agent"], emitted_by=ctx["cs_accounting"],
                )

                # 1.49. Grant CSM Accounting MANAGE_BOND_CURVES_ROLE to Identified DVT Cluster curve setup
                validate_role_grant_event(
                    dg_events[48], MANAGE_BOND_CURVES_ROLE, ctx["identified_dvt_cluster_curve_setup"],
                    sender=ctx["agent"], emitted_by=ctx["cs_accounting"],
                )

                # 1.50. Grant CSM ParametersRegistry MANAGE_CURVE_PARAMETERS_ROLE to Identified DVT Cluster curve setup
                validate_role_grant_event(
                    dg_events[49], MANAGE_CURVE_PARAMETERS_ROLE, ctx["identified_dvt_cluster_curve_setup"],
                    sender=ctx["agent"], emitted_by=ctx["cs_parameters_registry"],
                )

                # 1.51. Execute Identified DVT Cluster curve setup
                validate_events_chain(
                    [e.name for e in dg_events[50]],
                    [
                        "LogScriptCall",
                        "BondCurveAdded",
                        "KeyRemovalChargeSet",
                        "GeneralDelayedPenaltyAdditionalFineSet",
                        "QueueConfigSet",
                        "RewardShareDataSet",
                        "AllowedExitDelaySet",
                        "ExitDelayFeeSet",
                        "RoleRevoked",
                        "RoleRevoked",
                        "BondCurveDeployed",
                    ],
                )
                bond_curve_id = ctx["identified_dvt_cluster_bond_curve_id"]
                bond_curve_added_event = _single_event(dg_events[50], "BondCurveAdded")
                assert bond_curve_added_event["curveId"] == bond_curve_id
                assert bond_curve_added_event["bondCurveIntervals"] == IDVT_BOND_CURVE
                _assert_emitted_by(bond_curve_added_event, ctx["cs_accounting"])
                key_removal_charge_set_event = _single_event(dg_events[50], "KeyRemovalChargeSet")
                assert key_removal_charge_set_event["curveId"] == bond_curve_id
                assert key_removal_charge_set_event["keyRemovalCharge"] == IDVT_KEY_REMOVAL_CHARGE
                _assert_emitted_by(key_removal_charge_set_event, ctx["cs_parameters_registry"])
                general_delayed_penalty_fine_event = _single_event(dg_events[50], "GeneralDelayedPenaltyAdditionalFineSet")
                assert general_delayed_penalty_fine_event["curveId"] == bond_curve_id
                assert general_delayed_penalty_fine_event["fine"] == IDVT_GENERAL_DELAYED_PENALTY_FINE
                _assert_emitted_by(general_delayed_penalty_fine_event, ctx["cs_parameters_registry"])
                queue_config_set_event = _single_event(dg_events[50], "QueueConfigSet")
                assert queue_config_set_event["curveId"] == bond_curve_id
                assert queue_config_set_event["priority"] == IDVT_QUEUE_PRIORITY
                assert queue_config_set_event["maxDeposits"] == IDVT_QUEUE_MAX_DEPOSITS
                _assert_emitted_by(queue_config_set_event, ctx["cs_parameters_registry"])
                reward_share_data_set_event = _single_event(dg_events[50], "RewardShareDataSet")
                assert reward_share_data_set_event["curveId"] == bond_curve_id
                assert reward_share_data_set_event["data"] == IDVT_REWARD_SHARE_DATA
                _assert_emitted_by(reward_share_data_set_event, ctx["cs_parameters_registry"])
                allowed_exit_delay_set_event = _single_event(dg_events[50], "AllowedExitDelaySet")
                assert allowed_exit_delay_set_event["curveId"] == bond_curve_id
                assert allowed_exit_delay_set_event["delay"] == IDVT_ALLOWED_EXIT_DELAY
                _assert_emitted_by(allowed_exit_delay_set_event, ctx["cs_parameters_registry"])
                exit_delay_fee_event = _single_event(dg_events[50], "ExitDelayFeeSet")
                assert exit_delay_fee_event["curveId"] == bond_curve_id
                assert exit_delay_fee_event["penalty"] == IDVT_EXIT_DELAY_FEE
                _assert_emitted_by(exit_delay_fee_event, ctx["cs_parameters_registry"])
                role_revokes = _event_list(dg_events[50], "RoleRevoked")
                assert len(role_revokes) == 2
                assert _normalize_role(role_revokes[0]["role"]) == MANAGE_BOND_CURVES_ROLE.replace("0x", "")
                assert convert.to_address(role_revokes[0]["account"]) == convert.to_address(
                    ctx["identified_dvt_cluster_curve_setup"]
                )
                assert convert.to_address(role_revokes[0]["sender"]) == convert.to_address(
                    ctx["identified_dvt_cluster_curve_setup"]
                )
                _assert_emitted_by(role_revokes[0], ctx["cs_accounting"])
                assert _normalize_role(role_revokes[1]["role"]) == MANAGE_CURVE_PARAMETERS_ROLE.replace("0x", "")
                assert convert.to_address(role_revokes[1]["account"]) == convert.to_address(
                    ctx["identified_dvt_cluster_curve_setup"]
                )
                assert convert.to_address(role_revokes[1]["sender"]) == convert.to_address(
                    ctx["identified_dvt_cluster_curve_setup"]
                )
                _assert_emitted_by(role_revokes[1], ctx["cs_parameters_registry"])
                bond_curve_deployed_event = _single_event(dg_events[50], "BondCurveDeployed")
                assert bond_curve_deployed_event["curveId"] == bond_curve_id
                _assert_emitted_by(bond_curve_deployed_event, ctx["identified_dvt_cluster_curve_setup"])

                # 1.52. Grant CSM ParametersRegistry MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE to CSM Committee
                validate_role_grant_event(
                    dg_events[51], MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE, ctx["csm_committee"],
                    sender=ctx["agent"], emitted_by=ctx["cs_parameters_registry"],
                )

                # 1.53. Revoke Burner REQUEST_BURN_SHARES_ROLE from CSM Accounting
                validate_role_revoke_event(
                    dg_events[52], REQUEST_BURN_SHARES_ROLE, ctx["cs_accounting"],
                    sender=ctx["agent"], emitted_by=ctx["burner"],
                )

                # 1.54. Grant Burner REQUEST_BURN_MY_STETH_ROLE to CSM Accounting
                validate_role_grant_event(
                    dg_events[53], REQUEST_BURN_MY_STETH_ROLE, ctx["cs_accounting"],
                    sender=ctx["agent"], emitted_by=ctx["burner"],
                )

                # 1.55. Revoke TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE from the Old CSM Ejector
                validate_role_revoke_event(
                    dg_events[54], ADD_FULL_WITHDRAWAL_REQUEST_ROLE, ctx["config_old_csm_ejector"],
                    sender=ctx["agent"], emitted_by=ctx["triggerable_withdrawals_gateway"],
                )

                # 1.56. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the New CSM Ejector
                validate_role_grant_event(
                    dg_events[55], ADD_FULL_WITHDRAWAL_REQUEST_ROLE, ctx["new_csm_ejector"],
                    sender=ctx["agent"], emitted_by=ctx["triggerable_withdrawals_gateway"],
                )

                # -------------------- Curated Module ------------------------
                # 1.57. Add Curated Module v2 to StakingRouter
                validate_module_add(
                    dg_events[56], ctx["curated_module_item"], emitted_by=ctx["staking_router"], sender=ctx["agent"]
                )

                # 1.58. Grant Burner REQUEST_BURN_MY_STETH_ROLE to Curated Accounting
                validate_role_grant_event(
                    dg_events[57], REQUEST_BURN_MY_STETH_ROLE, ctx["curated_accounting"],
                    sender=ctx["agent"], emitted_by=ctx["burner"],
                )

                # 1.59. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to Curated Ejector
                validate_role_grant_event(
                    dg_events[58], ADD_FULL_WITHDRAWAL_REQUEST_ROLE, ctx["curated_ejector"],
                    sender=ctx["agent"], emitted_by=ctx["triggerable_withdrawals_gateway"],
                )

                # 1.60. Grant CM RESUME_ROLE to AGENT
                validate_role_grant_event(
                    dg_events[59], RESUME_ROLE, ctx["agent"], sender=ctx["agent"], emitted_by=ctx["curated_module"],
                )

                # 1.61. Resume Curated Module v2
                validate_events_chain([e.name for e in dg_events[60]], ["LogScriptCall", "Resumed"])
                _assert_emitted_by(_single_event(dg_events[60], "Resumed"), ctx["curated_module"])

                # 1.62. Revoke CM RESUME_ROLE from AGENT
                validate_role_revoke_event(
                    dg_events[61], RESUME_ROLE, ctx["agent"], sender=ctx["agent"], emitted_by=ctx["curated_module"],
                )

                # 1.63. Update Curated HashConsensus initial epoch
                validate_events_chain([e.name for e in dg_events[62]], ["LogScriptCall", "FrameConfigSet"])
                frame_config_set_event = _single_event(dg_events[62], "FrameConfigSet")
                assert frame_config_set_event["newInitialEpoch"] == ctx["curated_hash_consensus_initial_epoch"]
                assert frame_config_set_event["newEpochsPerFrame"] == ctx["curated_epochs_per_frame"]
                _assert_emitted_by(frame_config_set_event, ctx["curated_hash_consensus"])

                # 1.64. Register CircuitBreaker pauser for Curated Module v2
                validate_circuit_breaker_registration_event(
                    dg_events[63], circuit_breaker=ctx["circuit_breaker"], pausable=ctx["curated_module"],
                    pauser=ctx["curated_circuit_breaker_pauser"],
                )

                # 1.65. Register CircuitBreaker pauser for Curated Accounting
                validate_circuit_breaker_registration_event(
                    dg_events[64], circuit_breaker=ctx["circuit_breaker"], pausable=ctx["curated_accounting"],
                    pauser=ctx["curated_circuit_breaker_pauser"],
                )

                # 1.66. Register CircuitBreaker pauser for Curated FeeOracle
                validate_circuit_breaker_registration_event(
                    dg_events[65], circuit_breaker=ctx["circuit_breaker"], pausable=ctx["curated_fee_oracle"],
                    pauser=ctx["curated_circuit_breaker_pauser"],
                )

                # 1.67. Register CircuitBreaker pauser for Curated Verifier
                validate_circuit_breaker_registration_event(
                    dg_events[66], circuit_breaker=ctx["circuit_breaker"], pausable=ctx["curated_verifier"],
                    pauser=ctx["curated_circuit_breaker_pauser"],
                )

                # 1.68. Register CircuitBreaker pauser for Curated Ejector
                validate_circuit_breaker_registration_event(
                    dg_events[67], circuit_breaker=ctx["circuit_breaker"], pausable=ctx["curated_ejector"],
                    pauser=ctx["curated_circuit_breaker_pauser"],
                )

                # ---------------------- Finish upgrade ----------------------
                # 1.69. Call UpgradeTemplate.finishUpgrade (also migrates the sanity checker baseline snapshot)
                validate_events_chain(
                    [e.name for e in dg_events[68]],
                    ["LogScriptCall", "BaselineSnapshotMigrated", "UpgradeFinished", "ScriptResult", "Executed"],
                )
                _assert_emitted_by(
                    _single_event(dg_events[68], "BaselineSnapshotMigrated"), ctx["oracle_report_sanity_checker"]
                )
                _assert_emitted_by(_single_event(dg_events[68], "UpgradeFinished"), upgrade_template)

        # =====================================================================
        # ================= After DG proposal executed checks =================
        # =====================================================================
        assert timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["executed"]

        # Core upgrade landed.
        assert interface.AccountingOracle(ctx["accounting_oracle"]).getConsensusVersion() == AO_CONSENSUS_VERSION
        assert (
            interface.ValidatorsExitBusOracle(ctx["validators_exit_bus_oracle"]).getConsensusVersion()
            == VEBO_CONSENSUS_VERSION
        )
        assert interface.WithdrawalVault(ctx["withdrawal_vault"]).getContractVersion() == WITHDRAWAL_VAULT_CONTRACT_VERSION
        assert interface.Lido(ctx["lido"]).getContractVersion() == LIDO_CONTRACT_VERSION
        assert interface.FeeOracle(ctx["cs_fee_oracle"]).getConsensusVersion() == ctx["cs_fee_oracle_consensus_version"]

        # Staking Router role migration & new roles.
        assert staking_router.hasRole(STAKING_MODULE_SHARE_MANAGE_ROLE, ctx["easytrack_evm_script_executor"])
        assert staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, ctx["new_deposit_security_module"])
        assert not staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, ctx["old_deposit_security_module"])

        # Curated Module v2 registered and resumed.
        assert staking_router.getStakingModulesCount() == ctx["curated_module_item"].id
        curated_module = interface.CSModule(ctx["curated_module"])
        assert curated_module.isPaused() is False

        # Easy Track factory set updated (also checked right after the vote).
        current_factories = easy_track.getEVMScriptFactories()
        for factory in old_easy_track_factories:
            assert factory not in current_factories
        for factory in new_easy_track_factories:
            assert factory in current_factories
