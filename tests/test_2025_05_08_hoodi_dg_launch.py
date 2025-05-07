import pytest
import os

from typing import NamedTuple, List
from brownie import web3, chain, interface, ZERO_ADDRESS, accounts, reverts
from hexbytes import HexBytes
from scripts.vote_2025_05_08_hoodi_dg_launch import start_vote
from utils.config import contracts
from brownie.network.transaction import TransactionReceipt
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import (
    validate_dual_governance_submit_event,
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
    validate_set_permission_manager_event,
    Permission,
    validate_permission_grant_event,
    validate_grant_role_event,
    validate_revoke_role_event,
    validate_dg_permission_revoke_event,
)

from utils.test.event_validators.proxy import validate_proxy_admin_changed

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


DUAL_GOVERNANCE = "0x4d12b9f6aCAB54FF6a3a776BA3b8724D9B77845F"
TIMELOCK = "0x0A5E22782C0Bd4AddF10D771f0bF0406B038282d"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x0eCc17597D292271836691358B22340b78F3035B"
RESEAL_MANAGER = "0x05172CbCDb7307228F781436b327679e4DAE166B"
DAO_EMERGENCY_GOVERNANCE = "0x69E8e916c4A19F42C13C802abDF2767E1fB4F059"
ROLES_VALIDATOR = "0x9CCe5BfAcDcf80DAd2287106b57197284DacaE3F"
TIME_CONSTRAINTS = "0xB26Fd3b50280AbC55c572EE73071778A51088408"
DUAL_GOVERNANCE_CONFIG_PROVIDER = "0x2b685e6fB288bBb7A82533BAfb679FfDF6E5bb33"


# These addresses can be checked on https://docs.lido.fi/deployed-contracts/hoodi
ACL = "0x78780e70Eae33e2935814a327f7dB6c01136cc62"
LIDO = "0x3508A952176b3c15387C97BE809eaffB1982176a"
KERNEL = "0xA48DF029Fd2e5FCECB3886c5c2F60e3625A1E87d"
VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"
TOKEN_MANAGER = "0x8ab4a56721Ad8e68c6Ad86F9D9929782A78E39E5"
FINANCE = "0x254Ae22bEEba64127F0e59fe8593082F3cd13f6b"
AGENT = "0x0534aA41907c9631fae990960bCC72d75fA7cfeD"
EVM_SCRIPT_REGISTRY = "0xe4D32427b1F9b12ab89B142eD3714dCAABB3f38c"
CURATED_MODULE = "0x5cDbE1590c083b5A2A64427fAA63A7cfDB91FbB5"
SDVT_MODULE = "0x0B5236BECA68004DB89434462DfC3BB074d2c830"
ALLOWED_TOKENS_REGISTRY = "0x40Db7E8047C487bD8359289272c717eA3C34D1D3"
WITHDRAWAL_VAULT = "0x4473dCDDbf77679A643BdB654dbd86D67F8d32f2"
WITHDRAWAL_QUEUE = "0xfe56573178f1bcdf53F01A6E9977670dcBBD9186"
VEBO = "0x8664d394C2B3278F26A1B44B967aEf99707eeAB2"
UNLIMITED_STAKE = "0x064A4D64040bFD52D0d1dC7f42eA799cb0a8AC40"
STAKING_ROUTER = "0xCc820558B39ee15C7C45B59390B503b83fb499A8"
EVM_SCRIPT_EXECUTOR = "0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E"
GATE_SEAL = "0x2168Ea6D948Ab49c3D34c667A7e02F92369F3A9C"
AGENT_MANAGER = "0xD500a8aDB182F55741E267730dfbfb4F1944C205"

DEV_EOA_1 = "0xE28f573b732632fdE03BD5507A7d475383e8512E"
DEV_EOA_2 = "0xF865A1d43D36c713B4DA085f32b7d1e9739B9275"


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


class OZValidatedRole(NamedTuple):
    entity: str
    roleName: str
    grantedTo: List[str]
    revokedFrom: List[str]

class AragonValidatedPermission(NamedTuple):
    entity: str
    roleName: str
    grantedTo: List[str]
    revokedFrom: List[str]
    manager: str


def _validate_role_events(event: EventDict, roles: list, extra_events: list = None):
    _events_chain = ["LogScriptCall"]
    for role in roles:
        if isinstance(role, OZValidatedRole):
            _events_chain.append("OZRoleValidated")
        elif isinstance(role, AragonValidatedPermission):
            _events_chain.append("AragonPermissionValidated")
        else:
            raise TypeError("Unknown role type in roles list")
    if extra_events:
        _events_chain += extra_events

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, "Wrong number of LogScriptCall events"
    assert event.count("OZRoleValidated") == sum(isinstance(r, OZValidatedRole) for r in roles), "Wrong number of OZRoleValidated events"
    assert event.count("AragonPermissionValidated") == sum(isinstance(r, AragonValidatedPermission) for r in roles), "Wrong number of AragonPermissionValidated events"

    oz_idx = 0
    aragon_idx = 0
    for role in roles:
        if isinstance(role, OZValidatedRole):
            ev = event["OZRoleValidated"][oz_idx]
            oz_idx += 1
            assert ev["entity"] == role.entity, "Wrong entity for OZRoleValidated"
            assert ev["roleName"] == role.roleName, "Wrong roleName for OZRoleValidated"
            assert set(ev["grantedTo"]) == set(role.grantedTo), f"Wrong grantedTo for OZRoleValidated: {ev['grantedTo']} != {role.grantedTo}"
            assert set(ev["revokedFrom"]) == set(role.revokedFrom), f"Wrong revokedFrom for OZRoleValidated: {ev['revokedFrom']} != {role.revokedFrom}"
        elif isinstance(role, AragonValidatedPermission):
            ev = event["AragonPermissionValidated"][aragon_idx]
            aragon_idx += 1
            assert ev["entity"] == role.entity, "Wrong entity for AragonPermissionValidated"
            assert ev["roleName"] == role.roleName, "Wrong roleName for AragonPermissionValidated"
            assert ev["manager"] == role.manager, "Wrong manager for AragonPermissionValidated"
            assert set(ev["grantedTo"]) == set(role.grantedTo), f"Wrong grantedTo for AragonPermissionValidated: {ev['grantedTo']} != {role.grantedTo}"
            assert set(ev["revokedFrom"]) == set(role.revokedFrom), f"Wrong revokedFrom for AragonPermissionValidated: {ev['revokedFrom']} != {role.revokedFrom}"
        else:
            raise TypeError("Unknown role type in roles list")

def validate_role_validated_event(event: EventDict, roles: list) -> None:
    _validate_role_events(event, roles)

def validate_dg_role_validated_event(event: EventDict, roles: list) -> None:
    _validate_role_events(event, roles, extra_events=["ScriptResult", "Executed"])

def validate_dual_governance_governance_launch_verification_event(event: EventDict):
    _events_chain = ["LogScriptCall", "DGLaunchConfigurationValidated"]

    validate_events_chain([e.name for e in event], _events_chain)



