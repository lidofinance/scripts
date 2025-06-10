import pytest

from typing import NamedTuple, List
from brownie import web3, chain, interface, ZERO_ADDRESS, reverts, accounts, convert
from hexbytes import HexBytes
from scripts.vote_2025_06_25_mainnet_dg_launch import start_vote
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
from utils.test.event_validators.rewards_manager import validate_ownership_transferred_event, OwnershipTransferred


DUAL_GOVERNANCE = "0xcdF49b058D606AD34c5789FD8c3BF8B3E54bA2db"
TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
RESEAL_MANAGER = "0x7914b5a1539b97Bd0bbd155757F25FD79A522d24"
DAO_EMERGENCY_GOVERNANCE = "0x553337946F2FAb8911774b20025fa776B76a7CcE"
TIME_CONSTRAINTS = "0x2a30F5aC03187674553024296bed35Aa49749DDa"
ROLES_VALIDATOR = "0x31534e3aFE219B609da3715a00a1479D2A2d7981"

DAO_EMERGENCY_GOVERNANCE_DRY_RUN = "0x75850938C1Aa50B8cC6eb3c00995759dc1425ae6"


# These addresses can be checked on https://docs.lido.fi/deployed-contracts
ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
LIDO = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
KERNEL = "0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
TOKEN_MANAGER = "0xf73a1260d222f447210581DDf212D915c09a3249"
FINANCE = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EVM_SCRIPT_REGISTRY = "0x853cc0D5917f49B57B8e9F89e491F5E18919093A"
CURATED_MODULE = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
SDVT_MODULE = "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433"
ALLOWED_TOKENS_REGISTRY = "0x4AC40c34f8992bb1e5E856A448792158022551ca"
WITHDRAWAL_VAULT = "0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f"
WITHDRAWAL_QUEUE = "0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1"
VEBO = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
GATE_SEAL = "0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
INSURANCE_FUND = "0x8B3f33234ABD88493c0Cd28De33D583B70beDe35"
CS_MODULE = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
CS_ACCOUNTING = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"
CS_FEE_ORACLE = "0x4D4074628678Bd302921c20573EEa1ed38DdF7FB"
CS_GATE_SEAL = "0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0"
LDO_TOKEN = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"


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


