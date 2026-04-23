from typing import NamedTuple, Optional

import pytest

from brownie import chain, convert, interface
from brownie.network.event import EventDict
from brownie.network.transaction import TransactionReceipt

from utils.config import network_name
from utils.hoodi_upgrade import (
    get_consolidation_migrator_address,
    get_easy_track_new_factories,
    get_meta_registry_address,
    get_state_address,
    get_upgrade_vote_script_address,
)
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
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"
AGENT = "0x0534aA41907c9631fae990960bCC72d75fA7cfeD"
EMERGENCY_PROTECTED_TIMELOCK = "0x0A5E22782C0Bd4AddF10D771f0bF0406B038282d"
DUAL_GOVERNANCE = "0x9CAaCCc62c66d817CC59c44780D1b722359795bF"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x0eCc17597D292271836691358B22340b78F3035B"
ACL = "0x78780e70Eae33e2935814a327f7dB6c01136cc62"
ARAGON_KERNEL = "0xA48DF029Fd2e5FCECB3886c5c2F60e3625A1E87d"
LIDO = "0x3508A952176b3c15387C97BE809eaffB1982176a"
LIDO_LOCATOR = "0xe2EF9536DAAAEBFf5b1c130957AB3E80056b06D8"
STAKING_ROUTER = "0xCc820558B39ee15C7C45B59390B503b83fb499A8"
ACCOUNTING_ORACLE = "0xcb883B1bD0a41512b42D2dB267F2A2cd919FB216"
VALIDATORS_EXIT_BUS_ORACLE = "0x8664d394C2B3278F26A1B44B967aEf99707eeAB2"
ACCOUNTING = "0x9b5b78D1C9A3238bF24662067e34c57c83E8c354"
WITHDRAWAL_VAULT = "0x4473dCDDbf77679A643BdB654dbd86D67F8d32f2"
TRIGGERABLE_WITHDRAWALS_GATEWAY = "0x6679090D92b08a2a686eF8614feECD8cDFE209db"
VALIDATOR_EXIT_DELAY_VERIFIER = "0xa5F5A9360275390fF9728262a29384399f38d2f0"
EASYTRACK_EVMSCRIPT_EXECUTOR = "0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E"
LIDO_IMPL = "0x6147270470A9Ee5b55c33EA71e32000E5d6D8E6B"
LIDO_APP_ID = "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320"
CIRCUIT_BREAKER = "0x44a5789dFeDa59cD176Ab5709ec2F4829dE4d555"
CONSOLIDATION_GATEWAY = "0xce93710b849e0dC202AaC513837e05bEA9D7DdFD"
CURATED_MODULE_COMMITTEE = "0x84DffcfB232594975C608DE92544Ff239a24c9E9"
CSM = "0x79CEf36D84743222f37765204Bec41E92a93E59d"
CS_PARAMETERS_REGISTRY = "0xA4aD5236963f9Fe4229864712269D8d79B65C5Ad"
CS_FEE_ORACLE = "0xe7314f561B2e72f9543F1004e741bab6Fc51028B"
CS_VETTED_GATE = "0x10a254E724fe2b7f305F76f3F116a3969c53845f"
CS_ACCOUNTING = "0xA54b90BA34C5f326BC1485054080994e38FB4C60"
CS_FEE_DISTRIBUTOR = "0xaCd9820b0A2229a82dc1A0770307ce5522FF3582"
CS_EXIT_PENALTIES = "0xD259b31083Be841E5C85b2D481Cfc17C14276800"
CS_VALIDATOR_STRIKES = "0x8fBA385C3c334D251eE413e79d4D3890db98693c"
VERIFIER_V3 = "0xC96406b0eADdAC5708aFCa04DcCA67BAdC9642Fd"
OLD_VERIFIER = "0x1773b2Ff99A030F6000554Cb8A5Ec93145650cbA"
OLD_PERMISSIONLESS_GATE = "0x5553077102322689876A6AdFd48D75014c28acfb"
NEW_PERMISSIONLESS_GATE = "0xd7bD8D2A9888D1414c770B35ACF55890B15de26a"
OLD_DEPOSIT_SECURITY_MODULE = "0x2F0303F20E0795E6CCd17BD5efE791A586f28E03"
NEW_DEPOSIT_SECURITY_MODULE = "0x1a629bB7C0563650e46406Eb6764A2ba207a0eFE"
HOODI_LEGACY_STAKING_MODULE_MANAGER = "0xE28f573b732632fdE03BD5507A7d475383e8512E"
ICS_MANAGER = "0x4AF43Ee34a6fcD1fEcA1e1F832124C763561dA53"
CSM_GENERAL_DELAYED_PENALTY_REPORTER = ICS_MANAGER
CSM_PENALTIES_MANAGER = ICS_MANAGER
BURNER = "0xb2c99cd38a2636a6281a849C8de938B3eF4A7C3D"
OLD_CSM_EJECTOR = "0x777bd76326E4aDcD353b03AD45b33BAF41048476"
CSM_EJECTOR = "0xCAe028378d69D54dc8bF809e6C44CF751F997b80"
CURATED_MODULE = "0x87EB69Ae51317405FD285efD2326a4a11f6173b9"
CURATED_ACCOUNTING = "0x7f7356D29aCd915F1934220956c3305808ceB235"
CURATED_EJECTOR = "0xfDbde2B3554B69C84e0f8d7daB68D390Ff0f4394"
CURATED_HASH_CONSENSUS = "0x920883908A78c1554f682006a8aB32E62Be09F33"
LIDO_LOCATOR_IMPL = "0x9b110E022a13583679536B303d0C22467d1b567A"
STAKING_ROUTER_IMPL = "0x44d0b2B95d2C2bDF73FE4f5cD7E3A930494E5B1f"
ACCOUNTING_ORACLE_IMPL = "0x41bF10F28A1312f2241f86A2537A04b08e343C0a"
VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0x86aeA211B30174b3ee5d294ECeaDbD7f1C575eF3"
ACCOUNTING_IMPL = "0xDB47544d5813f15116bf95c1cF2ff4dEdb2226fD"
WITHDRAWAL_VAULT_IMPL = "0xB97e67CC20bd2970E30341c0ECc7497d8A5b7342"
CSM_IMPL = "0x161b1DAa658fD0D78a4603860edd8Ed06f98F4cA"
CS_PARAMETERS_REGISTRY_IMPL = "0x58376D8B192813E85532b25685D948EB49c2A8B5"
CS_FEE_ORACLE_IMPL = "0x27d1Ff0353AF6b7480CBc902169d0F89b49334B5"
CS_VETTED_GATE_IMPL = "0x3b834c6d043F4CE5C61d84723bA737D405B2e276"
CS_ACCOUNTING_IMPL = "0x3a18675fFB2C37A4296dD794A7Ed94644225F881"
CS_FEE_DISTRIBUTOR_IMPL = "0x74c5be19CcD1a264899FbCf8dB1a64C1e3fb73Ac"
CS_EXIT_PENALTIES_IMPL = "0xf38A3DA25B417D83182EEDD30d00557d78c35C96"
CS_VALIDATOR_STRIKES_IMPL = "0x47F96DCD5cf3e94492CD050c00C9F6e33b3ca677"
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"
APP_MANAGER_ROLE = "0xb6d92708f3d4817afc106147d969e229ced5c46e65e0a5002a0d391287762bd0"
BUFFER_RESERVE_MANAGER_ROLE = "0x33969636f1fbf3d7d062d4de4a08e7bd3c46606ec28b3a4398d2665be559b921"
STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"
STAKING_MODULE_UNVETTING_ROLE = "0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57"
STAKING_MODULE_SHARE_MANAGE_ROLE = "0x43bf0e13900cfaa1b03ed5681dc143266597e29a1d6f9cbd84114f0ac21cd208"
REPORT_EXITED_VALIDATORS_ROLE = "0xc23292b191d95d2a7dd94fc6436eb44338fda9e1307d9394fd27c28157c1b33c"
REPORT_VALIDATOR_EXITING_STATUS_ROLE = "0xbe1bd143a0dde8a867d58aab054bfdb25250951665c4570e39abc3b3de3c2d6c"
REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE = "0x0766e72e5c008b3df8129fb356d9176eef8544f6241e078b7d61aff604f8812b"
REPORT_REWARDS_MINTED_ROLE = "0x779e5c23cb7a5bcb9bfe1e9a5165a00057f12bcdfd13e374540fdf1a1cd91137"
TW_EXIT_LIMIT_MANAGER_ROLE = "0x03c30da9b9e4d4789ac88a294d39a63058ca4a498804c2aa823e381df59d0cf4"
REPORT_GENERAL_DELAYED_PENALTY_ROLE = "0xa2c92d51d5647473735e9dfd5e2edf65bcf2fc2c139c95cbed53c19dc227c0b5"
SETTLE_GENERAL_DELAYED_PENALTY_ROLE = "0xe4c6f42648e5067520394b287613558d8b8a48bc7a320523da96c04d46253bda"
REPORT_EL_REWARDS_STEALING_PENALTY_ROLE = "0x59911a6aa08a72fe3824aec4500dc42335c6d0702b6d5c5c72ceb265a0de9302"
SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE = "0xe85fdec10fe0f93d0792364051df7c3d73e37c17b3a954bffe593960e3cd3012"
VERIFIER_ROLE = "0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09"
REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE = "0xb169cb0459e6d91326174ff566a2fcc3c7bb31ef3d4d83bec1d5679c611ab094"
REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE = "0x2dba60a7b2c6bc437f1868d48dc8e53a95d71e78cef88de0aff6d952ecff8daa"
CREATE_NODE_OPERATOR_ROLE = "0xc72a21b38830f4d6418a239e17db78b945cc7cfee674bac97fd596eaf0438478"
RESUME_ROLE = "0x2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7"
START_REFERRAL_SEASON_ROLE = "0xc0bd4bb446c4ce6fd2289aa78c8ea233de3ad2b870bc787b2ba154e19c271f12"
END_REFERRAL_SEASON_ROLE = "0x4a1304957825c6a76938ccf907b92b9b872c8348083e23dae57e7e6111105d0c"
MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE = "0x00b6097bf7ad894f88f786cd383df3190b971af96510047737d0cb2e9bd25558"
REQUEST_BURN_SHARES_ROLE = "0x4be29e0e4eb91f98f709d98803cba271592782e293b84a625e025cbb40197ba8"
REQUEST_BURN_MY_STETH_ROLE = "0x28186f938b759084eea36948ef1cd8b40ec8790a98d5f1a09b70879fe054e5cc"
ADD_FULL_WITHDRAWAL_REQUEST_ROLE = "0x15fac8ba7fe8dd5344b88c1915452ce66976f270d1cd793c3b0ab579cecd33c0"
EXIT_BALANCE_LIMIT_SET_TOPIC = "0x28a59cb43d86267095565f85c40c9110eb77192a738ef87891ba3696c423a531"
CIRCUIT_BREAKER_BLOCKER_ADDED_TOPIC = "0xd92c3c28ed17463268f864776463c4c2154f89b18156d3edf77c0e37d0476913"
CIRCUIT_BREAKER_COMMITTEE_ACTIVATED_TOPIC = "0x4ea9e94baeeb3668b47d8d9b4cc8f5a1784d783dd263d7d76f8c10d6a10aed44"
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
CURATED_MODULE_NAME = "curated-onchain-v2"
CURATED_STAKE_SHARE_LIMIT = 2000
CURATED_PRIORITY_EXIT_SHARE_THRESHOLD = 2500
CURATED_STAKING_MODULE_FEE = 800
CURATED_TREASURY_FEE = 200
CURATED_MAX_DEPOSITS_PER_BLOCK = 30
CURATED_MIN_DEPOSIT_BLOCK_DISTANCE = 25
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


