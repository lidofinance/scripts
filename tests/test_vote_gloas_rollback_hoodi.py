import pytest

from brownie import ZERO_ADDRESS, chain, convert, interface, reverts, web3
from brownie.exceptions import VirtualMachineError
from brownie.network.event import EventDict
from brownie.network.transaction import TransactionReceipt

from utils.config import network_name
from utils.tx_tracing import tx_events_from_receipt
from utils.test.tx_tracing_helpers import (
    add_event_emitter,
    count_vote_items_by_events,
    display_dg_events,
    display_voting_events,
    group_dg_events_from_receipt,
    group_voting_events_from_receipt,
)
from utils.evm_script import encode_call_script, encode_error
from utils.dual_governance import PROPOSAL_STATUS, wait_for_time_window
from utils.test.event_validators.circuit_breaker import validate_register_pauser_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.proxy import validate_proxy_upgrade_event
from utils.test.event_validators.time_constraints import validate_dg_time_constraints_executed_within_day_time_event
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import calculate_vote_ipfs_description, get_lido_vote_cid_from_str


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_gloas_rollback_hoodi import (
    IPFS_DESCRIPTION,
    get_dg_items,
    get_vote_items,
    start_vote,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
# Addresses are hardcoded here on purpose, independently from the vote script,
# as a cross-check of the vote script data.
VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"
AGENT = "0x0534aA41907c9631fae990960bCC72d75fA7cfeD"
EMERGENCY_PROTECTED_TIMELOCK = "0x0A5E22782C0Bd4AddF10D771f0bF0406B038282d"
DUAL_GOVERNANCE = "0x9CAaCCc62c66d817CC59c44780D1b722359795bF"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x0eCc17597D292271836691358B22340b78F3035B"
TIME_CONSTRAINTS = "0xB26Fd3b50280AbC55c572EE73071778A51088408"

# Fill these independently from scripts/vote_gloas_rollback_hoodi.py (do not copy-paste from
# the script)
# https://github.com/lidofinance/core/blob/2bd532298d85cdf520169fdc0c5fb0cc9baf03c3/deployed-hoodi.json#L755
PREVIOUS_LIDO_LOCATOR_IMPLEMENTATION = "0x546d76dd8D4BC0c6a26Cb71a39De5d78E222Cbf8"
# https://github.com/lidofinance/core/blob/2bd532298d85cdf520169fdc0c5fb0cc9baf03c3/deployed-hoodi.json#L908
PREVIOUS_PREDEPOSIT_GUARANTEE_IMPLEMENTATION = "0xd1245b75d243A7e0b655479043f9C30b3e8717F5"
# https://github.com/lidofinance/core/blob/2bd532298d85cdf520169fdc0c5fb0cc9baf03c3/deployed-hoodi.json#L1019
PREVIOUS_TOP_UP_GATEWAY_IMPLEMENTATION = "0x8621D8a402fdf2a131E38e16ac50f4C97660Fc2b"
# https://github.com/lidofinance/core/blob/2bd532298d85cdf520169fdc0c5fb0cc9baf03c3/deployed-hoodi.json#L368
PREVIOUS_CONSOLIDATION_BUS_IMPLEMENTATION = "0x2908c4B32548D8799fDc601C1a75E7d5C2FbC556"
# https://github.com/lidofinance/core/blob/2bd532298d85cdf520169fdc0c5fb0cc9baf03c3/deployed-hoodi.json#L1424
PREVIOUS_WITHDRAWAL_VAULT_IMPLEMENTATION = "0x6724DaD16f7b05157dF72783F99cA6B813742330"
# https://github.com/lidofinance/core/blob/2bd532298d85cdf520169fdc0c5fb0cc9baf03c3/deployed-hoodi.json#L1325
PREVIOUS_VALIDATOR_EXIT_DELAY_VERIFIER = "0xa5F5A9360275390fF9728262a29384399f38d2f0"
# https://github.com/lidofinance/core/blob/2bd532298d85cdf520169fdc0c5fb0cc9baf03c3/deployed-hoodi.json#L374
PREVIOUS_CONSOLIDATION_GATEWAY = "0xC9991Bb865d025364BCbBd99f36e85889Fb68e69"
# https://github.com/lidofinance/staking-modules/blob/e225f8693d885bce2418ca1acccb214366c46bc1/artifacts/hoodi/csm/upgrade-v3-hoodi.json#L190
PREVIOUS_CSM_VERIFIER = "0xC96406b0eADdAC5708aFCa04DcCA67BAdC9642Fd"
# https://github.com/lidofinance/staking-modules/blob/e225f8693d885bce2418ca1acccb214366c46bc1/artifacts/hoodi/csm0x02/deploy-hoodi.json#L96
PREVIOUS_CSM0X02_VERIFIER = "0xFdE0FD9aDa4E898D3b34Dd4EA3433b75f0B6dd30"
# https://github.com/lidofinance/staking-modules/blob/e225f8693d885bce2418ca1acccb214366c46bc1/artifacts/hoodi/curated/deploy-hoodi.json#L624
PREVIOUS_CM_V2_VERIFIER = "0x209190Ebc2Be80367a15d05e626784Eb94d6A880"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L753
GLOAS_LIDO_LOCATOR_IMPLEMENTATION = "0x101430e537EFfA1385CC74838EbD43a91D58a722"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L906
GLOAS_PREDEPOSIT_GUARANTEE_IMPLEMENTATION = "0x972A2a03011D629cded15b5b7e70e60b3E17a142"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L1012
GLOAS_TOP_UP_GATEWAY_IMPLEMENTATION = "0x18Ed6Ba7EBaecEd415b71dbB3795362070b227C5"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L368
GLOAS_CONSOLIDATION_BUS_IMPLEMENTATION = "0x95a435Bbae97685d4a9B77d77E23e2a827a717a5"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L1403
GLOAS_WITHDRAWAL_VAULT_IMPLEMENTATION = "0xdfC1E89ceb393C15e2d864F453c7991230367708"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L1312
GLOAS_VALIDATOR_EXIT_DELAY_VERIFIER = "0x34eFB78e7e4241269D6fe96042Eaa0c5715C7Ba4"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L374
GLOAS_CONSOLIDATION_GATEWAY = "0x0718B7DE68ee5A82ebb17a86cF99371881154E51"
# https://github.com/lidofinance/staking-modules/blob/844b05f64370a06e6daceccb156238c8aad5a06b/artifacts/hoodi/csm/upgrade-v3-hoodi.json#L206
GLOAS_CSM_VERIFIER = "0xb70fA371989d7C1FCb88d6Be10A83F286E8e3508"
# https://github.com/lidofinance/staking-modules/blob/844b05f64370a06e6daceccb156238c8aad5a06b/artifacts/hoodi/csm0x02/deploy-hoodi.json#L114
GLOAS_CSM0X02_VERIFIER = "0x3B30b0F9b4dEc685F79192fAa407898B20E5688c"
# https://github.com/lidofinance/staking-modules/blob/844b05f64370a06e6daceccb156238c8aad5a06b/artifacts/hoodi/curated/deploy-hoodi.json#L636
GLOAS_CM_V2_VERIFIER = "0xda4e4a7F600bF6974e4837fBB0Caced8E9C8056D"
# https://github.com/lidofinance/staking-modules/blob/ce72d603f9460438d3c4544b7cc392758be16fdc/artifacts/hoodi/curated/deploy-hoodi.json#L611
CURATED_MODULE_IMPLEMENTATION = "0x0d7cBAf91cc6cbfB72ea70ec09c04855A06ac7Ee"

LIDO_LOCATOR = "0xe2EF9536DAAAEBFf5b1c130957AB3E80056b06D8"
STAKING_ROUTER = "0xCc820558B39ee15C7C45B59390B503b83fb499A8"
CIRCUIT_BREAKER = "0x44a5789dFeDa59cD176Ab5709ec2F4829dE4d555"
CIRCUIT_BREAKER_COMMITTEE = "0x83BCE68B4e8b7071b2a664a26e6D3Bc17eEe3102"
PREDEPOSIT_GUARANTEE = "0xa5F55f3402beA2B14AE15Dae1b6811457D43581d"
TOP_UP_GATEWAY = "0x10DBEb3367876826d00D21718D1d893e0fbD2956"
CONSOLIDATION_BUS = "0xe09fBcE63826468867eE66Eda491E444829E022A"
WITHDRAWAL_VAULT = "0x4473dCDDbf77679A643BdB654dbd86D67F8d32f2"
ORACLE_REPORT_SANITY_CHECKER = "0xD0261b0032A00a7449ee7fbE14d3f98702996441"
ORACLE_DAEMON_CONFIG = "0x2a833402e3F46fFC1ecAb3598c599147a78731a9"
ACCOUNTING_ORACLE = "0xcb883B1bD0a41512b42D2dB267F2A2cd919FB216"
VALIDATORS_EXIT_BUS_ORACLE = "0x8664d394C2B3278F26A1B44B967aEf99707eeAB2"

CSM = "0x79CEf36D84743222f37765204Bec41E92a93E59d"
CSM_FEE_ORACLE = "0xe7314f561B2e72f9543F1004e741bab6Fc51028B"
CSM_COMMITTEE = "0x4AF43Ee34a6fcD1fEcA1e1F832124C763561dA53"
CSM0X02 = "0xbb7dd81FAC80f3Effa10eA8b973c15AE65a4CAf9"
CSM0X02_FEE_ORACLE = "0x9B8bBA11bbE1a351CC8dD1CFCa6719FF7274A208"
CM_V2 = "0x87EB69Ae51317405FD285efD2326a4a11f6173b9"
CM_V2_FEE_ORACLE = "0x5D2F27000C80f6f7A03015Fd49dB7FEba3fBfa83"
CM_COMMITTEE = "0x84DffcfB232594975C608DE92544Ff239a24c9E9"

REPORT_VALIDATOR_EXITING_STATUS_ROLE = web3.keccak(text="REPORT_VALIDATOR_EXITING_STATUS_ROLE").hex()
VERIFIER_ROLE = web3.keccak(text="VERIFIER_ROLE").hex()
REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE = web3.keccak(text="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE").hex()
MANAGE_CONSENSUS_VERSION_ROLE = web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex()
CONFIG_MANAGER_ROLE = web3.keccak(text="CONFIG_MANAGER_ROLE").hex()
ENABLE_TOP_UP_ALLOCATION_ROLE = web3.keccak(text="ENABLE_TOP_UP_ALLOCATION_ROLE").hex()
ALL_LIMITS_MANAGER_ROLE = web3.keccak(text="ALL_LIMITS_MANAGER_ROLE").hex()

# Hoodi values before vote #86 (the Gloas vote), read on chain at block 3860143
ACCOUNTING_ORACLE_CONSENSUS_VERSION = 6
VALIDATORS_EXIT_BUS_ORACLE_CONSENSUS_VERSION = 5
FEE_ORACLE_CONSENSUS_VERSION = 4
GLOAS_ACCOUNTING_ORACLE_CONSENSUS_VERSION = 7
GLOAS_VALIDATORS_EXIT_BUS_ORACLE_CONSENSUS_VERSION = 6
GLOAS_FEE_ORACLE_CONSENSUS_VERSION = 5
MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_KEY = "MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT"
GLOAS_MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT = 500
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/scripts/upgrade/upgrade-params-hoodi.toml#L104
MAX_TOP_UP_PER_BLOCK_GWEI = 3_200 * 10**9
GLOAS_MAX_TOP_UP_PER_BLOCK_GWEI = 20_000 * 10**9
TIME_WINDOW_FROM = 14 * 3600
TIME_WINDOW_TO = 23 * 3600
EXITED_ETH_AMOUNT_PER_DAY_LIMIT = 57_600
CONSOLIDATION_ETH_AMOUNT_PER_DAY_LIMIT = 93_375
MAX_BALANCE_EXIT_REQUESTED_PER_REPORT_IN_ETH = 19_200
GLOAS_EXITED_ETH_AMOUNT_PER_DAY_LIMIT = 411_975
GLOAS_CONSOLIDATION_ETH_AMOUNT_PER_DAY_LIMIT = 205_875
GLOAS_MAX_BALANCE_EXIT_REQUESTED_PER_REPORT_IN_ETH = 11_520
# LimitsList in the ABI order of OracleReportSanityChecker.getOracleReportLimits
ORACLE_REPORT_LIMITS = (
    EXITED_ETH_AMOUNT_PER_DAY_LIMIT,  # exitedEthAmountPerDayLimit
    57_600,  # appearedEthAmountPerDayLimit
    1_000,  # annualBalanceIncreaseBPLimit
    50,  # simulatedShareRateDeviationBPLimit
    MAX_BALANCE_EXIT_REQUESTED_PER_REPORT_IN_ETH,  # maxBalanceExitRequestedPerReportInEth
    32,  # maxEffectiveBalanceWeightWCType01
    2_048,  # maxEffectiveBalanceWeightWCType02
    8,  # maxItemsPerExtraDataTransaction
    24,  # maxNodeOperatorsPerExtraDataItem
    128,  # requestTimestampMargin
    750_000,  # maxPositiveTokenRebase
    360,  # maxCLBalanceDecreaseBP
    50,  # clBalanceOraclesErrorUpperBPLimit
    CONSOLIDATION_ETH_AMOUNT_PER_DAY_LIMIT,  # consolidationEthAmountPerDayLimit
    32,  # exitedValidatorEthAmountLimit
    300,  # externalPendingBalanceCapEth
)
GLOAS_ORACLE_REPORT_LIMITS = (
    GLOAS_EXITED_ETH_AMOUNT_PER_DAY_LIMIT,
    57_600,
    1_000,
    50,
    GLOAS_MAX_BALANCE_EXIT_REQUESTED_PER_REPORT_IN_ETH,
    32,
    2_048,
    8,
    24,
    128,
    750_000,
    360,
    50,
    GLOAS_CONSOLIDATION_ETH_AMOUNT_PER_DAY_LIMIT,
    32,
    300,
)
SECOND_OPINION_ORACLE = ZERO_ADDRESS


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
# TODO set after the vote is started
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 1
# 10 core items + 3 * 6 module Verifier items + 5 * 3 consensus version items
# + 3 OracleDaemonConfig items + 3 OracleReportSanityChecker items
EXPECTED_DG_EVENTS_FROM_AGENT = 49
EXPECTED_DG_EVENTS_COUNT = 2
IPFS_DESCRIPTION_HASH = None
DG_PROPOSAL_METADATA = "Roll back the Gloas (LIP-43) upgrade on Hoodi except the Curated Module v2 implementation: previous verifiers and implementations, oracle consensus versions and sanity limits"


# ============================================================================
# ================================ Helpers ===================================
# ============================================================================
def _event_list(events: EventDict, name: str):
    return [event_item for event_item in events if event_item.name == name]


def _single_event(events: EventDict, name: str):
    items = _event_list(events, name)
    assert len(items) == 1, f"Expected exactly one {name} event, got {len(items)}"
    return items[0]


def _assert_emitted_by(event_item, emitted_by: str) -> None:
    assert convert.to_address(event_item["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}, got {event_item['_emitted_by']}"


def _assert_oz_role_members(contract_address: str, role: str, expected_members) -> None:
    contract = interface.AccessControlEnumerable(contract_address)
    actual_members = [contract.getRoleMember(role, i) for i in range(contract.getRoleMemberCount(role))]
    assert {convert.to_address(member) for member in actual_members} == {
        convert.to_address(member) for member in expected_members
    }


# ============================================================================
# =========================== Event validators ===============================
# ============================================================================
def _group_agent_dg_events_from_receipt(receipt: TransactionReceipt, timelock: str, agent: str, admin_executor: str):
    """Re-group a single-agent-forward DG proposal into one group per forwarded sub-call.

    The default DG grouping yields one group. Here each sub-call is delimited by a LogScriptCall
    emitted by the Agent while it runs the forwarded call script. Events after the Agent's forward
    call is executed by the admin executor (the following DG calls) are not part of any group.
    """
    events = tx_events_from_receipt(receipt)
    assert (
        web3.to_checksum_address(events[-1]["address"]) == web3.to_checksum_address(timelock)
        and events[-1]["name"] == "ProposalExecuted"
    ), "Unexpected Dual Governance service event"

    groups = []
    current_group = None
    for event in events[:-1]:
        is_start_of_new_group = event["name"] == "LogScriptCall" and web3.to_checksum_address(
            event["address"]
        ) == web3.to_checksum_address(agent)
        if is_start_of_new_group:
            current_group = []
            groups.append(current_group)
        if current_group is not None:
            current_group.append(add_event_emitter(event))
            is_end_of_agent_forward = event["name"] == "Executed" and web3.to_checksum_address(
                event["address"]
            ) == web3.to_checksum_address(admin_executor)
            if is_end_of_agent_forward:
                current_group = None

    return [EventDict(group) for group in groups]


def validate_circuit_breaker_unregistration_event(
    event: EventDict, pausable: str, previous_pauser: str, emitted_by: str
) -> None:
    # Unregister always emits PauserSet(pausable, previousPauser, 0). It additionally emits
    # HeartbeatUpdated(previousPauser, 0) iff previousPauser no longer guards any pausable
    # afterwards, so that tail is validated only when present.
    validate_events_chain(
        [e.name for e in event],
        ["LogScriptCall", "LogScriptCall", "PauserSet", "HeartbeatUpdated", "ScriptResult", "Executed"],
    )

    pauser_set_event = _single_event(event, "PauserSet")
    assert convert.to_address(pauser_set_event["pausable"]) == convert.to_address(pausable)
    assert convert.to_address(pauser_set_event["previousPauser"]) == convert.to_address(previous_pauser)
    assert convert.to_address(pauser_set_event["newPauser"]) == convert.to_address(ZERO_ADDRESS)
    _assert_emitted_by(pauser_set_event, emitted_by)

    if event.count("HeartbeatUpdated") > 0:
        heartbeat_updated_event = _single_event(event, "HeartbeatUpdated")
        assert convert.to_address(heartbeat_updated_event["pauser"]) == convert.to_address(previous_pauser)
        assert heartbeat_updated_event["newHeartbeatExpiry"] == 0
        _assert_emitted_by(heartbeat_updated_event, emitted_by)


def validate_consensus_version_set_event(event: EventDict, version: int, prev_version: int, emitted_by: str) -> None:
    validate_events_chain(
        [e.name for e in event], ["LogScriptCall", "LogScriptCall", "ConsensusVersionSet", "ScriptResult", "Executed"]
    )

    consensus_version_set_event = _single_event(event, "ConsensusVersionSet")
    assert consensus_version_set_event["version"] == version, "Wrong consensus version"
    assert consensus_version_set_event["prevVersion"] == prev_version, "Wrong previous consensus version"
    _assert_emitted_by(consensus_version_set_event, emitted_by)


def validate_config_value_unset_event(event: EventDict, key: str, emitted_by: str) -> None:
    validate_events_chain(
        [e.name for e in event], ["LogScriptCall", "LogScriptCall", "ConfigValueUnset", "ScriptResult", "Executed"]
    )

    config_value_unset_event = _single_event(event, "ConfigValueUnset")
    assert config_value_unset_event["key"] == key, "Wrong config key"
    _assert_emitted_by(config_value_unset_event, emitted_by)


def validate_max_top_up_per_block_gwei_set_event(event: EventDict, value: int, set_by: str, emitted_by: str) -> None:
    validate_events_chain(
        [e.name for e in event],
        ["LogScriptCall", "LogScriptCall", "MaxTopUpPerBlockGweiSet", "ScriptResult", "Executed"],
    )

    max_top_up_event = _single_event(event, "MaxTopUpPerBlockGweiSet")
    assert max_top_up_event["maxTopUpPerBlockGwei"] == value, "Wrong max top-up per block"
    assert convert.to_address(max_top_up_event["setBy"]) == convert.to_address(set_by), "Wrong setBy"
    _assert_emitted_by(max_top_up_event, emitted_by)


def validate_oracle_report_limits_event(
    event: EventDict, exited: int, consolidation: int, max_exit: int, emitted_by: str
) -> None:
    # The setter emits an event only for a changed limit, any other limit event or SecondOpinionOracleChanged is wrong
    assert [e.name for e in event] == [
        "LogScriptCall",
        "ExitedEthAmountPerDayLimitSet",
        "ConsolidationEthAmountPerDayLimitSet",
        "MaxBalanceExitRequestedPerReportInEthSet",
    ]

    exited_event = _single_event(event, "ExitedEthAmountPerDayLimitSet")
    assert exited_event["exitedEthAmountPerDayLimit"] == exited, "Wrong exitedEthAmountPerDayLimit"
    _assert_emitted_by(exited_event, emitted_by)

    consolidation_event = _single_event(event, "ConsolidationEthAmountPerDayLimitSet")
    assert consolidation_event["consolidationEthAmountPerDayLimit"] == consolidation, "Wrong consolidation limit"
    _assert_emitted_by(consolidation_event, emitted_by)

    max_exit_event = _single_event(event, "MaxBalanceExitRequestedPerReportInEthSet")
    assert max_exit_event["maxBalanceExitRequestedPerReportInEth"] == max_exit, "Wrong max exit requested limit"
    _assert_emitted_by(max_exit_event, emitted_by)


# ============================================================================
# =============================== Fixtures ===================================
# ============================================================================
@pytest.fixture(scope="module")
def runtime_upgrade_context():
    if network_name() != "hoodi-fork":
        pytest.skip("Run the Gloas rollback vote test on --network hoodi-fork.")


@pytest.fixture(scope="module")
def dual_governance_proposal_calls(runtime_upgrade_context):
    return [{"target": target, "value": 0, "data": data} for target, data in get_dg_items()]


# ============================================================================
# ================================= Test =====================================
# ============================================================================
def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):
    # =========================================================================
    # ========================== Arrange variables ============================
    # =========================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)
    locator = interface.LidoLocator(LIDO_LOCATOR)
    sanity_checker = interface.OracleReportSanityChecker(ORACLE_REPORT_SANITY_CHECKER)
    oracle_daemon_config = interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)
    cm_v2_proxy = interface.OssifiableProxy(CM_V2)

    expected_ipfs_description_hash = IPFS_DESCRIPTION_HASH or calculate_vote_ipfs_description(IPFS_DESCRIPTION)["cid"]

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
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
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
        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == expected_ipfs_description_hash

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        if expected_dg_proposal_id is None:
            expected_dg_proposal_id = dg_proposals_count_before_vote_execution + 1

        assert expected_dg_proposal_id == timelock.getProposalsCount()

        # 1. Submit the partial Gloas rollback to Dual Governance
        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=expected_dg_proposal_id,
            proposer=VOTING,
            executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            metadata=DG_PROPOSAL_METADATA,
            proposal_calls=dual_governance_proposal_calls,
        )

    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if expected_dg_proposal_id is None:
        expected_dg_proposal_id = timelock.getProposalsCount()

    details = timelock.getProposalDetails(expected_dg_proposal_id)
    if details["status"] != PROPOSAL_STATUS["executed"]:
        # =======================================================================
        # ================= DG before proposal executed checks ==================
        # =======================================================================
        assert convert.to_address(interface.OssifiableProxy(LIDO_LOCATOR).proxy__getImplementation()) == (
            convert.to_address(GLOAS_LIDO_LOCATOR_IMPLEMENTATION)
        )
        assert convert.to_address(
            interface.OssifiableProxy(PREDEPOSIT_GUARANTEE).proxy__getImplementation()
        ) == convert.to_address(GLOAS_PREDEPOSIT_GUARANTEE_IMPLEMENTATION)
        assert convert.to_address(
            interface.OssifiableProxy(TOP_UP_GATEWAY).proxy__getImplementation()
        ) == convert.to_address(GLOAS_TOP_UP_GATEWAY_IMPLEMENTATION)
        assert convert.to_address(
            interface.OssifiableProxy(CONSOLIDATION_BUS).proxy__getImplementation()
        ) == convert.to_address(GLOAS_CONSOLIDATION_BUS_IMPLEMENTATION)
        assert convert.to_address(
            interface.WithdrawalsManagerProxy(WITHDRAWAL_VAULT).implementation()
        ) == convert.to_address(GLOAS_WITHDRAWAL_VAULT_IMPLEMENTATION)
        assert convert.to_address(locator.validatorExitDelayVerifier()) == convert.to_address(
            GLOAS_VALIDATOR_EXIT_DELAY_VERIFIER
        )
        assert convert.to_address(locator.consolidationGateway()) == convert.to_address(GLOAS_CONSOLIDATION_GATEWAY)

        assert staking_router.hasRole(REPORT_VALIDATOR_EXITING_STATUS_ROLE, GLOAS_VALIDATOR_EXIT_DELAY_VERIFIER)
        assert not staking_router.hasRole(REPORT_VALIDATOR_EXITING_STATUS_ROLE, PREVIOUS_VALIDATOR_EXIT_DELAY_VERIFIER)
        assert staking_router.getMaxTopUpPerBlockGwei() == GLOAS_MAX_TOP_UP_PER_BLOCK_GWEI

        assert convert.to_address(circuit_breaker.getPauser(GLOAS_CONSOLIDATION_GATEWAY)) == convert.to_address(
            CIRCUIT_BREAKER_COMMITTEE
        )
        assert circuit_breaker.getPauser(PREVIOUS_CONSOLIDATION_GATEWAY) == ZERO_ADDRESS

        for module, previous_verifier, gloas_verifier, committee in [
            (CSM, PREVIOUS_CSM_VERIFIER, GLOAS_CSM_VERIFIER, CSM_COMMITTEE),
            (CSM0X02, PREVIOUS_CSM0X02_VERIFIER, GLOAS_CSM0X02_VERIFIER, CSM_COMMITTEE),
            (CM_V2, PREVIOUS_CM_V2_VERIFIER, GLOAS_CM_V2_VERIFIER, CM_COMMITTEE),
        ]:
            module_contract = interface.AccessControl(module)
            assert module_contract.hasRole(VERIFIER_ROLE, gloas_verifier)
            assert module_contract.hasRole(REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, gloas_verifier)
            assert not module_contract.hasRole(VERIFIER_ROLE, previous_verifier)
            assert not module_contract.hasRole(REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, previous_verifier)
            assert convert.to_address(circuit_breaker.getPauser(gloas_verifier)) == convert.to_address(committee)
            assert circuit_breaker.getPauser(previous_verifier) == ZERO_ADDRESS

        assert (
            interface.BaseOracle(ACCOUNTING_ORACLE).getConsensusVersion() == GLOAS_ACCOUNTING_ORACLE_CONSENSUS_VERSION
        )
        assert (
            interface.BaseOracle(VALIDATORS_EXIT_BUS_ORACLE).getConsensusVersion()
            == GLOAS_VALIDATORS_EXIT_BUS_ORACLE_CONSENSUS_VERSION
        )
        assert interface.BaseOracle(CSM_FEE_ORACLE).getConsensusVersion() == GLOAS_FEE_ORACLE_CONSENSUS_VERSION
        assert interface.BaseOracle(CSM0X02_FEE_ORACLE).getConsensusVersion() == GLOAS_FEE_ORACLE_CONSENSUS_VERSION
        assert interface.BaseOracle(CM_V2_FEE_ORACLE).getConsensusVersion() == GLOAS_FEE_ORACLE_CONSENSUS_VERSION

        assert convert.to_uint(oracle_daemon_config.get(MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_KEY)) == (
            GLOAS_MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT
        )

        assert tuple(sanity_checker.getOracleReportLimits()) == GLOAS_ORACLE_REPORT_LIMITS
        assert sanity_checker.secondOpinionOracle() == SECOND_OPINION_ORACLE

        assert convert.to_address(cm_v2_proxy.proxy__getImplementation()) == convert.to_address(
            CURATED_MODULE_IMPLEMENTATION
        )
        _assert_oz_role_members(CM_V2, ENABLE_TOP_UP_ALLOCATION_ROLE, [CM_COMMITTEE])

        if details["status"] == PROPOSAL_STATUS["submitted"]:
            chain.sleep(timelock.getAfterSubmitDelay() + 1)
            dual_governance.scheduleProposal(expected_dg_proposal_id, {"from": stranger})

        if timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["scheduled"]:
            chain.sleep(timelock.getAfterScheduleDelay() + 1)
            # The DG proposal reverts outside the 14:00 - 23:00 UTC window set by the last DG call
            wait_for_time_window(14, 23)

            dg_tx: TransactionReceipt = timelock.execute(expected_dg_proposal_id, {"from": stranger})
            display_dg_events(dg_tx)

            outer_dg_events = group_dg_events_from_receipt(
                dg_tx,
                timelock=EMERGENCY_PROTECTED_TIMELOCK,
                admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            )
            # Regroup by the Agent's sub-calls to validate each sub-calls events
            agent_dg_events = _group_agent_dg_events_from_receipt(
                dg_tx,
                timelock=EMERGENCY_PROTECTED_TIMELOCK,
                agent=AGENT,
                admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            )

            assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
            assert len(outer_dg_events) == EXPECTED_DG_EVENTS_COUNT
            assert len(agent_dg_events) == EXPECTED_DG_EVENTS_FROM_AGENT

            # =======================================================================
            # ============================ DG events checks =========================
            # =======================================================================
            # 1.1-1.5. Roll back the proxy implementations
            validate_proxy_upgrade_event(agent_dg_events[0], PREVIOUS_LIDO_LOCATOR_IMPLEMENTATION, LIDO_LOCATOR)
            validate_proxy_upgrade_event(
                agent_dg_events[1], PREVIOUS_PREDEPOSIT_GUARANTEE_IMPLEMENTATION, PREDEPOSIT_GUARANTEE
            )
            validate_proxy_upgrade_event(agent_dg_events[2], PREVIOUS_TOP_UP_GATEWAY_IMPLEMENTATION, TOP_UP_GATEWAY)
            validate_proxy_upgrade_event(
                agent_dg_events[3], PREVIOUS_CONSOLIDATION_BUS_IMPLEMENTATION, CONSOLIDATION_BUS
            )
            validate_proxy_upgrade_event(agent_dg_events[4], PREVIOUS_WITHDRAWAL_VAULT_IMPLEMENTATION, WITHDRAWAL_VAULT)

            # 1.6-1.7. Move REPORT_VALIDATOR_EXITING_STATUS_ROLE back to the previous ValidatorExitDelayVerifier
            validate_grant_role_event(
                agent_dg_events[5],
                REPORT_VALIDATOR_EXITING_STATUS_ROLE,
                PREVIOUS_VALIDATOR_EXIT_DELAY_VERIFIER,
                AGENT,
                STAKING_ROUTER,
            )
            validate_revoke_role_event(
                agent_dg_events[6],
                REPORT_VALIDATOR_EXITING_STATUS_ROLE,
                GLOAS_VALIDATOR_EXIT_DELAY_VERIFIER,
                AGENT,
                STAKING_ROUTER,
            )

            # 1.8. Set the max top-up per block on StakingRouter
            validate_max_top_up_per_block_gwei_set_event(
                agent_dg_events[7], MAX_TOP_UP_PER_BLOCK_GWEI, AGENT, STAKING_ROUTER
            )

            # 1.9-1.10. Previous ConsolidationGateway CircuitBreaker registration
            validate_register_pauser_event(
                agent_dg_events[8], PREVIOUS_CONSOLIDATION_GATEWAY, CIRCUIT_BREAKER_COMMITTEE, CIRCUIT_BREAKER
            )
            validate_circuit_breaker_unregistration_event(
                agent_dg_events[9], GLOAS_CONSOLIDATION_GATEWAY, CIRCUIT_BREAKER_COMMITTEE, CIRCUIT_BREAKER
            )

            # 1.11-1.16. CSM Verifier
            validate_grant_role_event(agent_dg_events[10], VERIFIER_ROLE, PREVIOUS_CSM_VERIFIER, AGENT, CSM)
            validate_grant_role_event(
                agent_dg_events[11], REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, PREVIOUS_CSM_VERIFIER, AGENT, CSM
            )
            validate_register_pauser_event(agent_dg_events[12], PREVIOUS_CSM_VERIFIER, CSM_COMMITTEE, CIRCUIT_BREAKER)
            validate_revoke_role_event(agent_dg_events[13], VERIFIER_ROLE, GLOAS_CSM_VERIFIER, AGENT, CSM)
            validate_revoke_role_event(
                agent_dg_events[14], REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, GLOAS_CSM_VERIFIER, AGENT, CSM
            )
            validate_circuit_breaker_unregistration_event(
                agent_dg_events[15], GLOAS_CSM_VERIFIER, CSM_COMMITTEE, CIRCUIT_BREAKER
            )

            # 1.17-1.22. CSM 0x02 Verifier
            validate_grant_role_event(agent_dg_events[16], VERIFIER_ROLE, PREVIOUS_CSM0X02_VERIFIER, AGENT, CSM0X02)
            validate_grant_role_event(
                agent_dg_events[17], REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, PREVIOUS_CSM0X02_VERIFIER, AGENT, CSM0X02
            )
            validate_register_pauser_event(
                agent_dg_events[18], PREVIOUS_CSM0X02_VERIFIER, CSM_COMMITTEE, CIRCUIT_BREAKER
            )
            validate_revoke_role_event(agent_dg_events[19], VERIFIER_ROLE, GLOAS_CSM0X02_VERIFIER, AGENT, CSM0X02)
            validate_revoke_role_event(
                agent_dg_events[20], REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, GLOAS_CSM0X02_VERIFIER, AGENT, CSM0X02
            )
            validate_circuit_breaker_unregistration_event(
                agent_dg_events[21], GLOAS_CSM0X02_VERIFIER, CSM_COMMITTEE, CIRCUIT_BREAKER
            )

            # 1.23-1.28. Curated Module v2 Verifier
            validate_grant_role_event(agent_dg_events[22], VERIFIER_ROLE, PREVIOUS_CM_V2_VERIFIER, AGENT, CM_V2)
            validate_grant_role_event(
                agent_dg_events[23], REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, PREVIOUS_CM_V2_VERIFIER, AGENT, CM_V2
            )
            validate_register_pauser_event(agent_dg_events[24], PREVIOUS_CM_V2_VERIFIER, CM_COMMITTEE, CIRCUIT_BREAKER)
            validate_revoke_role_event(agent_dg_events[25], VERIFIER_ROLE, GLOAS_CM_V2_VERIFIER, AGENT, CM_V2)
            validate_revoke_role_event(
                agent_dg_events[26], REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, GLOAS_CM_V2_VERIFIER, AGENT, CM_V2
            )
            validate_circuit_breaker_unregistration_event(
                agent_dg_events[27], GLOAS_CM_V2_VERIFIER, CM_COMMITTEE, CIRCUIT_BREAKER
            )

            # 1.29-1.31. OracleDaemonConfig MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT
            validate_grant_role_event(agent_dg_events[28], CONFIG_MANAGER_ROLE, AGENT, AGENT, ORACLE_DAEMON_CONFIG)
            validate_config_value_unset_event(
                agent_dg_events[29], MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_KEY, ORACLE_DAEMON_CONFIG
            )
            validate_revoke_role_event(agent_dg_events[30], CONFIG_MANAGER_ROLE, AGENT, AGENT, ORACLE_DAEMON_CONFIG)

            # 1.32-1.34. OracleReportSanityChecker limits
            validate_grant_role_event(
                agent_dg_events[31], ALL_LIMITS_MANAGER_ROLE, AGENT, AGENT, ORACLE_REPORT_SANITY_CHECKER
            )
            validate_oracle_report_limits_event(
                agent_dg_events[32],
                EXITED_ETH_AMOUNT_PER_DAY_LIMIT,
                CONSOLIDATION_ETH_AMOUNT_PER_DAY_LIMIT,
                MAX_BALANCE_EXIT_REQUESTED_PER_REPORT_IN_ETH,
                ORACLE_REPORT_SANITY_CHECKER,
            )
            validate_revoke_role_event(
                agent_dg_events[33], ALL_LIMITS_MANAGER_ROLE, AGENT, AGENT, ORACLE_REPORT_SANITY_CHECKER
            )

            # 1.35-1.37. AccountingOracle consensus version
            validate_grant_role_event(
                agent_dg_events[34], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, ACCOUNTING_ORACLE
            )
            validate_consensus_version_set_event(
                agent_dg_events[35],
                ACCOUNTING_ORACLE_CONSENSUS_VERSION,
                GLOAS_ACCOUNTING_ORACLE_CONSENSUS_VERSION,
                ACCOUNTING_ORACLE,
            )
            validate_revoke_role_event(
                agent_dg_events[36], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, ACCOUNTING_ORACLE
            )

            # 1.38-1.40. ValidatorsExitBusOracle consensus version
            validate_grant_role_event(
                agent_dg_events[37], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, VALIDATORS_EXIT_BUS_ORACLE
            )
            validate_consensus_version_set_event(
                agent_dg_events[38],
                VALIDATORS_EXIT_BUS_ORACLE_CONSENSUS_VERSION,
                GLOAS_VALIDATORS_EXIT_BUS_ORACLE_CONSENSUS_VERSION,
                VALIDATORS_EXIT_BUS_ORACLE,
            )
            validate_revoke_role_event(
                agent_dg_events[39], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, VALIDATORS_EXIT_BUS_ORACLE
            )

            # 1.41-1.43. CSM FeeOracle consensus version
            validate_grant_role_event(agent_dg_events[40], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, CSM_FEE_ORACLE)
            validate_consensus_version_set_event(
                agent_dg_events[41], FEE_ORACLE_CONSENSUS_VERSION, GLOAS_FEE_ORACLE_CONSENSUS_VERSION, CSM_FEE_ORACLE
            )
            validate_revoke_role_event(agent_dg_events[42], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, CSM_FEE_ORACLE)

            # 1.44-1.46. CSM 0x02 FeeOracle consensus version
            validate_grant_role_event(
                agent_dg_events[43], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, CSM0X02_FEE_ORACLE
            )
            validate_consensus_version_set_event(
                agent_dg_events[44],
                FEE_ORACLE_CONSENSUS_VERSION,
                GLOAS_FEE_ORACLE_CONSENSUS_VERSION,
                CSM0X02_FEE_ORACLE,
            )
            validate_revoke_role_event(
                agent_dg_events[45], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, CSM0X02_FEE_ORACLE
            )

            # 1.47-1.49. Curated Module v2 FeeOracle consensus version
            validate_grant_role_event(
                agent_dg_events[46], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, CM_V2_FEE_ORACLE
            )
            validate_consensus_version_set_event(
                agent_dg_events[47], FEE_ORACLE_CONSENSUS_VERSION, GLOAS_FEE_ORACLE_CONSENSUS_VERSION, CM_V2_FEE_ORACLE
            )
            validate_revoke_role_event(
                agent_dg_events[48], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, CM_V2_FEE_ORACLE
            )

            # 1.50. Time window constraint for Dual Governance Proposal execution
            validate_dg_time_constraints_executed_within_day_time_event(
                outer_dg_events[1],
                TIME_WINDOW_FROM,
                TIME_WINDOW_TO,
                emitted_by=TIME_CONSTRAINTS,
            )

    # =========================================================================
    # ==================== After DG proposal executed checks ==================
    # =========================================================================
    assert timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["executed"]

    # Proxies point to the previous implementations and the locator to the previous contracts
    assert convert.to_address(interface.OssifiableProxy(LIDO_LOCATOR).proxy__getImplementation()) == convert.to_address(
        PREVIOUS_LIDO_LOCATOR_IMPLEMENTATION
    )
    assert convert.to_address(
        interface.OssifiableProxy(PREDEPOSIT_GUARANTEE).proxy__getImplementation()
    ) == convert.to_address(PREVIOUS_PREDEPOSIT_GUARANTEE_IMPLEMENTATION)
    assert convert.to_address(
        interface.OssifiableProxy(TOP_UP_GATEWAY).proxy__getImplementation()
    ) == convert.to_address(PREVIOUS_TOP_UP_GATEWAY_IMPLEMENTATION)
    assert convert.to_address(
        interface.OssifiableProxy(CONSOLIDATION_BUS).proxy__getImplementation()
    ) == convert.to_address(PREVIOUS_CONSOLIDATION_BUS_IMPLEMENTATION)
    assert convert.to_address(
        interface.WithdrawalsManagerProxy(WITHDRAWAL_VAULT).implementation()
    ) == convert.to_address(PREVIOUS_WITHDRAWAL_VAULT_IMPLEMENTATION)
    assert convert.to_address(locator.validatorExitDelayVerifier()) == convert.to_address(
        PREVIOUS_VALIDATOR_EXIT_DELAY_VERIFIER
    )
    assert convert.to_address(locator.consolidationGateway()) == convert.to_address(PREVIOUS_CONSOLIDATION_GATEWAY)

    # The Curated Module v2 implementation and its top-up allocation role stay as upgraded by the Gloas vote
    assert convert.to_address(cm_v2_proxy.proxy__getImplementation()) == convert.to_address(
        CURATED_MODULE_IMPLEMENTATION
    )
    _assert_oz_role_members(CM_V2, ENABLE_TOP_UP_ALLOCATION_ROLE, [CM_COMMITTEE])

    # StakingRouter exit-delay reporting role and top-up limit
    assert staking_router.hasRole(REPORT_VALIDATOR_EXITING_STATUS_ROLE, PREVIOUS_VALIDATOR_EXIT_DELAY_VERIFIER)
    assert not staking_router.hasRole(REPORT_VALIDATOR_EXITING_STATUS_ROLE, GLOAS_VALIDATOR_EXIT_DELAY_VERIFIER)
    assert staking_router.getRoleMemberCount(REPORT_VALIDATOR_EXITING_STATUS_ROLE) == 1
    assert staking_router.getMaxTopUpPerBlockGwei() == MAX_TOP_UP_PER_BLOCK_GWEI

    # CircuitBreaker registration of the ConsolidationGateway
    assert convert.to_address(circuit_breaker.getPauser(PREVIOUS_CONSOLIDATION_GATEWAY)) == convert.to_address(
        CIRCUIT_BREAKER_COMMITTEE
    )
    assert circuit_breaker.getPauser(GLOAS_CONSOLIDATION_GATEWAY) == ZERO_ADDRESS

    # Module Verifiers
    for module, previous_verifier, gloas_verifier, committee in [
        (CSM, PREVIOUS_CSM_VERIFIER, GLOAS_CSM_VERIFIER, CSM_COMMITTEE),
        (CSM0X02, PREVIOUS_CSM0X02_VERIFIER, GLOAS_CSM0X02_VERIFIER, CSM_COMMITTEE),
        (CM_V2, PREVIOUS_CM_V2_VERIFIER, GLOAS_CM_V2_VERIFIER, CM_COMMITTEE),
    ]:
        module_contract = interface.AccessControl(module)

        assert module_contract.hasRole(VERIFIER_ROLE, previous_verifier)
        assert module_contract.hasRole(REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, previous_verifier)
        assert not module_contract.hasRole(VERIFIER_ROLE, gloas_verifier)
        assert not module_contract.hasRole(REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, gloas_verifier)
        _assert_oz_role_members(module, VERIFIER_ROLE, [previous_verifier])
        _assert_oz_role_members(module, REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE, [previous_verifier])

        assert convert.to_address(circuit_breaker.getPauser(previous_verifier)) == convert.to_address(committee)
        assert circuit_breaker.getPauser(gloas_verifier) == ZERO_ADDRESS

    # Oracles, OracleDaemonConfig and OracleReportSanityChecker
    assert interface.BaseOracle(ACCOUNTING_ORACLE).getConsensusVersion() == ACCOUNTING_ORACLE_CONSENSUS_VERSION
    assert (
        interface.BaseOracle(VALIDATORS_EXIT_BUS_ORACLE).getConsensusVersion()
        == VALIDATORS_EXIT_BUS_ORACLE_CONSENSUS_VERSION
    )
    assert interface.BaseOracle(CSM_FEE_ORACLE).getConsensusVersion() == FEE_ORACLE_CONSENSUS_VERSION
    assert interface.BaseOracle(CSM0X02_FEE_ORACLE).getConsensusVersion() == FEE_ORACLE_CONSENSUS_VERSION
    assert interface.BaseOracle(CM_V2_FEE_ORACLE).getConsensusVersion() == FEE_ORACLE_CONSENSUS_VERSION

    with pytest.raises(
        VirtualMachineError, match=rf'ValueDoesntExist\("{MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_KEY}"\)'
    ):
        oracle_daemon_config.get.call(MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_KEY)

    assert tuple(sanity_checker.getOracleReportLimits()) == ORACLE_REPORT_LIMITS
    assert sanity_checker.secondOpinionOracle() == SECOND_OPINION_ORACLE

    # The Agent keeps none of the temporary roles
    for contract, role in [
        (ACCOUNTING_ORACLE, MANAGE_CONSENSUS_VERSION_ROLE),
        (VALIDATORS_EXIT_BUS_ORACLE, MANAGE_CONSENSUS_VERSION_ROLE),
        (CSM_FEE_ORACLE, MANAGE_CONSENSUS_VERSION_ROLE),
        (CSM0X02_FEE_ORACLE, MANAGE_CONSENSUS_VERSION_ROLE),
        (CM_V2_FEE_ORACLE, MANAGE_CONSENSUS_VERSION_ROLE),
        (ORACLE_DAEMON_CONFIG, CONFIG_MANAGER_ROLE),
        (ORACLE_REPORT_SANITY_CHECKER, ALL_LIMITS_MANAGER_ROLE),
    ]:
        assert not interface.AccessControl(contract).hasRole(role, AGENT), f"Agent keeps {role} on {contract}"

    # Scenario: the CircuitBreaker committees pause the previous ConsolidationGateway and Verifiers, the Gloas ones are out
    for pausable_name, previous_pausable, gloas_pausable, committee in [
        (
            "ConsolidationGateway",
            PREVIOUS_CONSOLIDATION_GATEWAY,
            GLOAS_CONSOLIDATION_GATEWAY,
            CIRCUIT_BREAKER_COMMITTEE,
        ),
        ("CSM Verifier", PREVIOUS_CSM_VERIFIER, GLOAS_CSM_VERIFIER, CSM_COMMITTEE),
        ("CSM 0x02 Verifier", PREVIOUS_CSM0X02_VERIFIER, GLOAS_CSM0X02_VERIFIER, CSM_COMMITTEE),
        ("CM v2 Verifier", PREVIOUS_CM_V2_VERIFIER, GLOAS_CM_V2_VERIFIER, CM_COMMITTEE),
    ]:
        committee_account = accounts.at(committee, force=True)

        # .call() — a reverted transaction does not always surface custom-error data
        with reverts(encode_error("SenderNotPauser()")):
            circuit_breaker.pause.call(gloas_pausable, {"from": committee_account})

        chain.snapshot()
        try:
            assert not interface.IPausable(previous_pausable).isPaused(), f"Previous {pausable_name} is paused"
            circuit_breaker.pause(previous_pausable, {"from": committee_account})
            assert interface.IPausable(
                previous_pausable
            ).isPaused(), f"Previous {pausable_name} is not paused by CircuitBreaker"
            assert not interface.IPausable(gloas_pausable).isPaused(), f"Gloas {pausable_name} is paused"
        finally:
            chain.revert()
