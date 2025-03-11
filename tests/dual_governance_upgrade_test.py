from brownie import web3, chain, interface, ZERO_ADDRESS
from hexbytes import HexBytes
from scripts.dual_governance_upgrade import start_vote
from utils.config import contracts
from brownie.network.transaction import TransactionReceipt

DUAL_GOVERNANCE = ""
TIMELOCK = ""
DUAL_GOVERNANCE_ADMIN_EXECUTOR = ""
RESEAL_MANAGER = ""

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

def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding, stranger):
    acl = interface.ACL(ACL)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)

    # LIDO
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

    STAKING_PAUSE_ROLE = web3.keccak(text="STAKING_PAUSE_ROLE")
    assert acl.hasPermission(VOTING, LIDO, STAKING_PAUSE_ROLE)
    assert not acl.hasPermission(AGENT, LIDO, STAKING_PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, STAKING_PAUSE_ROLE) == VOTING

    # KERNEL
    APP_MANAGER_ROLE = web3.keccak(text="APP_MANAGER_ROLE")
    assert acl.hasPermission(VOTING, KERNEL, APP_MANAGER_ROLE)
    assert not acl.hasPermission(AGENT, KERNEL, APP_MANAGER_ROLE)
    assert acl.getPermissionManager(KERNEL, APP_MANAGER_ROLE) == VOTING

    # TOKEN MANAGER
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

    # FINANCE
    CHANGE_PERIOD_ROLE = web3.keccak(text="CHANGE_PERIOD_ROLE")
    assert not acl.hasPermission(VOTING, FINANCE, CHANGE_PERIOD_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_PERIOD_ROLE) == ZERO_ADDRESS

    CHANGE_BUDGETS_ROLE = web3.keccak(text="CHANGE_BUDGETS_ROLE")
    assert not acl.hasPermission(VOTING, FINANCE, CHANGE_BUDGETS_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_BUDGETS_ROLE) == ZERO_ADDRESS

    # EVM SCRIPT REGISTRY
    REGISTRY_MANAGER_ROLE = web3.keccak(text="REGISTRY_MANAGER_ROLE")
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE) == VOTING

    REGISTRY_ADD_EXECUTOR_ROLE = web3.keccak(text="REGISTRY_ADD_EXECUTOR_ROLE")
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE) == VOTING

    # CURATED MODULE
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

    # SDVT MODULE
    assert acl.getPermissionManager(SDVT_MODULE, STAKING_ROUTER_ROLE) == VOTING
    assert acl.getPermissionManager(SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING
    assert acl.getPermissionManager(SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING

    # AGENT
    RUN_SCRIPT_ROLE = web3.keccak(text="RUN_SCRIPT_ROLE")
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == VOTING

    EXECUTE_ROLE = web3.keccak(text="EXECUTE_ROLE")
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == VOTING

    # ACL
    CREATE_PERMISSIONS_ROLE = web3.keccak(text="CREATE_PERMISSIONS_ROLE")
    assert not acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == VOTING
    assert acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)

    # WITHDRAWAL QUEUE
    PAUSE_ROLE = web3.keccak(text="PAUSE_ROLE")
    withdrawal_queue = interface.WithdrawalQueue(WITHDRAWAL_QUEUE)
    assert not withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # ALLOWED TOKENS REGISTRY
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

    # WITHDRAWAL VAULT
    withdrawal_vault = interface.WithdrawalContractProxy(WITHDRAWAL_VAULT)
    assert withdrawal_vault.proxy_getAdmin() == VOTING

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=contracts.voting
    )

    # LIDO
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

    # KERNEL
    assert not acl.hasPermission(AGENT, KERNEL, APP_MANAGER_ROLE)
    assert not acl.hasPermission(VOTING, KERNEL, APP_MANAGER_ROLE)
    assert acl.getPermissionManager(KERNEL, APP_MANAGER_ROLE) == AGENT

    # TOKEN MANAGER
    assert acl.hasPermission(VOTING, TOKEN_MANAGER, MINT_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, MINT_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, REVOKE_VESTINGS_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, BURN_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, BURN_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, ISSUE_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, ISSUE_ROLE) == VOTING

    # FINANCE
    assert acl.hasPermission(VOTING, FINANCE, CHANGE_PERIOD_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_PERIOD_ROLE) == VOTING

    assert acl.hasPermission(VOTING, FINANCE, CHANGE_BUDGETS_ROLE)
    assert acl.getPermissionManager(FINANCE, CHANGE_BUDGETS_ROLE) == VOTING

    # EVM SCRIPT REGISTRY
    assert not acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_MANAGER_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert not acl.hasPermission(AGENT, EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE)
    assert acl.getPermissionManager(EVM_SCRIPT_REGISTRY, REGISTRY_ADD_EXECUTOR_ROLE) == AGENT

    # CURATED MODULE
    assert acl.getPermissionManager(CURATED_MODULE, STAKING_ROUTER_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == AGENT

    # SDVT MODULE
    assert acl.getPermissionManager(SDVT_MODULE, STAKING_ROUTER_ROLE) == AGENT
    assert acl.getPermissionManager(SDVT_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT
    assert acl.getPermissionManager(SDVT_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT

    # AGENT
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == AGENT
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == AGENT

    # ACL
    assert not acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == AGENT

    # WITHDRAWAL QUEUE
    assert withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # ALLOWED TOKENS REGISTRY
    assert allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, AGENT)

    assert allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, AGENT)

    assert allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, AGENT)

    # WITHDRAWAL VAULT
    assert withdrawal_vault.proxy_getAdmin() == AGENT

    chain.sleep(7 * 24 * 60)

    dual_governance.scheduleProposal(1, {"from": stranger})

    chain.sleep(7 * 24 * 60)

    timelock.execute(1, {"from": stranger})

    # AGENT
    assert not acl.hasPermission(AGENT, VOTING, RUN_SCRIPT_ROLE)
    assert not acl.hasPermission(AGENT, VOTING, EXECUTE_ROLE)
