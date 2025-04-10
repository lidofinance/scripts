import pytest
import os

from typing import NamedTuple, List
from brownie import web3, chain, interface, ZERO_ADDRESS, accounts
from hexbytes import HexBytes
from scripts.dual_governance_upgrade import start_vote
from utils.config import contracts
from brownie.network.transaction import TransactionReceipt
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import (
    validate_dual_governance_submit_event,
    dg_events_from_trace,
)
from utils.agent import agent_forward
from utils.test.event_validators.time_constraints import (
    validate_time_constraints_executed_before_event,
    validate_dg_time_constraints_executed_before_event,
    validate_dg_time_constraints_executed_with_day_time_event,
)

from utils.test.event_validators.permission import (
    validate_permission_create_event,
    validate_permission_revoke_event,
    validate_change_permission_manager_event,
    Permission,
    validate_permission_grant_event,
    validate_grant_role_event,
    validate_revoke_role_event,
    validate_dg_permission_revoke_event,
)

from utils.test.event_validators.proxy import validate_proxy_admin_changed

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

DUAL_GOVERNANCE = "0x490bf377734CA134A8E207525E8576745652212e"
TIMELOCK = "0xe9c5FfEAd0668AFdBB9aac16163840d649DB76DD"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x8BD0a916faDa88Ba3accb595a3Acd28F467130e8"
RESEAL_MANAGER = "0x9dE2273f9f1e81145171CcA927EFeE7aCC64c9fb"
DAO_EMERGENCY_GOVERNANCE = "0x46c6C7E1Cc438456d658Eed61A764a475abDa0C1"
AGENT_MANAGER = "0xc807d4036B400dE8f6cD2aDbd8d9cf9a3a01CC30"
TIME_CONSTRAINTS = "0x4D36598EA14bd70a1040CF59ABF6f9439afBf5d9"
ROLES_VALIDATOR = "0xf532fC0a18D3339A52b3f1152FcA9925De5855AA"

ACL = "0xfd1E42595CeC3E83239bf8dFc535250e7F48E0bC"
LIDO = "0x3F1c547b21f65e10480dE3ad8E19fAAC46C95034"
KERNEL = "0x3b03f75Ec541Ca11a223bB58621A3146246E1644"
VOTING = "0xdA7d2573Df555002503F29aA4003e398d28cc00f"
TOKEN_MANAGER = "0xFaa1692c6eea8eeF534e7819749aD93a1420379A"
FINANCE = "0xf0F281E5d7FBc54EAFcE0dA225CDbde04173AB16"
AGENT = "0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d"
EVM_SCRIPT_REGISTRY = "0xE1200ae048163B67D69Bc0492bF5FddC3a2899C0"
CURATED_MODULE = "0x595F64Ddc3856a3b5Ff4f4CC1d1fb4B46cFd2bAC"
SDVT_MODULE = "0x11a93807078f8BB880c1BD0ee4C387537de4b4b6"
ALLOWED_TOKENS_REGISTRY = "0x091C0eC8B4D54a9fcB36269B5D5E5AF43309e666"
WITHDRAWAL_VAULT = "0xF0179dEC45a37423EAD4FaD5fCb136197872EAd9"
WITHDRAWAL_QUEUE = "0xc7cc160b58F8Bb0baC94b80847E2CF2800565C50"
VEBO = "0xffDDF7025410412deaa05E3E1cE68FE53208afcb"


@pytest.fixture(scope="function", autouse=True)
def prepare_activated_dg_state():
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    if os.getenv("SKIP_DG_DRY_RUN") and timelock.getEmergencyGovernance() != DAO_EMERGENCY_GOVERNANCE:
        dg_impersonated = accounts.at(DUAL_GOVERNANCE, force=True)
        timelock.submit(
            DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            [(TIMELOCK, 0, timelock.setEmergencyGovernance.encode_input(DAO_EMERGENCY_GOVERNANCE))],
            {"from": dg_impersonated},
        )

        after_submit_delay = timelock.getAfterSubmitDelay()
        chain.sleep(after_submit_delay + 1)

        timelock.schedule(1, {"from": dg_impersonated})

        after_schedule_delay = timelock.getAfterScheduleDelay()
        chain.sleep(after_schedule_delay + 1)

        timelock.execute(1, {"from": dg_impersonated})

        assert timelock.getEmergencyGovernance() == DAO_EMERGENCY_GOVERNANCE
        assert timelock.getProposalsCount() == 1


