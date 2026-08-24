import pytest

from typing import NamedTuple

from brownie import chain, convert, interface, web3
from brownie.network.event import EventDict
from brownie.network.transaction import TransactionReceipt

from utils.config import network_name
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
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import calculate_vote_ipfs_description, get_lido_vote_cid_from_str


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
import scripts.vote_edf_hoodi as vote_script
from scripts.vote_edf_hoodi import (
    DG_PROPOSAL_METADATA,
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

# Fill these independently from scripts/vote_edf_hoodi.py (do not copy-paste from
# the script) - the fixture cross-checks both copies against each other
NEW_DEPOSIT_SECURITY_MODULE = "0x8E63F0aF403ffd3Cbd5dB18b4ee632314ab49B51"  # DSM v5
NEW_LIDO_LOCATOR_IMPLEMENTATION = "0x546d76dd8D4BC0c6a26Cb71a39De5d78E222Cbf8"

LIDO_LOCATOR = "0xe2EF9536DAAAEBFf5b1c130957AB3E80056b06D8"
STAKING_ROUTER = "0xCc820558B39ee15C7C45B59390B503b83fb499A8"
OLD_DEPOSIT_SECURITY_MODULE = "0xf738F86009Ec704880c9Aa175fc5869F020FEe4e"
TOP_UP_GATEWAY = "0x10DBEb3367876826d00D21718D1d893e0fbD2956"
DEPOSITOR_BOT_OLD_EOA = "0x9b186cE78Ddd6fF098b4a533Dd17a139e1FFeD76"
DEPOSITOR_BOT_DELEGATION_CONTRACT = "0x25636798f6E716b2e6b7dEA8ED52a45271768D7A"

STAKING_MODULE_UNVETTING_ROLE = web3.keccak(text="STAKING_MODULE_UNVETTING_ROLE").hex()
TOP_UP_ROLE = web3.keccak(text="TOP_UP_ROLE").hex()

ORACLE_COMMITTEE_QUORUM = 6
NEW_DSM_VERSION = 5
NEW_DSM_GUARDIAN_QUORUM = 2


class OracleCommittee(NamedTuple):
    name: str
    consensus_contract: str


class OracleMemberMapping(NamedTuple):
    name: str
    old_member: str
    delegation_contract: str


ORACLE_COMMITTEES = [
    OracleCommittee("HashConsensus for AccountingOracle",         "0x32EC59a78abaca3f91527aeB2008925D5AaC1eFC"),
    OracleCommittee("HashConsensus for ValidatorsExitBusOracle",  "0x30308CD8844fb2DB3ec4D056F1d475a802DCA07c"),
    OracleCommittee("CSHashConsensus for CSFeeOracle",            "0x54f74a10e4397dDeF85C4854d9dfcA129D72C637"),
    OracleCommittee("HashConsensus for Curated Module FeeOracle", "0x920883908A78c1554f682006a8aB32E62Be09F33"),
]

ORACLE_MEMBER_MAPPINGS = [
    OracleMemberMapping("Instadapp",          "0x43C45C2455C49eed320F463fF4f1Ece3D2BF5aE2", "0xe768fF17be4799D64649E9B8a58ee66Eb628FA93"),
    OracleMemberMapping("Caliber",            "0x948A62cc0414979dc7aa9364BA5b96ECb29f8736", "0x9F81976E461B82cfe3CAec06De8eFA8aD5543408"),
    OracleMemberMapping("Chorus One",         "0x1932f53B1457a5987791a40Ba91f71c5Efd5788F", "0x9950477b8D8154ef44745612832464C3c2155F79"),
    OracleMemberMapping("Chainlayer",         "0xf7aE520e99ed3C41180B5E12681d31Aa7302E4e5", "0xC51fE2B136a24D6eC8368C858Ae5211dc2FE0e0B"),
    OracleMemberMapping("P2P",                "0x99B2B75F490fFC9A29E4E1f5987BE8e30E690aDF", "0x43c97fEfeF1e41D6429814e2a3Ad37aA096d633e"),
    OracleMemberMapping("Staking Facilities", "0x219743f1911d84B32599BdC2Df21fC8Dba6F81a2", "0xc19a08e427351F51DA7A82136aF66d8F01931738"),
    OracleMemberMapping("Stakefish",          "0xD3b1e36A372Ca250eefF61f90E833Ca070559970", "0x9d7bFAa500b5DeC4FBab2257dfbC0cB3D5c1Fbc8"),
    OracleMemberMapping("bloXroute",          "0x4c75FA734a39f3a21C57e583c1c29942F021C6B7", "0x443e31892Ffd51f6f0Fef6DAE4ac2e2795f311Bf"),
    OracleMemberMapping("MatrixedLink",       "0xfe43A8B0b481Ae9fB1862d31826532047d2d538c", "0x89E9FCB24CC82e9A449A69f3932C70ca2FA07E1D"),
    OracleMemberMapping("Lido",               "0xcA80ee7313A315879f326105134F938676Cfd7a9", "0xAFca4694c06720Ad03037db3760a920320037217"),
]

# Guardians of the old DSM v4 (EOA hot keys); the second Lido dev team address is
# dropped by the upgrade, Kiln is remapped to the Stakely DelegationContract
OLD_DSM_GUARDIANS = [
    "0x89C102120452AfdFb63f2D4231C5CE3e939f393b",  # P2P
    "0xcc1fFeb60ee3A3Cb6711E5D191339b0aF263328C",  # Stake.fish
    "0x4E93C8c7B06F1CEEb03A8e13B0371b35F93d3257",  # Lido dev team
    "0x2aD1cBE1109376aD6f9D714c29c9A7FF452300FE",  # Lido dev team (extra, removed by the upgrade)
    "0xEf302FFC6830FbC464cDFFA84Fa4d5699aA8f06A",  # Blockscape
    "0x8C4C15870d27c1194B6893F6B94DD0CE9C2c8ba2",  # Kiln (replaced by Stakely)
    "0x1be2A219CBD0F18B825a4dDd580F7b3B33Bacb41",  # Staking Facilities
]

# Guardians of the new DSM v5 (EDF DelegationContracts)
NEW_DSM_GUARDIANS = [
    "0x56a1B0b5074818D568D6608dc07353e81b4b53ec",  # Lido dev team
    "0x89e1bEBAf6857312bCDc313B93F29aB9cA98000f",  # P2P
    "0x901789EA029B3c7CEa47019d6Df3C5973212976D",  # Staking Facilities
    "0xa66FDd65Cfc78964A62b5Ec50E5b0Afd0e52D610",  # Blockscape
    "0x4EEC6BEd8d5E45f0a6a99F067bC5F6370f2f7221",  # Stake.fish
    "0x03224cFc446F3166c83E875095e872DD1E098076",  # Stakely (replaces Kiln)
]


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 1
# 4 committees * 10 members * 2 (remove + add) + locator upgrade
# + unvetting role revoke + grant + top-up role revoke + grant
EXPECTED_DG_EVENTS_COUNT = 85
IPFS_DESCRIPTION_HASH = None


def _is_placeholder_address(value: str) -> bool:
    normalized = str(value).strip().lower()
    return normalized in ("", "0x0000000000000000000000000000000000000000") or normalized.startswith("todo")


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


def _raw_event_values(raw_event: dict) -> dict:
    return {item["name"]: item["value"] for item in raw_event["data"]}


def _locator_addresses(locator) -> dict:
    """Snapshot every zero-arg address getter the current locator implementation responds to."""
    addresses = {}
    for entry in locator.abi:
        if entry.get("type") != "function" or entry.get("inputs") or entry.get("stateMutability") != "view":
            continue
        outputs = entry.get("outputs") or []
        if len(outputs) != 1 or outputs[0].get("type") != "address":
            continue
        try:
            addresses[entry["name"]] = str(getattr(locator, entry["name"])())
        except Exception:
            continue
    return addresses


def _group_agent_dg_events_from_receipt(receipt: TransactionReceipt, timelock: str, agent: str) -> list[EventDict]:
    """Group DG proposal events by the Agent's inner call script items (single Agent.forward)."""
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


# ============================================================================
# =========================== Event validators ===============================
# ============================================================================
def validate_member_removed_event(
    event: EventDict, member: str, new_total_members: int, new_quorum: int, emitted_by: str
) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "MemberRemoved"])

    member_removed_event = _single_event(event, "MemberRemoved")
    assert convert.to_address(member_removed_event["addr"]) == convert.to_address(member), "Wrong removed member"
    assert member_removed_event["newTotalMembers"] == new_total_members, "Wrong new total members count"
    assert member_removed_event["newQuorum"] == new_quorum, "Wrong new quorum"
    _assert_emitted_by(member_removed_event, emitted_by)


