"""
Voting 28/02/2025.
"""

import time

from typing import Dict, Tuple, Optional

from web3 import Web3
from utils.agent import agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from brownie.network.transaction import TransactionReceipt
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.permissions import (
    encode_permission_set_manager,
    encode_permission_create,
    encode_permission_revoke,
    encode_permission_grant,
)

try:
    from brownie import interface
except ImportError:
    print(
        "You're probably running inside Brownie console. " "Please call:\n" "set_console_globals(interface=interface)"
    )


description = ""
DUAL_GOVERNANCE_EXECUTOR_ADDRESS = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    withdrawal_vault_as_proxy = interface.WithdrawalVaultManager(contracts.withdrawal_vault)
    DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"

    vote_desc_items, call_script_items = zip(
        # Kernel ====================================================================================================
        (
            "Revoke permission for APP_MANAGER_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.kernel,
                permission_name="APP_MANAGER_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "Grand permission for APP_MANAGER_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.kernel,
                permission_name="APP_MANAGER_ROLE",
                grant_to=contracts.agent,
            ),
        ),
        (
            "Change permission manager for Kernel APP_MANAGER_ROLE.",
            encode_permission_set_manager(
                contracts.kernel,
                "APP_MANAGER_ROLE",
                contracts.agent,
            ),
        ),
        # Lido ====================================================================================================
        (
            "Revoke permission for STAKING_CONTROL_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.lido, permission_name="STAKING_CONTROL_ROLE", revoke_from=contracts.voting
            ),
        ),
        (
            "Grant permission for STAKING_CONTROL_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.lido, permission_name="STAKING_CONTROL_ROLE", grant_to=contracts.agent
            ),
        ),
        (
            "Change permission manager for Lido STAKING_CONTROL_ROLE.",
            encode_permission_set_manager(contracts.lido, "STAKING_CONTROL_ROLE", contracts.agent),
        ),
        (
            "Revoke permission for RESUME_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.lido, permission_name="RESUME_ROLE", revoke_from=contracts.voting
            ),
        ),
        (
            "Grant permission for RESUME_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.lido, permission_name="RESUME_ROLE", grant_to=contracts.agent
            ),
        ),
        (
            "Change permission manager for Lido RESUME_ROLE.",
            encode_permission_set_manager(contracts.lido, "RESUME_ROLE", contracts.agent),
        ),
        (
            "Revoke permission for PAUSE_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.lido, permission_name="PAUSE_ROLE", revoke_from=contracts.voting
            ),
        ),
        (
            "Grant permission for PAUSE_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.lido, permission_name="PAUSE_ROLE", grant_to=contracts.agent
            ),
        ),
        (
            "Change permission manager for Lido PAUSE_ROLE.",
            encode_permission_set_manager(contracts.lido, "PAUSE_ROLE", contracts.agent),
        ),
        (
            "Revoke permission for STAKING_PAUSE_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.lido, permission_name="STAKING_PAUSE_ROLE", revoke_from=contracts.voting
            ),
        ),
        (
            "Grant permission for STAKING_PAUSE_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.lido, permission_name="STAKING_PAUSE_ROLE", grant_to=contracts.agent
            ),
        ),
        (
            "Change permission manager for Lido STAKING_PAUSE_ROLE.",
            encode_permission_set_manager(contracts.lido, "STAKING_PAUSE_ROLE", contracts.agent),
        ),
        # EVM Script Registry ==========================================================================================
        (
            "Revoke permission for REGISTRY_ADD_EXECUTOR_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.evm_script_registry,
                permission_name="REGISTRY_ADD_EXECUTOR_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "Grant permission for REGISTRY_ADD_EXECUTOR_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.evm_script_registry,
                permission_name="REGISTRY_ADD_EXECUTOR_ROLE",
                grant_to=contracts.agent,
            ),
        ),
        (
            "Change permission manager for EVM Script Registry REGISTRY_ADD_EXECUTOR_ROLE.",
            encode_permission_set_manager(
                contracts.evm_script_registry,
                "REGISTRY_ADD_EXECUTOR_ROLE",
                contracts.agent,
            ),
        ),
        (
            "Revoke permission for REGISTRY_MANAGER_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.evm_script_registry,
                permission_name="REGISTRY_MANAGER_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "Grant permission for REGISTRY_MANAGER_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.evm_script_registry,
                permission_name="REGISTRY_MANAGER_ROLE",
                grant_to=contracts.agent,
            ),
        ),
        (
            "Change permission manager for EVM Script Registry REGISTRY_MANAGER_ROLE.",
            encode_permission_set_manager(
                contracts.evm_script_registry,
                "REGISTRY_MANAGER_ROLE",
                contracts.agent,
            ),
        ),
        # Curated Module ====================================================================================================
        (
            "Change permission manager for Curated module STAKING_ROUTER_ROLE.",
            encode_permission_set_manager(
                contracts.node_operators_registry,
                "STAKING_ROUTER_ROLE",
                contracts.agent,
            ),
        ),
        (
            "Change permission manager for Curated module MANAGE_NODE_OPERATOR_ROLE.",
            encode_permission_set_manager(
                contracts.node_operators_registry,
                "MANAGE_NODE_OPERATOR_ROLE",
                contracts.agent,
            ),
        ),
        (
            "Revoke permission for SET_NODE_OPERATOR_LIMIT_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.node_operators_registry,
                permission_name="SET_NODE_OPERATOR_LIMIT_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "Grant permission for SET_NODE_OPERATOR_LIMIT_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.node_operators_registry,
                permission_name="SET_NODE_OPERATOR_LIMIT_ROLE",
                grant_to=contracts.agent,
            ),
        ),
        (
            "Change permission manager for EVM Script Registry SET_NODE_OPERATOR_LIMIT_ROLE.",
            encode_permission_set_manager(
                contracts.node_operators_registry,
                "SET_NODE_OPERATOR_LIMIT_ROLE",
                contracts.agent,
            ),
        ),
        (
            "Revoke permission for MANAGE_SIGNING_KEYS from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.node_operators_registry,
                permission_name="MANAGE_SIGNING_KEYS",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "Grant permission for MANAGE_SIGNING_KEYS to Agent contract.",
            encode_permission_grant(
                target_app=contracts.node_operators_registry,
                permission_name="MANAGE_SIGNING_KEYS",
                grant_to=contracts.agent,
            ),
        ),
        (
            "Change permission manager for EVM Script Registry MANAGE_SIGNING_KEYS.",
            encode_permission_set_manager(
                contracts.node_operators_registry,
                "MANAGE_SIGNING_KEYS",
                contracts.agent,
            ),
        ),
        # SDVT Module ====================================================================================================
        (
            "Change permission manager for SDVT module STAKING_ROUTER_ROLE.",
            encode_permission_set_manager(
                contracts.simple_dvt,
                "STAKING_ROUTER_ROLE",
                contracts.agent,
            ),
        ),
        (
            "Change permission manager for SDVT module MANAGE_NODE_OPERATOR_ROLE.",
            encode_permission_set_manager(
                contracts.simple_dvt,
                "MANAGE_NODE_OPERATOR_ROLE",
                contracts.agent,
            ),
        ),
        (
            "Change permission manager for SDVT module SET_NODE_OPERATOR_LIMIT_ROLE.",
            encode_permission_set_manager(
                contracts.simple_dvt,
                "SET_NODE_OPERATOR_LIMIT_ROLE",
                contracts.agent,
            ),
        ),
        # Withdrawal Vault ====================================================================================================
        (
            "Transfer Withdrawal Vault ownership from Voting to Agent.",
            (
                contracts.withdrawal_vault.address,
                withdrawal_vault_as_proxy.proxy_changeAdmin.encode_input(contracts.agent),
            ),
        ),
        # Insurance Fund ====================================================================================================
        (
            "Transfer Insurance Fund ownership from Agent to Voting.",
            (
                agent_forward(
                    [
                        (
                            contracts.insurance_fund.address,
                            contracts.insurance_fund.transferOwnership.encode_input(contracts.voting),
                        )
                    ]
                )
            ),
        ),
        # Finance ====================================================================================================
        (
            "Create new permission for CHANGE_PERIOD_ROLE, grant manager to Voting",
            encode_permission_create(
                target_app=contracts.finance.address,
                permission_name="CHANGE_PERIOD_ROLE",
                manager=contracts.voting,
                grant_to=contracts.voting,
            ),
        ),
        (
            "Create new permission for CHANGE_BUDGETS_ROLE, grant manager to Voting",
            encode_permission_create(
                target_app=contracts.finance.address,
                permission_name="CHANGE_BUDGETS_ROLE",
                manager=contracts.voting,
                grant_to=contracts.voting,
            ),
        ),
        # Token manager ====================================================================================================
        (
            "Create new permission for MINT_ROLE, grant manager to Voting",
            encode_permission_create(
                target_app=contracts.token_manager,
                permission_name="MINT_ROLE",
                manager=contracts.voting,
                grant_to=contracts.voting,
            ),
        ),
        (
            "Create new permission for REVOKE_VESTINGS_ROLE, grant manager to Voting",
            encode_permission_create(
                target_app=contracts.token_manager,
                permission_name="REVOKE_VESTINGS_ROLE",
                manager=contracts.voting,
                grant_to=contracts.voting,
            ),
        ),
        # Allowed Tokens Registry ====================================================================================================
        (
            "Grant DEFAULT_ADMIN_ROLE to Voting.",
            (
                agent_forward(
                    [
                        (
                            contracts.allowed_tokens_registry.address,
                            contracts.allowed_tokens_registry.grantRole.encode_input(
                                DEFAULT_ADMIN_ROLE, contracts.voting
                            ),
                        )
                    ]
                )
            ),
        ),
        (
            "Revoke DEFAULT_ADMIN_ROLE from Agent.",
            (
                contracts.allowed_tokens_registry.address,
                contracts.allowed_tokens_registry.revokeRole.encode_input(DEFAULT_ADMIN_ROLE, contracts.agent),
            ),
        ),
        (
            "Grant ADD_TOKEN_TO_ALLOWED_LIST_ROLE to Voting.",
            (
                contracts.allowed_tokens_registry.address,
                contracts.allowed_tokens_registry.grantRole.encode_input(
                    Web3.keccak(text="ADD_TOKEN_TO_ALLOWED_LIST_ROLE"), contracts.voting
                ),
            ),
        ),
        (
            "Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Agent.",
            (
                contracts.allowed_tokens_registry.address,
                contracts.allowed_tokens_registry.revokeRole.encode_input(
                    Web3.keccak(text="ADD_TOKEN_TO_ALLOWED_LIST_ROLE"), contracts.agent
                ),
            ),
        ),
        (
            "Grant REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE to Voting.",
            (
                contracts.allowed_tokens_registry.address,
                contracts.allowed_tokens_registry.grantRole.encode_input(
                    Web3.keccak(text="REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"), contracts.voting
                ),
            ),
        ),
        (
            "Revoke REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE from Agent.",
            (
                contracts.allowed_tokens_registry.address,
                contracts.allowed_tokens_registry.revokeRole.encode_input(
                    Web3.keccak(text="REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"), contracts.agent
                ),
            ),
        ),
        # Agent ====================================================================================================
        (
            "Create new permission for ADD_PROTECTED_TOKEN_ROLE, grant manager to Voting",
            encode_permission_create(
                target_app=contracts.agent,
                permission_name="ADD_PROTECTED_TOKEN_ROLE",
                manager=contracts.voting,
                grant_to=contracts.voting,
            ),
        ),
        (
            "Create new permission for REMOVE_PROTECTED_TOKEN_ROLE, grant manager to Voting",
            encode_permission_create(
                target_app=contracts.agent,
                permission_name="REMOVE_PROTECTED_TOKEN_ROLE",
                manager=contracts.voting,
                grant_to=contracts.voting,
            ),
        ),
        (
            "Revoke permission for RUN_SCRIPT_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.agent,
                permission_name="RUN_SCRIPT_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "Grant permission for RUN_SCRIPT_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.agent,
                permission_name="RUN_SCRIPT_ROLE",
                grant_to=contracts.agent
            ),
        ),
        (
            "Change permission manager for Agent RUN_SCRIPT_ROLE.",
            encode_permission_set_manager(
                target_app=contracts.agent,
                permission_name="RUN_SCRIPT_ROLE",
                grant_to=contracts.agent,
            ),
        ),
        (
            "Revoke permission for EXECUTE_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.agent,
                permission_name="EXECUTE_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "Grant permission for EXECUTE_ROLE to DG Executor contract.",
            encode_permission_grant(
                target_app=contracts.agent,
                permission_name="EXECUTE_ROLE",
                grant_to=DUAL_GOVERNANCE_EXECUTOR_ADDRESS,
            ),
        ),
        (
            "Change permission manager for Agent EXECUTE_ROLE.",
            encode_permission_set_manager(
                target_app=contracts.agent,
                permission_name="EXECUTE_ROLE",
                grant_to=contracts.agent,
            ),
        ),
        # ACL ====================================================================================================
        (
            "Revoke permission for CREATE_PERMISSIONS_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.acl,
                permission_name="CREATE_PERMISSIONS_ROLE",
                revoke_from=contracts.voting,
            ),
        ),
        (
            "Grant permission for CREATE_PERMISSIONS_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.acl,
                permission_name="CREATE_PERMISSIONS_ROLE",
                grant_to=contracts.agent,
            ),
        ),
        (
            "Change permission manager for ACL CREATE_PERMISSIONS_ROLE.",
            encode_permission_set_manager(
                contracts.acl,
                "CREATE_PERMISSIONS_ROLE",
                contracts.agent,
            ),
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