CURATED_MODULE_V2 = StakingModuleItem(
    id=CURATED_MODULE_ID,
    staking_module_address=CURATED_MODULE,
    name=CURATED_MODULE_NAME,
    staking_module_fee=CURATED_STAKING_MODULE_FEE,
    stake_share_limit=CURATED_STAKE_SHARE_LIMIT,
    treasury_fee=CURATED_TREASURY_FEE,
    priority_exit_share_threshold=CURATED_PRIORITY_EXIT_SHARE_THRESHOLD,
    max_deposits_per_block=CURATED_MAX_DEPOSITS_PER_BLOCK,
    min_deposit_block_distance=CURATED_MIN_DEPOSIT_BLOCK_DISTANCE,
)


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


def _group_raw_dg_events_from_receipt(receipt: TransactionReceipt) -> list[list[dict]]:
    events = tx_events_from_receipt(receipt)

    assert len(events) >= 1, "Unexpected raw DG events count"
    assert (
        convert.to_address(events[-1]["address"]) == convert.to_address(EMERGENCY_PROTECTED_TIMELOCK)
        and events[-1]["name"] == "ProposalExecuted"
    ), "Unexpected raw DG service event"

    groups = []
    current_group = []

    for event in events[:-1]:
        current_group.append(event)

        is_end_of_group = event["name"] == "Executed" and convert.to_address(event["address"]) == convert.to_address(
            DUAL_GOVERNANCE_ADMIN_EXECUTOR
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
    emitted_by: Optional[str] = None,
) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"])

    assert event.count("RoleGranted") == 1
    role_granted_event = _single_event(event, "RoleGranted")
    assert _normalize_role(role_granted_event["role"]) == role_hash.replace("0x", ""), "Wrong role hash"
    assert convert.to_address(role_granted_event["account"]) == convert.to_address(account), "Wrong granted account"
    assert convert.to_address(role_granted_event["sender"]) == convert.to_address(AGENT), "Wrong role grant sender"

    if emitted_by is not None:
        _assert_emitted_by(role_granted_event, emitted_by)