def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding, stranger):
    acl = interface.ACL(ACL)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    agent = interface.Agent(AGENT)
    voting = interface.Voting(VOTING)
    lido = interface.Lido(LIDO)
    token_manager = interface.TokenManager(TOKEN_MANAGER)
    finance = interface.Finance(FINANCE)

    # Lido Permissions Transition
    STAKING_CONTROL_ROLE = web3.keccak(text="STAKING_CONTROL_ROLE")
    assert acl.hasPermission(VOTING, LIDO, STAKING_CONTROL_ROLE)
    assert acl.hasPermission(UNLIMITED_STAKE, LIDO, STAKING_CONTROL_ROLE)
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

    # Voting Permissions Transition
    UNSAFELY_MODIFY_VOTE_TIME_ROLE = web3.keccak(text="UNSAFELY_MODIFY_VOTE_TIME_ROLE")
    assert not acl.hasPermission(VOTING, VOTING, UNSAFELY_MODIFY_VOTE_TIME_ROLE)
    assert not acl.hasPermission(AGENT, VOTING, UNSAFELY_MODIFY_VOTE_TIME_ROLE)
    assert acl.getPermissionManager(VOTING, UNSAFELY_MODIFY_VOTE_TIME_ROLE) == ZERO_ADDRESS

    # TokenManager Permissions Transition
    MINT_ROLE = web3.keccak(text="MINT_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, MINT_ROLE)
    assert not acl.hasPermission(AGENT, TOKEN_MANAGER, MINT_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, MINT_ROLE) == ZERO_ADDRESS

    REVOKE_VESTINGS_ROLE = web3.keccak(text="REVOKE_VESTINGS_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert not acl.hasPermission(AGENT, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, REVOKE_VESTINGS_ROLE) == ZERO_ADDRESS

    BURN_ROLE = web3.keccak(text="BURN_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, BURN_ROLE)
    assert not acl.hasPermission(AGENT, TOKEN_MANAGER, BURN_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, BURN_ROLE) == ZERO_ADDRESS

    ISSUE_ROLE = web3.keccak(text="ISSUE_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, ISSUE_ROLE)
    assert not acl.hasPermission(AGENT, TOKEN_MANAGER, ISSUE_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, ISSUE_ROLE) == ZERO_ADDRESS

    # Finance Permissions Transition
    CHANGE_PERIOD_ROLE = web3.keccak(text="CHANGE_PERIOD_ROLE")
    assert not acl.hasPermission(VOTING, FINANCE, CHANGE_PERIOD_ROLE)
    assert not acl.hasPermission(AGENT, FINANCE, CHANGE_PERIOD_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_PERIOD_ROLE) == ZERO_ADDRESS

    CHANGE_BUDGETS_ROLE = web3.keccak(text="CHANGE_BUDGETS_ROLE")
    assert not acl.hasPermission(VOTING, FINANCE, CHANGE_BUDGETS_ROLE)
    assert not acl.hasPermission(AGENT, FINANCE, CHANGE_BUDGETS_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_BUDGETS_ROLE) == ZERO_ADDRESS

    # EVMScriptRegistry Permissions Transition
    REGISTRY_MANAGER_ROLE = web3.keccak(text="REGISTRY_MANAGER_ROLE")
    assert acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE) == VOTING

    REGISTRY_ADD_EXECUTOR_ROLE = web3.keccak(text="REGISTRY_ADD_EXECUTOR_ROLE")
    assert acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE) == VOTING

    # CuratedModule Permissions Transition
    STAKING_ROUTER_ROLE = web3.keccak(text="STAKING_ROUTER_ROLE")
    assert not acl.hasPermission(VOTING, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert not acl.hasPermission(AGENT, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, STAKING_ROUTER_ROLE) == VOTING
    assert acl.hasPermission(DEV_EOA_1, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(DEV_EOA_2, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(STAKING_ROUTER, CURATED_MODULE, STAKING_ROUTER_ROLE)

    MANAGE_NODE_OPERATOR_ROLE = web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")
    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING
    assert acl.hasPermission(AGENT, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(DEV_EOA_1, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(DEV_EOA_2, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)

    SET_NODE_OPERATOR_LIMIT_ROLE = web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")
    assert not acl.hasPermission(AGENT, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING
    assert acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(DEV_EOA_1, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(DEV_EOA_2, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)

    MANAGE_SIGNING_KEYS = web3.keccak(text="MANAGE_SIGNING_KEYS")
    assert not acl.hasPermission(AGENT, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == VOTING
    assert acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.hasPermission(DEV_EOA_1, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.hasPermission(DEV_EOA_2, CURATED_MODULE, MANAGE_SIGNING_KEYS)

    # Simple DVT Module Permissions Transition
    assert acl.getPermissionManager(SDVT_MODULE, STAKING_ROUTER_ROLE) == VOTING
    assert acl.hasPermission(VOTING, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(AGENT, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(DEV_EOA_1, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(DEV_EOA_2, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(STAKING_ROUTER, SDVT_MODULE, STAKING_ROUTER_ROLE)

    assert acl.getPermissionManager(SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING
    assert not acl.hasPermission(AGENT, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(VOTING, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(DEV_EOA_1, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(DEV_EOA_2, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)

    assert not acl.hasPermission(AGENT, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING
    assert acl.hasPermission(VOTING, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(DEV_EOA_1, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(DEV_EOA_2, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)

    # ACL Permissions Transition
    CREATE_PERMISSIONS_ROLE = web3.keccak(text="CREATE_PERMISSIONS_ROLE")
    assert acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)
    assert not acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == VOTING

    # Agent Permissions Transition
    RUN_SCRIPT_ROLE = web3.keccak(text="RUN_SCRIPT_ROLE")
    assert acl.hasPermission(VOTING, AGENT, RUN_SCRIPT_ROLE)
    assert not acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT, RUN_SCRIPT_ROLE)
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == VOTING

    EXECUTE_ROLE = web3.keccak(text="EXECUTE_ROLE")
    assert acl.hasPermission(VOTING, AGENT, EXECUTE_ROLE)
    assert not acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT, EXECUTE_ROLE)
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == VOTING

    # WithdrawalQueue Roles Transition
    PAUSE_ROLE = web3.keccak(text="PAUSE_ROLE")
    withdrawal_queue = interface.WithdrawalQueue(WITHDRAWAL_QUEUE)
    assert not withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(PAUSE_ROLE, GATE_SEAL)

    assert not withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(RESUME_ROLE, AGENT)

    # VEBO Roles Transition
    vebo = interface.ValidatorsExitBusOracle(VEBO)
    assert not vebo.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert vebo.hasRole(PAUSE_ROLE, GATE_SEAL)

    assert not vebo.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert vebo.hasRole(RESUME_ROLE, AGENT)

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
    assert acl.hasPermission(UNLIMITED_STAKE, LIDO, STAKING_CONTROL_ROLE)

    assert not acl.hasPermission(AGENT, LIDO, RESUME_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, RESUME_ROLE)
    assert acl.getPermissionManager(LIDO, RESUME_ROLE) == AGENT

    assert not acl.hasPermission(AGENT, LIDO, PAUSE_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, PAUSE_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, LIDO, UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE)
    assert not acl.hasPermission(AGENT, LIDO, UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE)
    assert acl.getPermissionManager(LIDO, UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE) == AGENT

    assert not acl.hasPermission(AGENT, LIDO, STAKING_PAUSE_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, STAKING_PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, STAKING_PAUSE_ROLE) == AGENT

    # DAOKernel Permissions Transition
    assert not acl.hasPermission(AGENT, KERNEL, APP_MANAGER_ROLE)
    assert not acl.hasPermission(VOTING, KERNEL, APP_MANAGER_ROLE)
    assert acl.getPermissionManager(KERNEL, APP_MANAGER_ROLE) == AGENT

    # Voting Permissions Transition
    assert acl.hasPermission(VOTING, VOTING, UNSAFELY_MODIFY_VOTE_TIME_ROLE)
    assert not acl.hasPermission(AGENT, VOTING, UNSAFELY_MODIFY_VOTE_TIME_ROLE)
    assert acl.getPermissionManager(VOTING, UNSAFELY_MODIFY_VOTE_TIME_ROLE) == VOTING

    # TokenManager Permissions Transition
    assert acl.hasPermission(VOTING, TOKEN_MANAGER, MINT_ROLE)
    assert not acl.hasPermission(AGENT, TOKEN_MANAGER, MINT_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, MINT_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert not acl.hasPermission(AGENT, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, REVOKE_VESTINGS_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, BURN_ROLE)
    assert not acl.hasPermission(AGENT, TOKEN_MANAGER, BURN_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, BURN_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, ISSUE_ROLE)
    assert not acl.hasPermission(AGENT, TOKEN_MANAGER, ISSUE_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, ISSUE_ROLE) == VOTING

    # Finance Permissions Transition
    assert acl.hasPermission(VOTING, FINANCE, CHANGE_PERIOD_ROLE)
    assert not acl.hasPermission(AGENT, FINANCE, CHANGE_PERIOD_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_PERIOD_ROLE) == VOTING

    assert acl.hasPermission(VOTING, FINANCE, CHANGE_BUDGETS_ROLE)
    assert not acl.hasPermission(AGENT, FINANCE, CHANGE_BUDGETS_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_BUDGETS_ROLE) == VOTING

    # EVMScriptRegistry Permissions Transition
    assert not acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE) == AGENT

    # CuratedModule Permissions Transition
    assert not acl.hasPermission(VOTING, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert not acl.hasPermission(AGENT, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, STAKING_ROUTER_ROLE) == AGENT
    assert acl.hasPermission(DEV_EOA_1, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(DEV_EOA_2, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(STAKING_ROUTER, CURATED_MODULE, STAKING_ROUTER_ROLE)

    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT
    assert acl.hasPermission(AGENT, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(DEV_EOA_1, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(DEV_EOA_2, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)

    assert not acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert not acl.hasPermission(AGENT, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT
    assert acl.hasPermission(DEV_EOA_1, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(DEV_EOA_2, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)

    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert not acl.hasPermission(AGENT, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == AGENT
    assert acl.hasPermission(DEV_EOA_1, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.hasPermission(DEV_EOA_2, CURATED_MODULE, MANAGE_SIGNING_KEYS)

    # Simple DVT Module Permissions Transition
    assert not acl.hasPermission(VOTING, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.getPermissionManager(SDVT_MODULE, STAKING_ROUTER_ROLE) == AGENT
    assert acl.hasPermission(AGENT, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(DEV_EOA_1, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(DEV_EOA_2, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(STAKING_ROUTER, SDVT_MODULE, STAKING_ROUTER_ROLE)

    assert not acl.hasPermission(VOTING, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert not acl.hasPermission(AGENT, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.getPermissionManager(SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT
    assert acl.hasPermission(DEV_EOA_1, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(DEV_EOA_2, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)

    assert not acl.hasPermission(VOTING, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert not acl.hasPermission(AGENT, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT
    assert acl.hasPermission(DEV_EOA_1, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(DEV_EOA_2, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)

    # ACL Permissions Transition
    assert not acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == AGENT

    # Agent Permissions Transition
    assert acl.hasPermission(AGENT_MANAGER, AGENT, RUN_SCRIPT_ROLE)
    assert acl.hasPermission(VOTING, AGENT, RUN_SCRIPT_ROLE)
    assert acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT, RUN_SCRIPT_ROLE)
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == AGENT

    assert acl.hasPermission(VOTING, AGENT, EXECUTE_ROLE)
    assert acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT, EXECUTE_ROLE)
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == AGENT

    # WithdrawalQueue Roles Transition
    withdrawal_queue = interface.WithdrawalQueue(WITHDRAWAL_QUEUE)
    assert withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(PAUSE_ROLE, GATE_SEAL)

    assert withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(RESUME_ROLE, AGENT)

    # VEBO Roles Transition
    vebo = interface.ValidatorsExitBusOracle(VEBO)
    assert vebo.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert vebo.hasRole(PAUSE_ROLE, GATE_SEAL)

    assert vebo.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    
    # AllowedTokensRegistry Roles Transition
    allowed_tokens_registry = interface.AllowedTokensRegistry(ALLOWED_TOKENS_REGISTRY)

    assert allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, AGENT)

    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, AGENT)

    assert not allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, AGENT)

    # WithdrawalVault Roles Transition
    withdrawal_vault = interface.WithdrawalContractProxy(WITHDRAWAL_VAULT)
    assert withdrawal_vault.proxy_getAdmin() == AGENT


    chain.sleep(timelock.getAfterSubmitDelay() + 1)

    dual_governance.scheduleProposal(2, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)

    dg_tx: TransactionReceipt = timelock.execute(2, {"from": stranger})

    # AGENT
    assert not acl.hasPermission(AGENT, VOTING, RUN_SCRIPT_ROLE)
    assert not acl.hasPermission(AGENT, VOTING, EXECUTE_ROLE)

    # events
    evs = group_voting_events_from_receipt(vote_tx)

    metadata = find_metadata_by_vote_id(vote_id)
    # assert get_lido_vote_cid_from_str(metadata) == "bafkreia2qh6xvoowgwukqfyyer2zz266e2jifxovnddgqawruhe2g5asgi"

    assert count_vote_items_by_events(vote_tx, contracts.voting) == 56, "Incorrect voting items count"

    # Lido Permissions Transition
    validate_permission_revoke_event(evs[0], Permission(entity=VOTING, app=LIDO, role=STAKING_CONTROL_ROLE.hex()))
    validate_set_permission_manager_event(evs[1], app=LIDO, role=STAKING_CONTROL_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(evs[2], Permission(entity=VOTING, app=LIDO, role=RESUME_ROLE.hex()))
    validate_set_permission_manager_event(evs[3], app=LIDO, role=RESUME_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(evs[4], Permission(entity=VOTING, app=LIDO, role=PAUSE_ROLE.hex()))
    validate_set_permission_manager_event(evs[5], app=LIDO, role=PAUSE_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(
        evs[6], Permission(entity=VOTING, app=LIDO, role=UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE.hex())
    )
    validate_set_permission_manager_event(
        evs[7], app=LIDO, role=UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE.hex(), manager=AGENT
    )
    validate_permission_revoke_event(evs[8], Permission(entity=VOTING, app=LIDO, role=STAKING_PAUSE_ROLE.hex()))
    validate_set_permission_manager_event(evs[9], app=LIDO, role=STAKING_PAUSE_ROLE.hex(), manager=AGENT)

    # DAOKernel Permissions Transition
    validate_permission_revoke_event(evs[10], Permission(entity=VOTING, app=KERNEL, role=APP_MANAGER_ROLE.hex()))
    validate_set_permission_manager_event(evs[11], app=KERNEL, role=APP_MANAGER_ROLE.hex(), manager=AGENT)

    # Voting Permissions Transition
    validate_permission_create_event(
        evs[12], Permission(entity=VOTING, app=VOTING, role=UNSAFELY_MODIFY_VOTE_TIME_ROLE.hex()), VOTING
    )

    # TokenManager Permissions Transition
    validate_permission_create_event(
        evs[13], Permission(entity=VOTING, app=TOKEN_MANAGER, role=MINT_ROLE.hex()), VOTING
    )
    validate_permission_create_event(
        evs[14], Permission(entity=VOTING, app=TOKEN_MANAGER, role=REVOKE_VESTINGS_ROLE.hex()), VOTING
    )
    validate_permission_create_event(
        evs[15], Permission(entity=VOTING, app=TOKEN_MANAGER, role=BURN_ROLE.hex()), VOTING
    )
    validate_permission_create_event(
        evs[16], Permission(entity=VOTING, app=TOKEN_MANAGER, role=ISSUE_ROLE.hex()), VOTING
    )

    # Finance Permissions Transition
    validate_permission_create_event(
        evs[17], Permission(entity=VOTING, app=FINANCE, role=CHANGE_PERIOD_ROLE.hex()), VOTING
    )
    validate_permission_create_event(
        evs[18], Permission(entity=VOTING, app=FINANCE, role=CHANGE_BUDGETS_ROLE.hex()), VOTING
    )

    # EVMScriptRegistry Permissions Transition
    validate_permission_revoke_event(
        evs[19], Permission(entity=VOTING, app=EVM_SCRIPT_REGISTRY, role=REGISTRY_MANAGER_ROLE.hex())
    )
    validate_set_permission_manager_event(
        evs[20], app=EVM_SCRIPT_REGISTRY, role=REGISTRY_MANAGER_ROLE.hex(), manager=AGENT
    )
    validate_permission_revoke_event(
        evs[21], Permission(entity=VOTING, app=EVM_SCRIPT_REGISTRY, role=REGISTRY_ADD_EXECUTOR_ROLE.hex())
    )
    validate_set_permission_manager_event(
        evs[22], app=EVM_SCRIPT_REGISTRY, role=REGISTRY_ADD_EXECUTOR_ROLE.hex(), manager=AGENT
    )

    # CuratedModule Permissions Transition
    validate_set_permission_manager_event(evs[23], app=CURATED_MODULE, role=STAKING_ROUTER_ROLE.hex(), manager=AGENT)
    validate_set_permission_manager_event(
        evs[24], app=CURATED_MODULE, role=MANAGE_NODE_OPERATOR_ROLE.hex(), manager=AGENT
    )
    validate_permission_revoke_event(
        evs[25], Permission(entity=VOTING, app=CURATED_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex())
    )
    validate_set_permission_manager_event(
        evs[26], app=CURATED_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex(), manager=AGENT
    )
    validate_permission_revoke_event(
        evs[27], Permission(entity=VOTING, app=CURATED_MODULE, role=MANAGE_SIGNING_KEYS.hex())
    )
    validate_set_permission_manager_event(evs[28], app=CURATED_MODULE, role=MANAGE_SIGNING_KEYS.hex(), manager=AGENT)

    # Simple DVT Module Permissions Transition
    validate_permission_revoke_event(
        evs[29], Permission(entity=VOTING, app=SDVT_MODULE, role=STAKING_ROUTER_ROLE.hex())
    )
    validate_set_permission_manager_event(evs[30], app=SDVT_MODULE, role=STAKING_ROUTER_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(
        evs[31], Permission(entity=VOTING, app=SDVT_MODULE, role=MANAGE_NODE_OPERATOR_ROLE.hex())
    )
    validate_set_permission_manager_event(evs[32], app=SDVT_MODULE, role=MANAGE_NODE_OPERATOR_ROLE.hex(), manager=AGENT)
    validate_permission_revoke_event(
        evs[33], Permission(entity=VOTING, app=SDVT_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex())
    )
    validate_set_permission_manager_event(
        evs[34], app=SDVT_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex(), manager=AGENT
    )

    # ACL Permissions Transition
    validate_permission_grant_event(evs[35], Permission(entity=AGENT, app=ACL, role=CREATE_PERMISSIONS_ROLE.hex()))
    validate_permission_revoke_event(evs[36], Permission(entity=VOTING, app=ACL, role=CREATE_PERMISSIONS_ROLE.hex()))
    validate_set_permission_manager_event(evs[37], app=ACL, role=CREATE_PERMISSIONS_ROLE.hex(), manager=AGENT)

    # Agent Permissions Transition
    validate_permission_grant_event(
        evs[38], Permission(entity=DUAL_GOVERNANCE_ADMIN_EXECUTOR, app=AGENT, role=RUN_SCRIPT_ROLE.hex())
    )
    validate_permission_grant_event(evs[39], Permission(entity=AGENT_MANAGER, app=AGENT, role=RUN_SCRIPT_ROLE.hex()))
    validate_set_permission_manager_event(evs[40], app=AGENT, role=RUN_SCRIPT_ROLE.hex(), manager=AGENT)

    validate_permission_grant_event(
        evs[41], Permission(entity=DUAL_GOVERNANCE_ADMIN_EXECUTOR, app=AGENT, role=EXECUTE_ROLE.hex())
    )
    validate_set_permission_manager_event(evs[42], app=AGENT, role=EXECUTE_ROLE.hex(), manager=AGENT)

    # WithdrawalQueue Roles Transition
    validate_grant_role_event(evs[43], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex())
    validate_grant_role_event(evs[44], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex())

    # VEBO Roles Transition
    validate_grant_role_event(evs[45], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex())
    validate_grant_role_event(evs[46], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex())

    # AllowedTokensRegistry Roles Transition
    validate_grant_role_event(evs[47], grant_to=VOTING, sender=AGENT, role=DEFAULT_ADMIN_ROLE.hex())
    validate_revoke_role_event(evs[48], revoke_from=AGENT, sender=VOTING, role=DEFAULT_ADMIN_ROLE.hex())
    validate_revoke_role_event(evs[49], revoke_from=AGENT, sender=VOTING, role=ADD_TOKEN_TO_ALLOWED_LIST_ROLE.hex())
    validate_revoke_role_event(
        evs[50], revoke_from=AGENT, sender=VOTING, role=REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE.hex()
    )

    # WithdrawalVault Roles Transition
    validate_proxy_admin_changed(evs[51], VOTING, AGENT)

    validate_role_validated_event(
        evs[52],
        [
            AragonValidatedPermission(LIDO, "STAKING_CONTROL_ROLE", [UNLIMITED_STAKE], [VOTING], AGENT),
            AragonValidatedPermission(LIDO, "RESUME_ROLE", [], [VOTING], AGENT),
            AragonValidatedPermission(LIDO, "PAUSE_ROLE", [], [VOTING], AGENT),
            AragonValidatedPermission(LIDO, "UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE", [], [VOTING], AGENT),
            AragonValidatedPermission(LIDO, "STAKING_PAUSE_ROLE", [], [VOTING], AGENT),

            # DAOKernel
            AragonValidatedPermission(KERNEL, "APP_MANAGER_ROLE", [], [VOTING], AGENT),

            # Voting
            AragonValidatedPermission(VOTING, "UNSAFELY_MODIFY_VOTE_TIME_ROLE", [VOTING], [], VOTING),

            # TokenManager
            AragonValidatedPermission(TOKEN_MANAGER, "MINT_ROLE", [VOTING], [], VOTING),
            AragonValidatedPermission(TOKEN_MANAGER, "REVOKE_VESTINGS_ROLE", [VOTING], [], VOTING),
            AragonValidatedPermission(TOKEN_MANAGER, "BURN_ROLE", [VOTING], [], VOTING),
            AragonValidatedPermission(TOKEN_MANAGER, "ISSUE_ROLE", [VOTING], [], VOTING),

            # Finance
            AragonValidatedPermission(FINANCE, "CHANGE_PERIOD_ROLE", [VOTING], [], VOTING),
            AragonValidatedPermission(FINANCE, "CHANGE_BUDGETS_ROLE", [VOTING], [], VOTING),

            # Aragon EVMScriptRegistry
            AragonValidatedPermission(EVM_SCRIPT_REGISTRY, "REGISTRY_MANAGER_ROLE", [], [VOTING], AGENT),
            AragonValidatedPermission(EVM_SCRIPT_REGISTRY, "REGISTRY_ADD_EXECUTOR_ROLE", [], [VOTING], AGENT),

            # CuratedModule
            AragonValidatedPermission(CURATED_MODULE, "STAKING_ROUTER_ROLE", [STAKING_ROUTER, DEV_EOA_1, DEV_EOA_2], [], AGENT),
            AragonValidatedPermission(CURATED_MODULE, "MANAGE_NODE_OPERATOR_ROLE", [AGENT, DEV_EOA_1, DEV_EOA_2], [], AGENT),
            AragonValidatedPermission(CURATED_MODULE, "SET_NODE_OPERATOR_LIMIT_ROLE", [DEV_EOA_1, DEV_EOA_2, EVM_SCRIPT_EXECUTOR], [VOTING], AGENT),
            AragonValidatedPermission(CURATED_MODULE, "MANAGE_SIGNING_KEYS", [DEV_EOA_1, DEV_EOA_2], [VOTING], AGENT),

            # SDVTModule
            AragonValidatedPermission(SDVT_MODULE, "STAKING_ROUTER_ROLE", [STAKING_ROUTER, AGENT, DEV_EOA_2, DEV_EOA_1, EVM_SCRIPT_EXECUTOR], [VOTING], AGENT),
            AragonValidatedPermission(SDVT_MODULE, "MANAGE_NODE_OPERATOR_ROLE", [DEV_EOA_2, DEV_EOA_1, EVM_SCRIPT_EXECUTOR], [VOTING], AGENT),
            AragonValidatedPermission(SDVT_MODULE, "SET_NODE_OPERATOR_LIMIT_ROLE", [EVM_SCRIPT_EXECUTOR, DEV_EOA_1, DEV_EOA_2], [VOTING], AGENT),

            # ACL
            AragonValidatedPermission(ACL, "CREATE_PERMISSIONS_ROLE", [AGENT], [VOTING], AGENT),

            # Agent
            AragonValidatedPermission(AGENT, "RUN_SCRIPT_ROLE", [VOTING, DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT_MANAGER], [], AGENT),
            AragonValidatedPermission(AGENT, "EXECUTE_ROLE", [VOTING, DUAL_GOVERNANCE_ADMIN_EXECUTOR], [], AGENT),

            # WithdrawalQueue (OZ)
            OZValidatedRole(WITHDRAWAL_QUEUE, "PAUSE_ROLE", [RESEAL_MANAGER, GATE_SEAL], []),
            OZValidatedRole(WITHDRAWAL_QUEUE, "RESUME_ROLE", [RESEAL_MANAGER, AGENT], []),

            # VEBO (OZ)
            OZValidatedRole(VEBO, "PAUSE_ROLE", [RESEAL_MANAGER, GATE_SEAL], []),
            OZValidatedRole(VEBO, "RESUME_ROLE", [RESEAL_MANAGER, AGENT], []),

            # AllowedTokensRegistry (OZ)
            OZValidatedRole(ALLOWED_TOKENS_REGISTRY, "DEFAULT_ADMIN_ROLE", [VOTING], [AGENT]),
            OZValidatedRole(ALLOWED_TOKENS_REGISTRY, "ADD_TOKEN_TO_ALLOWED_LIST_ROLE", [], [AGENT]),
            OZValidatedRole(ALLOWED_TOKENS_REGISTRY, "REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE", [], [AGENT]),   
        ],
    )

    to_be_executed_before_timestamp = 1748563200
    to_be_executed_from_time = 3600 * 4
    to_be_executed_to_time = 3600 * 22
    validate_dual_governance_submit_event(
        evs[53],    
        proposal_id=2,
        proposer=VOTING,
        executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
        metadata="Revoke RUN_SCRIPT_ROLE and EXECUTE_ROLE from Aragon Voting",
        proposal_calls=[
            {
                "target": TIME_CONSTRAINTS,
                "value": 0,
                "data": interface.TimeConstraints(TIME_CONSTRAINTS).checkTimeBeforeTimestampAndEmit.encode_input(
                    to_be_executed_before_timestamp
                ),
            },
            {
                "target": TIME_CONSTRAINTS,
                "value": 0,
                "data": interface.TimeConstraints(TIME_CONSTRAINTS).checkTimeWithinDayTimeAndEmit.encode_input(
                    to_be_executed_from_time, to_be_executed_to_time
                ),
            },
            {
                "target": AGENT,
                "value": 0,
                "data": agent_forward([(ACL, acl.revokePermission.encode_input(VOTING, AGENT, RUN_SCRIPT_ROLE.hex()))])[
                    1
                ],
            },
            {
                "target": AGENT,
                "value": 0,
                "data": agent_forward([(ACL, acl.revokePermission.encode_input(VOTING, AGENT, EXECUTE_ROLE.hex()))])[1],
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

    validate_dual_governance_governance_launch_verification_event(evs[54])

    validate_time_constraints_executed_before_event(evs[55], to_be_executed_before_timestamp)

    dg_evs = dg_events_from_trace(dg_tx, timelock=TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR)

    validate_dg_time_constraints_executed_before_event(dg_evs[0], to_be_executed_before_timestamp)

    validate_dg_time_constraints_executed_with_day_time_event(dg_evs[1], to_be_executed_from_time, to_be_executed_to_time)

    validate_dg_permission_revoke_event(dg_evs[2], Permission(entity=VOTING, app=AGENT, role=RUN_SCRIPT_ROLE.hex()))
    validate_dg_permission_revoke_event(dg_evs[3], Permission(entity=VOTING, app=AGENT, role=EXECUTE_ROLE.hex()))

    validate_dg_role_validated_event(
        dg_evs[4],
        [
            # Agent
            AragonValidatedPermission(AGENT, "RUN_SCRIPT_ROLE", [DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT_MANAGER], [VOTING], AGENT),
            AragonValidatedPermission(AGENT, "EXECUTE_ROLE", [DUAL_GOVERNANCE_ADMIN_EXECUTOR], [VOTING], AGENT),
        ],
    )

    # Validation that all entities can or cannot perform actions after the vote

    ldo_token = token_manager.token()

    # Lido Permissions Transition
    # 1. Voting has no permission to call STAKING_CONTROL_ROLE actions

    with reverts("APP_AUTH_FAILED"):
        lido.resumeStaking({"from": VOTING})

    # 2. Agent has permission to manage STAKING_CONTROL_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, STAKING_CONTROL_ROLE, acl, AGENT)

    # 3. Voting has no permission to call RESUME_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        lido.resume({"from": VOTING})

    # 4. Agent has permission to manage RESUME_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, RESUME_ROLE, acl, AGENT)

    # 5. Voting has no permission to call PAUSE_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        lido.stop({"from": VOTING})

    # 6. Agent has permission to manage PAUSE_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, PAUSE_ROLE, acl, AGENT)

    # 7. Voting has no permission to call UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        lido.unsafeChangeDepositedValidators(100, {"from": VOTING})

    # 8. Agent has permission to manage UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE, acl, AGENT)

    # 9. Voting has no permission to call STAKING_PAUSE_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        lido.pauseStaking({"from": VOTING})

    # 10. Agent has permission to manage STAKING_PAUSE_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, STAKING_PAUSE_ROLE, acl, AGENT)

    # DAOKernel Permissions Transition
    # 11. Voting has no permission to call APP_MANAGER_ROLE actions
    appId = "0x3b4bf6bf3ad5000ecf0f989d5befde585c6860fea3e574a4fab4c49d1c177d9c"
    with reverts("KERNEL_AUTH_FAILED"):
        interface.Kernel(KERNEL).newAppInstance(appId, ZERO_ADDRESS, {"from": VOTING})

    # 12. Agent has permission to manage APP_MANAGER_ROLE
    checkCanPerformAragonRoleManagement(stranger, KERNEL, APP_MANAGER_ROLE, acl, AGENT)

    # Voting Permissions Transition
    # 13. Voting has permission to call UNSAFELY_MODIFY_VOTE_TIME_ROLE actions
    assert voting.voteTime() != 1000000
    voting.unsafelyChangeVoteTime(1000000, {"from": VOTING})
    assert voting.voteTime() == 1000000

    checkCanPerformAragonRoleManagement(stranger, VOTING, UNSAFELY_MODIFY_VOTE_TIME_ROLE, acl, VOTING)

    # TokenManager Permissions Transition
    # 14. Voting has permission to call MINT_ROLE actions
    assert interface.ERC20(ldo_token).balanceOf(stranger) == 0
    token_manager.mint(stranger, 100, {"from": VOTING})
    assert interface.ERC20(ldo_token).balanceOf(stranger) == 100
    token_manager.burn(stranger, 100, {"from": VOTING})
    assert interface.ERC20(ldo_token).balanceOf(stranger) == 0

    checkCanPerformAragonRoleManagement(stranger, TOKEN_MANAGER, MINT_ROLE, acl, VOTING)

    # 15. Voting has permission to call REVOKE_VESTINGS_ROLE actions
    assert token_manager.vestingsLengths(stranger) == 0
    ASSIGN_ROLE = web3.keccak(text="ASSIGN_ROLE")
    acl.grantPermission(AGENT, TOKEN_MANAGER, ASSIGN_ROLE, {"from": VOTING})
    interface.ERC20(ldo_token).transfer(TOKEN_MANAGER, 100, {"from": ldo_holder})
    date_now = chain.time()
    token_manager.assignVested(stranger, 100, date_now + 1000, date_now + 2000, date_now + 3000, True, {"from": AGENT})
    assert token_manager.vestingsLengths(stranger) == 1
    token_manager.revokeVesting(stranger, 0, {"from": VOTING})

    checkCanPerformAragonRoleManagement(stranger, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE, acl, VOTING)

    # 16. Voting has permission to call BURN_ROLE actions
    ldo_holder_balance = interface.ERC20(ldo_token).balanceOf(ldo_holder)
    assert ldo_holder_balance > 100
    token_manager.burn(ldo_holder, 100, {"from": VOTING})
    assert interface.ERC20(ldo_token).balanceOf(ldo_holder) == ldo_holder_balance - 100

    checkCanPerformAragonRoleManagement(stranger, TOKEN_MANAGER, BURN_ROLE, acl, VOTING)

    # 17. Voting has permission to call ISSUE_ROLE actions
    token_manager_balance = interface.ERC20(ldo_token).balanceOf(TOKEN_MANAGER)
    token_manager.issue(100, {"from": VOTING})
    assert interface.ERC20(ldo_token).balanceOf(TOKEN_MANAGER) == token_manager_balance + 100

    checkCanPerformAragonRoleManagement(stranger, TOKEN_MANAGER, ISSUE_ROLE, acl, VOTING)

    # 18. Voting has permission to call CHANGE_PERIOD_ROLE actions
    period = finance.getPeriodDuration()
    finance.setPeriodDuration(100000, {"from": VOTING})
    assert finance.getPeriodDuration() == 100000

    checkCanPerformAragonRoleManagement(stranger, FINANCE, CHANGE_PERIOD_ROLE, acl, VOTING)

    # 19. Voting has permission to call CHANGE_BUDGETS_ROLE actions
    (budgets, _) = finance.getBudget(ldo_token)
    assert budgets != 1000
    finance.setBudget(ldo_token, 1000, {"from": VOTING})
    (budgets, _) = finance.getBudget(ldo_token)
    assert budgets == 1000

    checkCanPerformAragonRoleManagement(stranger, FINANCE, CHANGE_BUDGETS_ROLE, acl, VOTING)

    # EVMScriptRegistry Permissions Transition
    # 20. Voting has no permission to call REGISTRY_MANAGER_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.EVMScriptRegistry(EVM_SCRIPT_REGISTRY).disableScriptExecutor(0, {"from": VOTING})

    # 21. Agent has permission to manage REGISTRY_MANAGER_ROLE
    checkCanPerformAragonRoleManagement(stranger, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE, acl, AGENT)

    # 22. Voting has no permission to call REGISTRY_ADD_EXECUTOR_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.EVMScriptRegistry(EVM_SCRIPT_REGISTRY).addScriptExecutor(AGENT, {"from": VOTING})

    # 23. Agent has permission to manage REGISTRY_ADD_EXECUTOR_ROLE
    checkCanPerformAragonRoleManagement(stranger, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE, acl, AGENT)

    # CuratedModule Permissions Transition
    # 24. Agent has permission to manage STAKING_ROUTER_ROLE
    checkCanPerformAragonRoleManagement(stranger, CURATED_MODULE, STAKING_ROUTER_ROLE, acl, AGENT)

    # 25. Agent has permission to manage MANAGE_NODE_OPERATOR_ROLE
    checkCanPerformAragonRoleManagement(stranger, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE, acl, AGENT)

    # 26. Voting has no permission to call SET_NODE_OPERATOR_LIMIT_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(CURATED_MODULE).setNodeOperatorStakingLimit(1, 100, {"from": VOTING})

    # 27. Agent has permission to manage SET_NODE_OPERATOR_LIMIT_ROLE
    checkCanPerformAragonRoleManagement(stranger, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE, acl, AGENT)

    # 28. Voting has no permission to call MANAGE_SIGNING_KEYS actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(CURATED_MODULE).addSigningKeys(1, 0, "0x", "0x", {"from": VOTING})

    # 29. Agent has permission to manage MANAGE_SIGNING_KEYS
    checkCanPerformAragonRoleManagement(stranger, CURATED_MODULE, MANAGE_SIGNING_KEYS, acl, AGENT)

    # Simple DVT Module Permissions Transition
    # 30. Voting has no permission to call STAKING_ROUTER_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(SDVT_MODULE).onRewardsMinted(0, {"from": VOTING})

    # 31. Agent has permission to manage STAKING_ROUTER_ROLE
    checkCanPerformAragonRoleManagement(stranger, SDVT_MODULE, STAKING_ROUTER_ROLE, acl, AGENT)

    # 32. Voting has no permission to call MANAGE_NODE_OPERATOR_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(SDVT_MODULE).setStuckPenaltyDelay(0, {"from": VOTING})

    # 33. Agent has permission to manage MANAGE_NODE_OPERATOR_ROLE
    checkCanPerformAragonRoleManagement(stranger, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE, acl, AGENT)

    # 34. Voting has no permission to call SET_NODE_OPERATOR_LIMIT_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(SDVT_MODULE).setNodeOperatorStakingLimit(1, 100, {"from": VOTING})

    # 35. Agent has permission to manage SET_NODE_OPERATOR_LIMIT_ROLE
    checkCanPerformAragonRoleManagement(stranger, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE, acl, AGENT)

    # ACL Permissions Transition
    # 36. Agent has permission to create permissions
    random_permission = web3.keccak(text="RANDOM_PERMISSION")
    assert not acl.hasPermission(stranger, stranger, random_permission)
    acl.createPermission(stranger, stranger, random_permission, AGENT, {"from": AGENT})
    assert acl.hasPermission(stranger, stranger, random_permission)
    acl.revokePermission(stranger, stranger, random_permission, {"from": AGENT})

    # 37. Voting has no permission to call CREATE_PERMISSIONS_ROLE actions
    with reverts("ACL_AUTH_NO_MANAGER"):
        acl.grantPermission(stranger, stranger, random_permission, {"from": VOTING})

    # 38. Agent has permission to manage CREATE_PERMISSIONS_ROLE
    checkCanPerformAragonRoleManagement(stranger, ACL, CREATE_PERMISSIONS_ROLE, acl, AGENT)

    # WithdrawalQueue Roles Transition
    # 39. ResealManager has permission to call PAUSE_ROLE actions
    assert withdrawal_queue.isPaused() == False
    withdrawal_queue.pauseFor(100, {"from": RESEAL_MANAGER})
    assert withdrawal_queue.isPaused() == True

    # 40. ResealManager has permission to call RESUME_ROLE actions
    withdrawal_queue.resume({"from": RESEAL_MANAGER})
    assert withdrawal_queue.isPaused() == False

    # VEBO Roles Transition
    # 41. ResealManager has permission to call PAUSE_ROLE actions
    assert vebo.isPaused() == False
    vebo.pauseFor(100, {"from": RESEAL_MANAGER})
    assert vebo.isPaused() == True

    # 42. ResealManager has permission to call RESUME_ROLE actions
    vebo.resume({"from": RESEAL_MANAGER})
    assert vebo.isPaused() == False

    # AllowedTokensRegistry Roles Transition
    # 43. Voting has permission to call DEFAULT_ADMIN_ROLE actions
    allowed_tokens_registry.grantRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger, {"from": VOTING})
    assert allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger)
    allowed_tokens_registry.revokeRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger, {"from": VOTING})
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger)

    # 44. Agent has permission to call DEFAULT_ADMIN_ROLE actions

    with reverts(
        f"AccessControl: account {AGENT.lower()} is missing role 0x0000000000000000000000000000000000000000000000000000000000000000"
    ):
        allowed_tokens_registry.grantRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger, {"from": AGENT})

    # 45. Agent has no permission to call ADD_TOKEN_TO_ALLOWED_LIST_ROLE actions
    with reverts(f"AccessControl: account {AGENT.lower()} is missing role {ADD_TOKEN_TO_ALLOWED_LIST_ROLE.hex()}"):
        allowed_tokens_registry.addToken(ldo_token, {"from": AGENT})

    # 46. Agent has no permission to call REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE actions
    tokens = allowed_tokens_registry.getAllowedTokens()
    with reverts(f"AccessControl: account {AGENT.lower()} is missing role {REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE.hex()}"):
        allowed_tokens_registry.removeToken(tokens[0], {"from": AGENT})

    # WithdrawalVault Roles Transition
    # 47. Agent has permission to call proxy_getAdmin actions
    assert withdrawal_vault.proxy_getAdmin() == AGENT

    # Agent Permissions Transition
    # 48. DualGovernance Executor has permission to call RUN_SCRIPT_ROLE actions
    agent.forward("0x00000001", {"from": DUAL_GOVERNANCE_ADMIN_EXECUTOR})

    # 49. Voting has no permission to call RUN_SCRIPT_ROLE actions
    with reverts("AGENT_CAN_NOT_FORWARD"):
        agent.forward("0x00000001", {"from": VOTING})

    # 50. Agent has permission to manage RUN_SCRIPT_ROLE
    checkCanPerformAragonRoleManagement(stranger, AGENT, RUN_SCRIPT_ROLE, acl, AGENT)

    # 51. DualGovernance Executor has permission to call EXECUTE_ROLE actions
    agent.execute(stranger, 0, "0x", {"from": DUAL_GOVERNANCE_ADMIN_EXECUTOR})
    # 52. Voting has no permission to call EXECUTE_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        agent.execute(stranger, 0, "0x", {"from": VOTING})

    # 53. Agent has permission to manage EXECUTE_ROLE
    checkCanPerformAragonRoleManagement(stranger, AGENT, EXECUTE_ROLE, acl, AGENT)

    # DG 3 Voting has no permission to call RUN_SCRIPT_ROLE actions
    with reverts("AGENT_CAN_NOT_FORWARD"):
        agent.forward("0x00000001", {"from": VOTING})

    # DG 4 Voting has no permission to call EXECUTE_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        agent.execute(stranger, 0, "0x", {"from": VOTING})


def checkCanPerformAragonRoleManagement(entity, app, role, acl, actor):
    """
    Check if the actor can perform Aragon role management on the app with the given role
    :param entity: The entity to check
    :param app: The app to check
    :param role: The role to check
    :param actor: The actor performing the role management
    """
    assert acl.hasPermission(entity, app, role) == False
    acl.grantPermission(entity, app, role, {"from": actor})
    assert acl.hasPermission(entity, app, role) == True
    acl.revokePermission(entity, app, role, {"from": actor})
    assert acl.hasPermission(entity, app, role) == False

def dg_events_from_trace(receipt: TransactionReceipt, timelock: str, admin_executor: str) -> List[EventDict]:
    events = tx_events_from_receipt(receipt)

    assert len(events) >= 1, "Unexpected events count"
    assert (
        events[-1]["address"] == timelock and events[-1]["name"] == "ProposalExecuted"
    ), "Unexpected Dual Governance service event"

    groups = []
    current_group = []

    for event in events[:-1]:
        current_group.append(event)

        is_end_of_group = event["name"] == "Executed" and event["address"] == admin_executor

        if is_end_of_group:
            groups.append(current_group)
            current_group = []

    return [EventDict(group) for group in groups]


def test_dual_governance_acceptance():
    dg = interface.DualGovernance(DUAL_GOVERNANCE)

    RESEAL_COMMITTEE = "0x83BCE68B4e8b7071b2a664a26e6D3Bc17eEe3102"

    assert dg.getConfigProvider() == DUAL_GOVERNANCE_CONFIG_PROVIDER
    assert dg.TIMELOCK() == TIMELOCK

    assert dg.getResealManager() == RESEAL_MANAGER
    assert dg.getResealCommittee() == RESEAL_COMMITTEE

    proposer_data = dg.getProposer(VOTING)
    assert proposer_data[0] == VOTING
    assert proposer_data[1] == DUAL_GOVERNANCE_ADMIN_EXECUTOR

    assert dg.MAX_TIEBREAKER_ACTIVATION_TIMEOUT() == 1800 # 30 mins
    assert dg.MIN_TIEBREAKER_ACTIVATION_TIMEOUT() == 300 # 5 mins

    assert dg.MAX_SEALABLE_WITHDRAWAL_BLOCKERS_COUNT() == 255


def test_emergency_protected_timelock_acceptance():
    ept = interface.EmergencyProtectedTimelock(TIMELOCK)

    EMERGENCY_ACTIVATION_COMMITTEE = "0xA678c29cbFde2C74aF15C7724EE4b1527A50D45B"
    EMERGENCY_EXECUTION_COMMITTEE = "0x8E1Ce8995E370222CbD825fFD7Dce2A5BfE1E631"

    assert ept.MAX_AFTER_SCHEDULE_DELAY() == 1800 # 30 mins
    assert ept.MAX_AFTER_SUBMIT_DELAY() == 1800 # 30 mins
    assert ept.MAX_EMERGENCY_MODE_DURATION() == 2592000 # 30 days
    assert ept.MAX_EMERGENCY_PROTECTION_DURATION() == 63072000 # 2 years
    assert ept.MIN_EXECUTION_DELAY() == 120 # 2 mins

    assert ept.getAfterScheduleDelay() == 120 # 2 mins
    assert ept.getAfterSubmitDelay() == 120 # 2 mins

    assert ept.getAdminExecutor() == DUAL_GOVERNANCE_ADMIN_EXECUTOR
    assert ept.getGovernance() == DUAL_GOVERNANCE

    assert ept.isEmergencyModeActive() == False
    assert ept.isEmergencyProtectionEnabled() == True

    assert ept.getEmergencyActivationCommittee() == EMERGENCY_ACTIVATION_COMMITTEE
    assert ept.getEmergencyExecutionCommittee() == EMERGENCY_EXECUTION_COMMITTEE

    emergency_protection_details = ept.getEmergencyProtectionDetails()

    assert emergency_protection_details[0] == 86400
    assert emergency_protection_details[1] == 0
    assert emergency_protection_details[2] == 1777975200
    

def test_dual_governance_config_provider_acceptance():
    dgcp = interface.DualGovernanceConfigProvider(DUAL_GOVERNANCE_CONFIG_PROVIDER)

    FIRST_SEAL_RAGE_QUIT_SUPPORT = 3 * 10 ** 16  # 3% in PercentD16
    SECOND_SEAL_RAGE_QUIT_SUPPORT = 15 * 10 ** 16  # 15% in PercentD16
    MIN_ASSETS_LOCK_DURATION = 300  # 5 mins
    RAGE_QUIT_ETH_WITHDRAWALS_DELAY_GROWTH = 1200  # 20 mins
    RAGE_QUIT_ETH_WITHDRAWALS_MIN_DELAY = 600  # 10 min
    RAGE_QUIT_ETH_WITHDRAWALS_MAX_DELAY = 3600  # 1 hour
    RAGE_QUIT_EXTENSION_PERIOD_DURATION = 180  # 3 mins
    VETO_COOLDOWN_DURATION = 180  # 3 mins
    VETO_SIGNALLING_DEACTIVATION_MAX_DURATION = 300  # 5 mins
    VETO_SIGNALLING_MIN_ACTIVE_DURATION = 180  # 3 mins
    VETO_SIGNALLING_MAX_DURATION = 1800  # 30 mins
    VETO_SIGNALLING_MIN_DURATION = 300  # 5 mins

    assert dgcp.FIRST_SEAL_RAGE_QUIT_SUPPORT() == FIRST_SEAL_RAGE_QUIT_SUPPORT
    assert dgcp.SECOND_SEAL_RAGE_QUIT_SUPPORT() == SECOND_SEAL_RAGE_QUIT_SUPPORT
    assert dgcp.MIN_ASSETS_LOCK_DURATION() == MIN_ASSETS_LOCK_DURATION
    assert dgcp.RAGE_QUIT_ETH_WITHDRAWALS_DELAY_GROWTH() == RAGE_QUIT_ETH_WITHDRAWALS_DELAY_GROWTH
    assert dgcp.RAGE_QUIT_ETH_WITHDRAWALS_MIN_DELAY() == RAGE_QUIT_ETH_WITHDRAWALS_MIN_DELAY
    assert dgcp.RAGE_QUIT_ETH_WITHDRAWALS_MAX_DELAY() == RAGE_QUIT_ETH_WITHDRAWALS_MAX_DELAY
    assert dgcp.RAGE_QUIT_EXTENSION_PERIOD_DURATION() == RAGE_QUIT_EXTENSION_PERIOD_DURATION
    assert dgcp.VETO_COOLDOWN_DURATION() == VETO_COOLDOWN_DURATION
    assert dgcp.VETO_SIGNALLING_DEACTIVATION_MAX_DURATION() == VETO_SIGNALLING_DEACTIVATION_MAX_DURATION
    assert dgcp.VETO_SIGNALLING_MIN_ACTIVE_DURATION() == VETO_SIGNALLING_MIN_ACTIVE_DURATION
    assert dgcp.VETO_SIGNALLING_MAX_DURATION() == VETO_SIGNALLING_MAX_DURATION
    assert dgcp.VETO_SIGNALLING_MIN_DURATION() == VETO_SIGNALLING_MIN_DURATION

    config = dgcp.getDualGovernanceConfig()

    assert config[0] == FIRST_SEAL_RAGE_QUIT_SUPPORT
    assert config[1] == SECOND_SEAL_RAGE_QUIT_SUPPORT
    assert config[2] == MIN_ASSETS_LOCK_DURATION
    assert config[3] == VETO_SIGNALLING_MIN_DURATION
    assert config[4] == VETO_SIGNALLING_MAX_DURATION
    assert config[5] == VETO_SIGNALLING_MIN_ACTIVE_DURATION
    assert config[6] == VETO_SIGNALLING_DEACTIVATION_MAX_DURATION
    assert config[7] == VETO_COOLDOWN_DURATION
    assert config[8] == RAGE_QUIT_EXTENSION_PERIOD_DURATION
    assert config[9] == RAGE_QUIT_ETH_WITHDRAWALS_MIN_DELAY
    assert config[10] == RAGE_QUIT_ETH_WITHDRAWALS_MAX_DELAY
    assert config[11] == RAGE_QUIT_ETH_WITHDRAWALS_DELAY_GROWTH
