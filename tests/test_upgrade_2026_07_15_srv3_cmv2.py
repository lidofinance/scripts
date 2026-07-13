"""
Acceptance test for vote 2026_07_15 — Staking Router v3 + Curated Module v2 + Community Staking Module v3.

Structure follows tests/_test_2026_MM_DD.py:
  * Arrange variables
  * Identify or create vote
  * Execute vote (before / after voting checks)
  * Execute Dual Governance proposal (before / after DG checks)

Upgrade parameters are pinned below as explicit constants so the test validates
the deployed vote script against the expected mainnet configuration.

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
from utils.ipfs import get_lido_vote_cid_from_str

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

UPGRADE_TEMPLATE = "0xD92b6303Ba39297Cb69a3a17A88b47586A6af14C"

# --- UpgradeConfig: protocol contracts and upgrade parameters ---
ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
ARAGON_KERNEL = "0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc"
BURNER = "0xE76c52750019b80B43E36DF30bf4060EB73F573a"
CIRCUIT_BREAKER = "0x6019CB557978296BA3C08a7B73225C0975DFB2F7"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"

LIDO = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
LIDO_IMPL = "0x028271E30a695c0527A0C50cA30603feD004cDb0"
LIDO_ARAGON_APP_ID = "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320"
LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
LIDO_LOCATOR_IMPL = "0x0360002bf51DCae1c0267aE0AFDaBacAF7De686b"
LIDO_DEPOSITS_RESERVE_TARGET = 1_500 * 10**18
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
STAKING_ROUTER_IMPL = "0xDD76927045435C7605cf6f5F978cfb8CABDb5F80"
MAX_TOP_UP_PER_BLOCK_GWEI = 3_200_000_000_000
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
ACCOUNTING_ORACLE_IMPL = "0xe4f03D1107d1905B6F2A28FCb6Af221E0CE19136"
VALIDATORS_EXIT_BUS_ORACLE = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0x2C3386b39db89eef0F362A3BE0C05a6811E809E3"
ACCOUNTING = "0x23ED611be0e1a820978875C0122F92260804cdDf"
ACCOUNTING_IMPL = "0x3aa937Ac2ab89CDd363EdC6b5A4d4A42dF5bc043"
WITHDRAWAL_VAULT = "0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f"
WITHDRAWAL_VAULT_IMPL = "0xfB4521BD151BFB45DB6045D2d07e58e0f597e340"
ORACLE_REPORT_SANITY_CHECKER = "0x147f8d3cf3004FAf9Bf94E88B54b6C06De507be9"

CIRCUIT_BREAKER_COMMITTEE = "0x8772E3a2D86B9347A2688f9bc1808A6d8917760C"
CONSOLIDATION_GATEWAY = "0x17be979344f2c2cC806229a532D92f8742C10462"
CONSOLIDATION_COMMITTEE = "0x2570e0b22AD904501dfB0d49575991ACB801dD91"
CONSOLIDATION_MIGRATOR = "0x9Dc70b5A4f4F5E4AF9058C983D560564F031f1D7"
TOP_UP_GATEWAY = "0x3FC2C71579D80790Aaa3fc7Be8B66ac39dC57374"
OLD_DEPOSIT_SECURITY_MODULE = "0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD"
NEW_DEPOSIT_SECURITY_MODULE = "0xF573E9E3de1f86B085417ab294f56E7920B4e9Be"
TRIGGERABLE_WITHDRAWALS_GATEWAY = "0xDC00116a0D3E064427dA2600449cfD2566B3037B"

# --- UpgradeConfig: Community Staking Module v3 ---
CSM = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
CSM_IMPL = "0x63992a86f009fcC796a8369feEfB68880aef4e3a"
CS_PARAMETERS_REGISTRY = "0x9D28ad303C90DF524BA960d7a2DAC56DcC31e428"
CS_PARAMETERS_REGISTRY_IMPL = "0x107d287F178cD54792614d7D63C47D8242240BeD"
CS_FEE_ORACLE = "0x4D4074628678Bd302921c20573EEa1ed38DdF7FB"
CS_FEE_ORACLE_IMPL = "0xecE6e0Cde61078F76b66Ef0C338a6875E5D01F79"
CS_FEE_ORACLE_CONSENSUS_VERSION = 4
CS_VETTED_GATE = "0xB314D4A76C457c93150d308787939063F4Cc67E0"
CS_VETTED_GATE_IMPL = "0x66ADb8b3F58d3DFdF6bAdB595E41f19e947E5c14"
CS_ACCOUNTING = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"
CS_ACCOUNTING_IMPL = "0xe768572cc5aE5C698345C59288d871a949Ea8bd3"
CS_FEE_DISTRIBUTOR = "0xD99CC66fEC647E68294C6477B40fC7E0F6F618D0"
CS_FEE_DISTRIBUTOR_IMPL = "0x936da7cDB7eed1084d294E23eA1d7Ad72DCcfE0E"
CS_EXIT_PENALTIES = "0x06cd61045f958A209a0f8D746e103eCc625f4193"
CS_EXIT_PENALTIES_IMPL = "0xA5b9e96E951089E629Ab0834AEaF242a81394EA0"
CS_VALIDATOR_STRIKES = "0xaa328816027F2D32B9F56d190BC9Fa4A5C07637f"
CS_VALIDATOR_STRIKES_IMPL = "0xd25E7C3923d2e68c325980b0e15eD20d62B2691F"
OLD_VERIFIER = "0xdC5FE1782B6943f318E05230d688713a560063DC"
VERIFIER_V3 = "0xfce7aB839e55de77730716D05b3553e45ab3A5Ba"
OLD_PERMISSIONLESS_GATE = "0xcF33a38111d0B1246A3F38a838fb41D626B454f0"
NEW_PERMISSIONLESS_GATE = "0xb8cd8F059Ad7a5dB8CAfDe34aAb007317F7156C8"
IDENTIFIED_DVT_CLUSTER_GATE = "0xa12760721A72A7199aB38059DA6690b9Cd4ed7B8"
IDENTIFIED_DVT_CLUSTER_CURVE_SETUP = "0x711985E069f4d702e0457C0dACAde3D3894Ce4E3"
IDENTIFIED_DVT_CLUSTER_BOND_CURVE_ID = 3
NEW_CSM_EJECTOR = "0x610B517D380f287c239C93F8eF6FfBd567AA4bA5"
CONFIG_OLD_CSM_EJECTOR = "0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C"
CSM_COMMITTEE = "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f"

# --- UpgradeConfig: Curated Module v2 ---
CURATED_MODULE = "0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1"
CURATED_GATES = [
    "0x6093EFA6B5E2FF3be54d1c895c9deA932805c49F",
    "0x8c002c6eE10cf8adb78D1F9EB2e134FdaF8A7C1a",
    "0x207798e6fD1aa7Ee8a63782A64c959cD6727b78C",
    "0xeF273Ca4A21Ba7B414Ae3C9f9b443038cb133F72",
    "0x3BbBb175f7F07954DE00052b20E1c5572223F24D",
    "0x86A8d4E0db5938D21d98047544668FCCB1A9ADc8",
    "0x773933F9db8964A17d62fb808f2EC7A2de4247CC",
]
CURATED_ACCOUNTING = "0x2F91e3A8C5d6593bf4F8403fCfeCcd62dF59f6F6"
CURATED_EJECTOR = "0xe181A377A2d2BDE9A83f1474BC3DB7A412de091E"
CURATED_FEE_ORACLE = "0x8EeFCdbD984c30E472BcbF545783D051CB5114e5"
CURATED_VERIFIER = "0xC392F457960f1B13Ebaf1aa6C065479dD507E1E3"
CURATED_CIRCUIT_BREAKER_PAUSER = "0x2570e0b22AD904501dfB0d49575991ACB801dD91"
CURATED_STRIKES = "0xf4618370a1fBf46905B16C10817c8CFaD924D6db"
CURATED_HASH_CONSENSUS = "0x902D64c93F6595339aA46105627a085591051aFb"
CURATED_HASH_CONSENSUS_INITIAL_EPOCH = 467_564
META_REGISTRY = "0xA64b339eebD3dC3De848298B6a140955932901d8"
CURATED_MODULE_NAME = "curated-onchain-v2"
CURATED_STAKE_SHARE_LIMIT = 10_000
CURATED_PRIORITY_EXIT_SHARE_THRESHOLD = 10_000
CURATED_STAKING_MODULE_FEE = 400
CURATED_TREASURY_FEE = 600
CURATED_MAX_DEPOSITS_PER_BLOCK = 100
CURATED_MIN_DEPOSIT_BLOCK_DISTANCE = 75

# --- UpgradeConfig: Easy Track factories ---
EASYTRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
EASYTRACK_EVMSCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x0C6703F1d8D9DdfB6c6e5F57b4f7432a6500D6D8"
ALLOW_CONSOLIDATION_PAIR_FACTORY = "0x29e23B1EF0c9fffAc8330F9abaCebDDD827E4b5C"
SET_MERKLE_GATE_TREE_FOR_CSM_FACTORY = "0xf3ec30B86c3dC1b8a1C754D885F9bE3160e15B4c"
REPORT_WITHDRAWALS_FOR_SLASHED_VALIDATORS_FOR_CSM_FACTORY = "0xE330516a03bDdEBA4209b5591112f1aa3dd90F0A"
SETTLE_GENERAL_DELAYED_PENALTY_FOR_CSM_FACTORY = "0xB71755bE764abB4Ce26cb4dADf056Be57fB8880F"
SET_MERKLE_GATE_TREE_FOR_CM_FACTORY = "0xa121667D1780a1D54EAEd67AE17ee13d0f872D60"
REPORT_WITHDRAWALS_FOR_SLASHED_VALIDATORS_FOR_CM_FACTORY = "0x71862Abd99819597670007bb992A7a7562fE50f2"
SETTLE_GENERAL_DELAYED_PENALTY_FOR_CM_FACTORY = "0xfffEFC16231eDC6Dc9C93e364ff4D4E3f787f416"
CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY = "0x2fC78638b77381e9D040163Bd6EB1cac967bDBdF"
OLD_CSM_SETTLE_EL_STEALING_PENALTY_FACTORY = "0xF6B6E7997338C48Ea3a8BCfa4BB64a315fDa76f4"
OLD_CSM_SET_VETTED_GATE_TREE_FACTORY = "0xBc5642bDD6F2a54b01A75605aAe9143525D97308"

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
EXPECTED_VOTE_ID = 203
EXPECTED_DG_PROPOSAL_ID = 12
EXPECTED_VOTE_EVENTS_COUNT = 12  # 1 DG submission + 11 Easy Track items
EXPECTED_DG_EVENTS_FROM_AGENT = 69
EXPECTED_DG_EVENTS_COUNT = 69
IPFS_DESCRIPTION_HASH = "bafkreieybnjlo5fydapeejdh252q3lsnt7uk4f3fui2kf6qau4kow5gqhq"


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

    # Load ABIs for Brownie receipt event decoding.
    interface.CircuitBreaker(CIRCUIT_BREAKER)
    interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE)
    interface.ParametersRegistry(CS_PARAMETERS_REGISTRY)
    interface.OneShotCurveSetup(IDENTIFIED_DVT_CLUSTER_CURVE_SETUP)
    interface.ModuleAccounting(CS_ACCOUNTING)  # BondCurveAdded (curve setup item)
    # ExitBalanceLimitSet exists only in the new ValidatorsExitBusOracle impl ABI (not in the
    # local interfaces/*.json), so fetch that impl from the explorer to make it decodable.
    Contract.from_explorer(convert.to_address(VALIDATORS_EXIT_BUS_ORACLE_IMPL))

    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    dual_governance_admin_executor = None
    for proposer in dual_governance.getProposers():
        try:
            proposer_account = proposer["account"]
            proposer_executor = proposer["executor"]
        except (KeyError, TypeError):
            proposer_account = proposer[0]
            proposer_executor = proposer[1]

        if convert.to_address(proposer_account) == convert.to_address(VOTING):
            dual_governance_admin_executor = proposer_executor
            break

    assert dual_governance_admin_executor is not None, "Voting proposer is not registered in Dual Governance"

    # Pre-upgrade state used to build dynamic expectations (read before the vote runs):
    #  - StakingRouter role migration performed by finalizeUpgrade_v4
    #  - new staking module id assigned to Curated Module v2
    #  - Curated HashConsensus epochsPerFrame preserved by updateInitialEpoch
    sr_role_migration_grants = _expected_sr_role_migration_grants(STAKING_ROUTER)
    expected_curated_module_id = interface.StakingRouter(STAKING_ROUTER).getStakingModulesCount() + 1
    curated_epochs_per_frame = interface.HashConsensus(CURATED_HASH_CONSENSUS).getFrameConfig()[1]

    return {
        "dual_governance_admin_executor": dual_governance_admin_executor,
        "sr_role_migration_grants": sr_role_migration_grants,
        "curated_epochs_per_frame": curated_epochs_per_frame,
        "curated_module_item": StakingModuleItem(
            id=expected_curated_module_id,
            staking_module_address=CURATED_MODULE,
            name=CURATED_MODULE_NAME,
            staking_module_fee=CURATED_STAKING_MODULE_FEE,
            stake_share_limit=CURATED_STAKE_SHARE_LIMIT,
            treasury_fee=CURATED_TREASURY_FEE,
            priority_exit_share_threshold=CURATED_PRIORITY_EXIT_SHARE_THRESHOLD,
            max_deposits_per_block=CURATED_MAX_DEPOSITS_PER_BLOCK,
            min_deposit_block_distance=CURATED_MIN_DEPOSIT_BLOCK_DISTANCE,
        ),
    }


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    dg_items = get_dg_items(UPGRADE_VOTE_SCRIPT)

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

    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    easy_track = interface.EasyTrack(EASYTRACK)
    staking_router = interface.StakingRouter(STAKING_ROUTER)

    _, call_script_items = get_vote_items(upgrade_vote_script=UPGRADE_VOTE_SCRIPT)
    # NB: get_dg_items() returns the Dual Governance proposal calls — a single packed
    # `Agent.forward(...)` call. The individual upgrade actions live inside it and only
    # surface as events during DG execution, so their count comes from DG_ITEMS_COUNT().
    vote_script = interface.UpgradeVoteScript(UPGRADE_VOTE_SCRIPT)
    onchain_dg_items_count = vote_script.DG_ITEMS_COUNT()

    # Guard against the deployed script drifting from the counts encoded in this test.
    assert (
        onchain_dg_items_count == EXPECTED_DG_EVENTS_COUNT
    ), f"On-chain DG_ITEMS_COUNT ({onchain_dg_items_count}) != EXPECTED_DG_EVENTS_COUNT ({EXPECTED_DG_EVENTS_COUNT})"
    assert len(call_script_items) == EXPECTED_VOTE_EVENTS_COUNT, (
        f"On-chain voting item count ({len(call_script_items)}) != EXPECTED_VOTE_EVENTS_COUNT "
        f"({EXPECTED_VOTE_EVENTS_COUNT})"
    )

    old_easy_track_factories = [
        OLD_CSM_SETTLE_EL_STEALING_PENALTY_FACTORY,
        OLD_CSM_SET_VETTED_GATE_TREE_FACTORY,
    ]
    new_easy_track_factories = [
        UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
        ALLOW_CONSOLIDATION_PAIR_FACTORY,
        SET_MERKLE_GATE_TREE_FOR_CSM_FACTORY,
        REPORT_WITHDRAWALS_FOR_SLASHED_VALIDATORS_FOR_CSM_FACTORY,
        SETTLE_GENERAL_DELAYED_PENALTY_FOR_CSM_FACTORY,
        SET_MERKLE_GATE_TREE_FOR_CM_FACTORY,
        REPORT_WITHDRAWALS_FOR_SLASHED_VALIDATORS_FOR_CM_FACTORY,
        SETTLE_GENERAL_DELAYED_PENALTY_FOR_CM_FACTORY,
        CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY,
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
            upgrade_vote_script=UPGRADE_VOTE_SCRIPT,
        )

    onchain_script = voting.getVote(vote_id)["script"]
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()

    expected_dg_proposal_id = EXPECTED_DG_PROPOSAL_ID

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

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

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

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        # 1. Submit a Dual Governance proposal
        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=expected_dg_proposal_id,
            proposer=VOTING,
            executor=ctx["dual_governance_admin_executor"],
            metadata=DG_PROPOSAL_METADATA,
            proposal_calls=dual_governance_proposal_calls,
        )

        # 2. Remove CSMSettleElStealingPenalty ET factory
        validate_evmscript_factory_removed_event(
            vote_events[1],
            factory_addr=OLD_CSM_SETTLE_EL_STEALING_PENALTY_FACTORY,
            emitted_by=easy_track,
        )

        # 3. Remove CSMSetVettedGateTree ET factory
        validate_evmscript_factory_removed_event(
            vote_events[2],
            factory_addr=OLD_CSM_SET_VETTED_GATE_TREE_FACTORY,
            emitted_by=easy_track,
        )

        # 4. Add UpdateStakingModuleShareLimits ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[3],
            p=EVMScriptFactoryAdded(
                factory_addr=UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
                permissions=_concat_permissions(
                    _permission(
                        UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
                        VALIDATE_STAKING_MODULE_SHARE_PARAMS_SELECTOR,
                    ),
                    _permission(STAKING_ROUTER, UPDATE_MODULE_SHARES_SELECTOR),
                ),
            ),
            emitted_by=easy_track,
        )

        # 5. Add AllowConsolidationPair ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[4],
            p=EVMScriptFactoryAdded(
                factory_addr=ALLOW_CONSOLIDATION_PAIR_FACTORY,
                permissions=_permission(CONSOLIDATION_MIGRATOR, ALLOW_CONSOLIDATION_PAIR_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 6. Add SetMerkleGateTree CSM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[5],
            p=EVMScriptFactoryAdded(
                factory_addr=SET_MERKLE_GATE_TREE_FOR_CSM_FACTORY,
                # SetMerkleGateTree permissions = factory.validateInputData + each gate.setTreeParams
                permissions=_concat_permissions(
                    _permission(
                        SET_MERKLE_GATE_TREE_FOR_CSM_FACTORY, SET_MERKLE_GATE_TREE_VALIDATE_INPUT_DATA_SELECTOR
                    ),
                    _permission(CS_VETTED_GATE, SET_TREE_PARAMS_SELECTOR),
                    _permission(IDENTIFIED_DVT_CLUSTER_GATE, SET_TREE_PARAMS_SELECTOR),
                ),
            ),
            emitted_by=easy_track,
        )

        # 7. Add ReportWithdrawalsForSlashedValidators CSM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[6],
            p=EVMScriptFactoryAdded(
                factory_addr=REPORT_WITHDRAWALS_FOR_SLASHED_VALIDATORS_FOR_CSM_FACTORY,
                permissions=_permission(CSM, REPORT_SLASHED_WITHDRAWN_VALIDATORS_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 8. Add SettleGeneralDelayedPenalty CSM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[7],
            p=EVMScriptFactoryAdded(
                factory_addr=SETTLE_GENERAL_DELAYED_PENALTY_FOR_CSM_FACTORY,
                permissions=_permission(CSM, SETTLE_GENERAL_DELAYED_PENALTY_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 9. Add SetMerkleGateTree CM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[8],
            p=EVMScriptFactoryAdded(
                factory_addr=SET_MERKLE_GATE_TREE_FOR_CM_FACTORY,
                # SetMerkleGateTree permissions = factory.validateInputData + each gate.setTreeParams
                permissions=_concat_permissions(
                    _permission(
                        SET_MERKLE_GATE_TREE_FOR_CM_FACTORY, SET_MERKLE_GATE_TREE_VALIDATE_INPUT_DATA_SELECTOR
                    ),
                    *[_permission(gate, SET_TREE_PARAMS_SELECTOR) for gate in CURATED_GATES],
                ),
            ),
            emitted_by=easy_track,
        )

        # 10. Add ReportWithdrawalsForSlashedValidators CM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[9],
            p=EVMScriptFactoryAdded(
                factory_addr=REPORT_WITHDRAWALS_FOR_SLASHED_VALIDATORS_FOR_CM_FACTORY,
                permissions=_permission(CURATED_MODULE, REPORT_SLASHED_WITHDRAWN_VALIDATORS_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 11. Add SettleGeneralDelayedPenalty CM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[10],
            p=EVMScriptFactoryAdded(
                factory_addr=SETTLE_GENERAL_DELAYED_PENALTY_FOR_CM_FACTORY,
                permissions=_permission(CURATED_MODULE, SETTLE_GENERAL_DELAYED_PENALTY_SELECTOR),
            ),
            emitted_by=easy_track,
        )

        # 12. Add CreateOrUpdateOperatorGroup CM ET factory
        validate_evmscript_factory_added_event(
            event=vote_events[11],
            p=EVMScriptFactoryAdded(
                factory_addr=CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY,
                permissions=_concat_permissions(
                    _permission(
                        CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY,
                        CREATE_OR_UPDATE_OPERATOR_GROUP_VALIDATE_INPUT_DATA_SELECTOR,
                    ),
                    _permission(META_REGISTRY, CREATE_OR_UPDATE_OPERATOR_GROUP_SELECTOR),
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
        initial_cs_fee_oracle_consensus_version = interface.FeeOracle(CS_FEE_ORACLE).getConsensusVersion()

        details = timelock.getProposalDetails(expected_dg_proposal_id)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =================================================================
            # ================ Before DG proposal executed checks =============
            # =================================================================
            assert (
                interface.AccountingOracle(ACCOUNTING_ORACLE).getConsensusVersion() == AO_CONSENSUS_VERSION - 1
            )
            assert (
                interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE).getConsensusVersion()
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
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
                assert len(outer_dg_events) == 1
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

                # =============================================================
                # ================ DG EXECUTION EVENTS VALIDATION =============
                # =============================================================

                # ------------------------ Core ------------------------------
                # 1.1. Call UpgradeTemplate.startUpgrade
                validate_events_chain([e.name for e in dg_events[0]], ["LogScriptCall", "UpgradeStarted"])
                _assert_emitted_by(_single_event(dg_events[0], "UpgradeStarted"), UPGRADE_TEMPLATE)

                # 1.2. Upgrade LidoLocator implementation
                validate_proxy_upgrade_event(dg_events[1], LIDO_LOCATOR_IMPL, emitted_by=LIDO_LOCATOR)

                # 1.3. Upgrade StakingRouter implementation and call finalizeUpgrade_v4.
                #      finalizeUpgrade_v4 sets maxTopUpPerBlockGwei and re-grants each pre-upgrade
                #      member of the migrated roles.
                sr_grants = ctx["sr_role_migration_grants"]
                validate_proxy_upgrade_event(
                    dg_events[2],
                    STAKING_ROUTER_IMPL,
                    emitted_by=STAKING_ROUTER,
                    events_chain=["LogScriptCall", "Upgraded", "MaxTopUpPerBlockGweiSet"]
                    + ["RoleGranted"] * len(sr_grants)
                    + ["Initialized"],
                )
                max_top_up_event = _single_event(dg_events[2], "MaxTopUpPerBlockGweiSet")
                assert max_top_up_event["maxTopUpPerBlockGwei"] == MAX_TOP_UP_PER_BLOCK_GWEI
                assert convert.to_address(max_top_up_event["setBy"]) == convert.to_address(AGENT)
                _assert_emitted_by(max_top_up_event, STAKING_ROUTER)
                role_grants = _event_list(dg_events[2], "RoleGranted")
                assert len(role_grants) == len(sr_grants)
                for role_granted_event, (role_hash, account) in zip(role_grants, sr_grants):
                    assert _normalize_role(role_granted_event["role"]) == _normalize_role(role_hash)
                    assert convert.to_address(role_granted_event["account"]) == convert.to_address(account)
                    assert convert.to_address(role_granted_event["sender"]) == convert.to_address(AGENT)
                    _assert_emitted_by(role_granted_event, STAKING_ROUTER)
                initialized_event = _single_event(dg_events[2], "Initialized")
                assert initialized_event["version"] == SR_INITIALIZED_VERSION
                _assert_emitted_by(initialized_event, STAKING_ROUTER)

                # 1.4. Upgrade AccountingOracle implementation and call finalizeUpgrade_v5
                ao_chain = ["LogScriptCall", "Upgraded", "ContractVersionSet", "ConsensusVersionSet"]
                validate_proxy_upgrade_event(
                    dg_events[3],
                    ACCOUNTING_ORACLE_IMPL,
                    emitted_by=ACCOUNTING_ORACLE,
                    events_chain=ao_chain,
                )
                validate_contract_version_set_event(
                    dg_events[3], AO_CONTRACT_VERSION, emitted_by=ACCOUNTING_ORACLE, events_chain=ao_chain
                )
                validate_consensus_version_set_event(
                    dg_events[3],
                    AO_CONSENSUS_VERSION,
                    AO_CONSENSUS_VERSION - 1,
                    emitted_by=ACCOUNTING_ORACLE,
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
                    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
                    emitted_by=VALIDATORS_EXIT_BUS_ORACLE,
                    events_chain=vebo_chain,
                )
                validate_contract_version_set_event(
                    dg_events[4],
                    VEBO_CONTRACT_VERSION,
                    emitted_by=VALIDATORS_EXIT_BUS_ORACLE,
                    events_chain=vebo_chain,
                )
                validate_consensus_version_set_event(
                    dg_events[4],
                    VEBO_CONSENSUS_VERSION,
                    VEBO_CONSENSUS_VERSION - 1,
                    emitted_by=VALIDATORS_EXIT_BUS_ORACLE,
                    events_chain=vebo_chain,
                )
                set_max_validators_event = _single_event(dg_events[4], "SetMaxValidatorsPerReport")
                assert set_max_validators_event["maxValidatorsPerReport"] == VEBO_MAX_VALIDATORS_PER_REPORT
                _assert_emitted_by(set_max_validators_event, VALIDATORS_EXIT_BUS_ORACLE)
                exit_balance_limit_event = _single_event(dg_events[4], "ExitBalanceLimitSet")
                assert exit_balance_limit_event["maxExitBalanceEth"] == VALIDATORS_EXIT_BUS_MAX_EXIT_BALANCE_ETH
                assert exit_balance_limit_event["balancePerFrameEth"] == VALIDATORS_EXIT_BUS_BALANCE_PER_FRAME_ETH
                assert exit_balance_limit_event["frameDurationInSec"] == VALIDATORS_EXIT_BUS_FRAME_DURATION_IN_SEC
                _assert_emitted_by(exit_balance_limit_event, VALIDATORS_EXIT_BUS_ORACLE)

                # 1.6. Upgrade Accounting implementation
                validate_proxy_upgrade_event(dg_events[5], ACCOUNTING_IMPL, emitted_by=ACCOUNTING)

                # 1.7. Upgrade WithdrawalVault implementation and call finalizeUpgrade_v3
                wv_chain = ["LogScriptCall", "Upgraded", "ContractVersionSet"]
                validate_proxy_upgrade_event(
                    dg_events[6],
                    WITHDRAWAL_VAULT_IMPL,
                    emitted_by=WITHDRAWAL_VAULT,
                    events_chain=wv_chain,
                )
                validate_contract_version_set_event(
                    dg_events[6],
                    WITHDRAWAL_VAULT_CONTRACT_VERSION,
                    emitted_by=WITHDRAWAL_VAULT,
                    events_chain=wv_chain,
                )

                # 1.8. Grant Aragon APP_MANAGER_ROLE to the AGENT
                validate_events_chain([e.name for e in dg_events[7]], ["LogScriptCall", "SetPermission"])
                set_permission_event = _single_event(dg_events[7], "SetPermission")
                assert convert.to_address(set_permission_event["entity"]) == convert.to_address(AGENT)
                assert convert.to_address(set_permission_event["app"]) == convert.to_address(ARAGON_KERNEL)
                assert set_permission_event["role"] == APP_MANAGER_ROLE
                assert set_permission_event["allowed"] is True
                _assert_emitted_by(set_permission_event, ACL)

                # 1.9. Set Lido implementation in Kernel
                validate_events_chain([e.name for e in dg_events[8]], ["LogScriptCall", "SetApp"])
                set_app_event = _single_event(dg_events[8], "SetApp")
                assert set_app_event["appId"] == LIDO_ARAGON_APP_ID
                assert convert.to_address(set_app_event["app"]) == convert.to_address(LIDO_IMPL)
                _assert_emitted_by(set_app_event, ARAGON_KERNEL)

                # 1.10. Revoke Aragon APP_MANAGER_ROLE from the AGENT
                validate_events_chain([e.name for e in dg_events[9]], ["LogScriptCall", "SetPermission"])
                set_permission_event = _single_event(dg_events[9], "SetPermission")
                assert convert.to_address(set_permission_event["entity"]) == convert.to_address(AGENT)
                assert convert.to_address(set_permission_event["app"]) == convert.to_address(ARAGON_KERNEL)
                assert set_permission_event["role"] == APP_MANAGER_ROLE
                assert set_permission_event["allowed"] is False
                _assert_emitted_by(set_permission_event, ACL)

                # 1.11. Create Aragon BUFFER_RESERVE_MANAGER_ROLE and grant role manager to the AGENT
                validate_events_chain(
                    [e.name for e in dg_events[10]],
                    ["LogScriptCall", "SetPermission", "ChangePermissionManager"],
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
                assert convert.to_address(change_permission_manager_event["manager"]) == convert.to_address(
                    AGENT
                )
                _assert_emitted_by(change_permission_manager_event, ACL)

                # 1.12. Call finalizeUpgrade_v4 on Lido
                lido_finalize_chain = ["LogScriptCall", "ContractVersionSet", "DepositsReserveTargetSet"]
                validate_contract_version_set_event(
                    dg_events[11], LIDO_CONTRACT_VERSION, emitted_by=LIDO, events_chain=lido_finalize_chain
                )
                deposits_reserve_target_event = _single_event(dg_events[11], "DepositsReserveTargetSet")
                assert deposits_reserve_target_event["depositsReserveTarget"] == LIDO_DEPOSITS_RESERVE_TARGET
                _assert_emitted_by(deposits_reserve_target_event, LIDO)

                # 1.13. Grant Staking Router STAKING_MODULE_SHARE_MANAGE_ROLE to EasyTrack executor
                validate_role_grant_event(
                    dg_events[12],
                    STAKING_MODULE_SHARE_MANAGE_ROLE,
                    EASYTRACK_EVMSCRIPT_EXECUTOR,
                    sender=AGENT,
                    emitted_by=STAKING_ROUTER,
                )

                # 1.14. Revoke Staking Router STAKING_MODULE_UNVETTING_ROLE from old DSM
                validate_role_revoke_event(
                    dg_events[13],
                    STAKING_MODULE_UNVETTING_ROLE,
                    OLD_DEPOSIT_SECURITY_MODULE,
                    sender=AGENT,
                    emitted_by=STAKING_ROUTER,
                )

                # 1.15. Grant Staking Router STAKING_MODULE_UNVETTING_ROLE to new DSM
                validate_role_grant_event(
                    dg_events[14],
                    STAKING_MODULE_UNVETTING_ROLE,
                    NEW_DEPOSIT_SECURITY_MODULE,
                    sender=AGENT,
                    emitted_by=STAKING_ROUTER,
                )

                # 1.16. Grant TWG TW_EXIT_LIMIT_MANAGER_ROLE to AGENT
                validate_role_grant_event(
                    dg_events[15],
                    TW_EXIT_LIMIT_MANAGER_ROLE,
                    AGENT,
                    sender=AGENT,
                    emitted_by=TRIGGERABLE_WITHDRAWALS_GATEWAY,
                )

                # 1.17. Set TWG exit request limits
                validate_events_chain([e.name for e in dg_events[16]], ["LogScriptCall", "ExitRequestsLimitSet"])
                exit_requests_limit_set_event = _single_event(dg_events[16], "ExitRequestsLimitSet")
                assert exit_requests_limit_set_event["maxExitRequestsLimit"] == TW_MAX_EXIT_REQUESTS
                assert exit_requests_limit_set_event["exitsPerFrame"] == TW_EXITS_PER_FRAME
                assert exit_requests_limit_set_event["frameDurationInSec"] == TW_FRAME_DURATION_IN_SEC
                _assert_emitted_by(exit_requests_limit_set_event, TRIGGERABLE_WITHDRAWALS_GATEWAY)

                # 1.18. Register CircuitBreaker pauser for ConsolidationGateway
                validate_circuit_breaker_registration_event(
                    dg_events[17],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=CONSOLIDATION_GATEWAY,
                    pauser=CIRCUIT_BREAKER_COMMITTEE,
                )

                # 1.19. Register CircuitBreaker pauser for TopUpGateway
                validate_circuit_breaker_registration_event(
                    dg_events[18],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=TOP_UP_GATEWAY,
                    pauser=CIRCUIT_BREAKER_COMMITTEE,
                )

                # ------------------------- CSM ------------------------------
                # 1.20. Upgrade CSM to v3 and call finalizeUpgradeV3
                validate_proxy_upgrade_event(
                    dg_events[19],
                    CSM_IMPL,
                    emitted_by=CSM,
                    events_chain=["LogScriptCall", "Upgraded", "Initialized"],
                )
                assert _single_event(dg_events[19], "Initialized")["version"] == CSM_INITIALIZED_VERSION
                _assert_emitted_by(_single_event(dg_events[19], "Initialized"), CSM)

                # 1.21. Upgrade CSM ParametersRegistry to v3 and call finalizeUpgradeV3
                validate_proxy_upgrade_event(
                    dg_events[20],
                    CS_PARAMETERS_REGISTRY_IMPL,
                    emitted_by=CS_PARAMETERS_REGISTRY,
                    events_chain=["LogScriptCall", "Upgraded", "Initialized"],
                )
                assert _single_event(dg_events[20], "Initialized")["version"] == CSM_INITIALIZED_VERSION
                _assert_emitted_by(_single_event(dg_events[20], "Initialized"), CS_PARAMETERS_REGISTRY)

                # 1.22. Upgrade CSM FeeOracle to v3 and call finalizeUpgradeV3
                fo_chain = ["LogScriptCall", "Upgraded", "ConsensusVersionSet", "ContractVersionSet"]
                validate_proxy_upgrade_event(
                    dg_events[21], CS_FEE_ORACLE_IMPL, emitted_by=CS_FEE_ORACLE, events_chain=fo_chain
                )
                validate_consensus_version_set_event(
                    dg_events[21],
                    CS_FEE_ORACLE_CONSENSUS_VERSION,
                    initial_cs_fee_oracle_consensus_version,
                    emitted_by=CS_FEE_ORACLE,
                    events_chain=fo_chain,
                )
                validate_contract_version_set_event(
                    dg_events[21],
                    CS_FEE_ORACLE_CONTRACT_VERSION,
                    emitted_by=CS_FEE_ORACLE,
                    events_chain=fo_chain,
                )

                # 1.23. Upgrade CSM VettedGate implementation
                validate_proxy_upgrade_event(
                    dg_events[22], CS_VETTED_GATE_IMPL, emitted_by=CS_VETTED_GATE
                )

                # 1.24. Upgrade CSM Accounting to v3 and call finalizeUpgradeV3
                validate_proxy_upgrade_event(
                    dg_events[23],
                    CS_ACCOUNTING_IMPL,
                    emitted_by=CS_ACCOUNTING,
                    events_chain=["LogScriptCall", "Upgraded", "Initialized"],
                )
                assert _single_event(dg_events[23], "Initialized")["version"] == CSM_INITIALIZED_VERSION
                _assert_emitted_by(_single_event(dg_events[23], "Initialized"), CS_ACCOUNTING)

                # 1.25. Upgrade CSM FeeDistributor to v3 and call finalizeUpgradeV3
                validate_proxy_upgrade_event(
                    dg_events[24],
                    CS_FEE_DISTRIBUTOR_IMPL,
                    emitted_by=CS_FEE_DISTRIBUTOR,
                    events_chain=["LogScriptCall", "Upgraded", "Initialized"],
                )
                assert _single_event(dg_events[24], "Initialized")["version"] == CSM_INITIALIZED_VERSION
                _assert_emitted_by(_single_event(dg_events[24], "Initialized"), CS_FEE_DISTRIBUTOR)

                # 1.26. Upgrade CSM ExitPenalties implementation
                validate_proxy_upgrade_event(
                    dg_events[25], CS_EXIT_PENALTIES_IMPL, emitted_by=CS_EXIT_PENALTIES
                )

                # 1.27. Upgrade CSM ValidatorStrikes implementation
                validate_proxy_upgrade_event(
                    dg_events[26], CS_VALIDATOR_STRIKES_IMPL, emitted_by=CS_VALIDATOR_STRIKES
                )

                # 1.28. Point CSM ValidatorStrikes to the New CSM Ejector
                validate_events_chain([e.name for e in dg_events[27]], ["LogScriptCall", "EjectorSet"])
                ejector_set_event = _single_event(dg_events[27], "EjectorSet")
                assert convert.to_address(ejector_set_event["ejector"]) == convert.to_address(NEW_CSM_EJECTOR)
                _assert_emitted_by(ejector_set_event, CS_VALIDATOR_STRIKES)

                # 1.29. Revoke CSM REPORT_EL_REWARDS_STEALING_PENALTY_ROLE from CSM Committee
                validate_role_revoke_event(
                    dg_events[28],
                    REPORT_EL_REWARDS_STEALING_PENALTY_ROLE,
                    CSM_COMMITTEE,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.30. Grant CSM REPORT_GENERAL_DELAYED_PENALTY_ROLE to CSM Committee
                validate_role_grant_event(
                    dg_events[29],
                    REPORT_GENERAL_DELAYED_PENALTY_ROLE,
                    CSM_COMMITTEE,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.31. Revoke CSM SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE from Easy Track executor
                validate_role_revoke_event(
                    dg_events[30],
                    SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE,
                    EASYTRACK_EVMSCRIPT_EXECUTOR,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.32. Grant CSM SETTLE_GENERAL_DELAYED_PENALTY_ROLE to Easy Track executor
                validate_role_grant_event(
                    dg_events[31],
                    SETTLE_GENERAL_DELAYED_PENALTY_ROLE,
                    EASYTRACK_EVMSCRIPT_EXECUTOR,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.33. Revoke CSM VERIFIER_ROLE from the Old CSM Verifier
                validate_role_revoke_event(
                    dg_events[32],
                    VERIFIER_ROLE,
                    OLD_VERIFIER,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.34. Grant CSM VERIFIER_ROLE to the New CSM Verifier
                validate_role_grant_event(
                    dg_events[33],
                    VERIFIER_ROLE,
                    VERIFIER_V3,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.35. Grant CSM REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE to the New CSM Verifier
                validate_role_grant_event(
                    dg_events[34],
                    REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE,
                    VERIFIER_V3,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.36. Grant CSM REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE to Easy Track executor
                validate_role_grant_event(
                    dg_events[35],
                    REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE,
                    EASYTRACK_EVMSCRIPT_EXECUTOR,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.37. Revoke CSM CREATE_NODE_OPERATOR_ROLE from the Old CSM PermissionlessGate
                validate_role_revoke_event(
                    dg_events[36],
                    CREATE_NODE_OPERATOR_ROLE,
                    OLD_PERMISSIONLESS_GATE,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.38. Grant CSM CREATE_NODE_OPERATOR_ROLE to the New CSM PermissionlessGate
                validate_role_grant_event(
                    dg_events[37],
                    CREATE_NODE_OPERATOR_ROLE,
                    NEW_PERMISSIONLESS_GATE,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.39. Revoke VettedGate START_REFERRAL_SEASON_ROLE from AGENT
                validate_role_revoke_event(
                    dg_events[38],
                    START_REFERRAL_SEASON_ROLE,
                    AGENT,
                    sender=AGENT,
                    emitted_by=CS_VETTED_GATE,
                )

                # 1.40. Revoke VettedGate END_REFERRAL_SEASON_ROLE from CSM Committee
                validate_role_revoke_event(
                    dg_events[39],
                    END_REFERRAL_SEASON_ROLE,
                    CSM_COMMITTEE,
                    sender=AGENT,
                    emitted_by=CS_VETTED_GATE,
                )

                # 1.41. Set name Identified Community Stakers for CSM VettedGate gate
                validate_gate_name_set_event(
                    dg_events[40], IDENTIFIED_COMMUNITY_STAKERS_GATE_NAME, emitted_by=CS_VETTED_GATE
                )

                # 1.42. Unregister CircuitBreaker pauser for Old CSM Verifier
                validate_circuit_breaker_unregistration_event(
                    dg_events[41],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=OLD_VERIFIER,
                    previous_pauser=CSM_COMMITTEE,
                )

                # 1.43. Unregister CircuitBreaker pauser for Old CSM Ejector
                validate_circuit_breaker_unregistration_event(
                    dg_events[42],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=CONFIG_OLD_CSM_EJECTOR,
                    previous_pauser=CSM_COMMITTEE,
                )

                # 1.44. Register CircuitBreaker pauser for New CSM Verifier
                validate_circuit_breaker_registration_event(
                    dg_events[43],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=VERIFIER_V3,
                    pauser=CSM_COMMITTEE,
                )

                # 1.45. Register CircuitBreaker pauser for New CSM Ejector
                validate_circuit_breaker_registration_event(
                    dg_events[44],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=NEW_CSM_EJECTOR,
                    pauser=CSM_COMMITTEE,
                )

                # 1.46. Register CircuitBreaker pauser for CSM Identified DVT Cluster gate
                validate_circuit_breaker_registration_event(
                    dg_events[45],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=IDENTIFIED_DVT_CLUSTER_GATE,
                    pauser=CSM_COMMITTEE,
                )

                # 1.47. Grant CSM CREATE_NODE_OPERATOR_ROLE to Identified DVT Cluster gate
                validate_role_grant_event(
                    dg_events[46],
                    CREATE_NODE_OPERATOR_ROLE,
                    IDENTIFIED_DVT_CLUSTER_GATE,
                    sender=AGENT,
                    emitted_by=CSM,
                )

                # 1.48. Grant CSM Accounting SET_BOND_CURVE_ROLE to Identified DVT Cluster gate
                validate_role_grant_event(
                    dg_events[47],
                    SET_BOND_CURVE_ROLE,
                    IDENTIFIED_DVT_CLUSTER_GATE,
                    sender=AGENT,
                    emitted_by=CS_ACCOUNTING,
                )

                # 1.49. Grant CSM Accounting MANAGE_BOND_CURVES_ROLE to Identified DVT Cluster curve setup
                validate_role_grant_event(
                    dg_events[48],
                    MANAGE_BOND_CURVES_ROLE,
                    IDENTIFIED_DVT_CLUSTER_CURVE_SETUP,
                    sender=AGENT,
                    emitted_by=CS_ACCOUNTING,
                )

                # 1.50. Grant CSM ParametersRegistry MANAGE_CURVE_PARAMETERS_ROLE to Identified DVT Cluster curve setup
                validate_role_grant_event(
                    dg_events[49],
                    MANAGE_CURVE_PARAMETERS_ROLE,
                    IDENTIFIED_DVT_CLUSTER_CURVE_SETUP,
                    sender=AGENT,
                    emitted_by=CS_PARAMETERS_REGISTRY,
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
                bond_curve_id = IDENTIFIED_DVT_CLUSTER_BOND_CURVE_ID
                bond_curve_added_event = _single_event(dg_events[50], "BondCurveAdded")
                assert bond_curve_added_event["curveId"] == bond_curve_id
                assert bond_curve_added_event["bondCurveIntervals"] == IDVT_BOND_CURVE
                _assert_emitted_by(bond_curve_added_event, CS_ACCOUNTING)
                key_removal_charge_set_event = _single_event(dg_events[50], "KeyRemovalChargeSet")
                assert key_removal_charge_set_event["curveId"] == bond_curve_id
                assert key_removal_charge_set_event["keyRemovalCharge"] == IDVT_KEY_REMOVAL_CHARGE
                _assert_emitted_by(key_removal_charge_set_event, CS_PARAMETERS_REGISTRY)
                general_delayed_penalty_fine_event = _single_event(
                    dg_events[50], "GeneralDelayedPenaltyAdditionalFineSet"
                )
                assert general_delayed_penalty_fine_event["curveId"] == bond_curve_id
                assert general_delayed_penalty_fine_event["fine"] == IDVT_GENERAL_DELAYED_PENALTY_FINE
                _assert_emitted_by(general_delayed_penalty_fine_event, CS_PARAMETERS_REGISTRY)
                queue_config_set_event = _single_event(dg_events[50], "QueueConfigSet")
                assert queue_config_set_event["curveId"] == bond_curve_id
                assert queue_config_set_event["priority"] == IDVT_QUEUE_PRIORITY
                assert queue_config_set_event["maxDeposits"] == IDVT_QUEUE_MAX_DEPOSITS
                _assert_emitted_by(queue_config_set_event, CS_PARAMETERS_REGISTRY)
                reward_share_data_set_event = _single_event(dg_events[50], "RewardShareDataSet")
                assert reward_share_data_set_event["curveId"] == bond_curve_id
                assert reward_share_data_set_event["data"] == IDVT_REWARD_SHARE_DATA
                _assert_emitted_by(reward_share_data_set_event, CS_PARAMETERS_REGISTRY)
                allowed_exit_delay_set_event = _single_event(dg_events[50], "AllowedExitDelaySet")
                assert allowed_exit_delay_set_event["curveId"] == bond_curve_id
                assert allowed_exit_delay_set_event["delay"] == IDVT_ALLOWED_EXIT_DELAY
                _assert_emitted_by(allowed_exit_delay_set_event, CS_PARAMETERS_REGISTRY)
                exit_delay_fee_event = _single_event(dg_events[50], "ExitDelayFeeSet")
                assert exit_delay_fee_event["curveId"] == bond_curve_id
                assert exit_delay_fee_event["penalty"] == IDVT_EXIT_DELAY_FEE
                _assert_emitted_by(exit_delay_fee_event, CS_PARAMETERS_REGISTRY)
                role_revokes = _event_list(dg_events[50], "RoleRevoked")
                assert len(role_revokes) == 2
                assert _normalize_role(role_revokes[0]["role"]) == MANAGE_BOND_CURVES_ROLE.replace("0x", "")
                assert convert.to_address(role_revokes[0]["account"]) == convert.to_address(
                    IDENTIFIED_DVT_CLUSTER_CURVE_SETUP
                )
                assert convert.to_address(role_revokes[0]["sender"]) == convert.to_address(
                    IDENTIFIED_DVT_CLUSTER_CURVE_SETUP
                )
                _assert_emitted_by(role_revokes[0], CS_ACCOUNTING)
                assert _normalize_role(role_revokes[1]["role"]) == MANAGE_CURVE_PARAMETERS_ROLE.replace("0x", "")
                assert convert.to_address(role_revokes[1]["account"]) == convert.to_address(
                    IDENTIFIED_DVT_CLUSTER_CURVE_SETUP
                )
                assert convert.to_address(role_revokes[1]["sender"]) == convert.to_address(
                    IDENTIFIED_DVT_CLUSTER_CURVE_SETUP
                )
                _assert_emitted_by(role_revokes[1], CS_PARAMETERS_REGISTRY)
                bond_curve_deployed_event = _single_event(dg_events[50], "BondCurveDeployed")
                assert bond_curve_deployed_event["curveId"] == bond_curve_id
                _assert_emitted_by(bond_curve_deployed_event, IDENTIFIED_DVT_CLUSTER_CURVE_SETUP)

                # 1.52. Grant CSM ParametersRegistry MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE to CSM Committee
                validate_role_grant_event(
                    dg_events[51],
                    MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE,
                    CSM_COMMITTEE,
                    sender=AGENT,
                    emitted_by=CS_PARAMETERS_REGISTRY,
                )

                # 1.53. Revoke Burner REQUEST_BURN_SHARES_ROLE from CSM Accounting
                validate_role_revoke_event(
                    dg_events[52],
                    REQUEST_BURN_SHARES_ROLE,
                    CS_ACCOUNTING,
                    sender=AGENT,
                    emitted_by=BURNER,
                )

                # 1.54. Grant Burner REQUEST_BURN_MY_STETH_ROLE to CSM Accounting
                validate_role_grant_event(
                    dg_events[53],
                    REQUEST_BURN_MY_STETH_ROLE,
                    CS_ACCOUNTING,
                    sender=AGENT,
                    emitted_by=BURNER,
                )

                # 1.55. Revoke TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE from the Old CSM Ejector
                validate_role_revoke_event(
                    dg_events[54],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    CONFIG_OLD_CSM_EJECTOR,
                    sender=AGENT,
                    emitted_by=TRIGGERABLE_WITHDRAWALS_GATEWAY,
                )

                # 1.56. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the New CSM Ejector
                validate_role_grant_event(
                    dg_events[55],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    NEW_CSM_EJECTOR,
                    sender=AGENT,
                    emitted_by=TRIGGERABLE_WITHDRAWALS_GATEWAY,
                )

                # -------------------- Curated Module ------------------------
                # 1.57. Add Curated Module v2 to StakingRouter
                validate_module_add(
                    dg_events[56], ctx["curated_module_item"], emitted_by=STAKING_ROUTER, sender=AGENT
                )

                # 1.58. Grant Burner REQUEST_BURN_MY_STETH_ROLE to Curated Accounting
                validate_role_grant_event(
                    dg_events[57],
                    REQUEST_BURN_MY_STETH_ROLE,
                    CURATED_ACCOUNTING,
                    sender=AGENT,
                    emitted_by=BURNER,
                )

                # 1.59. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to Curated Ejector
                validate_role_grant_event(
                    dg_events[58],
                    ADD_FULL_WITHDRAWAL_REQUEST_ROLE,
                    CURATED_EJECTOR,
                    sender=AGENT,
                    emitted_by=TRIGGERABLE_WITHDRAWALS_GATEWAY,
                )

                # 1.60. Grant CM RESUME_ROLE to AGENT
                validate_role_grant_event(
                    dg_events[59],
                    RESUME_ROLE,
                    AGENT,
                    sender=AGENT,
                    emitted_by=CURATED_MODULE,
                )

                # 1.61. Resume Curated Module v2
                validate_events_chain([e.name for e in dg_events[60]], ["LogScriptCall", "Resumed"])
                _assert_emitted_by(_single_event(dg_events[60], "Resumed"), CURATED_MODULE)

                # 1.62. Revoke CM RESUME_ROLE from AGENT
                validate_role_revoke_event(
                    dg_events[61],
                    RESUME_ROLE,
                    AGENT,
                    sender=AGENT,
                    emitted_by=CURATED_MODULE,
                )

                # 1.63. Update Curated HashConsensus initial epoch
                validate_events_chain([e.name for e in dg_events[62]], ["LogScriptCall", "FrameConfigSet"])
                frame_config_set_event = _single_event(dg_events[62], "FrameConfigSet")
                assert frame_config_set_event["newInitialEpoch"] == CURATED_HASH_CONSENSUS_INITIAL_EPOCH
                assert frame_config_set_event["newEpochsPerFrame"] == ctx["curated_epochs_per_frame"]
                _assert_emitted_by(frame_config_set_event, CURATED_HASH_CONSENSUS)

                # 1.64. Register CircuitBreaker pauser for Curated Module v2
                validate_circuit_breaker_registration_event(
                    dg_events[63],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=CURATED_MODULE,
                    pauser=CURATED_CIRCUIT_BREAKER_PAUSER,
                )

                # 1.65. Register CircuitBreaker pauser for Curated Accounting
                validate_circuit_breaker_registration_event(
                    dg_events[64],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=CURATED_ACCOUNTING,
                    pauser=CURATED_CIRCUIT_BREAKER_PAUSER,
                )

                # 1.66. Register CircuitBreaker pauser for Curated FeeOracle
                validate_circuit_breaker_registration_event(
                    dg_events[65],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=CURATED_FEE_ORACLE,
                    pauser=CURATED_CIRCUIT_BREAKER_PAUSER,
                )

                # 1.67. Register CircuitBreaker pauser for Curated Verifier
                validate_circuit_breaker_registration_event(
                    dg_events[66],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=CURATED_VERIFIER,
                    pauser=CURATED_CIRCUIT_BREAKER_PAUSER,
                )

                # 1.68. Register CircuitBreaker pauser for Curated Ejector
                validate_circuit_breaker_registration_event(
                    dg_events[67],
                    circuit_breaker=CIRCUIT_BREAKER,
                    pausable=CURATED_EJECTOR,
                    pauser=CURATED_CIRCUIT_BREAKER_PAUSER,
                )

                # ---------------------- Finish upgrade ----------------------
                # 1.69. Call UpgradeTemplate.finishUpgrade (also migrates the sanity checker baseline snapshot)
                validate_events_chain(
                    [e.name for e in dg_events[68]],
                    ["LogScriptCall", "BaselineSnapshotMigrated", "UpgradeFinished", "ScriptResult", "Executed"],
                )
                _assert_emitted_by(
                    _single_event(dg_events[68], "BaselineSnapshotMigrated"), ORACLE_REPORT_SANITY_CHECKER
                )
                _assert_emitted_by(_single_event(dg_events[68], "UpgradeFinished"), UPGRADE_TEMPLATE)

        # =====================================================================
        # ================= After DG proposal executed checks =================
        # =====================================================================
        assert timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["executed"]

        # Core upgrade landed.
        assert interface.AccountingOracle(ACCOUNTING_ORACLE).getConsensusVersion() == AO_CONSENSUS_VERSION
        assert (
            interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE).getConsensusVersion()
            == VEBO_CONSENSUS_VERSION
        )
        assert (
            interface.WithdrawalVault(WITHDRAWAL_VAULT).getContractVersion() == WITHDRAWAL_VAULT_CONTRACT_VERSION
        )
        assert interface.Lido(LIDO).getContractVersion() == LIDO_CONTRACT_VERSION
        assert interface.FeeOracle(CS_FEE_ORACLE).getConsensusVersion() == CS_FEE_ORACLE_CONSENSUS_VERSION

        # Staking Router role migration & new roles.
        assert staking_router.hasRole(STAKING_MODULE_SHARE_MANAGE_ROLE, EASYTRACK_EVMSCRIPT_EXECUTOR)
        assert staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE)
        assert not staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE)

        # Curated Module v2 registered and resumed.
        assert staking_router.getStakingModulesCount() == ctx["curated_module_item"].id
        curated_module = interface.CSModule(CURATED_MODULE)
        assert curated_module.isPaused() is False

        # Easy Track factory set updated (also checked right after the vote).
        current_factories = easy_track.getEVMScriptFactories()
        for factory in old_easy_track_factories:
            assert factory not in current_factories
        for factory in new_easy_track_factories:
            assert factory in current_factories