def validate_role_revoke_event(
    event: EventDict,
    role_hash: str,
    account: str,
    emitted_by: Optional[str] = None,
) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "RoleRevoked", "ScriptResult", "Executed"])

    assert event.count("RoleRevoked") == 1
    role_revoked_event = _single_event(event, "RoleRevoked")
    assert _normalize_role(role_revoked_event["role"]) == role_hash.replace("0x", ""), "Wrong role hash"
    assert convert.to_address(role_revoked_event["account"]) == convert.to_address(account), "Wrong revoked account"
    assert convert.to_address(role_revoked_event["sender"]) == convert.to_address(AGENT), "Wrong role revoke sender"

    if emitted_by is not None:
        _assert_emitted_by(role_revoked_event, emitted_by)

def validate_dg_noop_event(event: EventDict) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "ScriptResult", "Executed"])
    assert event.count("LogScriptCall") == 1
    assert event.count("ScriptResult") == 1
    assert event.count("Executed") == 1

def validate_module_add(event: EventDict, module: StakingModuleItem, emitted_by: str) -> None:
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
    assert convert.to_address(module_added_event["createdBy"]) == convert.to_address(AGENT)
    _assert_emitted_by(module_added_event, emitted_by)

    module_share_limit_event = _single_event(event, "StakingModuleShareLimitSet")
    assert module_share_limit_event["stakingModuleId"] == module.id
    assert module_share_limit_event["stakeShareLimit"] == module.stake_share_limit
    assert module_share_limit_event["priorityExitShareThreshold"] == module.priority_exit_share_threshold
    assert convert.to_address(module_share_limit_event["setBy"]) == convert.to_address(AGENT)
    _assert_emitted_by(module_share_limit_event, emitted_by)

    module_fees_event = _single_event(event, "StakingModuleFeesSet")
    assert module_fees_event["stakingModuleId"] == module.id
    assert module_fees_event["stakingModuleFee"] == module.staking_module_fee
    assert module_fees_event["treasuryFee"] == module.treasury_fee
    assert convert.to_address(module_fees_event["setBy"]) == convert.to_address(AGENT)
    _assert_emitted_by(module_fees_event, emitted_by)

    max_deposits_event = _single_event(event, "StakingModuleMaxDepositsPerBlockSet")
    assert max_deposits_event["stakingModuleId"] == module.id
    assert max_deposits_event["maxDepositsPerBlock"] == module.max_deposits_per_block
    assert convert.to_address(max_deposits_event["setBy"]) == convert.to_address(AGENT)
    _assert_emitted_by(max_deposits_event, emitted_by)

    min_distance_event = _single_event(event, "StakingModuleMinDepositBlockDistanceSet")
    assert min_distance_event["stakingModuleId"] == module.id
    assert min_distance_event["minDepositBlockDistance"] == module.min_deposit_block_distance
    assert convert.to_address(min_distance_event["setBy"]) == convert.to_address(AGENT)
    _assert_emitted_by(min_distance_event, emitted_by)

    deposited_event = _single_event(event, "StakingRouterETHDeposited")
    assert deposited_event["stakingModuleId"] == module.id
    assert deposited_event["amount"] == 0
    _assert_emitted_by(deposited_event, emitted_by)


