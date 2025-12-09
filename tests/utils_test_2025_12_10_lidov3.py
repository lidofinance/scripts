from brownie import chain, interface, web3, convert, accounts, reverts, ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events
)
from utils.evm_script import encode_call_script, encode_error
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.dual_governance import PROPOSAL_STATUS, wait_for_target_time_to_satisfy_time_constrains
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event

from utils.agent import agent_forward
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.easy_track import create_permissions
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.proxy import validate_proxy_upgrade_event
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.aragon import validate_aragon_set_app_event, validate_aragon_grant_permission_event, validate_aragon_revoke_permission_event
from utils.test.easy_track_helpers import _encode_calldata, create_and_enact_motion


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_2025_12_10_mainnet_v3 import start_vote, get_vote_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================

DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"

# Voting addresses
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
DUAL_GOVERNANCE_TIME_CONSTRAINTS = "0x2a30F5aC03187674553024296bed35Aa49749DDa"
ARAGON_KERNEL = "0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc"
ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
EASYTRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
EASYTRACK_EVMSCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

# Old Lido addresses
LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
HASH_CONSENSUS = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288" # HashConsensus for AccountingOracle
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
ORACLE_DAEMON_CONFIG = "0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09"
CSM_ACCOUNTING = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"
OLD_BURNER = "0xD15a672319Cf0352560eE76d9e89eAB0889046D3"
LIDO_APP_ID = "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320"
WITHDRAWAL_QUEUE = "0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1"

# Our custom Aragon apps
LIDO = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
NODE_OPERATORS_REGISTRY = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
SIMPLE_DVT = "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433"

# New Lido V3 addresses
VAULT_HUB = "0x1d201BE093d847f6446530Efb0E8Fb426d176709"
ACCOUNTING = "0x23ED611be0e1a820978875C0122F92260804cdDf"
ACCOUNTING_IMPL = "0xd43a3E984071F40d5d840f60708Af0e9526785df"
OPERATOR_GRID = "0xC69685E89Cefc327b43B7234AC646451B27c544d"
LAZY_ORACLE = "0x5DB427080200c235F2Ae8Cd17A7be87921f7AD6c"
PREDEPOSIT_GUARANTEE = "0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3"
VAULTS_ADAPTER = "0xe2DE6d2DefF15588a71849c0429101F8ca9FB14D"
GATE_SEAL_V3 = "0x881dAd714679A6FeaA636446A0499101375A365c"
LIDO_IMPL = "0x6ca84080381E43938476814be61B779A8bB6a600"
UPGRADE_TEMPLATE = "0x34E01ecFebd403370b0879C628f8A5319dDb8507"
LIDO_LOCATOR_IMPL = "0x2f8779042EFaEd4c53db2Ce293eB6B3f7096C72d"
ACCOUNTING_ORACLE_IMPL = "0x1455B96780A93e08abFE41243Db92E2fCbb0141c"
RESEAL_MANAGER = "0x7914b5a1539b97Bd0bbd155757F25FD79A522d24"
BURNER = "0xE76c52750019b80B43E36DF30bf4060EB73F573a"
VAULTS_FACTORY = "0x02Ca7772FF14a9F6c1a08aF385aA96bb1b34175A"

# New Easy Track factories
ST_VAULTS_COMMITTEE = "0x18A1065c81b0Cc356F1b1C843ddd5E14e4AefffF"
ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0xa29173C7BCf39dA48D5E404146A652d7464aee14"
REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0x194A46DA1947E98c9D79af13E06Cfbee0D8610cC"
REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0x5292A1284e4695B95C0840CF8ea25A818751C17F"
SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x93F1DEE4473Ee9F42c8257C201e33a6Da30E5d67"
SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0x1dF50522A1D868C12bF71747Bb6F24A18Fe6d32C"
FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6C968cD89CA358fbAf57B18e77a8973Fa869a6aA"
UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0x8Bdc726a3147D8187820391D7c6F9F942606aEe6"
UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0x5C3bDFa3E7f312d8cf72F56F2b797b026f6B471c"

# New versions of apps after upgrade
NEW_LIDO_VERSION = 3
NEW_ACCOUNTING_ORACLE_VERSION = 4
NEW_HASH_CONSENSUS_VERSION = 5

UTC14 = 60 * 60 * 14
UTC23 = 60 * 60 * 23
SLASHING_RESERVE_SHIFT = 8192
MAX_EXTERNAL_RATIO_BP = 300 # 3%
INFINITE_ALLOWANCE = 2**256 - 1 # type(uint256).max


# ============================================================================
# ============================== Helper functions ============================
# ============================================================================

def get_ossifiable_proxy_impl(proxy_address):
    """Get implementation address from an OssifiableProxy"""
    proxy = interface.OssifiableProxy(proxy_address)
    return proxy.proxy__getImplementation()


# ============================================================================
# =================== Aragon event validators for DG =========================
# ============================================================================

def validate_config_value_set_event(
    event,
    key: str,
    value: int,
    emitted_by: str,
) -> None:
    """
    Validate OracleDaemonConfig ConfigValueSet event via DG proposal.
    Ensures only expected events are fired and all parameters are correct.
    """
    _events_chain = ["LogScriptCall", "ConfigValueSet", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {event.count('LogScriptCall')}"
    assert event.count("ConfigValueSet") == 1, f"Expected 1 ConfigValueSet, got {event.count('ConfigValueSet')}"
    assert event.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {event.count('ScriptResult')}"
    assert event.count("Executed") == 1, f"Expected 1 Executed, got {event.count('Executed')}"

    assert key == event["ConfigValueSet"][0]["key"], f"Wrong key: expected {key} to be equal to {event['ConfigValueSet'][0]['key']}"
    assert convert.to_int(event["ConfigValueSet"][0]["value"]) == value, f"Wrong value: expected {value}, got {convert.to_int(event['ConfigValueSet'][0]['value'])}"

    assert convert.to_address(event["ConfigValueSet"][0]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}"


def validate_upgrade_started_event(events) -> None:
    """
    Validate V3Template UpgradeStarted event via DG proposal.
    Ensures only expected events are fired.
    """
    _events_chain = ["LogScriptCall", "UpgradeStarted", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in events], _events_chain)

    assert events.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {events.count('LogScriptCall')}"
    assert events.count("UpgradeStarted") == 1, f"Expected 1 UpgradeStarted, got {events.count('UpgradeStarted')}"
    assert events.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {events.count('ScriptResult')}"
    assert events.count("Executed") == 1, f"Expected 1 Executed, got {events.count('Executed')}"

    assert convert.to_address(events["UpgradeStarted"][0]["_emitted_by"]) == convert.to_address(
        UPGRADE_TEMPLATE
    ), f"Wrong event emitter: expected {UPGRADE_TEMPLATE}"