class ValidatedRole(NamedTuple):
    entity: str
    roleName: str


def validate_role_validated_event(event: EventDict, roles: List[ValidatedRole]) -> None:
    _events_chain = ["LogScriptCall"]
    _events_chain += ["RoleValidated"] * len(roles)

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, "Wrong number of LogScriptCall events"
    assert event.count("RoleValidated") == len(roles), "Wrong number of RoleValidated events"

    for i in range(len(roles)):
        role = roles[i].roleName
        account = roles[i].entity

        assert event["RoleValidated"][i]["entity"] == account, "Wrong account"
        assert event["RoleValidated"][i]["roleName"] == role, "Wrong role"


def validate_dg_role_validated_event(event: EventDict, roles: List[ValidatedRole]) -> None:
    _events_chain = ["LogScriptCall"]
    _events_chain += ["RoleValidated"] * len(roles)
    _events_chain += ["ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("RoleValidated") == len(roles), "Wrong number of RoleValidated events"
    assert event.count("ScriptResult") == 1
    assert event.count("Executed") == 1

    for i in range(len(roles)):
        role = roles[i].roleName
        account = roles[i].entity

        assert event["RoleValidated"][i]["entity"] == account, "Wrong account"
        assert event["RoleValidated"][i]["roleName"] == role, "Wrong role"


def validate_dual_governance_governance_launch_verification_event(event: EventDict):
    _events_chain = ["LogScriptCall", "DGLaunchConfigurationValidated"]

    validate_events_chain([e.name for e in event], _events_chain)


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding, stranger):
    acl = interface.ACL(ACL)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)

    # Lido Permissions Transition
    STAKING_CONTROL_ROLE = web3.keccak(text="STAKING_CONTROL_ROLE")
    assert acl.hasPermission(VOTING, LIDO, STAKING_CONTROL_ROLE)
    assert not acl.hasPermission(AGENT, LIDO, STAKING_CONTROL_ROLE)
    assert acl.getPermissionManager(LIDO, STAKING_CONTROL_ROLE) == VOTING

    RESUME_ROLE = web3.keccak(text="RESUME_ROLE")
    assert acl.hasPermission(VOTING, LIDO, RESUME_ROLE)
    assert not acl.hasPermission(AGENT, LIDO, RESUME_ROLE)
    assert acl.getPermissionManager(LIDO, RESUME_ROLE) == VOTING

    PAUSE_ROLE = web3.keccak(text="PAUSE_ROLE")
    assert acl.hasPermission(VOTING, LIDO, PAUSE_ROLE)
    assert not acl.hasPermission(AGENT, LIDO, PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, PAUSE_ROLE) == VOTING

    UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE = web3.keccak(text="UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE")
    assert acl.hasPermission(VOTING, LIDO, UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE)
    assert not acl.hasPermission(AGENT, LIDO, UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE)
    assert acl.getPermissionManager(LIDO, UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE) == VOTING

    STAKING_PAUSE_ROLE = web3.keccak(text="STAKING_PAUSE_ROLE")
    assert acl.hasPermission(VOTING, LIDO, STAKING_PAUSE_ROLE)
    assert not acl.hasPermission(AGENT, LIDO, STAKING_PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, STAKING_PAUSE_ROLE) == VOTING

    # DAOKernel Permissions Transition
    APP_MANAGER_ROLE = web3.keccak(text="APP_MANAGER_ROLE")
    assert acl.hasPermission(VOTING, KERNEL, APP_MANAGER_ROLE)
    assert not acl.hasPermission(AGENT, KERNEL, APP_MANAGER_ROLE)
    assert acl.getPermissionManager(KERNEL, APP_MANAGER_ROLE) == VOTING

    # TokenManager Permissions Transition
    MINT_ROLE = web3.keccak(text="MINT_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, MINT_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, MINT_ROLE) == ZERO_ADDRESS

    REVOKE_VESTINGS_ROLE = web3.keccak(text="REVOKE_VESTINGS_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, REVOKE_VESTINGS_ROLE) == ZERO_ADDRESS

    BURN_ROLE = web3.keccak(text="BURN_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, BURN_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, BURN_ROLE) == ZERO_ADDRESS

    ISSUE_ROLE = web3.keccak(text="ISSUE_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, ISSUE_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, ISSUE_ROLE) == ZERO_ADDRESS

    # Finance Permissions Transition
    CHANGE_PERIOD_ROLE = web3.keccak(text="CHANGE_PERIOD_ROLE")
    assert not acl.hasPermission(VOTING, FINANCE, CHANGE_PERIOD_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_PERIOD_ROLE) == ZERO_ADDRESS

    CHANGE_BUDGETS_ROLE = web3.keccak(text="CHANGE_BUDGETS_ROLE")
    assert not acl.hasPermission(VOTING, FINANCE, CHANGE_BUDGETS_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_BUDGETS_ROLE) == ZERO_ADDRESS

    # EVMScriptRegistry Permissions Transition
    REGISTRY_MANAGER_ROLE = web3.keccak(text="REGISTRY_MANAGER_ROLE")
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE) == VOTING

    REGISTRY_ADD_EXECUTOR_ROLE = web3.keccak(text="REGISTRY_ADD_EXECUTOR_ROLE")
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE) == VOTING

    # CuratedModule Permissions Transition
    STAKING_ROUTER_ROLE = web3.keccak(text="STAKING_ROUTER_ROLE")
    assert not acl.hasPermission(AGENT, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, STAKING_ROUTER_ROLE) == VOTING

    MANAGE_NODE_OPERATOR_ROLE = web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")
    assert acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING

    SET_NODE_OPERATOR_LIMIT_ROLE = web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")
    assert acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING

    MANAGE_SIGNING_KEYS = web3.keccak(text="MANAGE_SIGNING_KEYS")
    assert acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == VOTING

    # Simple DVT Module Permissions Transition
    assert acl.getPermissionManager(SDVT_MODULE, STAKING_ROUTER_ROLE) == VOTING
    assert acl.getPermissionManager(SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING
    assert acl.getPermissionManager(SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING

    # ACL Permissions Transition
    CREATE_PERMISSIONS_ROLE = web3.keccak(text="CREATE_PERMISSIONS_ROLE")
    assert not acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == VOTING
    assert acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)

    # Agent Permissions Transition
    RUN_SCRIPT_ROLE = web3.keccak(text="RUN_SCRIPT_ROLE")
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == VOTING

    EXECUTE_ROLE = web3.keccak(text="EXECUTE_ROLE")
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == VOTING

    # WithdrawalQueue Roles Transition
    PAUSE_ROLE = web3.keccak(text="PAUSE_ROLE")
    withdrawal_queue = interface.WithdrawalQueue(WITHDRAWAL_QUEUE)
    assert not withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # VEBO Roles Transition
    vebo = interface.ValidatorsExitBusOracle(VEBO)
    assert not vebo.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not vebo.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # AllowedTokensRegistry Roles Transition
    allowed_tokens_registry = interface.AllowedTokensRegistry(ALLOWED_TOKENS_REGISTRY)

    DEFAULT_ADMIN_ROLE = HexBytes(0)
    assert not allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, VOTING)
    assert allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, AGENT)

    ADD_TOKEN_TO_ALLOWED_LIST_ROLE = web3.keccak(text="ADD_TOKEN_TO_ALLOWED_LIST_ROLE")
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, VOTING)
    assert allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, AGENT)

    REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE = web3.keccak(text="REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE")
    assert not allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, VOTING)
    assert allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, AGENT)

    # WithdrawalVault Roles Transition
    withdrawal_vault = interface.WithdrawalContractProxy(WITHDRAWAL_VAULT)
    assert withdrawal_vault.proxy_getAdmin() == VOTING

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

    vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=contracts.voting)

    # Lido Permissions Transition
    assert not acl.hasPermission(AGENT, LIDO, STAKING_CONTROL_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, STAKING_CONTROL_ROLE)
    assert acl.getPermissionManager(LIDO, STAKING_CONTROL_ROLE) == AGENT

    assert not acl.hasPermission(AGENT, LIDO, RESUME_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, RESUME_ROLE)
    assert acl.getPermissionManager(LIDO, RESUME_ROLE) == AGENT

    assert not acl.hasPermission(AGENT, LIDO, PAUSE_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, PAUSE_ROLE) == AGENT

    assert not acl.hasPermission(AGENT, LIDO, STAKING_PAUSE_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, STAKING_PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, STAKING_PAUSE_ROLE) == AGENT

    # DAOKernel Permissions Transition
    assert not acl.hasPermission(AGENT, KERNEL, APP_MANAGER_ROLE)
    assert not acl.hasPermission(VOTING, KERNEL, APP_MANAGER_ROLE)
    assert acl.getPermissionManager(KERNEL, APP_MANAGER_ROLE) == AGENT

    # TokenManager Permissions Transition
    assert acl.hasPermission(VOTING, TOKEN_MANAGER, MINT_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, MINT_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, REVOKE_VESTINGS_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, BURN_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, BURN_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, ISSUE_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, ISSUE_ROLE) == VOTING

    # Finance Permissions Transition
    assert acl.hasPermission(VOTING, FINANCE, CHANGE_PERIOD_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_PERIOD_ROLE) == VOTING

    assert acl.hasPermission(VOTING, FINANCE, CHANGE_BUDGETS_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_BUDGETS_ROLE) == VOTING

    # EVMScriptRegistry Permissions Transition
    assert not acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE) == AGENT

    # CuratedModule Permissions Transition
    assert acl.getPermissionManager(CURATED_MODULE, STAKING_ROUTER_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == AGENT

    # Simple DVT Module Permissions Transition
    assert acl.getPermissionManager(SDVT_MODULE, STAKING_ROUTER_ROLE) == AGENT
    assert acl.getPermissionManager(SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT
    assert acl.getPermissionManager(SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT

    # Agent Permissions Transition
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == AGENT
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == AGENT

    # ACL Permissions Transition
    assert not acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == AGENT

    # WithdrawalQueue Roles Transition
    assert withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # VEBO Roles Transition
    assert vebo.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert vebo.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # AllowedTokensRegistry Roles Transition
    assert allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, AGENT)

    assert allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, AGENT)

    assert allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, AGENT)

    # WithdrawalVault Roles Transition
    assert withdrawal_vault.proxy_getAdmin() == AGENT

    chain.sleep(24 * 60 * 60)

    dual_governance.scheduleProposal(2, {"from": stranger})

    chain.sleep(24 * 60 * 60)

    dg_tx: TransactionReceipt = timelock.execute(2, {"from": stranger})

    # AGENT
    assert not acl.hasPermission(AGENT, VOTING, RUN_SCRIPT_ROLE)
    assert not acl.hasPermission(AGENT, VOTING, EXECUTE_ROLE)

    # events
    evs = group_voting_events_from_receipt(vote_tx)

    metadata = find_metadata_by_vote_id(vote_id)
    # assert get_lido_vote_cid_from_str(metadata) == "bafkreia2qh6xvoowgwukqfyyer2zz266e2jifxovnddgqawruhe2g5asgi"

    assert count_vote_items_by_events(vote_tx, contracts.voting) == 55, "Incorrect voting items count"

    # Lido Permissions Transition
    validate_permission_revoke_event(evs[0], Permission(entity=VOTING, app=LIDO, role=STAKING_CONTROL_ROLE.hex()))
    validate_change_permission_manager_event(evs[1], app=LIDO, role=STAKING_CONTROL_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(evs[2], Permission(entity=VOTING, app=LIDO, role=RESUME_ROLE.hex()))
    validate_change_permission_manager_event(evs[3], app=LIDO, role=RESUME_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(evs[4], Permission(entity=VOTING, app=LIDO, role=PAUSE_ROLE.hex()))
    validate_change_permission_manager_event(evs[5], app=LIDO, role=PAUSE_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(
        evs[6], Permission(entity=VOTING, app=LIDO, role=UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE.hex())
    )
    validate_change_permission_manager_event(
        evs[7], app=LIDO, role=UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE.hex(), manager=AGENT
    )
    validate_permission_revoke_event(evs[8], Permission(entity=VOTING, app=LIDO, role=STAKING_PAUSE_ROLE.hex()))
    validate_change_permission_manager_event(evs[9], app=LIDO, role=STAKING_PAUSE_ROLE.hex(), manager=AGENT)

    # DAOKernel Permissions Transition
    validate_permission_revoke_event(evs[10], Permission(entity=VOTING, app=KERNEL, role=APP_MANAGER_ROLE.hex()))
    validate_change_permission_manager_event(evs[11], app=KERNEL, role=APP_MANAGER_ROLE.hex(), manager=AGENT)

    # TokenManager Permissions Transition
    validate_permission_create_event(
        evs[12], Permission(entity=VOTING, app=TOKEN_MANAGER, role=MINT_ROLE.hex()), VOTING
    )
    validate_permission_create_event(
        evs[13], Permission(entity=VOTING, app=TOKEN_MANAGER, role=REVOKE_VESTINGS_ROLE.hex()), VOTING
    )
    validate_permission_create_event(
        evs[14], Permission(entity=VOTING, app=TOKEN_MANAGER, role=BURN_ROLE.hex()), VOTING
    )
    validate_permission_create_event(
        evs[15], Permission(entity=VOTING, app=TOKEN_MANAGER, role=ISSUE_ROLE.hex()), VOTING
    )

    # Finance Permissions Transition
    validate_permission_create_event(
        evs[16], Permission(entity=VOTING, app=FINANCE, role=CHANGE_PERIOD_ROLE.hex()), VOTING
    )
    validate_permission_create_event(
        evs[17], Permission(entity=VOTING, app=FINANCE, role=CHANGE_BUDGETS_ROLE.hex()), VOTING
    )

    # EVMScriptRegistry Permissions Transition
    validate_permission_revoke_event(
        evs[18], Permission(entity=VOTING, app=EVM_SCRIPT_REGISTRY, role=REGISTRY_MANAGER_ROLE.hex())
    )
    validate_change_permission_manager_event(
        evs[19], app=EVM_SCRIPT_REGISTRY, role=REGISTRY_MANAGER_ROLE.hex(), manager=AGENT
    )
    validate_permission_revoke_event(
        evs[20], Permission(entity=VOTING, app=EVM_SCRIPT_REGISTRY, role=REGISTRY_ADD_EXECUTOR_ROLE.hex())
    )
    validate_change_permission_manager_event(
        evs[21], app=EVM_SCRIPT_REGISTRY, role=REGISTRY_ADD_EXECUTOR_ROLE.hex(), manager=AGENT
    )

    # CuratedModule Permissions Transition
    validate_change_permission_manager_event(evs[22], app=CURATED_MODULE, role=STAKING_ROUTER_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(
        evs[23], Permission(entity=VOTING, app=CURATED_MODULE, role=MANAGE_NODE_OPERATOR_ROLE.hex())
    )
    validate_change_permission_manager_event(
        evs[24], app=CURATED_MODULE, role=MANAGE_NODE_OPERATOR_ROLE.hex(), manager=AGENT
    )
    validate_permission_revoke_event(
        evs[25], Permission(entity=VOTING, app=CURATED_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex())
    )
    validate_change_permission_manager_event(
        evs[26], app=CURATED_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex(), manager=AGENT
    )
    validate_permission_revoke_event(
        evs[27], Permission(entity=VOTING, app=CURATED_MODULE, role=MANAGE_SIGNING_KEYS.hex())
    )
    validate_change_permission_manager_event(evs[28], app=CURATED_MODULE, role=MANAGE_SIGNING_KEYS.hex(), manager=AGENT)

    # Simple DVT Module Permissions Transition
    validate_change_permission_manager_event(evs[29], app=SDVT_MODULE, role=STAKING_ROUTER_ROLE.hex(), manager=AGENT)
    validate_change_permission_manager_event(
        evs[30], app=SDVT_MODULE, role=MANAGE_NODE_OPERATOR_ROLE.hex(), manager=AGENT
    )
    validate_change_permission_manager_event(
        evs[31], app=SDVT_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex(), manager=AGENT
    )

    # ACL Permissions Transition
    validate_permission_grant_event(evs[32], Permission(entity=AGENT, app=ACL, role=CREATE_PERMISSIONS_ROLE.hex()))
    validate_permission_revoke_event(evs[33], Permission(entity=VOTING, app=ACL, role=CREATE_PERMISSIONS_ROLE.hex()))
    validate_change_permission_manager_event(evs[34], app=ACL, role=CREATE_PERMISSIONS_ROLE.hex(), manager=AGENT)

    # Agent Permissions Transition
    validate_permission_grant_event(
        evs[35], Permission(entity=DUAL_GOVERNANCE_ADMIN_EXECUTOR, app=AGENT, role=RUN_SCRIPT_ROLE.hex())
    )
    validate_permission_grant_event(evs[36], Permission(entity=AGENT_MANAGER, app=AGENT, role=RUN_SCRIPT_ROLE.hex()))
    validate_change_permission_manager_event(evs[37], app=AGENT, role=RUN_SCRIPT_ROLE.hex(), manager=AGENT)
    validate_permission_grant_event(
        evs[38], Permission(entity=DUAL_GOVERNANCE_ADMIN_EXECUTOR, app=AGENT, role=EXECUTE_ROLE.hex())
    )
    validate_change_permission_manager_event(evs[39], app=AGENT, role=EXECUTE_ROLE.hex(), manager=AGENT)

    # WithdrawalQueue Roles Transition
    validate_grant_role_event(evs[40], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex())
    validate_grant_role_event(evs[41], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex())

    # VEBO Roles Transition
    validate_grant_role_event(evs[42], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex())
    validate_grant_role_event(evs[43], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex())

    # AllowedTokensRegistry Roles Transition
    validate_grant_role_event(evs[44], grant_to=VOTING, sender=AGENT, role=DEFAULT_ADMIN_ROLE.hex())
    validate_revoke_role_event(evs[45], revoke_from=AGENT, sender=VOTING, role=DEFAULT_ADMIN_ROLE.hex())
    validate_grant_role_event(evs[46], grant_to=VOTING, sender=VOTING, role=ADD_TOKEN_TO_ALLOWED_LIST_ROLE.hex())
    validate_revoke_role_event(evs[47], revoke_from=AGENT, sender=VOTING, role=ADD_TOKEN_TO_ALLOWED_LIST_ROLE.hex())
    validate_grant_role_event(evs[48], grant_to=VOTING, sender=VOTING, role=REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE.hex())
    validate_revoke_role_event(
        evs[49], revoke_from=AGENT, sender=VOTING, role=REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE.hex()
    )

    # WithdrawalVault Roles Transition
    validate_proxy_admin_changed(evs[50], VOTING, AGENT)

    validate_role_validated_event(
        evs[51],
        [
            ValidatedRole(entity=LIDO, roleName="STAKING_CONTROL_ROLE"),
            ValidatedRole(entity=LIDO, roleName="RESUME_ROLE"),
            ValidatedRole(entity=LIDO, roleName="PAUSE_ROLE"),
            ValidatedRole(entity=LIDO, roleName="UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE"),
            ValidatedRole(entity=LIDO, roleName="STAKING_PAUSE_ROLE"),
            ValidatedRole(entity=KERNEL, roleName="APP_MANAGER_ROLE"),
            ValidatedRole(entity=TOKEN_MANAGER, roleName="MINT_ROLE"),
            ValidatedRole(entity=TOKEN_MANAGER, roleName="REVOKE_VESTINGS_ROLE"),
            ValidatedRole(entity=TOKEN_MANAGER, roleName="BURN_ROLE"),
            ValidatedRole(entity=TOKEN_MANAGER, roleName="ISSUE_ROLE"),
            ValidatedRole(entity=FINANCE, roleName="CHANGE_PERIOD_ROLE"),
            ValidatedRole(entity=FINANCE, roleName="CHANGE_BUDGETS_ROLE"),
            ValidatedRole(entity=EVM_SCRIPT_REGISTRY, roleName="REGISTRY_MANAGER_ROLE"),
            ValidatedRole(entity=EVM_SCRIPT_REGISTRY, roleName="REGISTRY_ADD_EXECUTOR_ROLE"),
            ValidatedRole(entity=CURATED_MODULE, roleName="MANAGE_NODE_OPERATOR_ROLE"),
            ValidatedRole(entity=CURATED_MODULE, roleName="SET_NODE_OPERATOR_LIMIT_ROLE"),
            ValidatedRole(entity=CURATED_MODULE, roleName="MANAGE_SIGNING_KEYS"),
            ValidatedRole(entity=CURATED_MODULE, roleName="STAKING_ROUTER_ROLE"),
            ValidatedRole(entity=SDVT_MODULE, roleName="STAKING_ROUTER_ROLE"),
            ValidatedRole(entity=SDVT_MODULE, roleName="MANAGE_NODE_OPERATOR_ROLE"),
            ValidatedRole(entity=SDVT_MODULE, roleName="SET_NODE_OPERATOR_LIMIT_ROLE"),
            ValidatedRole(entity=ACL, roleName="CREATE_PERMISSIONS_ROLE"),
            ValidatedRole(entity=AGENT, roleName="RUN_SCRIPT_ROLE"),
            ValidatedRole(entity=AGENT, roleName="EXECUTE_ROLE"),
            ValidatedRole(entity=WITHDRAWAL_QUEUE, roleName="PAUSE_ROLE"),
            ValidatedRole(entity=WITHDRAWAL_QUEUE, roleName="RESUME_ROLE"),
            ValidatedRole(entity=VEBO, roleName="PAUSE_ROLE"),
            ValidatedRole(entity=VEBO, roleName="RESUME_ROLE"),
            ValidatedRole(entity=ALLOWED_TOKENS_REGISTRY, roleName="DEFAULT_ADMIN_ROLE"),
            ValidatedRole(entity=ALLOWED_TOKENS_REGISTRY, roleName="ADD_TOKEN_TO_ALLOWED_LIST_ROLE"),
            ValidatedRole(entity=ALLOWED_TOKENS_REGISTRY, roleName="REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"),
        ],
    )

    validate_dual_governance_submit_event(
        evs[52],
        proposal_id=2,
        proposer=VOTING,
        executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
        metadata="Revoke RUN_SCRIPT_ROLE and EXECUTE_ROLE from Aragon Voting",
        proposal_calls=[
            {
                "target": TIME_CONSTRAINTS,
                "value": 0,
                "data": interface.TimeConstraints(TIME_CONSTRAINTS).checkExecuteBeforeTimestamp.encode_input(
                    1745971200
                ),
            },
            {
                "target": TIME_CONSTRAINTS,
                "value": 0,
                "data": interface.TimeConstraints(TIME_CONSTRAINTS).checkExecuteWithinDayTime.encode_input(
                    3600 * 4, 3600 * 22
                ),
            },
            {
                "target": AGENT,
                "value": 0,
                "data": agent_forward(
                    [(ACL, interface.ACL(ACL).revokePermission.encode_input(VOTING, AGENT, RUN_SCRIPT_ROLE.hex()))]
                )[1],
            },
            {
                "target": AGENT,
                "value": 0,
                "data": agent_forward(
                    [(ACL, interface.ACL(ACL).revokePermission.encode_input(VOTING, AGENT, EXECUTE_ROLE.hex()))]
                )[1],
            },
            {
                "target": AGENT,
                "value": 0,
                "data": agent_forward(
                    [
                        (
                            ROLES_VALIDATOR,
                            interface.RolesValidator(ROLES_VALIDATOR).validateDGProposalLaunchPhase.encode_input(),
                        )
                    ]
                )[1],
            },
        ],
    )

    validate_dual_governance_governance_launch_verification_event(evs[53])

    validate_time_constraints_executed_before_event(evs[54])

    dg_evs = dg_events_from_trace(dg_tx, timelock=TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR)

    validate_dg_time_constraints_executed_before_event(dg_evs[0])

    validate_dg_time_constraints_executed_with_day_time_event(dg_evs[1])

    validate_dg_permission_revoke_event(dg_evs[2], Permission(entity=VOTING, app=AGENT, role=RUN_SCRIPT_ROLE.hex()))
    validate_dg_permission_revoke_event(dg_evs[3], Permission(entity=VOTING, app=AGENT, role=EXECUTE_ROLE.hex()))

    validate_dg_role_validated_event(
        dg_evs[4],
        [
            ValidatedRole(entity=AGENT, roleName="RUN_SCRIPT_ROLE"),
            ValidatedRole(entity=AGENT, roleName="EXECUTE_ROLE"),
        ],
    )