def validate_exit_balance_limit_set_raw_group(raw_group: list[dict]) -> None:
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
    assert convert.to_address(unknown_event["address"]) == convert.to_address(VALIDATORS_EXIT_BUS_ORACLE)
    assert unknown_event_values["topic1"] == EXIT_BALANCE_LIMIT_SET_TOPIC

    decoded_words = _decode_uint256_words(unknown_event_values["data"])
    assert decoded_words == [
        VALIDATORS_EXIT_BUS_MAX_EXIT_BALANCE_ETH,
        VALIDATORS_EXIT_BUS_BALANCE_PER_FRAME_ETH,
        VALIDATORS_EXIT_BUS_FRAME_DURATION_IN_SEC,
    ]


def validate_circuit_breaker_registration_raw_group(raw_group: list[dict]) -> None:
    validate_events_chain(
        [event["name"] for event in raw_group],
        ["LogScriptCall", "(unknown)", "(unknown)", "ScriptResult", "Executed"],
    )

    first_unknown_event = raw_group[1]
    second_unknown_event = raw_group[2]

    assert convert.to_address(first_unknown_event["address"]) == convert.to_address(CIRCUIT_BREAKER)
    first_unknown_event_values = _raw_event_values(first_unknown_event)
    assert first_unknown_event_values["topic1"] == CIRCUIT_BREAKER_BLOCKER_ADDED_TOPIC
    assert first_unknown_event_values["topic2"] == _address_to_topic(CONSOLIDATION_GATEWAY)
    assert first_unknown_event_values["topic3"] == _address_to_topic("0x0000000000000000000000000000000000000000")
    assert first_unknown_event_values["topic4"] == _address_to_topic(CURATED_MODULE_COMMITTEE)
    assert _normalize_hex_data(first_unknown_event_values["data"]) == "00"

    assert convert.to_address(second_unknown_event["address"]) == convert.to_address(CIRCUIT_BREAKER)
    second_unknown_event_values = _raw_event_values(second_unknown_event)
    assert second_unknown_event_values["topic1"] == CIRCUIT_BREAKER_COMMITTEE_ACTIVATED_TOPIC
    assert second_unknown_event_values["topic2"] == _address_to_topic(CURATED_MODULE_COMMITTEE)
    assert int(_normalize_hex_data(second_unknown_event_values["data"]), 16) > 0


@pytest.fixture(scope="module")
def runtime_upgrade_addresses():
    if network_name() != "hoodi-fork":
        pytest.skip("Run the dedicated Hoodi upgrade test on --network hoodi-fork.")

    upgrade_vote_script = get_upgrade_vote_script_address()
    factories = get_easy_track_new_factories()
    update_staking_module_share_limits_factory = factories["UpdateStakingModuleShareLimits"]
    allow_consolidation_pair_factory = factories["AllowConsolidationPair"]
    create_or_update_operator_group_factory = factories["CreateOrUpdateOperatorGroup"]
    consolidation_migrator = get_consolidation_migrator_address()
    meta_registry = get_meta_registry_address()

    if (
        _is_placeholder_address(upgrade_vote_script)
        or _is_placeholder_address(update_staking_module_share_limits_factory)
        or _is_placeholder_address(allow_consolidation_pair_factory)
        or _is_placeholder_address(create_or_update_operator_group_factory)
        or _is_placeholder_address(consolidation_migrator)
        or _is_placeholder_address(meta_registry)
        or _is_placeholder_text(DG_PROPOSAL_METADATA)
        or _is_placeholder_text(get_ipfs_description(dg_only=DG_ONLY_MODE))
    ):
        pytest.skip("Local Hoodi upgrade artifacts are missing. Run the lido-core deploy flow first.")

    return {
        "upgrade_vote_script": upgrade_vote_script,
        "update_staking_module_share_limits_factory": update_staking_module_share_limits_factory,
        "allow_consolidation_pair_factory": allow_consolidation_pair_factory,
        "create_or_update_operator_group_factory": create_or_update_operator_group_factory,
        "consolidation_migrator": consolidation_migrator,
        "meta_registry": meta_registry,
    }