def validate_upgrade_finished_events(events) -> None:
    """
    Validate V3Template UpgradeFinished events via DG proposal.
    Ensures only expected events are fired.
    """
    _events_chain = ["LogScriptCall", "ContractVersionSet", "Transfer", "TransferShares", "Approval", "Approval", "Approval", "Approval",
    "MaxExternalRatioBPSet", "ContractVersionSet", "ConsensusVersionSet", "UpgradeFinished", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in events], _events_chain)

    assert events.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {events.count('LogScriptCall')}"
    assert events.count("ContractVersionSet") == 2, f"Expected 1 ContractVersionSet, got {events.count('ContractVersionSet')}"
    assert events.count("Approval") == 4, f"Expected 4 Approval, got {events.count('Approval')}"
    assert events.count("MaxExternalRatioBPSet") == 1, f"Expected 1 MaxExternalRatioBPSet, got {events.count('MaxExternalRatioBPSet')}"
    assert events.count("ConsensusVersionSet") == 1, f"Expected 1 ConsensusVersionSet, got {events.count('ConsensusVersionSet')}"
    assert events.count("UpgradeFinished") == 1, f"Expected 1 UpgradeFinished, got {events.count('UpgradeFinished')}"
    assert events.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {events.count('ScriptResult')}"
    assert events.count("Executed") == 1, f"Expected 1 Executed, got {events.count('Executed')}"

    lido_version = events["ContractVersionSet"][0]["version"]
    assert lido_version == NEW_LIDO_VERSION, f"Wrong version: expected {NEW_LIDO_VERSION}, got {lido_version}"
    assert convert.to_address(events["ContractVersionSet"][0]["_emitted_by"]) == LIDO, f"Wrong event emitter: expected {LIDO}"

    # Transfer and TransferShares events are emitted only if old Burner has some shares on balance
    if events.count("Transfer") > 0:
        assert events.count("Transfer") == 1, "Transfer event should be emitted only once"
        assert events.count("TransferShares") == 1, "TransferShares event should be emitted only once"
        assert convert.to_address(events["Transfer"][0]["from"]) == OLD_BURNER, f"Wrong from: expected {OLD_BURNER}"
        assert convert.to_address(events["Transfer"][0]["to"]) == BURNER, f"Wrong to: expected {BURNER}"
        assert convert.to_address(events["Transfer"][0]["_emitted_by"]) == LIDO, f"Wrong event emitter: expected {LIDO}"
        assert convert.to_address(events["TransferShares"][0]["from"]) == OLD_BURNER, f"Wrong from: expected {OLD_BURNER}"
        assert convert.to_address(events["TransferShares"][0]["to"]) == BURNER, f"Wrong to: expected {BURNER}"
        assert convert.to_address(events["TransferShares"][0]["_emitted_by"]) == LIDO, f"Wrong event emitter: expected {LIDO}"

    assert convert.to_address(events["Approval"][0]["owner"]) == WITHDRAWAL_QUEUE, f"Wrong owner: expected {WITHDRAWAL_QUEUE}"
    assert convert.to_address(events["Approval"][0]["spender"]) == OLD_BURNER, f"Wrong spender: expected {OLD_BURNER}"
    assert convert.to_uint(events["Approval"][0]["value"]) == 0, f"Wrong value: expected {0}"
    assert convert.to_address(events["Approval"][0]["_emitted_by"]) == LIDO, f"Wrong event emitter: expected {LIDO}"

    assert convert.to_address(events["Approval"][1]["owner"]) == WITHDRAWAL_QUEUE, f"Wrong owner: expected {WITHDRAWAL_QUEUE}"
    assert convert.to_address(events["Approval"][1]["spender"]) == BURNER, f"Wrong spender: expected {BURNER}"
    assert convert.to_uint(events["Approval"][1]["value"]) == INFINITE_ALLOWANCE, f"Wrong value: expected {INFINITE_ALLOWANCE}"
    assert convert.to_address(events["Approval"][1]["_emitted_by"]) == LIDO, f"Wrong event emitter: expected {LIDO}"

    assert convert.to_address(events["Approval"][2]["owner"]) == CSM_ACCOUNTING, f"Wrong owner: expected {CSM_ACCOUNTING}"
    assert convert.to_address(events["Approval"][2]["spender"]) == OLD_BURNER, f"Wrong spender: expected {OLD_BURNER}"
    assert convert.to_uint(events["Approval"][2]["value"]) == 0, f"Wrong value: expected {0}"
    assert convert.to_address(events["Approval"][2]["_emitted_by"]) == LIDO, f"Wrong event emitter: expected {LIDO}"

    assert convert.to_address(events["Approval"][3]["owner"]) == CSM_ACCOUNTING, f"Wrong owner: expected {CSM_ACCOUNTING}"
    assert convert.to_address(events["Approval"][3]["spender"]) == BURNER, f"Wrong spender: expected {BURNER}"
    assert convert.to_uint(events["Approval"][3]["value"]) == INFINITE_ALLOWANCE, f"Wrong value: expected {INFINITE_ALLOWANCE}"
    assert convert.to_address(events["Approval"][3]["_emitted_by"]) == LIDO, f"Wrong event emitter: expected {LIDO}"

    max_external_ratio_bp = events["MaxExternalRatioBPSet"][0]["maxExternalRatioBP"]
    assert max_external_ratio_bp == MAX_EXTERNAL_RATIO_BP, f"Wrong max external ratio: expected {MAX_EXTERNAL_RATIO_BP}, got {max_external_ratio_bp}"
    assert convert.to_address(events["MaxExternalRatioBPSet"][0]["_emitted_by"]) == LIDO, f"Wrong event emitter: expected {LIDO}"

    oracle_version = events["ContractVersionSet"][1]["version"]
    assert oracle_version == NEW_ACCOUNTING_ORACLE_VERSION, f"Wrong version: expected {NEW_ACCOUNTING_ORACLE_VERSION}, got {oracle_version}"
    assert convert.to_address(events["ContractVersionSet"][1]["_emitted_by"]) == ACCOUNTING_ORACLE, f"Wrong event emitter: expected {ACCOUNTING_ORACLE}"

    consensus_version = events["ConsensusVersionSet"][0]["version"]
    assert consensus_version == NEW_HASH_CONSENSUS_VERSION, f"Wrong version: expected {NEW_HASH_CONSENSUS_VERSION}, got {consensus_version}"
    assert convert.to_address(events["ConsensusVersionSet"][0]["_emitted_by"]) == ACCOUNTING_ORACLE, f"Wrong event emitter: expected {ACCOUNTING_ORACLE}"

    assert convert.to_address(events["UpgradeFinished"][0]["_emitted_by"]) == convert.to_address(
        UPGRADE_TEMPLATE
    ), f"Wrong event emitter: expected {UPGRADE_TEMPLATE}"


# ============================================================================
# ============================== Test functions ==============================
# ============================================================================

