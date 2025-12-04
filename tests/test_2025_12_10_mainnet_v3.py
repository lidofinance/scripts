from typing import Optional
from brownie import chain, interface, web3, convert
from brownie.network.transaction import TransactionReceipt
import pytest

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events
)
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.dual_governance import PROPOSAL_STATUS, wait_for_target_time_to_satisfy_time_constrains
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event

from utils.agent import agent_forward
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.easy_track import create_permissions
from brownie.network.event import EventDict
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.proxy import validate_proxy_upgrade_event
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event


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
STETH = "0xAE7ab96520DE3A18E5e111B5EaAb095312D7fE84"
LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
NODE_OPERATORS_REGISTRY = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
SIMPLE_DVT = "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433"
ORACLE_DAEMON_CONFIG = "0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09"
CSM_ACCOUNTING = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"
OLD_BURNER = "0xD15a672319Cf0352560eE76d9e89eAB0889046D3"
LIDO_APP_ID = "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320"

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

ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0xa29173C7BCf39dA48D5E404146A652d7464aee14"
REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0x194A46DA1947E98c9D79af13E06Cfbee0D8610cC"
REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0x5292A1284e4695B95C0840CF8ea25A818751C17F"
SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x93F1DEE4473Ee9F42c8257C201e33a6Da30E5d67"
SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0x1dF50522A1D868C12bF71747Bb6F24A18Fe6d32C"
FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6C968cD89CA358fbAf57B18e77a8973Fa869a6aA"
UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0x8Bdc726a3147D8187820391D7c6F9F942606aEe6"
UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0x5C3bDFa3E7f312d8cf72F56F2b797b026f6B471c"

NEW_LIDO_VERSION = 3
NEW_ACCOUNTING_ORACLE_VERSION = 4

UTC14 = 60 * 60 * 14
UTC23 = 60 * 60 * 23
SLASHING_RESERVE_SHIFT = 8192


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

