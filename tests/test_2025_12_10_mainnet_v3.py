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

# New Lido V3 addresses - TODO fix after mainnet deployment
VAULT_HUB = "0xdcC04F506E24495E9F2599A7b214522647363669"
ACCOUNTING = "0xc9158c756D2a510eaC85792C847798a30dE20D46"
ACCOUNTING_IMPL = "0x1bE2Ee7D32e3F9C4ecd5b6BfF69306ACb8Ab239e"
OPERATOR_GRID = "0x79e2685C1DD4756AC709a6CeE7C6cC960128B031"
LAZY_ORACLE = "0x4fA3c917BB8f8CD9d056C5DDF0a38bd1834c43F9"
PREDEPOSIT_GUARANTEE = "0x7B49b203A100E326B84886dCC0e2c426f9b8cbBd"
VAULTS_ADAPTER = "0x8cDA09f41970A8f4416b6bA4696a2f09a6080c76"
GATE_SEAL_V3 = "0x9c2D30177DB12334998EB554f5d4E6dD44458167"
LIDO_IMPL = "0xD0b9826e0EAf6dE91CE7A6783Cd6fd137ae422Ec"
UPGRADE_TEMPLATE = "0x2AE2847a77a1d24100be2163AfdC49B06DC808E4"
LIDO_LOCATOR_IMPL = "0x26329a3D4cF2F89923b5c4C14a25A2485cD01aA2"
ACCOUNTING_ORACLE_IMPL = "0xb2295820F5286BE40c2da8102eB2cDB24aD608Be"
RESEAL_MANAGER = "0x7914b5a1539b97Bd0bbd155757F25FD79A522d24"
BURNER = "0xD140f4f3C515E1a328F6804C5426d9e8b883ED50"

ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0x25AB9D07356E8a3F95a5905f597c93CD8F31990b"
REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0x9Ba3E4aDDe415943A831b97F9f7B8b842052b709"
REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0x663cE8Aa1ded537Dc319529e71DE6BAb2E7D0747"
SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x88D32aABa5B6A972D82E55D26B212eBeca07C983"
SET_LIABILITY_SHARES_TARGET_IN_VAULT_HUB_FACTORY = "0xf61601787E84d89c30911e5A48d9CA630eC47044"
SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0xD60671a489948641954736A0e7272137b3A335CE"
FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6D0F542591eF4f8ebA8c77a11dc3676D9E9F7e66"
UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0xAEDB8D15197984D39152A2814e0BdCDAEED5462d"
UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0x7DCf0746ff2F77A36ceC8E318b59dc8a8A5c066e"

UTC14 = 60 * 60 * 14
UTC23 = 60 * 60 * 23
SLASHING_RESERVE_SHIFT = 8192

EXPECTED_VOTE_ID = 194
EXPECTED_DG_PROPOSAL_ID = 6
EXPECTED_VOTE_EVENTS_COUNT = 10
EXPECTED_DG_EVENTS_FROM_AGENT = 17
EXPECTED_DG_EVENTS_COUNT = 18
IPFS_DESCRIPTION_HASH = "bafkreic4xuaowfowt7faxnngnzynv7biuo7guv4s4jrngngjzzxyz3up2i"


# ============================================================================
# ============================== Helper functions ============================
# ============================================================================