def dual_governance_proposal_calls():
    """Returns list of dual governance proposal calls for events checking"""

    # Helper function to encode proxy upgrades
    def encode_proxy_upgrade_to(proxy_contract, new_impl_address):
        return (proxy_contract.address, proxy_contract.proxy__upgradeTo.encode_input(new_impl_address))

    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    upgradeTemplate = interface.UpgradeTemplateV3(UPGRADE_TEMPLATE)
    old_burner = interface.Burner(OLD_BURNER)
    oracle_daemon_config = interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)
    accounting_oracle_proxy = interface.OssifiableProxy(ACCOUNTING_ORACLE)
    kernel = interface.Kernel(ARAGON_KERNEL)
    acl = interface.ACL(ACL)
    staking_router = interface.StakingRouter(STAKING_ROUTER)

    dg_items = [
        # 1.1. Ensure DG proposal execution is within daily time window (14:00 UTC - 23:00 UTC)
        (
            DUAL_GOVERNANCE_TIME_CONSTRAINTS,
            interface.TimeConstraints(DUAL_GOVERNANCE_TIME_CONSTRAINTS).checkTimeWithinDayTimeAndEmit.encode_input(
                UTC14,  # 14:00 UTC
                UTC23  # 23:00 UTC
            ),
        ),

        # 1.2. Call V3Template.startUpgrade
        agent_forward([
            (upgradeTemplate.address, upgradeTemplate.startUpgrade.encode_input())
        ]),

        # 1.3. Upgrade LidoLocator implementation
        agent_forward([encode_proxy_upgrade_to(lido_locator_proxy, LIDO_LOCATOR_IMPL)]),

        # 1.4. Grant Aragon APP_MANAGER_ROLE to the AGENT
        agent_forward([
            (acl.address,
             acl.grantPermission.encode_input(
                 AGENT,
                 ARAGON_KERNEL,
                 web3.keccak(text="APP_MANAGER_ROLE")
             ))
        ]),

        # 1.5. Set Lido implementation in Kernel
        agent_forward([
            (kernel.address,
             kernel.setApp.encode_input(
                kernel.APP_BASES_NAMESPACE(),
                LIDO_APP_ID,
                LIDO_IMPL
             ))
        ]),

        # 1.6. Revoke Aragon APP_MANAGER_ROLE from the AGENT
        agent_forward([
            (acl.address,
             acl.revokePermission.encode_input(
                 AGENT,
                 ARAGON_KERNEL,
                 web3.keccak(text="APP_MANAGER_ROLE")
             ))
        ]),

        # 1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido
        agent_forward([
            encode_oz_revoke_role(
                contract=old_burner,
                role_name="REQUEST_BURN_SHARES_ROLE",
                revoke_from=LIDO
            )
        ]),

        # 1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking module
        agent_forward([
            encode_oz_revoke_role(
                contract=old_burner,
                role_name="REQUEST_BURN_SHARES_ROLE",
                revoke_from=NODE_OPERATORS_REGISTRY
            )
        ]),

        # 1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
        agent_forward([
            encode_oz_revoke_role(
                contract=old_burner,
                role_name="REQUEST_BURN_SHARES_ROLE",
                revoke_from=SIMPLE_DVT
            )
        ]),

        # 1.10. Revoke REQUEST_BURN_SHARES_ROLE from Community Staking Accounting
        agent_forward([
            encode_oz_revoke_role(
                contract=old_burner,
                role_name="REQUEST_BURN_SHARES_ROLE",
                revoke_from=CSM_ACCOUNTING
            )
        ]),

        # 1.11. Upgrade AccountingOracle implementation
        agent_forward([encode_proxy_upgrade_to(accounting_oracle_proxy, ACCOUNTING_ORACLE_IMPL)]),

        # 1.12. Revoke REPORT_REWARDS_MINTED_ROLE from Lido
        agent_forward([
            encode_oz_revoke_role(
                contract=staking_router,
                role_name="REPORT_REWARDS_MINTED_ROLE",
                revoke_from=LIDO
            )
        ]),

        # 1.13. Grant REPORT_REWARDS_MINTED_ROLE to Accounting
        agent_forward([
            encode_oz_grant_role(
                contract=staking_router,
                role_name="REPORT_REWARDS_MINTED_ROLE",
                grant_to=ACCOUNTING
            )
        ]),

        # 1.14. Grant OracleDaemonConfig's CONFIG_MANAGER_ROLE to Agent
        agent_forward([
            encode_oz_grant_role(
                contract=oracle_daemon_config,
                role_name="CONFIG_MANAGER_ROLE",
                grant_to=AGENT
            )
        ]),

        # 1.15. Set SLASHING_RESERVE_WE_RIGHT_SHIFT to 0x2000 at OracleDaemonConfig
        agent_forward([
            (oracle_daemon_config.address, oracle_daemon_config.set.encode_input(
                "SLASHING_RESERVE_WE_RIGHT_SHIFT",
                web3.codec.encode(['uint256'], [SLASHING_RESERVE_SHIFT])
            ))
        ]),

        # 1.16. Set SLASHING_RESERVE_WE_LEFT_SHIFT to 0x2000 at OracleDaemonConfig
        agent_forward([
            (oracle_daemon_config.address, oracle_daemon_config.set.encode_input(
                "SLASHING_RESERVE_WE_LEFT_SHIFT",
                web3.codec.encode(['uint256'], [SLASHING_RESERVE_SHIFT])
            ))
        ]),

        # 1.17. Revoke OracleDaemonConfig's CONFIG_MANAGER_ROLE from Agent
        agent_forward([
            encode_oz_revoke_role(
                contract=oracle_daemon_config,
                role_name="CONFIG_MANAGER_ROLE",
                revoke_from=AGENT
            )
        ]),

        # 1.18. Call V3Template.finishUpgrade
        agent_forward([
            (upgradeTemplate.address, upgradeTemplate.finishUpgrade.encode_input())
        ]),
    ]

    # Convert each dg_item to the expected format
    proposal_calls = []
    for dg_item in dg_items:
        target, data = dg_item  # agent_forward returns (target, data)
        proposal_calls.append({
            "target": target,
            "value": 0,
            "data": data
        })

    return proposal_calls