@pytest.fixture(scope="module")
def dual_governance_proposal_calls(runtime_upgrade_addresses):
    dg_items = get_dg_items()

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


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    # TODO: restore once Easy Track items are enabled in the vote again.
    # easy_track = interface.EasyTrack(EASYTRACK)
    # staking_router = interface.StakingRouter(STAKING_ROUTER)
    # consolidation_migrator = interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR)
    # meta_registry = interface.IMetaRegistry(META_REGISTRY)

    vote_desc_items, call_script_items = get_vote_items(dg_only=DG_ONLY_MODE)
    dg_items = get_dg_items()
    upgrade_template = get_state_address("upgradeTemplate")

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
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True, dg_only=DG_ONLY_MODE)

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
            proposer=VOTING,
            executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
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
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                raw_dg_events = _group_raw_dg_events_from_receipt(dg_tx)
                assert count_vote_items_by_events(dg_tx, agent.address) == expected_dg_events_from_agent
                assert len(dg_events) == expected_dg_events_count
                assert len(raw_dg_events) == expected_dg_events_count

                # === DG EXECUTION EVENTS VALIDATION ===

                # 1. Call UpgradeTemplate.startUpgrade
                validate_events_chain([e.name for e in dg_events[0]], ["LogScriptCall", "UpgradeStarted", "ScriptResult", "Executed"])
                upgrade_started_event = _single_event(dg_events[0], "UpgradeStarted")
                _assert_emitted_by(upgrade_started_event, upgrade_template)

                # 2. Upgrade LidoLocator proxy
                validate_proxy_upgrade_event(dg_events[1], LIDO_LOCATOR_IMPL, emitted_by=LIDO_LOCATOR)

                # 3. Upgrade and finalize StakingRouter
                validate_proxy_upgrade_event(
                    dg_events[2],
                    STAKING_ROUTER_IMPL,
                    emitted_by=STAKING_ROUTER,
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
                        (DEFAULT_ADMIN_ROLE, AGENT),
                        (STAKING_MODULE_MANAGE_ROLE, AGENT),
                        (STAKING_MODULE_MANAGE_ROLE, HOODI_LEGACY_STAKING_MODULE_MANAGER),
                        (STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE),
                        (REPORT_EXITED_VALIDATORS_ROLE, ACCOUNTING_ORACLE),
                        (REPORT_VALIDATOR_EXITING_STATUS_ROLE, VALIDATOR_EXIT_DELAY_VERIFIER),
                        (REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE, TRIGGERABLE_WITHDRAWALS_GATEWAY),
                        (REPORT_REWARDS_MINTED_ROLE, ACCOUNTING),
                    ],
                ):
                    assert _normalize_role(role_granted_event["role"]) == role_hash.replace("0x", "")
                    assert convert.to_address(role_granted_event["account"]) == convert.to_address(account)
                    assert convert.to_address(role_granted_event["sender"]) == convert.to_address(AGENT)
                    _assert_emitted_by(role_granted_event, STAKING_ROUTER)
                initialized_event = _single_event(dg_events[2], "Initialized")
                assert initialized_event["version"] == 4
                _assert_emitted_by(initialized_event, STAKING_ROUTER)

                # 4. Upgrade and finalize AccountingOracle
                validate_proxy_upgrade_event(
                    dg_events[3],
                    ACCOUNTING_ORACLE_IMPL,
                    emitted_by=ACCOUNTING_ORACLE,
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
                    emitted_by=ACCOUNTING_ORACLE,
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
                    emitted_by=ACCOUNTING_ORACLE,
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
                    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
                    emitted_by=VALIDATORS_EXIT_BUS_ORACLE,
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
                    emitted_by=VALIDATORS_EXIT_BUS_ORACLE,
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
                    emitted_by=VALIDATORS_EXIT_BUS_ORACLE,
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
                _assert_emitted_by(set_max_validators_event, VALIDATORS_EXIT_BUS_ORACLE)
                validate_exit_balance_limit_set_raw_group(raw_dg_events[4])

                # 6. Upgrade Accounting implementation
                validate_proxy_upgrade_event(dg_events[5], ACCOUNTING_IMPL, emitted_by=ACCOUNTING)

                # 7. Upgrade and finalize WithdrawalVault
                validate_proxy_upgrade_event(
                    dg_events[6],
                    WITHDRAWAL_VAULT_IMPL,
                    emitted_by=WITHDRAWAL_VAULT,
                    events_chain=["LogScriptCall", "Upgraded", "ContractVersionSet", "ScriptResult", "Executed"],
                )
                validate_contract_version_set_event(
                    dg_events[6],
                    WITHDRAWAL_VAULT_CONTRACT_VERSION,
                    emitted_by=WITHDRAWAL_VAULT,
                    events_chain=["LogScriptCall", "Upgraded", "ContractVersionSet", "ScriptResult", "Executed"],
                )

                # 8. Grant APP_MANAGER_ROLE on Kernel to Agent
                validate_aragon_grant_permission_event(
                    dg_events[7],
                    entity=AGENT,
                    app=ARAGON_KERNEL,
                    role=APP_MANAGER_ROLE,
                    emitted_by=ACL,
                )

                # 9. Set new Lido implementation in Kernel
                validate_aragon_set_app_event(
                    dg_events[8],
                    app_id=LIDO_APP_ID,
                    app=LIDO_IMPL,
                    emitted_by=ARAGON_KERNEL,
                )

                # 10. Revoke APP_MANAGER_ROLE on Kernel from Agent
                validate_aragon_revoke_permission_event(
                    dg_events[9],
                    entity=AGENT,
                    app=ARAGON_KERNEL,
                    role=APP_MANAGER_ROLE,
                    emitted_by=ACL,
                )

                # 11. Grant BUFFER_RESERVE_MANAGER_ROLE on Lido and transfer permission manager to Agent
                validate_events_chain(
                    [e.name for e in dg_events[10]],
                    ["LogScriptCall", "SetPermission", "ChangePermissionManager", "ScriptResult", "Executed"],
                )
                set_permission_event = _single_event(dg_events[10], "SetPermission")
                assert convert.to_address(set_permission_event["entity"]) == convert.to_address(AGENT)
                assert convert.to_address(set_permission_event["app"]) == convert.to_address(LIDO)
                assert set_permission_event["role"] == BUFFER_RESERVE_MANAGER_ROLE
                assert set_permission_event["allowed"] is True
                _assert_emitted_by(set_permission_event, ACL)
                change_permission_manager_event = _single_event(dg_events[10], "ChangePermissionManager")
                assert convert.to_address(change_permission_manager_event["app"]) == convert.to_address(LIDO)
                assert change_permission_manager_event["role"] == BUFFER_RESERVE_MANAGER_ROLE
                assert convert.to_address(change_permission_manager_event["manager"]) == convert.to_address(AGENT)
                _assert_emitted_by(change_permission_manager_event, ACL)

                # 12. Finalize Lido contract version
                validate_contract_version_set_event(dg_events[11], LIDO_CONTRACT_VERSION, emitted_by=LIDO)

                # 13. Grant STAKING_MODULE_SHARE_MANAGE_ROLE to EasyTrack executor
                validate_role_grant_event(
                    dg_events[12],
                    STAKING_MODULE_SHARE_MANAGE_ROLE,
                    EASYTRACK_EVMSCRIPT_EXECUTOR,
                    emitted_by=STAKING_ROUTER,
                )

                # 14. Revoke STAKING_MODULE_UNVETTING_ROLE from old DSM
                validate_role_revoke_event(
                    dg_events[13],
                    STAKING_MODULE_UNVETTING_ROLE,
                    OLD_DEPOSIT_SECURITY_MODULE,
                    emitted_by=STAKING_ROUTER,
                )

                # 15. Grant STAKING_MODULE_UNVETTING_ROLE to new DSM
                validate_role_grant_event(
                    dg_events[14],
                    STAKING_MODULE_UNVETTING_ROLE,
                    NEW_DEPOSIT_SECURITY_MODULE,
                    emitted_by=STAKING_ROUTER,
                )

                # 16. Grant TW_EXIT_LIMIT_MANAGER_ROLE to Agent
                validate_role_grant_event(
                    dg_events[15],
                    TW_EXIT_LIMIT_MANAGER_ROLE,
                    AGENT,
                    emitted_by=TRIGGERABLE_WITHDRAWALS_GATEWAY,
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
                _assert_emitted_by(exit_requests_limit_set_event, TRIGGERABLE_WITHDRAWALS_GATEWAY)

                # 18. Register CircuitBreaker integration
                validate_circuit_breaker_registration_raw_group(raw_dg_events[17])

                # 19. Upgrade and initialize CSM
                validate_proxy_upgrade_event(
                    dg_events[18],
                    CSM_IMPL,
                    emitted_by=CSM,
                    events_chain=["LogScriptCall", "Upgraded", "Initialized", "ScriptResult", "Executed"],
                )
                initialized_event = _single_event(dg_events[18], "Initialized")
                assert initialized_event["version"] == 3
                _assert_emitted_by(initialized_event, CSM)

                # 20. Upgrade and initialize CSParametersRegistry
                validate_proxy_upgrade_event(
                    dg_events[19],
                    CS_PARAMETERS_REGISTRY_IMPL,
                    emitted_by=CS_PARAMETERS_REGISTRY,
                    events_chain=["LogScriptCall", "Upgraded", "Initialized", "ScriptResult", "Executed"],
                )
                initialized_event = _single_event(dg_events[19], "Initialized")
                assert initialized_event["version"] == 3
                _assert_emitted_by(initialized_event, CS_PARAMETERS_REGISTRY)

                # 21. Upgrade and finalize CSFeeOracle
                validate_proxy_upgrade_event(
                    dg_events[20],
                    CS_FEE_ORACLE_IMPL,
                    emitted_by=CS_FEE_ORACLE,
                    events_chain=["LogScriptCall", "Upgraded", "ConsensusVersionSet", "ContractVersionSet", "ScriptResult", "Executed"],
                )
                validate_consensus_version_set_event(
                    dg_events[20],
                    4,
                    3,
                    emitted_by=CS_FEE_ORACLE,
                    events_chain=["LogScriptCall", "Upgraded", "ConsensusVersionSet", "ContractVersionSet", "ScriptResult", "Executed"],
                )
                validate_contract_version_set_event(
                    dg_events[20],
                    3,
                    emitted_by=CS_FEE_ORACLE,
                    events_chain=["LogScriptCall", "Upgraded", "ConsensusVersionSet", "ContractVersionSet", "ScriptResult", "Executed"],
                )

                # 22. Upgrade CSVettedGate
                validate_proxy_upgrade_event(dg_events[21], CS_VETTED_GATE_IMPL, emitted_by=CS_VETTED_GATE)

                # 23. Upgrade and initialize CSAccounting
                validate_proxy_upgrade_event(
                    dg_events[22],
                    CS_ACCOUNTING_IMPL,
                    emitted_by=CS_ACCOUNTING,
                    events_chain=["LogScriptCall", "Upgraded", "Initialized", "ScriptResult", "Executed"],
                )
                initialized_event = _single_event(dg_events[22], "Initialized")
                assert initialized_event["version"] == 3
                _assert_emitted_by(initialized_event, CS_ACCOUNTING)

                # 24. Upgrade and initialize CSFeeDistributor
                validate_proxy_upgrade_event(
                    dg_events[23],
                    CS_FEE_DISTRIBUTOR_IMPL,
                    emitted_by=CS_FEE_DISTRIBUTOR,
                    events_chain=["LogScriptCall", "Upgraded", "Initialized", "ScriptResult", "Executed"],
                )
                initialized_event = _single_event(dg_events[23], "Initialized")
                assert initialized_event["version"] == 3
                _assert_emitted_by(initialized_event, CS_FEE_DISTRIBUTOR)

                # 25. Upgrade CSExitPenalties
                validate_proxy_upgrade_event(dg_events[24], CS_EXIT_PENALTIES_IMPL, emitted_by=CS_EXIT_PENALTIES)

                # 26. Upgrade CSValidatorStrikes
                validate_proxy_upgrade_event(dg_events[25], CS_VALIDATOR_STRIKES_IMPL, emitted_by=CS_VALIDATOR_STRIKES)

                # 27. Set CSM ejector
                validate_events_chain([e.name for e in dg_events[26]], ["LogScriptCall", "EjectorSet", "ScriptResult", "Executed"])
                ejector_set_event = _single_event(dg_events[26], "EjectorSet")
                assert convert.to_address(ejector_set_event["ejector"]) == convert.to_address(CSM_EJECTOR)
                _assert_emitted_by(ejector_set_event, CS_VALIDATOR_STRIKES)

                # 28. Grant REPORT_GENERAL_DELAYED_PENALTY_ROLE
                validate_role_grant_event(
                    dg_events[27],
                    REPORT_GENERAL_DELAYED_PENALTY_ROLE,
                    CSM_GENERAL_DELAYED_PENALTY_REPORTER,
                    emitted_by=CSM,
                )

                # 29. Grant SETTLE_GENERAL_DELAYED_PENALTY_ROLE
                validate_role_grant_event(
                    dg_events[28],
                    SETTLE_GENERAL_DELAYED_PENALTY_ROLE,
                    EASYTRACK_EVMSCRIPT_EXECUTOR,
                    emitted_by=CSM,
                )

                # 30. Revoke REPORT_EL_REWARDS_STEALING_PENALTY_ROLE
                validate_role_revoke_event(
                    dg_events[29],
                    REPORT_EL_REWARDS_STEALING_PENALTY_ROLE,
                    CSM_GENERAL_DELAYED_PENALTY_REPORTER,
                    emitted_by=CSM,
                )

                # 31. Revoke SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE
                validate_role_revoke_event(
                    dg_events[30],
                    SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE,
                    EASYTRACK_EVMSCRIPT_EXECUTOR,
                    emitted_by=CSM,
                )

                # 32. Revoke VERIFIER_ROLE from old verifier
                validate_role_revoke_event(
                    dg_events[31],
                    VERIFIER_ROLE,
                    OLD_VERIFIER,
                    emitted_by=CSM,
                )

                # 33. Grant VERIFIER_ROLE to verifier v3
                validate_role_grant_event(
                    dg_events[32],
                    VERIFIER_ROLE,
                    VERIFIER_V3,
                    emitted_by=CSM,
                )

                # 34. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE
                validate_role_grant_event(
                    dg_events[33],
                    REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE,
                    VERIFIER_V3,
                    emitted_by=CSM,
                )

                # 35. Grant REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE
                validate_role_grant_event(
                    dg_events[34],
                    REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE,
                    EASYTRACK_EVMSCRIPT_EXECUTOR,
                    emitted_by=CSM,
                )

                # 36. Revoke CREATE_NODE_OPERATOR_ROLE from old permissionless gate
                validate_role_revoke_event(
                    dg_events[35],
                    CREATE_NODE_OPERATOR_ROLE,
                    OLD_PERMISSIONLESS_GATE,
                    emitted_by=CSM,
                )

                # 37. Grant CREATE_NODE_OPERATOR_ROLE to new permissionless gate
                validate_role_grant_event(
                    dg_events[36],
                    CREATE_NODE_OPERATOR_ROLE,
                    NEW_PERMISSIONLESS_GATE,
                    emitted_by=CSM,
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
                    AGENT,
                    emitted_by=CS_VETTED_GATE,
                )

                # 43. Revoke END_REFERRAL_SEASON_ROLE from ICS manager
                validate_role_revoke_event(
                    dg_events[42],
                    END_REFERRAL_SEASON_ROLE,
                    ICS_MANAGER,
                    emitted_by=CS_VETTED_GATE,
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
                    CSM_PENALTIES_MANAGER,
                    emitted_by=CS_PARAMETERS_REGISTRY,
                )

                # 49. Revoke REQUEST_BURN_SHARES_ROLE from CSAccounting
                validate_role_revoke_event(
                    dg_events[48],
                    REQUEST_BURN_SHARES_ROLE,
                    CS_ACCOUNTING,
                    emitted_by=BURNER,
                )

                # 50. Grant REQUEST_BURN_MY_STETH_ROLE to CSAccounting
                validate_role_grant_event(
                    dg_events[49],
                    REQUEST_BURN_MY_STETH_ROLE,
                    CS_ACCOUNTING,
                    emitted_by=BURNER,
                )

                # 51. Revoke ADD_FULL_WITHDRAWAL_REQUEST_ROLE from old CSM ejector
                validate_role_revoke_event(
                    dg_events[50],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    OLD_CSM_EJECTOR,
                    emitted_by=TRIGGERABLE_WITHDRAWALS_GATEWAY,
                )

                # 52. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to CSM ejector
                validate_role_grant_event(
                    dg_events[51],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    CSM_EJECTOR,
                    emitted_by=TRIGGERABLE_WITHDRAWALS_GATEWAY,
                )

                # 53. Add curated-onchain-v2 module
                validate_module_add(dg_events[52], CURATED_MODULE_V2, emitted_by=STAKING_ROUTER)

                # 54. Grant REQUEST_BURN_MY_STETH_ROLE to curated accounting
                validate_role_grant_event(
                    dg_events[53],
                    REQUEST_BURN_MY_STETH_ROLE,
                    CURATED_ACCOUNTING,
                    emitted_by=BURNER,
                )

                # 55. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to curated ejector
                validate_role_grant_event(
                    dg_events[54],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    CURATED_EJECTOR,
                    emitted_by=TRIGGERABLE_WITHDRAWALS_GATEWAY,
                )

                # 56. Grant RESUME_ROLE on curated module to Agent
                validate_role_grant_event(
                    dg_events[55],
                    RESUME_ROLE,
                    AGENT,
                    emitted_by=CURATED_MODULE,
                )

                # 57. Resume curated module
                validate_events_chain([e.name for e in dg_events[56]], ["LogScriptCall", "Resumed", "ScriptResult", "Executed"])
                resumed_event = _single_event(dg_events[56], "Resumed")
                _assert_emitted_by(resumed_event, CURATED_MODULE)

                # 58. Revoke RESUME_ROLE from Agent
                validate_role_revoke_event(
                    dg_events[57],
                    RESUME_ROLE,
                    AGENT,
                    emitted_by=CURATED_MODULE,
                )

                # 59. Set curated HashConsensus frame config
                validate_events_chain([e.name for e in dg_events[58]], ["LogScriptCall", "FrameConfigSet", "ScriptResult", "Executed"])
                frame_config_set_event = _single_event(dg_events[58], "FrameConfigSet")
                assert frame_config_set_event["newInitialEpoch"] == CURATED_INITIAL_EPOCH
                assert frame_config_set_event["newEpochsPerFrame"] == CURATED_EPOCHS_PER_FRAME
                _assert_emitted_by(frame_config_set_event, CURATED_HASH_CONSENSUS)

                # 60. Call UpgradeTemplate.finishUpgrade
                validate_events_chain([e.name for e in dg_events[59]], ["LogScriptCall", "UpgradeFinished", "ScriptResult", "Executed"])
                upgrade_finished_event = _single_event(dg_events[59], "UpgradeFinished")
                _assert_emitted_by(upgrade_finished_event, upgrade_template)

        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # TODO Acceptance tests (after DG state)

        # TODO Scenario tests (after DG state)
