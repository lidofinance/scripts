"""
Tests for voting 23/07/2024.
"""

from scripts.dual_governance_upgrade import start_vote
from utils.config import contracts
from utils.test.tx_tracing_helpers import *
from brownie.network.transaction import TransactionReceipt
from utils.config import contracts

try:
    from brownie import interface
except ImportError:
    print(
        "You're probably running inside Brownie console. " "Please call:\n" "set_console_globals(interface=interface)"
    )

def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding):
    dao_voting = contracts.voting
    withdrawal_vault_as_proxy = interface.WithdrawalVaultManager(contracts.withdrawal_vault)

    # ACL
    assert (
        contracts.acl.getPermissionManager(contracts.acl, contracts.acl.CREATE_PERMISSIONS_ROLE()) == contracts.voting
    )
    assert contracts.acl.hasPermission(contracts.voting, contracts.acl, contracts.acl.CREATE_PERMISSIONS_ROLE())

    # Kernel
    assert contracts.acl.getPermissionManager(contracts.kernel, contracts.kernel.APP_MANAGER_ROLE()) == contracts.voting
    assert contracts.acl.hasPermission(contracts.voting, contracts.kernel, contracts.kernel.APP_MANAGER_ROLE())

    # Lido
    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.STAKING_CONTROL_ROLE()) == contracts.voting
    assert contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())

    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.RESUME_ROLE()) == contracts.voting
    assert contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.RESUME_ROLE())

    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.PAUSE_ROLE()) == contracts.voting
    assert contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.PAUSE_ROLE())

    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.STAKING_PAUSE_ROLE()) == contracts.voting
    assert contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.STAKING_PAUSE_ROLE())

    # EVM Script Registry
    assert (
        contracts.acl.getPermissionManager(
            contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_ADD_EXECUTOR_ROLE()
        )
        == contracts.voting
    )
    assert contracts.acl.hasPermission(
        contracts.voting, contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_ADD_EXECUTOR_ROLE()
    )

    assert (
        contracts.acl.getPermissionManager(
            contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_MANAGER_ROLE()
        )
        == contracts.voting
    )
    assert contracts.acl.hasPermission(
        contracts.voting, contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_MANAGER_ROLE()
    )

    # Node Operators Registry
    assert (
        contracts.acl.getPermissionManager(
            contracts.node_operators_registry, contracts.node_operators_registry.STAKING_ROUTER_ROLE()
        )
        == contracts.voting
    )
    assert (
        contracts.acl.getPermissionManager(
            contracts.node_operators_registry, contracts.node_operators_registry.MANAGE_NODE_OPERATOR_ROLE()
        )
        == contracts.voting
    )

    assert (
        contracts.acl.getPermissionManager(
            contracts.node_operators_registry, contracts.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE()
        )
        == contracts.voting
    )
    assert contracts.acl.hasPermission(
        contracts.voting,
        contracts.node_operators_registry,
        contracts.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE(),
    )

    assert (
        contracts.acl.getPermissionManager(
            contracts.node_operators_registry, contracts.node_operators_registry.MANAGE_SIGNING_KEYS()
        )
        == contracts.voting
    )
    assert contracts.acl.hasPermission(
        contracts.voting, contracts.node_operators_registry, contracts.node_operators_registry.MANAGE_SIGNING_KEYS()
    )

    # SDVT Module

    assert (
        contracts.acl.getPermissionManager(
            contracts.simple_dvt, contracts.simple_dvt.STAKING_ROUTER_ROLE()
        )
        == contracts.voting
    )
    assert (
        contracts.acl.getPermissionManager(
            contracts.simple_dvt, contracts.simple_dvt.SET_NODE_OPERATOR_LIMIT_ROLE()
        )
        == contracts.voting
    )
    assert (
        contracts.acl.getPermissionManager(
            contracts.simple_dvt, contracts.simple_dvt.MANAGE_NODE_OPERATOR_ROLE()
        )
        == contracts.voting
    )

    # Withdrawal vault

    assert withdrawal_vault_as_proxy.proxy_getAdmin() == contracts.voting

    # Insurance fund

    assert contracts.insurance_fund.owner() == contracts.agent

    # Finance

    assert contracts.acl.getPermissionManager(contracts.finance, contracts.finance.CHANGE_PERIOD_ROLE()) != contracts.voting
    assert contracts.acl.getPermissionManager(contracts.finance, contracts.finance.CHANGE_BUDGETS_ROLE()) != contracts.voting

    # Token manager
    assert contracts.acl.getPermissionManager(contracts.token_manager, contracts.token_manager.MINT_ROLE()) != contracts.voting
    assert contracts.acl.getPermissionManager(contracts.token_manager, contracts.token_manager.REVOKE_VESTINGS_ROLE()) != contracts.voting

    # Allowed tokens registry

    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.agent)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.voting)
    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.ADD_TOKEN_TO_ALLOWED_LIST_ROLE(), contracts.agent)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.ADD_TOKEN_TO_ALLOWED_LIST_ROLE(), contracts.voting)
    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE(), contracts.agent)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE(), contracts.voting)

    # Agent

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    assert contracts.acl.getPermissionManager(contracts.acl, contracts.acl.CREATE_PERMISSIONS_ROLE()) == contracts.agent
    assert not contracts.acl.hasPermission(contracts.voting, contracts.acl, contracts.acl.CREATE_PERMISSIONS_ROLE())
    assert contracts.acl.hasPermission(contracts.agent, contracts.acl, contracts.acl.CREATE_PERMISSIONS_ROLE())

    # Kernel
    assert contracts.acl.getPermissionManager(contracts.kernel, contracts.kernel.APP_MANAGER_ROLE()) == contracts.agent
    assert not contracts.acl.hasPermission(contracts.voting, contracts.kernel, contracts.kernel.APP_MANAGER_ROLE())
    assert contracts.acl.hasPermission(contracts.agent, contracts.kernel, contracts.kernel.APP_MANAGER_ROLE())

    # Lido
    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.STAKING_CONTROL_ROLE()) == contracts.agent
    assert not contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())
    assert contracts.acl.hasPermission(contracts.agent, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())

    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.RESUME_ROLE()) == contracts.agent
    assert not contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.RESUME_ROLE())
    assert contracts.acl.hasPermission(contracts.agent, contracts.lido, contracts.lido.RESUME_ROLE())

    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.PAUSE_ROLE()) == contracts.agent
    assert not contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.PAUSE_ROLE())
    assert contracts.acl.hasPermission(contracts.agent, contracts.lido, contracts.lido.PAUSE_ROLE())

    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.STAKING_PAUSE_ROLE()) == contracts.agent
    assert not contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.STAKING_PAUSE_ROLE())
    assert contracts.acl.hasPermission(contracts.agent, contracts.lido, contracts.lido.STAKING_PAUSE_ROLE())

    # EVM Script Registry
    assert (
        contracts.acl.getPermissionManager(
            contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_ADD_EXECUTOR_ROLE()
        )
        == contracts.agent
    )
    assert not contracts.acl.hasPermission(
        contracts.voting, contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_ADD_EXECUTOR_ROLE()
    )
    assert contracts.acl.hasPermission(
        contracts.agent, contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_ADD_EXECUTOR_ROLE()
    )

    assert (
        contracts.acl.getPermissionManager(
            contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_MANAGER_ROLE()
        )
        == contracts.agent
    )
    assert not contracts.acl.hasPermission(
        contracts.voting, contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_MANAGER_ROLE()
    )
    assert contracts.acl.hasPermission(
        contracts.agent, contracts.evm_script_registry, contracts.evm_script_registry.REGISTRY_MANAGER_ROLE()
    )

    # Node Operators Registry
    assert (
        contracts.acl.getPermissionManager(
            contracts.node_operators_registry, contracts.node_operators_registry.STAKING_ROUTER_ROLE()
        )
        == contracts.agent
    )
    assert (
        contracts.acl.getPermissionManager(
            contracts.node_operators_registry, contracts.node_operators_registry.MANAGE_NODE_OPERATOR_ROLE()
        )
        == contracts.agent
    )

    assert (
        contracts.acl.getPermissionManager(
            contracts.node_operators_registry, contracts.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE()
        )
        == contracts.agent
    )
    assert not contracts.acl.hasPermission(
        contracts.voting,
        contracts.node_operators_registry,
        contracts.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE(),
    )

    assert (
        contracts.acl.getPermissionManager(
            contracts.node_operators_registry, contracts.node_operators_registry.MANAGE_SIGNING_KEYS()
        )
        == contracts.agent
    )
    assert not contracts.acl.hasPermission(
        contracts.voting, contracts.node_operators_registry, contracts.node_operators_registry.MANAGE_SIGNING_KEYS()
    )

    # SDVT Module

    assert (
        contracts.acl.getPermissionManager(
            contracts.simple_dvt, contracts.simple_dvt.STAKING_ROUTER_ROLE()
        )
        == contracts.agent
    )
    assert (
        contracts.acl.getPermissionManager(
            contracts.simple_dvt, contracts.simple_dvt.SET_NODE_OPERATOR_LIMIT_ROLE()
        )
        == contracts.agent
    )
    assert (
        contracts.acl.getPermissionManager(
            contracts.simple_dvt, contracts.simple_dvt.MANAGE_NODE_OPERATOR_ROLE()
        )
        == contracts.agent
    )

    # Withdrawal vault

    assert withdrawal_vault_as_proxy.proxy_getAdmin() == contracts.agent

    # Insurance fund

    assert contracts.insurance_fund.owner() == contracts.voting

    # Finance

    assert contracts.acl.getPermissionManager(contracts.finance, contracts.finance.CHANGE_PERIOD_ROLE()) == contracts.voting
    assert contracts.acl.getPermissionManager(contracts.finance, contracts.finance.CHANGE_BUDGETS_ROLE()) == contracts.voting

    # Token manager
    assert contracts.acl.getPermissionManager(contracts.token_manager, contracts.token_manager.MINT_ROLE()) == contracts.voting
    assert contracts.acl.getPermissionManager(contracts.token_manager, contracts.token_manager.REVOKE_VESTINGS_ROLE()) == contracts.voting

    # Allowed tokens registry

    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.voting)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.agent)
    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.ADD_TOKEN_TO_ALLOWED_LIST_ROLE(), contracts.voting)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.ADD_TOKEN_TO_ALLOWED_LIST_ROLE(), contracts.agent)
    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE(), contracts.voting)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE(), contracts.agent)

    # # Validate vote events
    # if not bypass_events_decoding:
    #     assert count_vote_items_by_events(tx, dao_voting) == 2, "Incorrect voting items count"