def enact_and_test_voting(
    helpers,
    accounts,
    ldo_holder,
    vote_ids_from_env,
    stranger,
    expected_vote_id,
    expected_dg_proposal_id,
):
    """
    Submit, enact and test the voting proposal.
    Includes all before/after voting checks and event validation.
    """
    EXPECTED_VOTE_EVENTS_COUNT = 9
    IPFS_DESCRIPTION_HASH = "bafkreic4xuaowfowt7faxnngnzynv7biuo7guv4s4jrngngjzzxyz3up2i"

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    easy_track = interface.EasyTrack(EASYTRACK)

    vault_hub = interface.VaultHub(VAULT_HUB)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)

    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        if expected_vote_id is not None:
            assert vote_id == expected_vote_id
    elif expected_vote_id is not None and voting.votesLength() > expected_vote_id:
        vote_id = expected_vote_id
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
    onchain_script = voting.getVote(vote_id)["script"]
    assert onchain_script == encode_call_script(call_script_items)


    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        # Steps 2-9: Add EasyTrack factories
        initial_factories = easy_track.getEVMScriptFactories()
        assert ALTER_TIERS_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY not in initial_factories, "EasyTrack should not have SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY factory before vote"
        assert FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY not in initial_factories, "EasyTrack should not have FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY factory before vote"
        assert UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY factory before vote"

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        # Check roles that are needed for Easy Track factories
        registry_role = web3.keccak(text="vaults.OperatorsGrid.Registry")
        assert operator_grid.hasRole(registry_role, VAULTS_ADAPTER), "Operator Grid should have REGISTRY_ROLE on VAULTS_ADAPTER after upgrade"
        assert operator_grid.hasRole(registry_role, EASYTRACK_EVMSCRIPT_EXECUTOR), "Operator Grid should have REGISTRY_ROLE on EASYTRACK_EVMSCRIPT_EXECUTOR after upgrade"
        validator_exit_role = web3.keccak(text="vaults.VaultHub.ValidatorExitRole")
        assert vault_hub.hasRole(validator_exit_role, VAULTS_ADAPTER), "Vault Hub should have VALIDATOR_EXIT_ROLE on VAULTS_ADAPTER after upgrade"
        bad_debt_master_role = web3.keccak(text="vaults.VaultHub.BadDebtMasterRole")
        assert vault_hub.hasRole(bad_debt_master_role, VAULTS_ADAPTER), "Vault Hub should have BAD_DEBT_MASTER_ROLE on VAULTS_ADAPTER after upgrade"

        # Steps 2-9: Add EasyTrack factories
        new_factories = easy_track.getEVMScriptFactories()
        assert ALTER_TIERS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY factory after vote"
        assert FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY factory after vote"
        assert UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY factory after vote"

        # Check that after the Aragon vote has passed, creation of the vaults via VaultFactory still reverts
        with reverts():
            interface.VaultFactory(VAULTS_FACTORY).createVaultWithDashboard(
                stranger,
                stranger,
                stranger,
                100,
                3600,
                [],
                {"from": stranger, "value": "1 ether"},
            )

        vote_events = group_voting_events_from_receipt(vote_tx)
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        if expected_dg_proposal_id is not None:
            assert expected_dg_proposal_id == timelock.getProposalsCount()

            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=expected_dg_proposal_id,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata="Activate Lido V3",
                proposal_calls=dual_governance_proposal_calls(),
            )

            # Validate EasyTrack bypass events for new factories
            validate_evmscript_factory_added_event(
                event=vote_events[1],
                p=EVMScriptFactoryAdded(
                    factory_addr=ALTER_TIERS_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(interface.OperatorGrid(OPERATOR_GRID), "alterTiers")
                ),
                emitted_by=easy_track,
            )

            validate_evmscript_factory_added_event(
                event=vote_events[2],
                p=EVMScriptFactoryAdded(
                    factory_addr=REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(interface.OperatorGrid(OPERATOR_GRID), "registerGroup") + create_permissions(interface.OperatorGrid(OPERATOR_GRID), "registerTiers")[2:]
                ),
                emitted_by=easy_track,
            )

            validate_evmscript_factory_added_event(
                event=vote_events[3],
                p=EVMScriptFactoryAdded(
                    factory_addr=REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(interface.OperatorGrid(OPERATOR_GRID), "registerTiers")
                ),
                emitted_by=easy_track,
            )

            validate_evmscript_factory_added_event(
                event=vote_events[4],
                p=EVMScriptFactoryAdded(
                    factory_addr=UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(interface.OperatorGrid(OPERATOR_GRID), "updateGroupShareLimit")
                ),
                emitted_by=easy_track,
            )

            validate_evmscript_factory_added_event(
                event=vote_events[5],
                p=EVMScriptFactoryAdded(
                    factory_addr=SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(interface.IVaultsAdapter(VAULTS_ADAPTER), "setVaultJailStatus")
                ),
                emitted_by=easy_track,
            )

            validate_evmscript_factory_added_event(
                event=vote_events[6],
                p=EVMScriptFactoryAdded(
                    factory_addr=UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(interface.IVaultsAdapter(VAULTS_ADAPTER), "updateVaultFees")
                ),
                emitted_by=easy_track,
            )

            validate_evmscript_factory_added_event(
                event=vote_events[7],
                p=EVMScriptFactoryAdded(
                    factory_addr=FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY,
                    permissions=create_permissions(interface.IVaultsAdapter(VAULTS_ADAPTER), "forceValidatorExit")
                ),
                emitted_by=easy_track,
            )

            validate_evmscript_factory_added_event(
                event=vote_events[8],
                p=EVMScriptFactoryAdded(
                    factory_addr=SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY,
                    permissions=create_permissions(interface.IVaultsAdapter(VAULTS_ADAPTER), "socializeBadDebt")
                ),
                emitted_by=easy_track,
            )