def validate_member_added_event(
    event: EventDict, member: str, new_total_members: int, new_quorum: int, emitted_by: str
) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "MemberAdded"])

    member_added_event = _single_event(event, "MemberAdded")
    assert convert.to_address(member_added_event["addr"]) == convert.to_address(member), "Wrong added member"
    assert member_added_event["newTotalMembers"] == new_total_members, "Wrong new total members count"
    assert member_added_event["newQuorum"] == new_quorum, "Wrong new quorum"
    _assert_emitted_by(member_added_event, emitted_by)


def validate_proxy_upgrade_event(event: EventDict, implementation: str, emitted_by: str) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "Upgraded"])

    upgraded_event = _single_event(event, "Upgraded")
    assert convert.to_address(upgraded_event["implementation"]) == convert.to_address(
        implementation
    ), "Wrong implementation address"
    _assert_emitted_by(upgraded_event, emitted_by)


def validate_role_revoke_event(event: EventDict, role_hash: str, account: str, sender: str, emitted_by: str) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "RoleRevoked"])

    role_revoked_event = _single_event(event, "RoleRevoked")
    assert _normalize_role(role_revoked_event["role"]) == role_hash.replace("0x", ""), "Wrong role hash"
    assert convert.to_address(role_revoked_event["account"]) == convert.to_address(account), "Wrong revoked account"
    assert convert.to_address(role_revoked_event["sender"]) == convert.to_address(sender), "Wrong role revoke sender"
    _assert_emitted_by(role_revoked_event, emitted_by)


