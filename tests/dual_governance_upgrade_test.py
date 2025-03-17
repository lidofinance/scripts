import pytest
import os

from brownie import web3, chain, interface, ZERO_ADDRESS, accounts
from hexbytes import HexBytes
from scripts.dual_governance_upgrade import start_vote
from utils.config import contracts
from brownie.network.transaction import TransactionReceipt

DUAL_GOVERNANCE = ""
TIMELOCK = ""
DUAL_GOVERNANCE_ADMIN_EXECUTOR = ""
RESEAL_MANAGER = ""
DAO_EMERGENCY_GOVERNANCE = ""

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
INSURANCE_FUND = "0x8B3f33234ABD88493c0Cd28De33D583B70beDe35"
VEBO = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"


@pytest.fixture(scope="function", autouse=True)
def prepare_activated_dg_state():

    if os.getenv("SKIP_DG_DRY_RUN"):
        dg_impersonated = accounts.at(DUAL_GOVERNANCE, force=True)
        timelock = interface.EmergencyProtectedTimelock(TIMELOCK)

        timelock.submit(
            DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            [(TIMELOCK, 0, timelock.setEmergencyGovernance.encode_input(DAO_EMERGENCY_GOVERNANCE))],
            {"from": dg_impersonated},
        )

        assert timelock.getEmergencyGovernance() == DAO_EMERGENCY_GOVERNANCE
        assert timelock.getProposalsCount() == 1


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
    assert acl.hasPermission(AGENT, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING

    SET_NODE_OPERATOR_LIMIT_ROLE = web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")
    assert not acl.hasPermission(AGENT, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING

    MANAGE_SIGNING_KEYS = web3.keccak(text="MANAGE_SIGNING_KEYS")
    assert not acl.hasPermission(AGENT, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == VOTING

    # SDVT MODULE
    STAKING_ROUTER_ROLE = web3.keccak(text="STAKING_ROUTER_ROLE")
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == VOTING

    MANAGE_NODE_OPERATOR_ROLE = web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == VOTING

    SET_NODE_OPERATOR_LIMIT_ROLE = web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == VOTING

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
    RESUME_ROLE = web3.keccak(text="RESUME_ROLE")
    withdrawal_queue = interface.WithdrawalQueue(WITHDRAWAL_QUEUE)
    assert not withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # VEBO
    vebo = interface.ValidatorsExitBusOracle(VEBO)
    assert not vebo.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert not vebo.hasRole(RESUME_ROLE, RESEAL_MANAGER)

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

    # INSURANCE FUND
    insurance_fund = interface.InsuranceFund(INSURANCE_FUND)
    assert insurance_fund.owner() == AGENT

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=contracts.voting)

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

    assert not acl.hasPermission(AGENT, LIDO, PAUSE_ROLE)
    assert not acl.hasPermission(VOTING, LIDO, PAUSE_ROLE)
    assert acl.getPermissionManager(LIDO, PAUSE_ROLE) == AGENT

    # KERNEL
    assert not acl.hasPermission(AGENT, KERNEL, APP_MANAGER_ROLE)
    assert not acl.hasPermission(VOTING, KERNEL, APP_MANAGER_ROLE)
    assert acl.getPermissionManager(KERNEL, APP_MANAGER_ROLE) == AGENT

    # TOKEN MANAGER
    assert acl.hasPermission(VOTING, TOKEN_MANAGER, MINT_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, MINT_ROLE) == VOTING

    assert acl.hasPermission(VOTING, TOKEN_MANAGER, REVOKE_VESTINGS_ROLE)
    assert acl.getPermissionManager(TOKEN_MANAGER, REVOKE_VESTINGS_ROLE) == VOTING

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

    assert acl.hasPermission(AGENT, CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE)
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT

    assert not acl.hasPermission(VOTING, CURATED_MODULE, MANAGE_SIGNING_KEYS)
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == AGENT

    # SDVT MODULE
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_SIGNING_KEYS) == AGENT
    assert acl.getPermissionManager(CURATED_MODULE, MANAGE_NODE_OPERATOR_ROLE) == AGENT
    assert acl.getPermissionManager(CURATED_MODULE, SET_NODE_OPERATOR_LIMIT_ROLE) == AGENT

    # AGENT
    assert acl.getPermissionManager(AGENT, RUN_SCRIPT_ROLE) == AGENT
    assert acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT, RUN_SCRIPT_ROLE)
    assert acl.getPermissionManager(AGENT, EXECUTE_ROLE) == AGENT
    assert acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, AGENT, EXECUTE_ROLE)

    # ACL
    assert not acl.hasPermission(VOTING, ACL, CREATE_PERMISSIONS_ROLE)
    assert acl.getPermissionManager(ACL, CREATE_PERMISSIONS_ROLE) == AGENT
    assert acl.hasPermission(AGENT, ACL, CREATE_PERMISSIONS_ROLE)

    # WITHDRAWAL QUEUE
    assert withdrawal_queue.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert withdrawal_queue.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # VEBO
    assert vebo.hasRole(PAUSE_ROLE, RESEAL_MANAGER)
    assert vebo.hasRole(RESUME_ROLE, RESEAL_MANAGER)

    # ALLOWED TOKENS REGISTRY
    assert allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, AGENT)

    assert allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, AGENT)

    assert allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, VOTING)
    assert not allowed_tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, AGENT)

    # WITHDRAWAL VAULT
    assert withdrawal_vault.proxy_getAdmin() == AGENT

    # INSURANCE FUND
    assert insurance_fund.owner() == VOTING

    chain.sleep(7 * 24 * 60)

    dual_governance.scheduleProposal(1, {"from": stranger})

    chain.sleep(7 * 24 * 60)

    timelock.execute(1, {"from": stranger})

    # AGENT
    assert not acl.hasPermission(AGENT, VOTING, RUN_SCRIPT_ROLE)
    assert not acl.hasPermission(AGENT, VOTING, EXECUTE_ROLE)