def enact_and_test_dg(stranger, expected_dg_proposal_id):
    """
    Enact and test the dual governance proposal.
    Includes all before/after DG checks and event validation.
    """
    if expected_dg_proposal_id is None:
        return

    EXPECTED_DG_EVENTS_FROM_AGENT = 17
    EXPECTED_DG_EVENTS_COUNT = 18

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    kernel = interface.Kernel(ARAGON_KERNEL)
    acl = interface.ACL(ACL)

    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    accounting_oracle_proxy = interface.OssifiableProxy(ACCOUNTING_ORACLE)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    old_burner = interface.Burner(OLD_BURNER)
    oracle_daemon_config = interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)
    upgradeTemplate = interface.UpgradeTemplateV3(UPGRADE_TEMPLATE)
    lido = interface.Lido(LIDO)

    # Save original implementations for comparison
    locator_impl_before = get_ossifiable_proxy_impl(LIDO_LOCATOR)
    accounting_oracle_impl_before = get_ossifiable_proxy_impl(ACCOUNTING_ORACLE)

    report_rewards_minted_role = web3.keccak(text="REPORT_REWARDS_MINTED_ROLE")
    request_burn_shares_role = web3.keccak(text="REQUEST_BURN_SHARES_ROLE")
    config_manager_role = web3.keccak(text="CONFIG_MANAGER_ROLE")
    app_manager_role = web3.keccak(text="APP_MANAGER_ROLE")

    details = timelock.getProposalDetails(expected_dg_proposal_id)
    if details["status"] != PROPOSAL_STATUS["executed"]:
        # =========================================================================
        # ================== DG before proposal executed checks ===================
        # =========================================================================

        # Step 1.2. Call V3Template.startUpgrade
        assert upgradeTemplate.upgradeBlockNumber() == 0, "V3Template should have upgradeBlockNumber 0 before startUpgrade"
        assert upgradeTemplate.initialTotalShares() == 0, "V3Template should have initialTotalShares 0 before startUpgrade"
        assert upgradeTemplate.initialTotalPooledEther() == 0, "V3Template should have initialTotalPooledEther 0 before startUpgrade"
        assert upgradeTemplate.initialOldBurnerStethSharesBalance() == 0, "V3Template should have initialOldBurnerStethSharesBalance 0 before startUpgrade"
        initial_total_shares_before = lido.getTotalShares()
        initial_total_pooled_ether_before = lido.getTotalPooledEther()

        # Step 1.3: Check Lido Locator implementation initial state
        assert locator_impl_before != LIDO_LOCATOR_IMPL, "Locator implementation should be different before upgrade"

        # Step 1.4. Grant Aragon APP_MANAGER_ROLE to the AGENT
        assert not acl.hasPermission(AGENT, ARAGON_KERNEL, app_manager_role), "AGENT should not have APP_MANAGER_ROLE before upgrade"

        # Step 1.5. Set Lido implementation in Kernel
        assert not kernel.getApp(kernel.APP_BASES_NAMESPACE(), LIDO_APP_ID) == LIDO_IMPL, "Lido implementation should be different before upgrade"

        # Step 1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido
        assert old_burner.hasRole(request_burn_shares_role, LIDO), "Old Burner should have REQUEST_BURN_SHARES_ROLE on Lido before upgrade"

        # Step 1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking module
        assert old_burner.hasRole(request_burn_shares_role, NODE_OPERATORS_REGISTRY), "Old Burner should have REQUEST_BURN_SHARES_ROLE on Curated staking module before upgrade"

        # Step 1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
        assert old_burner.hasRole(request_burn_shares_role, SIMPLE_DVT), "Old Burner should have REQUEST_BURN_SHARES_ROLE on SimpleDVT before upgrade"

        # Step 1.10. Revoke REQUEST_BURN_SHARES_ROLE from Community Staking Accounting
        assert old_burner.hasRole(request_burn_shares_role, CSM_ACCOUNTING), "Old Burner should have REQUEST_BURN_SHARES_ROLE on Community Staking Accounting before upgrade"

        # Step 1.11: Check Accounting Oracle implementation initial state
        assert accounting_oracle_impl_before != ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be different before upgrade"

        # Step 1.12. Revoke REPORT_REWARDS_MINTED_ROLE from Lido
        assert staking_router.hasRole(report_rewards_minted_role, LIDO), "Staking Router should have REPORT_REWARDS_MINTED_ROLE on Lido before upgrade"

        # Step 1.13. Grant REPORT_REWARDS_MINTED_ROLE to Accounting
        assert not staking_router.hasRole(report_rewards_minted_role, ACCOUNTING), "Staking Router should not have REPORT_REWARDS_MINTED_ROLE on Accounting before upgrade"

        # Step 1.14. Grant OracleDaemonConfig's CONFIG_MANAGER_ROLE to Agent
        assert not oracle_daemon_config.hasRole(config_manager_role, AGENT), "OracleDaemonConfig should not have CONFIG_MANAGER_ROLE on Agent before upgrade"

        # Step 1.15. Set SLASHING_RESERVE_WE_RIGHT_SHIFT to 0x2000 at OracleDaemonConfig
        try:
            oracle_daemon_config.get('SLASHING_RESERVE_WE_RIGHT_SHIFT')
            assert False, "SLASHING_RESERVE_WE_RIGHT_SHIFT should not exist before vote"
        except Exception:
            pass  # Expected to fail

        # Step 1.16. Set SLASHING_RESERVE_WE_LEFT_SHIFT to 0x2000 at OracleDaemonConfig
        try:
            oracle_daemon_config.get('SLASHING_RESERVE_WE_LEFT_SHIFT')
            assert False, "SLASHING_RESERVE_WE_LEFT_SHIFT should not exist before vote"
        except Exception:
            pass  # Expected to fail

        # Step 1.18. Call V3Template.finishUpgrade
        assert lido.getContractVersion() == NEW_LIDO_VERSION - 1, "LIDO should have version 2 before finishUpgrade"
        assert lido.allowance(CSM_ACCOUNTING, BURNER) == 0, "No allowance from CSM_ACCOUNTING to BURNER before finishUpgrade"
        assert lido.allowance(CSM_ACCOUNTING, OLD_BURNER) == INFINITE_ALLOWANCE, "Infinite allowance from CSM_ACCOUNTING to OLD_BURNER before finishUpgrade"
        assert lido.allowance(WITHDRAWAL_QUEUE, BURNER) == 0, "No allowance from WITHDRAWAL_QUEUE to BURNER before finishUpgrade"
        assert lido.allowance(WITHDRAWAL_QUEUE, OLD_BURNER) == INFINITE_ALLOWANCE, "Infinite allowance from WITHDRAWAL_QUEUE to OLD_BURNER before finishUpgrade"

        accounting_oracle = interface.AccountingOracle(ACCOUNTING_ORACLE)
        assert accounting_oracle.getContractVersion() == NEW_ACCOUNTING_ORACLE_VERSION - 1, "AccountingOracle should have version 3 before finishUpgrade"
        assert accounting_oracle.getConsensusVersion() == NEW_HASH_CONSENSUS_VERSION - 1, "HashConsensus should have version 4 before finishUpgrade"

        assert upgradeTemplate.isUpgradeFinished() == False, "V3Template should have isUpgradeFinished False before finishUpgrade"

        if details["status"] == PROPOSAL_STATUS["submitted"]:
            chain.sleep(timelock.getAfterSubmitDelay() + 1)
            dual_governance.scheduleProposal(expected_dg_proposal_id, {"from": stranger})

        if timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["scheduled"]:
            chain.sleep(timelock.getAfterScheduleDelay() + 1)

            wait_for_target_time_to_satisfy_time_constrains()

            dg_tx: TransactionReceipt = timelock.execute(expected_dg_proposal_id, {"from": stranger})
            display_dg_events(dg_tx)
            dg_events = group_dg_events_from_receipt(
                dg_tx,
                timelock=EMERGENCY_PROTECTED_TIMELOCK,
                admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            )
            assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
            assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

            # === DG EXECUTION EVENTS VALIDATION ===

            # 1.2. Call V3Template.startUpgrade
            validate_upgrade_started_event(dg_events[1])

            # 1.3. Lido Locator upgrade events
            validate_proxy_upgrade_event(dg_events[2], LIDO_LOCATOR_IMPL, emitted_by=lido_locator_proxy)

            # 1.4. Grant Aragon APP_MANAGER_ROLE to the AGENT
            validate_aragon_grant_permission_event(
                dg_events[3],
                entity=AGENT,
                app=ARAGON_KERNEL,
                role=app_manager_role.hex(),
                emitted_by=ACL,
            )

            # 1.5. Set Lido implementation in Kernel
            validate_aragon_set_app_event(
                dg_events[4],
                app_id=LIDO_APP_ID,
                app=LIDO_IMPL,
                emitted_by=ARAGON_KERNEL,
            )

            # 1.6. Revoke Aragon APP_MANAGER_ROLE from the AGENT
            validate_aragon_revoke_permission_event(
                dg_events[5],
                entity=AGENT,
                app=ARAGON_KERNEL,
                role=app_manager_role.hex(),
                emitted_by=ACL,
            )

            # 1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido
            validate_revoke_role_event(
                dg_events[6],
                role=request_burn_shares_role.hex(),
                revoke_from=LIDO,
                sender=AGENT,
                emitted_by=old_burner,
            )

            # 1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking module
            validate_revoke_role_event(
                dg_events[7],
                role=request_burn_shares_role.hex(),
                revoke_from=NODE_OPERATORS_REGISTRY,
                sender=AGENT,
                emitted_by=old_burner,
            )

            # 1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
            validate_revoke_role_event(
                dg_events[8],
                role=request_burn_shares_role.hex(),
                revoke_from=SIMPLE_DVT,
                sender=AGENT,
                emitted_by=old_burner,
            )

            # 1.10. Revoke REQUEST_BURN_SHARES_ROLE from Community Staking Accounting
            validate_revoke_role_event(
                dg_events[9],
                role=request_burn_shares_role.hex(),
                revoke_from=CSM_ACCOUNTING,
                sender=AGENT,
                emitted_by=old_burner,
            )

            # 1.11. Accounting Oracle upgrade events
            validate_proxy_upgrade_event(dg_events[10], ACCOUNTING_ORACLE_IMPL, emitted_by=accounting_oracle_proxy)

            # 1.12. Revoke Staking Router REPORT_REWARDS_MINTED_ROLE from the Lido
            validate_revoke_role_event(
                dg_events[11],
                role=report_rewards_minted_role.hex(),
                revoke_from=LIDO,
                sender=AGENT,
                emitted_by=staking_router,
            )

            # 1.13. Grant Staking Router REPORT_REWARDS_MINTED_ROLE to Accounting
            validate_grant_role_event(
                dg_events[12],
                role=report_rewards_minted_role.hex(),
                grant_to=ACCOUNTING,
                sender=AGENT,
                emitted_by=staking_router,
            )

            # 1.14. Grant OracleDaemonConfig's CONFIG_MANAGER_ROLE to Agent
            validate_grant_role_event(
                dg_events[13],
                role=config_manager_role.hex(),
                grant_to=AGENT,
                sender=AGENT,
                emitted_by=oracle_daemon_config,
            )

            # 1.15. Set SLASHING_RESERVE_WE_RIGHT_SHIFT to 0x2000 at OracleDaemonConfig
            validate_config_value_set_event(
                dg_events[14],
                key='SLASHING_RESERVE_WE_RIGHT_SHIFT',
                value=SLASHING_RESERVE_SHIFT,
                emitted_by=oracle_daemon_config,
            )

            # 1.16. Set SLASHING_RESERVE_WE_LEFT_SHIFT to 0x2000 at OracleDaemonConfig
            validate_config_value_set_event(
                dg_events[15],
                key='SLASHING_RESERVE_WE_LEFT_SHIFT',
                value=SLASHING_RESERVE_SHIFT,
                emitted_by=oracle_daemon_config,
            )

            # 1.17. Revoke OracleDaemonConfig's CONFIG_MANAGER_ROLE from Agent
            validate_revoke_role_event(
                dg_events[16],
                role=config_manager_role.hex(),
                revoke_from=AGENT,
                sender=AGENT,
                emitted_by=oracle_daemon_config,
            )

            # 1.18. Call V3Template.finishUpgrade
            validate_upgrade_finished_events(dg_events[17])

    # =========================================================================
    # ==================== After DG proposal executed checks ==================
    # =========================================================================

    # Step 1.2. Call V3Template.startUpgrade
    assert upgradeTemplate.upgradeBlockNumber() != 0, "V3Template should have upgradeBlockNumber not 0 after startUpgrade"
    assert upgradeTemplate.initialTotalShares() == initial_total_shares_before, "V3Template should have initialTotalShares equal to the initial total shares before upgrade"
    assert upgradeTemplate.initialTotalPooledEther() == initial_total_pooled_ether_before, "V3Template should have initialTotalPooledEther equal to the initial total pooled ether before upgrade"

    # Step 1.3: Validate Lido Locator implementation was updated
    assert get_ossifiable_proxy_impl(lido_locator_proxy) == LIDO_LOCATOR_IMPL, "Locator implementation should be updated to the new value"

    # Step 1.5. Set Lido implementation in Kernel
    assert kernel.getApp(kernel.APP_BASES_NAMESPACE(), LIDO_APP_ID) == LIDO_IMPL, "Lido implementation should be updated to the new value"

    # Step 1.6. Revoke Aragon APP_MANAGER_ROLE from the AGENT
    assert not acl.hasPermission(AGENT, ARAGON_KERNEL, app_manager_role), "AGENT should not have APP_MANAGER_ROLE after upgrade"

    # Step 1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido
    assert not old_burner.hasRole(request_burn_shares_role, LIDO), "Old Burner should not have REQUEST_BURN_SHARES_ROLE on Lido after upgrade"

    # Step 1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking module
    assert not old_burner.hasRole(request_burn_shares_role, NODE_OPERATORS_REGISTRY), "Old Burner should not have REQUEST_BURN_SHARES_ROLE on Curated staking module after upgrade"

    # Step 1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
    assert not old_burner.hasRole(request_burn_shares_role, SIMPLE_DVT), "Old Burner should not have REQUEST_BURN_SHARES_ROLE on SimpleDVT after upgrade"

    # Step 1.10. Revoke REQUEST_BURN_SHARES_ROLE from Community Staking Accounting
    assert not old_burner.hasRole(request_burn_shares_role, CSM_ACCOUNTING), "Old Burner should not have REQUEST_BURN_SHARES_ROLE on Community Staking Accounting after upgrade"

    # Step 1.11: Validate Accounting Oracle implementation was updated
    assert get_ossifiable_proxy_impl(accounting_oracle_proxy) == ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be updated to the new value"

    # Step 1.12. Revoke REPORT_REWARDS_MINTED_ROLE from Lido
    assert not staking_router.hasRole(report_rewards_minted_role, LIDO), "Staking Router should not have REPORT_REWARDS_MINTED_ROLE on Lido after upgrade"

    # Step 1.13. Grant REPORT_REWARDS_MINTED_ROLE to Accounting
    assert staking_router.hasRole(report_rewards_minted_role, ACCOUNTING), "Staking Router should have REPORT_REWARDS_MINTED_ROLE on Accounting after upgrade"

    # Step 1.15. Set SLASHING_RESERVE_WE_RIGHT_SHIFT to 0x2000 at OracleDaemonConfig
    assert convert.to_uint(oracle_daemon_config.get("SLASHING_RESERVE_WE_RIGHT_SHIFT")) == SLASHING_RESERVE_SHIFT, "OracleDaemonConfig should have SLASHING_RESERVE_WE_RIGHT_SHIFT set to 0x2000 after upgrade"

    # Step 1.16. Set SLASHING_RESERVE_WE_LEFT_SHIFT to 0x2000 at OracleDaemonConfig
    assert convert.to_uint(oracle_daemon_config.get("SLASHING_RESERVE_WE_LEFT_SHIFT")) == SLASHING_RESERVE_SHIFT, "OracleDaemonConfig should have SLASHING_RESERVE_WE_LEFT_SHIFT set to 0x2000 after upgrade"

    # Step 1.17. Revoke OracleDaemonConfig's CONFIG_MANAGER_ROLE from Agent
    assert not oracle_daemon_config.hasRole(config_manager_role, AGENT), "OracleDaemonConfig should not have CONFIG_MANAGER_ROLE on Agent after upgrade"

    # Step 1.18. Call V3Template.finishUpgrade
    lido = interface.Lido(LIDO)
    assert lido.getContractVersion() == NEW_LIDO_VERSION, "LIDO should have version 3 after finishUpgrade"
    assert lido.getMaxExternalRatioBP() == MAX_EXTERNAL_RATIO_BP, "LIDO should have max external ratio 3% after finishUpgrade"
    assert lido.allowance(CSM_ACCOUNTING, OLD_BURNER) == 0, "No allowance from CSM_ACCOUNTING to OLD_BURNER after finishUpgrade"
    assert lido.allowance(CSM_ACCOUNTING, BURNER) == INFINITE_ALLOWANCE, "Infinite allowance from CSM_ACCOUNTING to BURNER after finishUpgrade"
    assert lido.allowance(WITHDRAWAL_QUEUE, OLD_BURNER) == 0, "No allowance from WITHDRAWAL_QUEUE to OLD_BURNER after finishUpgrade"
    assert lido.allowance(WITHDRAWAL_QUEUE, BURNER) == INFINITE_ALLOWANCE, "Infinite allowance from WITHDRAWAL_QUEUE to BURNER after finishUpgrade"

    accounting_oracle = interface.AccountingOracle(ACCOUNTING_ORACLE)
    assert accounting_oracle.getContractVersion() == NEW_ACCOUNTING_ORACLE_VERSION, "AccountingOracle should have version 4 after finishUpgrade"
    assert accounting_oracle.getConsensusVersion() == NEW_HASH_CONSENSUS_VERSION, "HashConsensus should have version 5 after finishUpgrade"
    assert upgradeTemplate.isUpgradeFinished() == True, "V3Template should have isUpgradeFinished True after finishUpgrade"

    # Check that a second call to finishUpgrade reverts
    agent_account = accounts.at(AGENT, force=True)
    with reverts(encode_error("UpgradeAlreadyFinished()")):
        upgradeTemplate.finishUpgrade({"from": agent_account})

    # Check that after the DG proposal has passed, creation of the vaults via VaultFactory can be done
    creation_tx = interface.VaultFactory(VAULTS_FACTORY).createVaultWithDashboard(
        stranger,
        stranger,
        stranger,
        100,
        3600, # 1 hour
        [],
        {"from": stranger, "value": "1 ether"},
    )
    assert creation_tx.events.count("VaultCreated") == 1
    assert creation_tx.events.count("DashboardCreated") == 1

    # Scenario tests for Easy Track factories behavior after the vote
    trusted_address = accounts.at(ST_VAULTS_COMMITTEE, force=True)
    easy_track = interface.EasyTrack(EASYTRACK)
    test_register_groups_in_operator_grid(easy_track, trusted_address, stranger)
    test_register_tiers_in_operator_grid(easy_track, trusted_address, stranger)
    test_alter_tiers_in_operator_grid(easy_track, trusted_address, stranger)
    test_update_groups_share_limit_in_operator_grid(easy_track, trusted_address, stranger)
    test_set_jail_status_in_operator_grid(easy_track, trusted_address, stranger)
    test_update_vaults_fees_in_operator_grid(easy_track, trusted_address, stranger)
    test_force_validator_exits_in_vault_hub(easy_track, trusted_address, stranger)
    test_socialize_bad_debt_in_vault_hub(easy_track, trusted_address, stranger)