def validate_role_grant_event(
    event: EventDict, role_hash: str, account: str, sender: str, emitted_by: str, events_chain: list = None
) -> None:
    validate_events_chain([e.name for e in event], events_chain or ["LogScriptCall", "RoleGranted"])

    role_granted_event = _single_event(event, "RoleGranted")
    assert _normalize_role(role_granted_event["role"]) == role_hash.replace("0x", ""), "Wrong role hash"
    assert convert.to_address(role_granted_event["account"]) == convert.to_address(account), "Wrong granted account"
    assert convert.to_address(role_granted_event["sender"]) == convert.to_address(sender), "Wrong role grant sender"
    _assert_emitted_by(role_granted_event, emitted_by)


# ============================================================================
# =============================== Fixtures ===================================
# ============================================================================
@pytest.fixture(scope="module")
def runtime_upgrade_context():
    if network_name() != "hoodi-fork":
        pytest.skip("Run the EDF upgrade test on --network hoodi-fork.")

    missing_addresses = [
        name
        for name, value in [
            ("NEW_DEPOSIT_SECURITY_MODULE", NEW_DEPOSIT_SECURITY_MODULE),
            ("NEW_LIDO_LOCATOR_IMPLEMENTATION", NEW_LIDO_LOCATOR_IMPLEMENTATION),
        ]
        if _is_placeholder_address(value)
    ]
    missing_addresses += [
        f"DelegationContract for {m.name}"
        for m in ORACLE_MEMBER_MAPPINGS
        if _is_placeholder_address(m.delegation_contract)
    ]
    if missing_addresses:
        pytest.skip(
            "EDF deploy addresses are missing, fill the TODOs in scripts/vote_edf_hoodi.py "
            f"and tests/test_vote_edf_hoodi.py first: {', '.join(missing_addresses)}"
        )

    # Cross-check the deploy addresses against the vote script copies
    assert NEW_DEPOSIT_SECURITY_MODULE.lower() == vote_script.NEW_DEPOSIT_SECURITY_MODULE.lower()
    assert NEW_LIDO_LOCATOR_IMPLEMENTATION.lower() == vote_script.NEW_LIDO_LOCATOR_IMPLEMENTATION.lower()
    for test_mapping, script_mapping in zip(ORACLE_MEMBER_MAPPINGS, vote_script.ORACLE_MEMBER_MAPPINGS):
        assert test_mapping.old_member.lower() == script_mapping.old_member.lower()
        assert test_mapping.delegation_contract.lower() == script_mapping.delegation_contract.lower()

    return {
        "new_dsm": interface.DepositSecurityModule(NEW_DEPOSIT_SECURITY_MODULE),
        "old_dsm": interface.DepositSecurityModule(OLD_DEPOSIT_SECURITY_MODULE),
        "locator_proxy": interface.OssifiableProxy(LIDO_LOCATOR),
        "staking_router": interface.StakingRouter(STAKING_ROUTER),
        "top_up_gateway": interface.TopUpGateway(TOP_UP_GATEWAY),
    }