def _validate_role_events(event: EventDict, roles: list, extra_events: list = None, log_script_count: int = 1, emitted_by: str = None):
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

    assert event.count("LogScriptCall") == log_script_count, "Wrong number of LogScriptCall events"
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
        if emitted_by is not None:
            assert convert.to_address(ev["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"

def validate_role_validated_event(event: EventDict, roles: list, emitted_by: str = None) -> None:
    _validate_role_events(event, roles, emitted_by=emitted_by)

def validate_dg_role_validated_event(event: EventDict, roles: list, emitted_by: str = None) -> None:
    _validate_role_events(event, roles, extra_events=["ScriptResult", "Executed"], log_script_count=0, emitted_by=emitted_by)

def validate_dual_governance_governance_launch_verification_event(event: EventDict):
    _events_chain = ["LogScriptCall", "DGLaunchConfigurationValidated"]

    print(event)

    validate_events_chain([e.name for e in event], _events_chain)

def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):
    voting = interface.Voting(VOTING)
    acl = interface.ACL(ACL)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    agent = interface.Agent(AGENT)
    lido = interface.Lido(LIDO)
    token_manager = interface.TokenManager(TOKEN_MANAGER)
    ldo_token = interface.ERC20(LDO_TOKEN)
    finance = interface.Finance(FINANCE)

    # Lido Permissions Transition
    STAKING_CONTROL_ROLE = web3.keccak(text="STAKING_CONTROL_ROLE")
    assert acl.hasPermission(VOTING, LIDO, STAKING_CONTROL_ROLE)
    assert acl.getPermissionManager(LIDO, STAKING_CONTROL_ROLE) == VOTING

    RESUME_ROLE = web3.keccak(text="RESUME_ROLE")
    assert acl.hasPermission(VOTING, LIDO, RESUME_ROLE)
    assert acl.getPermissionManager(LIDO, RESUME_ROLE) == VOTING

    PAUSE_ROLE = web3.keccak(text="PAUSE_ROLE")
    assert acl.hasPermission(VOTING, LIDO, PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, PAUSE_ROLE) == VOTING

    STAKING_PAUSE_ROLE = web3.keccak(text="STAKING_PAUSE_ROLE")
    assert acl.hasPermission(VOTING, LIDO, STAKING_PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, STAKING_PAUSE_ROLE) == VOTING

    # DAOKernel Permissions Transition
    APP_MANAGER_ROLE = web3.keccak(text="APP_MANAGER_ROLE")
    assert acl.hasPermission(VOTING, KERNEL, APP_MANAGER_ROLE)
    assert acl.getPermissionManager(KERNEL, APP_MANAGER_ROLE) == VOTING

    # TokenManager Permissions Transition
    MINT_ROLE = web3.keccak(text="MINT_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, MINT_ROLE)
    assert not acl.getPermissionManager(TOKEN_MANAGER, MINT_ROLE) == VOTING

    REVOKE_VESTINGS_ROLE = web3.keccak(text="REVOKE_VESTINGS_ROLE")
    assert not acl.hasPermission(VOTING, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert not acl.getPermissionManager(TOKEN_MANAGER, REVOKE_VESTINGS_ROLE) == VOTING

    # Finance permissions checks
    CHANGE_PERIOD_ROLE = web3.keccak(text="CHANGE_PERIOD_ROLE")
    assert not acl.hasPermission(VOTING, FINANCE, CHANGE_PERIOD_ROLE)
    assert not acl.getPermissionManager(FINANCE, CHANGE_PERIOD_ROLE) == VOTING

    CHANGE_BUDGETS_ROLE = web3.keccak(text="CHANGE_BUDGETS_ROLE")
    assert not acl.hasPermission(VOTING, FINANCE, CHANGE_BUDGETS_ROLE)
    assert not acl.getPermissionManager(FINANCE, CHANGE_BUDGETS_ROLE) == VOTING

    # EVMScriptRegistry permissions checks
    REGISTRY_ADD_EXECUTOR_ROLE = web3.keccak(text="REGISTRY_ADD_EXECUTOR_ROLE")
    assert acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE) == VOTING

    REGISTRY_MANAGER_ROLE = web3.keccak(text="REGISTRY_MANAGER_ROLE")
    assert acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE) == VOTING

    # CuratedModule permissions checks
    STAKING_ROUTER_ROLE = web3.keccak(text="STAKING_ROUTER_ROLE")
    assert acl.getPermissionManager(CURATED_MODULE, STAKING_ROUTER_ROLE) == VOTING
    assert acl.hasPermission(STAKING_ROUTER, CURATED_MODULE, STAKING_ROUTER_ROLE)
    
    MANAGE_NODE_OPERATOR_ROLE = web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING
    
    SET_NODE_OPERATOR_LIMIT_ROLE = web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING
    assert acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)

    MANAGE_SIGNING_KEYS = web3.keccak(text="MANAGE_SIGNING_KEYS")
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == VOTING
    assert acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)

    # Simple DVT Module permissions checks
    assert acl.getPermissionManager(SDVT_MODULE, STAKING_ROUTER_ROLE) == VOTING
    assert acl.getPermissionManager(SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING
    assert acl.getPermissionManager(SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING

    assert acl.hasPermission(STAKING_ROUTER, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)

    # ACL permissions checks
    CREATE_PERMISSIONS_ROLE = web3.keccak(text="CREATE_PERMISSIONS_ROLE")
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == VOTING
    assert acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)
    assert not acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)

    # Agent permissions checks
    RUN_SCRIPT_ROLE = web3.keccak(text="RUN_SCRIPT_ROLE")
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == VOTING
    assert acl.hasPermission(VOTING, AGENT, RUN_SCRIPT_ROLE)

    EXECUTE_ROLE = web3.keccak(text="EXECUTE_ROLE")
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == VOTING
    assert acl.hasPermission(VOTING, AGENT, EXECUTE_ROLE)

    # WithdrawalQueue and VEBO permissions checks
    withdrawal_queue = interface.WithdrawalQueue(WITHDRAWAL_QUEUE)
    assert not withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(PAUSE_ROLE, GATE_SEAL)
    
    vebo = interface.ValidatorsExitBusOracle(VEBO)
    assert not vebo.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not vebo.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert vebo.hasRole(PAUSE_ROLE, GATE_SEAL)

    # CSM permissions checks
    csm = interface.CSModule(CS_MODULE)
    assert not csm.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not csm.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert csm.hasRole(PAUSE_ROLE, CS_GATE_SEAL)

    cs_accounting = interface.CSAccounting(CS_ACCOUNTING)
    assert not cs_accounting.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not cs_accounting.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert cs_accounting.hasRole(PAUSE_ROLE, CS_GATE_SEAL)

    cs_fee_oracle = interface.CSFeeOracle(CS_FEE_ORACLE)
    assert not cs_fee_oracle.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not cs_fee_oracle.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert cs_fee_oracle.hasRole(PAUSE_ROLE, CS_GATE_SEAL)

    # AllowedTokensRegistry permissions checks
    allowed_tokens_registry = interface.AllowedTokensRegistry(ALLOWED_TOKENS_REGISTRY)
    DEFAULT_ADMIN_ROLE = HexBytes(0)
    assert allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, AGENT)
    assert not allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, VOTING)
    
    ADD_TOKEN_TO_ALLOWED_LIST_ROLE = web3.keccak(text="ADD_TOKEN_TO_ALLOWED_LIST_ROLE")
    assert allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, AGENT)
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, VOTING)
    
    REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE = web3.keccak(text="REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE")
    assert allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, AGENT)
    assert not allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, VOTING)

    # WithdrawalVault Roles Transition
    withdrawal_vault = interface.WithdrawalContractProxy(WITHDRAWAL_VAULT)
    assert withdrawal_vault.proxy_getAdmin() == VOTING

    # Verify current owner of InsuranceFund
    insurance_fund = interface.InsuranceFund(INSURANCE_FUND)
    assert insurance_fund.owner() == AGENT

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

    vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)

    # After aragon voting checks - Lido permissions
    assert acl.getPermissionManager(LIDO, STAKING_CONTROL_ROLE) == AGENT
    assert acl.getPermissionManager(LIDO, RESUME_ROLE) == AGENT
    assert acl.getPermissionManager(LIDO, PAUSE_ROLE) == AGENT
    assert acl.getPermissionManager(LIDO, STAKING_PAUSE_ROLE) == AGENT
    
    assert not acl.hasPermission(VOTING, LIDO, STAKING_CONTROL_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, RESUME_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, PAUSE_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, STAKING_PAUSE_ROLE)

    # DAOKernel permissions checks
    assert acl.getPermissionManager(KERNEL, APP_MANAGER_ROLE) == AGENT
    assert not acl.hasPermission(VOTING, KERNEL, APP_MANAGER_ROLE)

    # TokenManager permissions checks
    assert acl.getPermissionManager(TOKEN_MANAGER, MINT_ROLE) == VOTING
    assert acl.getPermissionManager(TOKEN_MANAGER, REVOKE_VESTINGS_ROLE) == VOTING
    
    assert acl.hasPermission(VOTING, TOKEN_MANAGER, MINT_ROLE)
    assert acl.hasPermission(VOTING, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)

    # Finance permissions checks
    assert acl.getPermissionManager(FINANCE, CHANGE_PERIOD_ROLE) == VOTING
    assert acl.getPermissionManager(FINANCE, CHANGE_BUDGETS_ROLE) == VOTING
    
    assert acl.hasPermission(VOTING, FINANCE, CHANGE_PERIOD_ROLE)
    assert acl.hasPermission(VOTING, FINANCE, CHANGE_BUDGETS_ROLE)

    # EVMScriptRegistry permissions checks
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE) == AGENT
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE) == AGENT
    
    assert not acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert not acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)

    # CuratedModule permissions checks
    assert acl.getPermissionManager(CURATED_MODULE, STAKING_ROUTER_ROLE) == AGENT
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == AGENT
    
    assert not acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)

    assert acl.hasPermission(STAKING_ROUTER, CURATED_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)

    # Simple DVT Module permissions checks
    assert acl.getPermissionManager(SDVT_MODULE, STAKING_ROUTER_ROLE) == AGENT
    assert acl.getPermissionManager(SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT
    assert acl.getPermissionManager(SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT

    assert acl.hasPermission(STAKING_ROUTER, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, STAKING_ROUTER_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.hasPermission(EVM_SCRIPT_EXECUTOR, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    
    # ACL permissions checks
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == AGENT
    assert not acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)

    # Agent permissions checks
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == AGENT
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == AGENT
    
    assert acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT, RUN_SCRIPT_ROLE)
    assert acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT, EXECUTE_ROLE)

    # CSM permissions checks
    assert csm.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert csm.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert csm.hasRole(PAUSE_ROLE, CS_GATE_SEAL)

    assert cs_accounting.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert cs_accounting.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert cs_accounting.hasRole(PAUSE_ROLE, CS_GATE_SEAL)

    assert cs_fee_oracle.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert cs_fee_oracle.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert cs_fee_oracle.hasRole(PAUSE_ROLE, CS_GATE_SEAL)

    # WithdrawalQueue and VEBO permissions checks
    assert withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(PAUSE_ROLE, GATE_SEAL)
    assert vebo.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert vebo.hasRole(RESUME_ROLE, RESEAL_MANAGER)
    assert vebo.hasRole(PAUSE_ROLE, GATE_SEAL)

    # AllowedTokensRegistry permissions checks
    assert not allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, AGENT)
    assert allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, VOTING)
    
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, AGENT)
    assert not allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, AGENT)

    # Verify new admin of WithdrawalVault
    assert withdrawal_vault.proxy_getAdmin() == AGENT
    
    # Verify InsuranceFund owner has been changed to VOTING
    assert insurance_fund.owner() == VOTING

    chain.sleep(timelock.getAfterSubmitDelay() + 1)

    dual_governance.scheduleProposal(2, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)

    dg_tx: TransactionReceipt = timelock.execute(2, {"from": stranger})

    # After launch permissions checks
    assert not acl.hasPermission(VOTING, AGENT, RUN_SCRIPT_ROLE)
    assert not acl.hasPermission(VOTING, AGENT, EXECUTE_ROLE)

    evs = group_voting_events_from_receipt(vote_tx)

    # 54 events
    assert len(evs) == 54

    # metadata = find_metadata_by_vote_id(vote_id)
    # assert get_lido_vote_cid_from_str(metadata) == "bafkreia2qh6xvoowgwukqfyyer2zz266e2jifxovnddgqawruhe2g5asgi"

    assert count_vote_items_by_events(vote_tx, voting) == 54, "Incorrect voting items count"

    # Lido Permissions Transition
    validate_permission_revoke_event(evs[0], Permission(entity=VOTING, app=LIDO, role=STAKING_CONTROL_ROLE.hex()), emitted_by=ACL)
    validate_set_permission_manager_event(evs[1], app=LIDO, role=STAKING_CONTROL_ROLE.hex(), manager=AGENT, emitted_by=ACL)
    validate_permission_revoke_event(evs[2], Permission(entity=VOTING, app=LIDO, role=RESUME_ROLE.hex()), emitted_by=ACL)
    validate_set_permission_manager_event(evs[3], app=LIDO, role=RESUME_ROLE.hex(), manager=AGENT, emitted_by=ACL)
    validate_permission_revoke_event(evs[4], Permission(entity=VOTING, app=LIDO, role=PAUSE_ROLE.hex()), emitted_by=ACL)
    validate_set_permission_manager_event(evs[5], app=LIDO, role=PAUSE_ROLE.hex(), manager=AGENT, emitted_by=ACL)
    validate_permission_revoke_event(evs[6], Permission(entity=VOTING, app=LIDO, role=STAKING_PAUSE_ROLE.hex()), emitted_by=ACL)
    validate_set_permission_manager_event(evs[7], app=LIDO, role=STAKING_PAUSE_ROLE.hex(), manager=AGENT, emitted_by=ACL)

    # DAOKernel Permissions Transition
    validate_permission_revoke_event(evs[8], Permission(entity=VOTING, app=KERNEL, role=APP_MANAGER_ROLE.hex()), emitted_by=ACL)
    validate_set_permission_manager_event(evs[9], app=KERNEL, role=APP_MANAGER_ROLE.hex(), manager=AGENT, emitted_by=ACL)

    # TokenManager Permissions Transition
    validate_permission_create_event(
        evs[10], Permission(entity=VOTING, app=TOKEN_MANAGER, role=MINT_ROLE.hex()), VOTING, emitted_by=ACL
    )
    validate_permission_create_event(
        evs[11], Permission(entity=VOTING, app=TOKEN_MANAGER, role=REVOKE_VESTINGS_ROLE.hex()), VOTING, emitted_by=ACL
    )

    # Finance Permissions Transition
    validate_permission_create_event(
        evs[12], Permission(entity=VOTING, app=FINANCE, role=CHANGE_PERIOD_ROLE.hex()), VOTING, emitted_by=ACL
    )
    validate_permission_create_event(
        evs[13], Permission(entity=VOTING, app=FINANCE, role=CHANGE_BUDGETS_ROLE.hex()), VOTING, emitted_by=ACL
    )

    # EVMScriptRegistry Permissions Transition
    validate_permission_revoke_event(
        evs[14], Permission(entity=VOTING, app=EVM_SCRIPT_REGISTRY, role=REGISTRY_ADD_EXECUTOR_ROLE.hex()), emitted_by=ACL
    )
    validate_set_permission_manager_event(
        evs[15], app=EVM_SCRIPT_REGISTRY, role=REGISTRY_ADD_EXECUTOR_ROLE.hex(), manager=AGENT, emitted_by=ACL
    )
    validate_permission_revoke_event(
        evs[16], Permission(entity=VOTING, app=EVM_SCRIPT_REGISTRY, role=REGISTRY_MANAGER_ROLE.hex()), emitted_by=ACL
    )
    validate_set_permission_manager_event(
        evs[17], app=EVM_SCRIPT_REGISTRY, role=REGISTRY_MANAGER_ROLE.hex(), manager=AGENT, emitted_by=ACL
    )

    # CuratedModule Permissions Transition
    validate_set_permission_manager_event(evs[18], app=CURATED_MODULE, role=STAKING_ROUTER_ROLE.hex(), manager=AGENT, emitted_by=ACL)
    validate_set_permission_manager_event(
        evs[19], app=CURATED_MODULE, role=MANAGE_NODE_OPERATOR_ROLE.hex(), manager=AGENT, emitted_by=ACL
    )
    validate_permission_revoke_event(
        evs[20], Permission(entity=VOTING, app=CURATED_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex()), emitted_by=ACL
    )
    validate_set_permission_manager_event(
        evs[21], app=CURATED_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex(), manager=AGENT, emitted_by=ACL
    )
    validate_permission_revoke_event(
        evs[22], Permission(entity=VOTING, app=CURATED_MODULE, role=MANAGE_SIGNING_KEYS.hex()), emitted_by=ACL
    )
    validate_set_permission_manager_event(evs[23], app=CURATED_MODULE, role=MANAGE_SIGNING_KEYS.hex(), manager=AGENT, emitted_by=ACL)

    # Simple DVT Module Permissions Transition
    validate_set_permission_manager_event(evs[24], app=SDVT_MODULE, role=STAKING_ROUTER_ROLE.hex(), manager=AGENT, emitted_by=ACL)
    validate_set_permission_manager_event(evs[25], app=SDVT_MODULE, role=MANAGE_NODE_OPERATOR_ROLE.hex(), manager=AGENT, emitted_by=ACL)
    validate_set_permission_manager_event(
        evs[26], app=SDVT_MODULE, role=SET_NODE_OPERATOR_LIMIT_ROLE.hex(), manager=AGENT, emitted_by=ACL
    )

    # ACL Permissions Transition
    validate_permission_grant_event(evs[27], Permission(entity=AGENT, app=ACL, role=CREATE_PERMISSIONS_ROLE.hex()), emitted_by=ACL)
    validate_permission_revoke_event(evs[28], Permission(entity=VOTING, app=ACL, role=CREATE_PERMISSIONS_ROLE.hex()), emitted_by=ACL)
    validate_set_permission_manager_event(evs[29], app=ACL, role=CREATE_PERMISSIONS_ROLE.hex(), manager=AGENT, emitted_by=ACL)

    # Agent Permissions Transition
    validate_permission_grant_event(
        evs[30], Permission(entity=DUAL_GOVERNANCE_ADMIN_EXECUTOR, app=AGENT, role=RUN_SCRIPT_ROLE.hex()), emitted_by=ACL
    )
    validate_set_permission_manager_event(evs[31], app=AGENT, role=RUN_SCRIPT_ROLE.hex(), manager=AGENT, emitted_by=ACL)

    validate_permission_grant_event(
        evs[32], Permission(entity=DUAL_GOVERNANCE_ADMIN_EXECUTOR, app=AGENT, role=EXECUTE_ROLE.hex()), emitted_by=ACL
    )
    validate_set_permission_manager_event(evs[33], app=AGENT, role=EXECUTE_ROLE.hex(), manager=AGENT, emitted_by=ACL)

    # WithdrawalQueue Roles Transition
    validate_grant_role_event(evs[34], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex(), emitted_by=WITHDRAWAL_QUEUE)
    validate_grant_role_event(evs[35], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex(), emitted_by=WITHDRAWAL_QUEUE)

    # VEBO Roles Transition
    validate_grant_role_event(evs[36], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex(), emitted_by=VEBO)
    validate_grant_role_event(evs[37], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex(), emitted_by=VEBO)

    # CS Module Roles Transition
    validate_grant_role_event(evs[38], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex(), emitted_by=CS_MODULE)
    validate_grant_role_event(evs[39], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex(), emitted_by=CS_MODULE)

    # CS Accounting Roles Transition
    validate_grant_role_event(evs[40], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex(), emitted_by=CS_ACCOUNTING)
    validate_grant_role_event(evs[41], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex(), emitted_by=CS_ACCOUNTING)

    # CS Fee Oracle Roles Transition
    validate_grant_role_event(evs[42], grant_to=RESEAL_MANAGER, sender=AGENT, role=PAUSE_ROLE.hex(), emitted_by=CS_FEE_ORACLE)
    validate_grant_role_event(evs[43], grant_to=RESEAL_MANAGER, sender=AGENT, role=RESUME_ROLE.hex(), emitted_by=CS_FEE_ORACLE)

    # AllowedTokensRegistry Roles Transition
    validate_grant_role_event(evs[44], grant_to=VOTING, sender=AGENT, role=DEFAULT_ADMIN_ROLE.hex(), emitted_by=ALLOWED_TOKENS_REGISTRY)
    validate_revoke_role_event(evs[45], revoke_from=AGENT, sender=VOTING, role=DEFAULT_ADMIN_ROLE.hex(), emitted_by=ALLOWED_TOKENS_REGISTRY)
    validate_revoke_role_event(evs[46], revoke_from=AGENT, sender=VOTING, role=ADD_TOKEN_TO_ALLOWED_LIST_ROLE.hex(), emitted_by=ALLOWED_TOKENS_REGISTRY)
    validate_revoke_role_event(
        evs[47], revoke_from=AGENT, sender=VOTING, role=REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE.hex(), emitted_by=ALLOWED_TOKENS_REGISTRY
    )

    # WithdrawalVault ownership Transition
    validate_proxy_admin_changed(evs[48], VOTING, AGENT, emitted_by=WITHDRAWAL_VAULT)

    # InsuranceFund ownership Transition
    validate_ownership_transferred_event(evs[49], OwnershipTransferred(previous_owner_addr=AGENT, new_owner_addr=VOTING), emitted_by=INSURANCE_FUND)

    validate_role_validated_event(
        evs[50],
        [
            # Lido
            AragonValidatedPermission(LIDO, "STAKING_CONTROL_ROLE", [], [VOTING], AGENT),
            AragonValidatedPermission(LIDO, "RESUME_ROLE", [], [VOTING], AGENT),
            AragonValidatedPermission(LIDO, "PAUSE_ROLE", [], [VOTING], AGENT),
            AragonValidatedPermission(LIDO, "STAKING_PAUSE_ROLE", [], [VOTING], AGENT),

            # DAOKernel
            AragonValidatedPermission(KERNEL, "APP_MANAGER_ROLE", [], [VOTING], AGENT),

            # TokenManager
            AragonValidatedPermission(TOKEN_MANAGER, "MINT_ROLE", [VOTING], [], VOTING),
            AragonValidatedPermission(TOKEN_MANAGER, "REVOKE_VESTINGS_ROLE", [VOTING], [], VOTING),

            # Finance
            AragonValidatedPermission(FINANCE, "CHANGE_PERIOD_ROLE", [VOTING], [], VOTING),
            AragonValidatedPermission(FINANCE, "CHANGE_BUDGETS_ROLE", [VOTING], [], VOTING),

            # Aragon EVMScriptRegistry
            AragonValidatedPermission(EVM_SCRIPT_REGISTRY, "REGISTRY_ADD_EXECUTOR_ROLE", [], [VOTING], AGENT),
            AragonValidatedPermission(EVM_SCRIPT_REGISTRY, "REGISTRY_MANAGER_ROLE", [], [VOTING], AGENT),

            # CuratedModule
            AragonValidatedPermission(CURATED_MODULE, "STAKING_ROUTER_ROLE", [STAKING_ROUTER], [], AGENT),
            AragonValidatedPermission(CURATED_MODULE, "MANAGE_NODE_OPERATOR_ROLE", [AGENT], [], AGENT),
            AragonValidatedPermission(CURATED_MODULE, "SET_NODE_OPERATOR_LIMIT_ROLE", [EVM_SCRIPT_EXECUTOR], [VOTING], AGENT),
            AragonValidatedPermission(CURATED_MODULE, "MANAGE_SIGNING_KEYS", [], [VOTING], AGENT),

            # SDVTModule
            AragonValidatedPermission(SDVT_MODULE, "STAKING_ROUTER_ROLE", [STAKING_ROUTER, EVM_SCRIPT_EXECUTOR], [], AGENT),
            AragonValidatedPermission(SDVT_MODULE, "MANAGE_NODE_OPERATOR_ROLE", [EVM_SCRIPT_EXECUTOR], [], AGENT),
            AragonValidatedPermission(SDVT_MODULE, "SET_NODE_OPERATOR_LIMIT_ROLE", [EVM_SCRIPT_EXECUTOR], [], AGENT),

            # ACL
            AragonValidatedPermission(ACL, "CREATE_PERMISSIONS_ROLE", [AGENT], [VOTING], AGENT),

            # Agent
            AragonValidatedPermission(AGENT, "RUN_SCRIPT_ROLE", [VOTING, DUAL_GOVERNANCE_ADMIN_EXECUTOR], [], AGENT),
            AragonValidatedPermission(AGENT, "EXECUTE_ROLE", [VOTING, DUAL_GOVERNANCE_ADMIN_EXECUTOR], [], AGENT),

            # WithdrawalQueue (OZ)
            OZValidatedRole(WITHDRAWAL_QUEUE, "PAUSE_ROLE", [RESEAL_MANAGER, GATE_SEAL], []),
            OZValidatedRole(WITHDRAWAL_QUEUE, "RESUME_ROLE", [RESEAL_MANAGER], []),

            # VEBO (OZ)
            OZValidatedRole(VEBO, "PAUSE_ROLE", [RESEAL_MANAGER, GATE_SEAL], []),
            OZValidatedRole(VEBO, "RESUME_ROLE", [RESEAL_MANAGER], []),

            # CS Module (OZ)
            OZValidatedRole(CS_MODULE, "PAUSE_ROLE", [RESEAL_MANAGER, CS_GATE_SEAL], []),
            OZValidatedRole(CS_MODULE, "RESUME_ROLE", [RESEAL_MANAGER], []),
            
            # CS Accounting (OZ)
            OZValidatedRole(CS_ACCOUNTING, "PAUSE_ROLE", [RESEAL_MANAGER, CS_GATE_SEAL], []),
            OZValidatedRole(CS_ACCOUNTING, "RESUME_ROLE", [RESEAL_MANAGER], []),
            
            # CS Fee Oracle (OZ)
            OZValidatedRole(CS_FEE_ORACLE, "PAUSE_ROLE", [RESEAL_MANAGER, CS_GATE_SEAL], []),
            OZValidatedRole(CS_FEE_ORACLE, "RESUME_ROLE", [RESEAL_MANAGER], []),

            # AllowedTokensRegistry (OZ)
            OZValidatedRole(ALLOWED_TOKENS_REGISTRY, "DEFAULT_ADMIN_ROLE", [VOTING], [AGENT]),
            OZValidatedRole(ALLOWED_TOKENS_REGISTRY, "ADD_TOKEN_TO_ALLOWED_LIST_ROLE", [], [AGENT]),
            OZValidatedRole(ALLOWED_TOKENS_REGISTRY, "REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE", [], [AGENT]),   
        ],
        emitted_by=ROLES_VALIDATOR,
    )
    
    # Submit first dual governance proposal
    to_be_executed_before_timestamp_proposal = 1754071200
    to_be_executed_from_time = 3600 * 6  # 06:00 UTC
    to_be_executed_to_time = 3600 * 18 # 18:00 UTC
    
    validate_dual_governance_submit_event(
        evs[51],    
        proposal_id=2,
        proposer=VOTING,
        executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
        metadata="Revoke RUN_SCRIPT_ROLE and EXECUTE_ROLE from Aragon Voting",
        proposal_calls=[
            {
                "target": TIME_CONSTRAINTS,
                "value": 0,
                "data": interface.TimeConstraints(TIME_CONSTRAINTS).checkTimeBeforeTimestampAndEmit.encode_input(
                    to_be_executed_before_timestamp_proposal
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
                "target": ROLES_VALIDATOR,
                "value": 0,
                "data": interface.RolesValidator(ROLES_VALIDATOR).validateDGProposalLaunchPhase.encode_input(),
            },
        ],
        emitted_by=TIMELOCK,
    )

    # Validate roles were transferred correctly
    validate_dual_governance_governance_launch_verification_event(evs[52])
    
    # Verify state of the DG after launch
    to_be_executed_before_timestamp = 1753466400
    validate_time_constraints_executed_before_event(evs[53], to_be_executed_before_timestamp, emitted_by=TIME_CONSTRAINTS)

    # Check DG execution events
    dg_evs = group_dg_events_from_receipt(dg_tx, timelock=TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR)

    # Execution is allowed before Tuesday, 15 July 2025 00:00:00
    validate_dg_time_constraints_executed_before_event(dg_evs[0], to_be_executed_before_timestamp_proposal, emitted_by=TIME_CONSTRAINTS)

    # Execution is allowed since 04:00 to 22:00 UTC
    validate_dg_time_constraints_executed_with_day_time_event(dg_evs[1], to_be_executed_from_time, to_be_executed_to_time, emitted_by=TIME_CONSTRAINTS)

    # Revoke RUN_SCRIPT_ROLE permission from Voting on Agent
    validate_dg_permission_revoke_event(dg_evs[2], Permission(entity=VOTING, app=AGENT, role=RUN_SCRIPT_ROLE.hex()), emitted_by=ACL)
    
    # Revoke EXECUTE_ROLE permission from Voting on Agent
    validate_dg_permission_revoke_event(dg_evs[3], Permission(entity=VOTING, app=AGENT, role=EXECUTE_ROLE.hex()), emitted_by=ACL)

    # Validate roles were updated correctly
    validate_dg_role_validated_event(
        dg_evs[4],
        [
            # Agent
            AragonValidatedPermission(AGENT, "RUN_SCRIPT_ROLE", [DUAL_GOVERNANCE_ADMIN_EXECUTOR], [VOTING], AGENT),
            AragonValidatedPermission(AGENT, "EXECUTE_ROLE", [DUAL_GOVERNANCE_ADMIN_EXECUTOR], [VOTING], AGENT),
        ],
        emitted_by=ROLES_VALIDATOR,
    )

    # Validation that all entities can or cannot perform actions after the vote

    ldo_token = token_manager.token()

    # Lido Permissions Transition
    # Voting has no permission to call STAKING_CONTROL_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        lido.resumeStaking({"from": VOTING})

    # Agent has permission to manage STAKING_CONTROL_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, STAKING_CONTROL_ROLE, acl, AGENT)

    # Voting has no permission to call RESUME_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        lido.resume({"from": VOTING})

    # Agent has permission to manage RESUME_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, RESUME_ROLE, acl, AGENT)

    # Voting has no permission to call PAUSE_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        lido.stop({"from": VOTING})

    # Agent has permission to manage PAUSE_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, PAUSE_ROLE, acl, AGENT)

    # Voting has no permission to call STAKING_PAUSE_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        lido.pauseStaking({"from": VOTING})

    # Agent has permission to manage STAKING_PAUSE_ROLE
    checkCanPerformAragonRoleManagement(stranger, LIDO, STAKING_PAUSE_ROLE, acl, AGENT)

    # DAOKernel Permissions Transition
    # Voting has no permission to call APP_MANAGER_ROLE actions
    appId = "0x3b4bf6bf3ad5000ecf0f989d5befde585c6860fea3e574a4fab4c49d1c177d9c"
    with reverts("KERNEL_AUTH_FAILED"):
        interface.Kernel(KERNEL).newAppInstance(appId, ZERO_ADDRESS, {"from": VOTING})

    # Agent has permission to manage APP_MANAGER_ROLE
    checkCanPerformAragonRoleManagement(stranger, KERNEL, APP_MANAGER_ROLE, acl, AGENT)

    # TokenManager Permissions Transition
    # Voting has permission to call MINT_ROLE actions
    assert interface.ERC20(ldo_token).balanceOf(stranger) == 0
    token_manager.mint(stranger, 100, {"from": VOTING})
    assert interface.ERC20(ldo_token).balanceOf(stranger) == 100

    checkCanPerformAragonRoleManagement(stranger, TOKEN_MANAGER, MINT_ROLE, acl, VOTING)

    # Voting has permission to call REVOKE_VESTINGS_ROLE actions
    assert token_manager.vestingsLengths(stranger) == 0
    ASSIGN_ROLE = web3.keccak(text="ASSIGN_ROLE")
    acl.grantPermission(AGENT, TOKEN_MANAGER, ASSIGN_ROLE, {"from": VOTING})
    interface.ERC20(ldo_token).transfer(TOKEN_MANAGER, 100, {"from": ldo_holder})
    date_now = chain.time()
    token_manager.assignVested(stranger, 100, date_now + 1000, date_now + 2000, date_now + 3000, True, {"from": AGENT})
    assert token_manager.vestingsLengths(stranger) == 1
    token_manager.revokeVesting(stranger, 0, {"from": VOTING})

    checkCanPerformAragonRoleManagement(stranger, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE, acl, VOTING)

    # Voting has permission to call CHANGE_PERIOD_ROLE actions
    period = finance.getPeriodDuration()
    assert period != 100000
    finance.setPeriodDuration(100000, {"from": VOTING})
    assert finance.getPeriodDuration() == 100000

    checkCanPerformAragonRoleManagement(stranger, FINANCE, CHANGE_PERIOD_ROLE, acl, VOTING)

    # Voting has permission to call CHANGE_BUDGETS_ROLE actions
    (budgets, _) = finance.getBudget(ldo_token)
    assert budgets != 1000
    finance.setBudget(ldo_token, 1000, {"from": VOTING})
    (budgets, _) = finance.getBudget(ldo_token)
    assert budgets == 1000

    checkCanPerformAragonRoleManagement(stranger, FINANCE, CHANGE_BUDGETS_ROLE, acl, VOTING)

    # EVMScriptRegistry Permissions Transition
    # Voting has no permission to call REGISTRY_MANAGER_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.EVMScriptRegistry(EVM_SCRIPT_REGISTRY).disableScriptExecutor(0, {"from": VOTING})

    # Agent has permission to manage REGISTRY_MANAGER_ROLE
    checkCanPerformAragonRoleManagement(stranger, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE, acl, AGENT)

    # Voting has no permission to call REGISTRY_ADD_EXECUTOR_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.EVMScriptRegistry(EVM_SCRIPT_REGISTRY).addScriptExecutor(AGENT, {"from": VOTING})

    # Agent has permission to manage REGISTRY_ADD_EXECUTOR_ROLE
    checkCanPerformAragonRoleManagement(stranger, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE, acl, AGENT)

    # CuratedModule Permissions Transition
    # Agent has permission to manage STAKING_ROUTER_ROLE
    checkCanPerformAragonRoleManagement(stranger, CURATED_MODULE, STAKING_ROUTER_ROLE, acl, AGENT)

    # Agent has permission to manage MANAGE_NODE_OPERATOR_ROLE
    checkCanPerformAragonRoleManagement(stranger, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE, acl, AGENT)

    # Voting has no permission to call SET_NODE_OPERATOR_LIMIT_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(CURATED_MODULE).setNodeOperatorStakingLimit(1, 100, {"from": VOTING})

    # Agent has permission to manage SET_NODE_OPERATOR_LIMIT_ROLE
    checkCanPerformAragonRoleManagement(stranger, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE, acl, AGENT)

    # Voting has no permission to call MANAGE_SIGNING_KEYS actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(CURATED_MODULE).addSigningKeys(1, 0, "0x", "0x", {"from": VOTING})

    # Agent has permission to manage MANAGE_SIGNING_KEYS
    checkCanPerformAragonRoleManagement(stranger, CURATED_MODULE, MANAGE_SIGNING_KEYS, acl, AGENT)

    # Simple DVT Module Permissions Transition
    # Voting has no permission to call STAKING_ROUTER_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(SDVT_MODULE).onRewardsMinted(0, {"from": VOTING})

    # Agent has permission to manage STAKING_ROUTER_ROLE
    checkCanPerformAragonRoleManagement(stranger, SDVT_MODULE, STAKING_ROUTER_ROLE, acl, AGENT)

    # Voting has no permission to call MANAGE_NODE_OPERATOR_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(SDVT_MODULE).setStuckPenaltyDelay(0, {"from": VOTING})

    # Agent has permission to manage MANAGE_NODE_OPERATOR_ROLE
    checkCanPerformAragonRoleManagement(stranger, SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE, acl, AGENT)

    # Voting has no permission to call SET_NODE_OPERATOR_LIMIT_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        interface.NodeOperatorsRegistry(SDVT_MODULE).setNodeOperatorStakingLimit(1, 100, {"from": VOTING})

    # Agent has permission to manage SET_NODE_OPERATOR_LIMIT_ROLE
    checkCanPerformAragonRoleManagement(stranger, SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE, acl, AGENT)

    # ACL Permissions Transition
    # Agent has permission to create permissions
    random_permission = web3.keccak(text="RANDOM_PERMISSION")
    assert not acl.hasPermission(stranger, stranger, random_permission)
    acl.createPermission(stranger, stranger, random_permission, AGENT, {"from": AGENT})
    assert acl.hasPermission(stranger, stranger, random_permission)
    acl.revokePermission(stranger, stranger, random_permission, {"from": AGENT})

    # Voting has no permission to call CREATE_PERMISSIONS_ROLE actions
    with reverts("ACL_AUTH_NO_MANAGER"):
        acl.grantPermission(stranger, stranger, random_permission, {"from": VOTING})

    # Agent has permission to manage CREATE_PERMISSIONS_ROLE
    checkCanPerformAragonRoleManagement(stranger, ACL, CREATE_PERMISSIONS_ROLE, acl, AGENT)

    # WithdrawalQueue Roles Transition
    # ResealManager has permission to call PAUSE_ROLE actions
    assert withdrawal_queue.isPaused() == False
    withdrawal_queue.pauseFor(100, {"from": RESEAL_MANAGER})
    assert withdrawal_queue.isPaused() == True

    # ResealManager has permission to call RESUME_ROLE actions
    withdrawal_queue.resume({"from": RESEAL_MANAGER})
    assert withdrawal_queue.isPaused() == False

    # VEBO Roles Transition
    # ResealManager has permission to call PAUSE_ROLE actions
    assert vebo.isPaused() == False
    vebo.pauseFor(100, {"from": RESEAL_MANAGER})
    assert vebo.isPaused() == True

    # ResealManager has permission to call RESUME_ROLE actions
    vebo.resume({"from": RESEAL_MANAGER})
    assert vebo.isPaused() == False

    # CS Module Roles Transition
    # ResealManager has permission to call PAUSE_ROLE actions
    assert csm.isPaused() == False
    csm.pauseFor(100, {"from": RESEAL_MANAGER})
    assert csm.isPaused() == True

    # ResealManager has permission to call RESUME_ROLE actions
    csm.resume({"from": RESEAL_MANAGER})
    assert csm.isPaused() == False

    # CS Accounting Roles Transition
    # ResealManager has permission to call PAUSE_ROLE actions
    assert cs_accounting.isPaused() == False
    cs_accounting.pauseFor(100, {"from": RESEAL_MANAGER})
    assert cs_accounting.isPaused() == True

    # ResealManager has permission to call RESUME_ROLE actions
    cs_accounting.resume({"from": RESEAL_MANAGER})
    assert cs_accounting.isPaused() == False

    # CS Fee Oracle Roles Transition
    # ResealManager has permission to call PAUSE_ROLE actions
    assert cs_fee_oracle.isPaused() == False
    cs_fee_oracle.pauseFor(100, {"from": RESEAL_MANAGER})
    assert cs_fee_oracle.isPaused() == True

    # ResealManager has permission to call RESUME_ROLE actions
    cs_fee_oracle.resume({"from": RESEAL_MANAGER})
    assert cs_fee_oracle.isPaused() == False

    # AllowedTokensRegistry Roles Transition
    # Voting has permission to call DEFAULT_ADMIN_ROLE actions
    allowed_tokens_registry.grantRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger, {"from": VOTING})
    assert allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger)
    allowed_tokens_registry.revokeRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger, {"from": VOTING})
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger)

    # Agent has permission to call DEFAULT_ADMIN_ROLE actions
    with reverts(
        f"AccessControl: account {AGENT.lower()} is missing role 0x0000000000000000000000000000000000000000000000000000000000000000"
    ):
        allowed_tokens_registry.grantRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, stranger, {"from": AGENT})

    # Agent has no permission to call ADD_TOKEN_TO_ALLOWED_LIST_ROLE actions
    with reverts(f"AccessControl: account {AGENT.lower()} is missing role {ADD_TOKEN_TO_ALLOWED_LIST_ROLE.hex()}"):
        allowed_tokens_registry.addToken(ldo_token, {"from": AGENT})

    # Agent has no permission to call REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE actions
    tokens = allowed_tokens_registry.getAllowedTokens()
    with reverts(f"AccessControl: account {AGENT.lower()} is missing role {REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE.hex()}"):
        allowed_tokens_registry.removeToken(tokens[0], {"from": AGENT})

    # WithdrawalVault Roles Transition
    # Voting has no permission to call proxy_changeAdmin actions
    with reverts("proxy: unauthorized"):
        withdrawal_vault.proxy_changeAdmin(AGENT, {"from": VOTING})

    # Agent has permission to call proxy_changeAdmin actions
    withdrawal_vault.proxy_changeAdmin(AGENT, {"from": AGENT})

    # InsuranceFund Roles Transition
    # Agent has no permission to call transferOwnership actions
    with reverts("Ownable: caller is not the owner"):
        insurance_fund.transferOwnership(VOTING, {"from": AGENT})

    # Voting has permission to call transferOwnership actions
    insurance_fund.transferOwnership(VOTING, {"from": VOTING})

    # Agent Permissions Transition
    # DualGovernance Executor has permission to call RUN_SCRIPT_ROLE actions
    agent.forward("0x00000001", {"from": DUAL_GOVERNANCE_ADMIN_EXECUTOR})

    # Voting has no permission to call RUN_SCRIPT_ROLE actions
    with reverts("AGENT_CAN_NOT_FORWARD"):
        agent.forward("0x00000001", {"from": VOTING})

    # Agent has permission to manage RUN_SCRIPT_ROLE
    checkCanPerformAragonRoleManagement(stranger, AGENT, RUN_SCRIPT_ROLE, acl, AGENT)

    # DualGovernance Executor has permission to call EXECUTE_ROLE actions
    agent.execute(stranger, 0, "0x", {"from": DUAL_GOVERNANCE_ADMIN_EXECUTOR})

    # Voting has no permission to call EXECUTE_ROLE actions
    with reverts("APP_AUTH_FAILED"):
        agent.execute(stranger, 0, "0x", {"from": VOTING})

    # Agent has permission to manage EXECUTE_ROLE
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