def validate_aragon_grant_permission_event(
    event,
    entity: str,
    app: str,
    role: str,
    emitted_by: str,
) -> None:
    """
    Validate Aragon ACL SetPermission event for granting permission via DG proposal.
    Ensures only expected events are fired and all parameters are correct.
    """
    _events_chain = ["LogScriptCall", "SetPermission", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {event.count('LogScriptCall')}"
    assert event.count("SetPermission") == 1, f"Expected 1 SetPermission, got {event.count('SetPermission')}"
    assert event.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {event.count('ScriptResult')}"
    assert event.count("Executed") == 1, f"Expected 1 Executed, got {event.count('Executed')}"

    assert event["SetPermission"]["allowed"] is True, "Permission should be granted (allowed=True)"
    assert event["SetPermission"]["entity"] == entity, f"Wrong entity: expected {entity}, got {event['SetPermission']['entity']}"
    assert event["SetPermission"]["app"] == app, f"Wrong app: expected {app}, got {event['SetPermission']['app']}"
    assert event["SetPermission"]["role"] == role, f"Wrong role: expected {role}, got {event['SetPermission']['role']}"

    assert convert.to_address(event["SetPermission"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}"


def validate_aragon_revoke_permission_event(
    event,
    entity: str,
    app: str,
    role: str,
    emitted_by: str,
) -> None:
    """
    Validate Aragon ACL SetPermission event for revoking permission via DG proposal.
    Ensures only expected events are fired and all parameters are correct.
    """
    _events_chain = ["LogScriptCall", "SetPermission", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {event.count('LogScriptCall')}"
    assert event.count("SetPermission") == 1, f"Expected 1 SetPermission, got {event.count('SetPermission')}"
    assert event.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {event.count('ScriptResult')}"
    assert event.count("Executed") == 1, f"Expected 1 Executed, got {event.count('Executed')}"

    assert event["SetPermission"]["allowed"] is False, "Permission should be revoked (allowed=False)"
    assert event["SetPermission"]["entity"] == entity, f"Wrong entity: expected {entity}, got {event['SetPermission']['entity']}"
    assert event["SetPermission"]["app"] == app, f"Wrong app: expected {app}, got {event['SetPermission']['app']}"
    assert event["SetPermission"]["role"] == role, f"Wrong role: expected {role}, got {event['SetPermission']['role']}"

    assert convert.to_address(event["SetPermission"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}"


def validate_set_app_event(
    event,
    app_id: str,
    app: str,
    emitted_by: str,
) -> None:
    """
    Validate Aragon Kernel SetApp event via DG proposal.
    Ensures only expected events are fired and all parameters are correct.
    """
    _events_chain = ["LogScriptCall", "SetApp", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {event.count('LogScriptCall')}"
    assert event.count("SetApp") == 1, f"Expected 1 SetApp, got {event.count('SetApp')}"
    assert event.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {event.count('ScriptResult')}"
    assert event.count("Executed") == 1, f"Expected 1 Executed, got {event.count('Executed')}"

    assert event["SetApp"]["appId"] == app_id, f"Wrong appId: expected {app_id}, got {event['SetApp']['appId']}"
    assert event["SetApp"]["app"] == app, f"Wrong app: expected {app}, got {event['SetApp']['app']}"

    assert convert.to_address(event["SetApp"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}"


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


def validate_upgrade_finished_event(events) -> None:
    """
    Validate V3Template UpgradeFinished event via DG proposal.
    Ensures only expected events are fired.
    """
    _events_chain = ["LogScriptCall", "ContractVersionSet", "Approval", "Approval", "Approval", "Approval",
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

    assert convert.to_address(events["UpgradeFinished"][0]["_emitted_by"]) == convert.to_address(
        UPGRADE_TEMPLATE
    ), f"Wrong event emitter: expected {UPGRADE_TEMPLATE}"


# ============================================================================
# ============================== Test functions ==============================
# ============================================================================

@pytest.fixture(scope="module")
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
                revoke_from=STETH # Lido
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
                revoke_from=STETH # Lido
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
    dual_governance_proposal_calls,
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
                metadata="TODO DG proposal description",
                proposal_calls=dual_governance_proposal_calls,
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

        # Step 1.3: Check Lido Locator implementation initial state
        assert locator_impl_before != LIDO_LOCATOR_IMPL, "Locator implementation should be different before upgrade"

        # Step 1.4. Grant Aragon APP_MANAGER_ROLE to the AGENT
        assert not acl.hasPermission(AGENT, ARAGON_KERNEL, app_manager_role), "AGENT should not have APP_MANAGER_ROLE before upgrade"

        # Step 1.5. Set Lido implementation in Kernel
        assert not kernel.getApp(kernel.APP_BASES_NAMESPACE(), LIDO_APP_ID) == LIDO_IMPL, "Lido implementation should be different before upgrade"

        # Step 1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido
        assert old_burner.hasRole(request_burn_shares_role, STETH), "Old Burner should have REQUEST_BURN_SHARES_ROLE on Lido before upgrade"

        # Step 1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking module
        assert old_burner.hasRole(request_burn_shares_role, NODE_OPERATORS_REGISTRY), "Old Burner should have REQUEST_BURN_SHARES_ROLE on Curated staking module before upgrade"

        # Step 1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
        assert old_burner.hasRole(request_burn_shares_role, SIMPLE_DVT), "Old Burner should have REQUEST_BURN_SHARES_ROLE on SimpleDVT before upgrade"

        # Step 1.10. Revoke REQUEST_BURN_SHARES_ROLE from Community Staking Accounting
        assert old_burner.hasRole(request_burn_shares_role, CSM_ACCOUNTING), "Old Burner should have REQUEST_BURN_SHARES_ROLE on Community Staking Accounting before upgrade"

        # Step 1.11: Check Accounting Oracle implementation initial state
        assert accounting_oracle_impl_before != ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be different before upgrade"

        # Step 1.12. Revoke REPORT_REWARDS_MINTED_ROLE from Lido
        assert staking_router.hasRole(report_rewards_minted_role, STETH), "Staking Router should have REPORT_REWARDS_MINTED_ROLE on Lido before upgrade"

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
            validate_set_app_event(
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
                revoke_from=STETH,
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
                revoke_from=STETH,
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
            validate_upgrade_finished_event(dg_events[17])

    # =========================================================================
    # ==================== After DG proposal executed checks ==================
    # =========================================================================

    # Step 1.3: Validate Lido Locator implementation was updated
    assert get_ossifiable_proxy_impl(lido_locator_proxy) == LIDO_LOCATOR_IMPL, "Locator implementation should be updated to the new value"

    # Step 1.5. Set Lido implementation in Kernel
    assert kernel.getApp(kernel.APP_BASES_NAMESPACE(), LIDO_APP_ID) == LIDO_IMPL, "Lido implementation should be updated to the new value"

    # Step 1.6. Revoke Aragon APP_MANAGER_ROLE from the AGENT
    assert not acl.hasPermission(AGENT, ARAGON_KERNEL, app_manager_role), "AGENT should not have APP_MANAGER_ROLE after upgrade"

    # Step 1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido
    assert not old_burner.hasRole(request_burn_shares_role, STETH), "Old Burner should not have REQUEST_BURN_SHARES_ROLE on Lido after upgrade"

    # Step 1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking module
    assert not old_burner.hasRole(request_burn_shares_role, NODE_OPERATORS_REGISTRY), "Old Burner should not have REQUEST_BURN_SHARES_ROLE on Curated staking module after upgrade"

    # Step 1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
    assert not old_burner.hasRole(request_burn_shares_role, SIMPLE_DVT), "Old Burner should not have REQUEST_BURN_SHARES_ROLE on SimpleDVT after upgrade"

    # Step 1.10. Revoke REQUEST_BURN_SHARES_ROLE from Community Staking Accounting
    assert not old_burner.hasRole(request_burn_shares_role, CSM_ACCOUNTING), "Old Burner should not have REQUEST_BURN_SHARES_ROLE on Community Staking Accounting after upgrade"

    # Step 1.11: Validate Accounting Oracle implementation was updated
    assert get_ossifiable_proxy_impl(accounting_oracle_proxy) == ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be updated to the new value"

    # Step 1.12. Revoke REPORT_REWARDS_MINTED_ROLE from Lido
    assert not staking_router.hasRole(report_rewards_minted_role, STETH), "Staking Router should not have REPORT_REWARDS_MINTED_ROLE on Lido after upgrade"

    # Step 1.13. Grant REPORT_REWARDS_MINTED_ROLE to Accounting
    assert staking_router.hasRole(report_rewards_minted_role, ACCOUNTING), "Staking Router should have REPORT_REWARDS_MINTED_ROLE on Accounting after upgrade"

    # Step 1.15. Set SLASHING_RESERVE_WE_RIGHT_SHIFT to 0x2000 at OracleDaemonConfig
    assert convert.to_uint(oracle_daemon_config.get("SLASHING_RESERVE_WE_RIGHT_SHIFT")) == SLASHING_RESERVE_SHIFT, "OracleDaemonConfig should have SLASHING_RESERVE_WE_RIGHT_SHIFT set to 0x2000 after upgrade"

    # Step 1.16. Set SLASHING_RESERVE_WE_LEFT_SHIFT to 0x2000 at OracleDaemonConfig
    assert convert.to_uint(oracle_daemon_config.get("SLASHING_RESERVE_WE_LEFT_SHIFT")) == SLASHING_RESERVE_SHIFT, "OracleDaemonConfig should have SLASHING_RESERVE_WE_LEFT_SHIFT set to 0x2000 after upgrade"

    # Step 1.17. Revoke OracleDaemonConfig's CONFIG_MANAGER_ROLE from Agent
    assert not oracle_daemon_config.hasRole(config_manager_role, AGENT), "OracleDaemonConfig should not have CONFIG_MANAGER_ROLE on Agent after upgrade"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):
    EXPECTED_VOTE_ID = 194
    EXPECTED_DG_PROPOSAL_ID = 6

    enact_and_test_voting(
        helpers,
        accounts,
        ldo_holder,
        vote_ids_from_env,
        dual_governance_proposal_calls,
        expected_vote_id=EXPECTED_VOTE_ID,
        expected_dg_proposal_id=EXPECTED_DG_PROPOSAL_ID,
    )

    enact_and_test_dg(
        stranger,
        expected_dg_proposal_id=EXPECTED_DG_PROPOSAL_ID,
    )