@pytest.fixture(scope="module")
def dual_governance_proposal_calls(runtime_upgrade_context):
    return [{"target": target, "value": 0, "data": data} for target, data in get_dg_items()]


# ============================================================================
# ================================= Test =====================================
# ============================================================================
def test_vote(
    helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls, runtime_upgrade_context
):
    ctx = runtime_upgrade_context

    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

    new_dsm = ctx["new_dsm"]
    old_dsm = ctx["old_dsm"]
    locator_proxy = ctx["locator_proxy"]
    staking_router = ctx["staking_router"]
    top_up_gateway = ctx["top_up_gateway"]

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

        # 1. Submit the EDF/DSM v5 upgrade to Dual Governance
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
    locator_addresses_before = None
    if details["status"] != PROPOSAL_STATUS["executed"]:
        # =======================================================================
        # ==================== Before DG enactment checks =======================
        # =======================================================================
        for committee in ORACLE_COMMITTEES:
            consensus = interface.HashConsensus(committee.consensus_contract)
            assert consensus.getQuorum() == ORACLE_COMMITTEE_QUORUM
            members = [str(m).lower() for m in consensus.getMembers()[0]]
            assert len(members) == len(ORACLE_MEMBER_MAPPINGS)
            for mapping in ORACLE_MEMBER_MAPPINGS:
                assert mapping.old_member.lower() in members
                assert mapping.delegation_contract.lower() not in members

        assert staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE)
        assert not staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE)
        assert top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_OLD_EOA)
        assert not top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_DELEGATION_CONTRACT)

        assert str(locator_proxy.proxy__getImplementation()).lower() != NEW_LIDO_LOCATOR_IMPLEMENTATION.lower()

        # Snapshot the full locator address registry - the upgrade must change
        # only the depositSecurityModule entry
        locator_addresses_before = _locator_addresses(interface.LidoLocator(LIDO_LOCATOR))
        assert locator_addresses_before["depositSecurityModule"].lower() == OLD_DEPOSIT_SECURITY_MODULE.lower()

        # Old DSM v4 holds the EOA guardian set (7 guardians: 6 mapped + 1 extra Lido dev team)
        old_dsm_guardians = {str(g).lower() for g in old_dsm.getGuardians()}
        assert old_dsm_guardians == {g.lower() for g in OLD_DSM_GUARDIANS}

        # New DSM v5 is deployed with the DelegationContract guardian set
        assert new_dsm.VERSION() == NEW_DSM_VERSION
        assert convert.to_address(new_dsm.getOwner()) == convert.to_address(AGENT)
        assert new_dsm.getGuardianQuorum() == NEW_DSM_GUARDIAN_QUORUM
        new_dsm_guardians = {str(g).lower() for g in new_dsm.getGuardians()}
        assert new_dsm_guardians == {g.lower() for g in NEW_DSM_GUARDIANS}

        if details["status"] == PROPOSAL_STATUS["submitted"]:
            chain.sleep(timelock.getAfterSubmitDelay() + 1)
            dual_governance.scheduleProposal(expected_dg_proposal_id, {"from": stranger})

        if timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["scheduled"]:
            chain.sleep(timelock.getAfterScheduleDelay() + 1)

            dg_tx: TransactionReceipt = timelock.execute(expected_dg_proposal_id, {"from": stranger})
            display_dg_events(dg_tx)

            outer_dg_events = group_dg_events_from_receipt(
                dg_tx,
                timelock=EMERGENCY_PROTECTED_TIMELOCK,
                admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            )
            dg_events = _group_agent_dg_events_from_receipt(
                dg_tx,
                timelock=EMERGENCY_PROTECTED_TIMELOCK,
                agent=AGENT,
            )

            # The whole upgrade is a single Agent.forward with 85 inner calls
            assert len(outer_dg_events) == 1
            assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_COUNT
            assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

            # =======================================================================
            # ============================ DG events checks =========================
            # =======================================================================
            event_index = 0

            # 1.1-1.80. Rotate oracle committee members
            for committee in ORACLE_COMMITTEES:
                for mapping in ORACLE_MEMBER_MAPPINGS:
                    validate_member_removed_event(
                        dg_events[event_index],
                        member=mapping.old_member,
                        new_total_members=len(ORACLE_MEMBER_MAPPINGS) - 1,
                        new_quorum=ORACLE_COMMITTEE_QUORUM,
                        emitted_by=committee.consensus_contract,
                    )
                    event_index += 1

                    validate_member_added_event(
                        dg_events[event_index],
                        member=mapping.delegation_contract,
                        new_total_members=len(ORACLE_MEMBER_MAPPINGS),
                        new_quorum=ORACLE_COMMITTEE_QUORUM,
                        emitted_by=committee.consensus_contract,
                    )
                    event_index += 1

            # 1.81. Upgrade LidoLocator implementation
            validate_proxy_upgrade_event(
                dg_events[event_index],
                implementation=NEW_LIDO_LOCATOR_IMPLEMENTATION,
                emitted_by=LIDO_LOCATOR,
            )
            event_index += 1

            # 1.82. Revoke STAKING_MODULE_UNVETTING_ROLE from the old DSM
            validate_role_revoke_event(
                dg_events[event_index],
                role_hash=STAKING_MODULE_UNVETTING_ROLE,
                account=OLD_DEPOSIT_SECURITY_MODULE,
                sender=AGENT,
                emitted_by=STAKING_ROUTER,
            )
            event_index += 1

            # 1.83. Grant STAKING_MODULE_UNVETTING_ROLE to the new DSM
            validate_role_grant_event(
                dg_events[event_index],
                role_hash=STAKING_MODULE_UNVETTING_ROLE,
                account=NEW_DEPOSIT_SECURITY_MODULE,
                sender=AGENT,
                emitted_by=STAKING_ROUTER,
            )
            event_index += 1

            # 1.84. Revoke TOP_UP_ROLE from the old depositor bot EOA
            validate_role_revoke_event(
                dg_events[event_index],
                role_hash=TOP_UP_ROLE,
                account=DEPOSITOR_BOT_OLD_EOA,
                sender=AGENT,
                emitted_by=TOP_UP_GATEWAY,
            )
            event_index += 1

            # 1.85. Grant TOP_UP_ROLE to the depositor bot DelegationContract
            # (the last inner call group also carries the Agent.forward service events)
            validate_role_grant_event(
                dg_events[event_index],
                role_hash=TOP_UP_ROLE,
                account=DEPOSITOR_BOT_DELEGATION_CONTRACT,
                sender=AGENT,
                emitted_by=TOP_UP_GATEWAY,
                events_chain=["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"],
            )
            event_index += 1

            assert event_index == EXPECTED_DG_EVENTS_COUNT

    # =========================================================================
    # ==================== After DG proposal executed checks ==================
    # =========================================================================
    assert timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["executed"]

    for committee in ORACLE_COMMITTEES:
        consensus = interface.HashConsensus(committee.consensus_contract)
        assert consensus.getQuorum() == ORACLE_COMMITTEE_QUORUM
        members = [str(m).lower() for m in consensus.getMembers()[0]]
        assert len(members) == len(ORACLE_MEMBER_MAPPINGS)
        for mapping in ORACLE_MEMBER_MAPPINGS:
            assert mapping.old_member.lower() not in members
            assert mapping.delegation_contract.lower() in members

    assert str(locator_proxy.proxy__getImplementation()).lower() == NEW_LIDO_LOCATOR_IMPLEMENTATION.lower()
    assert (
        str(interface.LidoLocator(LIDO_LOCATOR).depositSecurityModule()).lower()
        == NEW_DEPOSIT_SECURITY_MODULE.lower()
    )

    # Every locator entry except depositSecurityModule must stay unchanged
    if locator_addresses_before is not None:
        locator = interface.LidoLocator(LIDO_LOCATOR)
        for name, before_value in locator_addresses_before.items():
            after_value = str(getattr(locator, name)())
            if name == "depositSecurityModule":
                assert after_value.lower() == NEW_DEPOSIT_SECURITY_MODULE.lower()
            else:
                assert after_value == before_value, f"Locator entry {name} changed unexpectedly"

    assert not staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE)
    assert staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE)
    assert not top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_OLD_EOA)
    assert top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_DELEGATION_CONTRACT)

    assert new_dsm.VERSION() == NEW_DSM_VERSION
    assert convert.to_address(new_dsm.getOwner()) == convert.to_address(AGENT)
    assert new_dsm.getGuardianQuorum() == NEW_DSM_GUARDIAN_QUORUM
    assert {str(g).lower() for g in new_dsm.getGuardians()} == {g.lower() for g in NEW_DSM_GUARDIANS}