def validate_proxy_upgrade_event(event: EventDict, implementation: str, emitted_by: Optional[str] = None, events_chain: Optional[list] = None):
    _events_chain = events_chain or ["LogScriptCall", "Upgraded", "ScriptResult", "Executed"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("Upgraded") == 1

    assert "Upgraded" in event, "No Upgraded event found"

    assert event["Upgraded"][0]["implementation"] == implementation, "Wrong implementation address"

    if emitted_by is not None:
        assert convert.to_address(event["Upgraded"][0]["_emitted_by"]) == convert.to_address(
            emitted_by), "Wrong event emitter"


def validate_role_grant_event(event: EventDict, role_hash: str, account: str, emitted_by: Optional[str] = None):
    _events_chain = ["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("RoleGranted") == 1

    assert "RoleGranted" in event, "No RoleGranted event found"

    # Strip 0x prefix for consistent comparison
    expected_role_hash = role_hash.replace('0x', '')
    actual_role_hash = event["RoleGranted"][0]["role"].hex().replace('0x', '')

    assert actual_role_hash == expected_role_hash, "Wrong role hash"

    assert convert.to_address(event["RoleGranted"][0]["account"]) == convert.to_address(account), "Wrong account"

    if emitted_by is not None:
        assert convert.to_address(event["RoleGranted"][0]["_emitted_by"]) == convert.to_address(
            emitted_by), "Wrong event emitter"


def validate_role_revoke_event(event: EventDict, role_hash: str, account: str, emitted_by: Optional[str] = None):
    _events_chain = ["LogScriptCall", "RoleRevoked", "ScriptResult", "Executed"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("RoleRevoked") == 1

    assert "RoleRevoked" in event, "No RoleRevoked event found"

    # Strip 0x prefix for consistent comparison
    expected_role_hash = role_hash.replace('0x', '')
    actual_role_hash = event["RoleRevoked"][0]["role"].hex().replace('0x', '')

    assert actual_role_hash == expected_role_hash, "Wrong role hash"

    assert convert.to_address(event["RoleRevoked"][0]["account"]) == convert.to_address(account), "Wrong account"

    if emitted_by is not None:
        assert convert.to_address(event["RoleRevoked"][0]["_emitted_by"]) == convert.to_address(
            emitted_by), "Wrong event emitter"


def get_ossifiable_proxy_impl(proxy_address):
    """Get implementation address from an OssifiableProxy"""
    proxy = interface.OssifiableProxy(proxy_address)
    return proxy.proxy__getImplementation()


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


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    easy_track = interface.EasyTrack(EASYTRACK)
    kernel = interface.Kernel(ARAGON_KERNEL)
    acl = interface.ACL(ACL)

    vault_hub = interface.VaultHub(VAULT_HUB)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    predeposit_guarantee = interface.PredepositGuarantee(PREDEPOSIT_GUARANTEE)
    burner = interface.Burner(BURNER)

    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    accounting_oracle_proxy = interface.OssifiableProxy(ACCOUNTING_ORACLE)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    old_burner = interface.Burner(OLD_BURNER)
    oracle_daemon_config = interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)

    # Save original implementations for comparison
    locator_impl_before = get_ossifiable_proxy_impl(LIDO_LOCATOR)
    accounting_oracle_impl_before = get_ossifiable_proxy_impl(ACCOUNTING_ORACLE)

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
    assert onchain_script == encode_call_script(call_script_items)


    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        # Steps 2-10: Add EasyTrack factories
        initial_factories = easy_track.getEVMScriptFactories()
        assert ALTER_TIERS_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY not in initial_factories, "EasyTrack should not have SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert SET_LIABILITY_SHARES_TARGET_IN_VAULT_HUB_FACTORY not in initial_factories, "EasyTrack should not have SET_LIABILITY_SHARES_TARGET_IN_VAULT_HUB_FACTORY factory before vote"
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

        # Deployment state checks:
        # Check Predeposit Guarantee roles
        pause_role = web3.keccak(text="PausableUntilWithRoles.PauseRole")
        resume_role = web3.keccak(text="PausableUntilWithRoles.ResumeRole")
        assert predeposit_guarantee.hasRole(pause_role, GATE_SEAL_V3), "Predeposit Guarantee should have PAUSE_ROLE on GATE_SEAL_V3 after upgrade"
        assert predeposit_guarantee.hasRole(pause_role, RESEAL_MANAGER), "Predeposit Guarantee should have PAUSE_ROLE on RESEAL_MANAGER after upgrade"
        assert predeposit_guarantee.hasRole(resume_role, RESEAL_MANAGER), "Predeposit Guarantee should have RESUME_ROLE on RESEAL_MANAGER after upgrade"
        assert predeposit_guarantee.hasRole(DEFAULT_ADMIN_ROLE, AGENT), "Predeposit Guarantee should have DEFAULT_ADMIN_ROLE on AGENT after upgrade"
        # Check Operator Grid roles
        registry_role = web3.keccak(text="vaults.OperatorsGrid.Registry")
        assert operator_grid.hasRole(registry_role, VAULTS_ADAPTER), "Operator Grid should have REGISTRY_ROLE on VAULTS_ADAPTER after upgrade"
        assert operator_grid.hasRole(registry_role, EASYTRACK_EVMSCRIPT_EXECUTOR), "Operator Grid should have REGISTRY_ROLE on EASYTRACK_EVMSCRIPT_EXECUTOR after upgrade"
        assert operator_grid.hasRole(DEFAULT_ADMIN_ROLE, AGENT), "Operator Grid should have DEFAULT_ADMIN_ROLE on AGENT after upgrade"
        # Check Burner roles
        request_burn_shares_role = web3.keccak(text="REQUEST_BURN_SHARES_ROLE")
        assert burner.hasRole(request_burn_shares_role, ACCOUNTING), "Burner should have REQUEST_BURN_SHARES_ROLE on ACCOUNTING after upgrade"
        assert burner.hasRole(request_burn_shares_role, CSM_ACCOUNTING), "Burner should have REQUEST_BURN_SHARES_ROLE on CSM_ACCOUNTING after upgrade"
        assert burner.hasRole(DEFAULT_ADMIN_ROLE, AGENT), "Burner should have DEFAULT_ADMIN_ROLE on AGENT after upgrade"
        # Check Vault Hub roles
        assert vault_hub.hasRole(pause_role, GATE_SEAL_V3), "Vault Hub should have PAUSE_ROLE on GATE_SEAL_V3 after upgrade"
        assert vault_hub.hasRole(pause_role, RESEAL_MANAGER), "Vault Hub should have PAUSE_ROLE on RESEAL_MANAGER after upgrade"
        assert vault_hub.hasRole(resume_role, RESEAL_MANAGER), "Vault Hub should have RESUME_ROLE on RESEAL_MANAGER after upgrade"
        validator_exit_role = web3.keccak(text="vaults.VaultHub.ValidatorExitRole")
        assert vault_hub.hasRole(validator_exit_role, VAULTS_ADAPTER), "Vault Hub should have VALIDATOR_EXIT_ROLE on VAULTS_ADAPTER after upgrade"
        bad_debt_master_role = web3.keccak(text="vaults.VaultHub.BadDebtMasterRole")
        assert vault_hub.hasRole(bad_debt_master_role, VAULTS_ADAPTER), "Vault Hub should have BAD_DEBT_MASTER_ROLE on VAULTS_ADAPTER after upgrade"
        assert vault_hub.hasRole(DEFAULT_ADMIN_ROLE, AGENT), "Vault Hub` should have DEFAULT_ADMIN_ROLE on AGENT after upgrade"

        # Steps 2-10: Add EasyTrack factories
        new_factories = easy_track.getEVMScriptFactories()
        assert ALTER_TIERS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert SET_LIABILITY_SHARES_TARGET_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have SET_LIABILITY_SHARES_TARGET_IN_VAULT_HUB_FACTORY factory after vote"
        assert SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY factory after vote"
        assert FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY factory after vote"
        assert UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY factory after vote"

        vote_events = group_voting_events_from_receipt(vote_tx)
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata="TODO DG proposal description",
                proposal_calls=dual_governance_proposal_calls,
                emitted_by=[EMERGENCY_PROTECTED_TIMELOCK, DUAL_GOVERNANCE],
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
                    factory_addr=SET_LIABILITY_SHARES_TARGET_IN_VAULT_HUB_FACTORY,
                    permissions=create_permissions(interface.IVaultsAdapter(VAULTS_ADAPTER), "setLiabilitySharesTarget")
                ),
                emitted_by=easy_track,
            )

            validate_evmscript_factory_added_event(
                event=vote_events[9],
                p=EVMScriptFactoryAdded(
                    factory_addr=SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY,
                    permissions=create_permissions(interface.IVaultsAdapter(VAULTS_ADAPTER), "socializeBadDebt")
                ),
                emitted_by=easy_track,
            )


    if EXPECTED_DG_PROPOSAL_ID is not None:
        report_rewards_minted_role = web3.keccak(text="REPORT_REWARDS_MINTED_ROLE")
        request_burn_shares_role = web3.keccak(text="REQUEST_BURN_SHARES_ROLE")
        config_manager_role = web3.keccak(text="CONFIG_MANAGER_ROLE")
        app_manager_role = web3.keccak(text="APP_MANAGER_ROLE")

        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
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
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)

                wait_for_target_time_to_satisfy_time_constrains()

                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

                # === DG EXECUTION EVENTS VALIDATION ===

                # 1.3. Lido Locator upgrade events
                validate_proxy_upgrade_event(dg_events[2], LIDO_LOCATOR_IMPL, emitted_by=lido_locator_proxy)

                # 1.4. Grant Aragon APP_MANAGER_ROLE to the AGENT
                assert 'SetPermission' in dg_events[3]
                assert dg_events[3]['SetPermission'][0]['allowed'] is True
                assert dg_events[3]['SetPermission'][0]['_emitted_by'] == ACL
                assert dg_events[3]['SetPermission'][0]['entity'] == AGENT
                assert dg_events[3]['SetPermission'][0]['role'] == app_manager_role.hex()

                # 1.5. Set Lido implementation in Kernel
                assert 'SetApp' in dg_events[4]
                assert dg_events[4]['SetApp'][0]['appId'] == LIDO_APP_ID
                assert dg_events[4]['SetApp'][0]['_emitted_by'] == ARAGON_KERNEL
                assert dg_events[4]['SetApp'][0]['app'] == LIDO_IMPL

                # 1.6. Revoke Aragon APP_MANAGER_ROLE from the AGENT
                assert 'SetPermission' in dg_events[5]
                assert dg_events[5]['SetPermission'][0]['allowed'] is False
                assert dg_events[5]['SetPermission'][0]['_emitted_by'] == ACL
                assert dg_events[5]['SetPermission'][0]['entity'] == AGENT
                assert dg_events[5]['SetPermission'][0]['role'] == app_manager_role.hex()

                # 1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido
                validate_role_revoke_event(
                    dg_events[6],
                    role_hash=request_burn_shares_role.hex(),
                    account=STETH,
                    emitted_by=old_burner
                )

                # 1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking module
                validate_role_revoke_event(
                    dg_events[7],
                    role_hash=request_burn_shares_role.hex(),
                    account=NODE_OPERATORS_REGISTRY,
                    emitted_by=old_burner
                )

                # 1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
                validate_role_revoke_event(
                    dg_events[8],
                    role_hash=request_burn_shares_role.hex(),
                    account=SIMPLE_DVT,
                    emitted_by=old_burner
                )

                # 1.10. Revoke REQUEST_BURN_SHARES_ROLE from Community Staking Accounting
                validate_role_revoke_event(
                    dg_events[9],
                    role_hash=request_burn_shares_role.hex(),
                    account=CSM_ACCOUNTING,
                    emitted_by=old_burner
                )

                # 1.11. Accounting Oracle upgrade events
                validate_proxy_upgrade_event(dg_events[10], ACCOUNTING_ORACLE_IMPL, emitted_by=accounting_oracle_proxy)

                # 1.12. Revoke Staking Router REPORT_REWARDS_MINTED_ROLE from the Lido
                validate_role_revoke_event(
                    dg_events[11],
                    role_hash=report_rewards_minted_role.hex(),
                    account=STETH,
                    emitted_by=staking_router
                )

                # 1.13. Grant Staking Router REPORT_REWARDS_MINTED_ROLE to Accounting
                validate_role_grant_event(
                    dg_events[12],
                    role_hash=report_rewards_minted_role.hex(),
                    account=ACCOUNTING,
                    emitted_by=staking_router
                )

                # 1.14. Grant OracleDaemonConfig's CONFIG_MANAGER_ROLE to Agent
                validate_role_grant_event(
                    dg_events[13],
                    role_hash=config_manager_role.hex(),
                    account=AGENT,
                    emitted_by=oracle_daemon_config
                )

                # 1.15. Set SLASHING_RESERVE_WE_RIGHT_SHIFT to 0x2000 at OracleDaemonConfig
                assert 'ConfigValueSet' in dg_events[14]
                assert 'SLASHING_RESERVE_WE_RIGHT_SHIFT' in dg_events[14]['ConfigValueSet'][0]['key']
                assert convert.to_int(dg_events[14]['ConfigValueSet'][0]['value']) == SLASHING_RESERVE_SHIFT

                # 1.16. Set SLASHING_RESERVE_WE_LEFT_SHIFT to 0x2000 at OracleDaemonConfig
                assert 'ConfigValueSet' in dg_events[15]
                assert 'SLASHING_RESERVE_WE_LEFT_SHIFT' in dg_events[15]['ConfigValueSet'][0]['key']
                assert convert.to_int(dg_events[15]['ConfigValueSet'][0]['value']) == SLASHING_RESERVE_SHIFT

                # 1.17. Revoke OracleDaemonConfig's CONFIG_MANAGER_ROLE from Agent
                validate_role_revoke_event(
                    dg_events[16],
                    role_hash=config_manager_role.hex(),
                    account=AGENT,
                    emitted_by=oracle_daemon_config
                )


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