def test_register_groups_in_operator_grid(easy_track, trusted_address, stranger):
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)

    chain.snapshot()

    operator_addresses = [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
    ]
    share_limits = [1000, 5000]
    tiers_params_array = [
        [(500, 200, 100, 50, 40, 10), (800, 200, 100, 50, 40, 10)],
        [(800, 200, 100, 50, 40, 10), (800, 200, 100, 50, 40, 10)],
    ]

    calldata = _encode_calldata(
        ["address[]", "uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"],
        [operator_addresses, share_limits, tiers_params_array]
    )

    # Check initial state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == ZERO_ADDRESS  # operator
        assert group[1] == 0  # shareLimit
        assert len(group[3]) == 0  # tiersId array should be empty

    create_and_enact_motion(easy_track, trusted_address, REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == share_limits[i]  # shareLimit
        assert len(group[3]) == len(tiers_params_array[i])  # tiersId array should have the same length as tiers_params

        # Check tier details
        for j, tier_id in enumerate(group[3]):
            tier = operator_grid.tier(tier_id)
            assert tier[1] == tiers_params_array[i][j][0]  # shareLimit
            assert tier[3] == tiers_params_array[i][j][1]  # reserveRatioBP
            assert tier[4] == tiers_params_array[i][j][2]  # forcedRebalanceThresholdBP
            assert tier[5] == tiers_params_array[i][j][3]  # infraFeeBP
            assert tier[6] == tiers_params_array[i][j][4]  # liquidityFeeBP
            assert tier[7] == tiers_params_array[i][j][5]  # reservationFeeBP

    chain.revert()


def test_register_tiers_in_operator_grid(easy_track, trusted_address, stranger):
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)

    chain.snapshot()

    # Define operator addresses
    operator_addresses = [
        "0x0000000000000000000000000000000000000003",
        "0x0000000000000000000000000000000000000004"
    ]

    # Define tier parameters for each operator
    tiers_params_array = [
        [  # Tiers for operator 1
            (500, 200, 100, 50, 40, 10),
            (300, 150, 75, 25, 20, 5),
        ],
        [  # Tiers for operator 2
            (800, 250, 125, 60, 50, 15),
            (400, 180, 90, 30, 25, 8),
        ]
    ]

    # First register the groups to add tiers to
    executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
    for operator_address in operator_addresses:
        operator_grid.registerGroup(operator_address, 1000, {"from": executor})

    # Check initial state - no tiers
    for operator_address in operator_addresses:
        group = operator_grid.group(operator_address)
        assert len(group[3]) == 0  # tiersId array should be empty

    calldata = _encode_calldata(
        ["address[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"],
        [operator_addresses, tiers_params_array]
    )

    create_and_enact_motion(easy_track, trusted_address, REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state - tiers should be registered
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert len(group[3]) == len(tiers_params_array[i])  # tiersId array should have the same length as tiers_params

        # Check tier details
        for j, tier_id in enumerate(group[3]):
            tier = operator_grid.tier(tier_id)
            assert tier[1] == tiers_params_array[i][j][0]  # shareLimit
            assert tier[3] == tiers_params_array[i][j][1]  # reserveRatioBP
            assert tier[4] == tiers_params_array[i][j][2]  # forcedRebalanceThresholdBP
            assert tier[5] == tiers_params_array[i][j][3]  # infraFeeBP
            assert tier[6] == tiers_params_array[i][j][4]  # liquidityFeeBP
            assert tier[7] == tiers_params_array[i][j][5]  # reservationFeeBP

    chain.revert()


def test_alter_tiers_in_operator_grid(easy_track, trusted_address, stranger):
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)

    chain.snapshot()

    # Define new tier parameters
    # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, infraFeeBP, liquidityFeeBP, reservationFeeBP)
    new_tier_params = [(2000, 300, 150, 75, 60, 20), (3000, 400, 200, 100, 80, 30)]

    # First register a group and tier to alter
    executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
    operator_address = "0x0000000000000000000000000000000000000005"
    operator_grid.registerGroup(operator_address, 10000, {"from": executor})
    initial_tier_params = [(1000, 200, 100, 50, 40, 10), (1000, 200, 100, 50, 40, 10)]
    operator_grid.registerTiers(operator_address, initial_tier_params, {"from": executor})

    tiers_count = operator_grid.tiersCount()
    tier_ids = [tiers_count - 2, tiers_count - 1]

    # Check initial state
    for i, tier_id in enumerate(tier_ids):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == initial_tier_params[i][0]  # shareLimit
        assert tier[3] == initial_tier_params[i][1]  # reserveRatioBP
        assert tier[4] == initial_tier_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == initial_tier_params[i][3]  # infraFeeBP
        assert tier[6] == initial_tier_params[i][4]  # liquidityFeeBP
        assert tier[7] == initial_tier_params[i][5]  # reservationFeeBP

    calldata = _encode_calldata(["uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[]"], [tier_ids, new_tier_params])

    create_and_enact_motion(easy_track, trusted_address, ALTER_TIERS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state
    for i, tier_id in enumerate(tier_ids):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == new_tier_params[i][0]  # shareLimit
        assert tier[3] == new_tier_params[i][1]  # reserveRatioBP
        assert tier[4] == new_tier_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == new_tier_params[i][3]  # infraFeeBP
        assert tier[6] == new_tier_params[i][4]  # liquidityFeeBP
        assert tier[7] == new_tier_params[i][5]  # reservationFeeBP

    chain.revert()


def test_update_groups_share_limit_in_operator_grid(easy_track, trusted_address, stranger):
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)

    chain.snapshot()

    operator_addresses = ["0x0000000000000000000000000000000000000006", "0x0000000000000000000000000000000000000007"]
    new_share_limits = [2000, 3000]

    # First register the group to update
    executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
    for i, operator_address in enumerate(operator_addresses):
        operator_grid.registerGroup(operator_address, new_share_limits[i]*2, {"from": executor})

    # Check initial state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == new_share_limits[i]*2  # shareLimit

    calldata = _encode_calldata(
        ["address[]", "uint256[]"],
        [operator_addresses, new_share_limits]
    )

    create_and_enact_motion(easy_track, trusted_address, UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == new_share_limits[i] # shareLimit

    chain.revert()


def test_set_jail_status_in_operator_grid(easy_track, trusted_address, stranger):
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)

    chain.snapshot()

    # First create the vaults
    vaults = []
    for i in range(2):
        creation_tx = interface.VaultFactory(VAULTS_FACTORY).createVaultWithDashboard(
            stranger,
            stranger,
            stranger,
            100,
            3600, # 1 hour
            [],
            {"from": stranger, "value": "1 ether"},
        )
        vaults.append(creation_tx.events["VaultCreated"][0]["vault"])

    # Check initial state
    for vault in vaults:
        is_in_jail = operator_grid.isVaultInJail(vault)
        assert is_in_jail == False

    calldata = _encode_calldata(["address[]", "bool[]"], [vaults, [True, True]])

    create_and_enact_motion(easy_track, trusted_address, SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state
    for i, vault in enumerate(vaults):
        is_in_jail = operator_grid.isVaultInJail(vault)
        assert is_in_jail == True

    chain.revert()

def test_update_vaults_fees_in_operator_grid(easy_track, trusted_address, stranger):
    vault_hub = interface.VaultHub(VAULT_HUB)

    chain.snapshot()

    # First create the vault
    creation_tx = interface.VaultFactory(VAULTS_FACTORY).createVaultWithDashboard(
        stranger,
        stranger,
        stranger,
        100,
        3600, # 1 hour
        [],
        {"from": stranger, "value": "1 ether"},
    )
    vault = creation_tx.events["VaultCreated"][0]["vault"]

    # Check initial state
    connection = vault_hub.vaultConnection(vault)
    assert connection[6] != 1 # infraFeeBP
    assert connection[7] != 1 # liquidityFeeBP
    assert connection[8] == 0 # reservationFeeBP

    calldata = _encode_calldata(["address[]", "uint256[]", "uint256[]", "uint256[]"], [[vault], [1], [1], [0]])

    motions_before = easy_track.getMotions()
    tx = easy_track.createMotion(UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY, calldata, {"from": trusted_address})
    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    (
        motion_id,
        _,
        _,
        motion_duration,
        motion_start_date,
        _,
        _,
        _,
        _,
    ) = motions[-1]

    chain.mine(1, motion_start_date + motion_duration + 1)

    # bring fresh report for vault
    current_time = chain.time()
    accounting_oracle = accounts.at(ACCOUNTING_ORACLE, force=True)
    interface.LazyOracle(LAZY_ORACLE).updateReportData(
        current_time,
        1000,
        "0x00",
        "0x00",
        {"from": accounting_oracle})

    lazy_oracle = accounts.at(LAZY_ORACLE, force=True)
    vault_hub.applyVaultReport(
        vault,
        current_time,
        2 * 10**18,
        2 * 10**18,
        0,
        0,
        0,
        0,
        {"from": lazy_oracle})

    easy_track.enactMotion(
        motion_id,
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    # Check final state
    connection = vault_hub.vaultConnection(vault)
    assert connection[6] == 1 # infraFeeBP
    assert connection[7] == 1 # liquidityFeeBP
    assert connection[8] == 0 # reservationFeeBP

    chain.revert()


def test_force_validator_exits_in_vault_hub(easy_track, trusted_address, stranger):
    vault_hub = interface.VaultHub(VAULT_HUB)

    chain.snapshot()

    # top up VAULTS_ADAPTER
    stranger.transfer(VAULTS_ADAPTER, 2 * 10**18)

    pubkey = b"01" * 48
    # First create the vault
    creation_tx = interface.VaultFactory(VAULTS_FACTORY).createVaultWithDashboard(
        stranger,
        stranger,
        stranger,
        100,
        3600, # 1 hour
        [],
        {"from": stranger, "value": "1 ether"},
    )
    vault = creation_tx.events["VaultCreated"][0]["vault"]

    calldata = _encode_calldata(["address[]", "bytes[]"], [[vault], [pubkey]])

    motions_before = easy_track.getMotions()
    tx = easy_track.createMotion(FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY, calldata, {"from": trusted_address})
    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    (
        motion_id,
        _,
        _,
        motion_duration,
        motion_start_date,
        _,
        _,
        _,
        _,
    ) = motions[-1]

    chain.mine(1, motion_start_date + motion_duration + 1)

    # bring fresh report for vault
    current_time = chain.time()
    accounting_oracle = accounts.at(ACCOUNTING_ORACLE, force=True)
    interface.LazyOracle(LAZY_ORACLE).updateReportData(
        current_time,
        1000,
        "0x00",
        "0x00",
        {"from": accounting_oracle})

    # make vault unhealthy
    lazy_oracle = accounts.at(LAZY_ORACLE, force=True)
    vault_hub.applyVaultReport(
        vault,
        current_time,
        2 * 10**18,
        2 * 10**18,
        7 * 10**18,
        0,
        0,
        0,
        {"from": lazy_oracle})

    tx = easy_track.enactMotion(
        motion_id,
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    # Check event was emitted
    assert len(tx.events["ForcedValidatorExitTriggered"]) == 1
    event = tx.events["ForcedValidatorExitTriggered"][0]
    assert event["vault"] == vault
    assert event["pubkeys"] == "0x" + pubkey.hex()
    assert event["refundRecipient"] == VAULTS_ADAPTER

    chain.revert()


def test_socialize_bad_debt_in_vault_hub(easy_track, trusted_address, stranger):
    vault_hub = interface.VaultHub(VAULT_HUB)
