import time

from typing import Dict

from utils.agent import agent_forward, dual_governance_agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
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
from utils.mainnet_fork import pass_and_exec_dao_vote
from scripts.dual_governance_upgrade_holesky import dual_governance_contracts


try:
    from brownie import interface
except ImportError:
    print(
        "You're probably running inside Brownie console. " "Please call:\n" "set_console_globals(interface=interface)"
    )

description = "Holesky dual governance downgrade dry-run"

def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = zip(
        (
            "Change permission manager for Lido STAKING_CONTROL_ROLE.",
            agent_forward(
                [
                    encode_permission_set_manager(contracts.lido, "STAKING_CONTROL_ROLE", contracts.voting)
                ]
            )
        ),
        (
            "Revoke permission for STAKING_CONTROL_ROLE from Agent contract.",
            encode_permission_revoke(
                target_app=contracts.lido, permission_name="STAKING_CONTROL_ROLE", revoke_from=contracts.agent
            ),
        ),
        (
            "Grant permission for STAKING_CONTROL_ROLE to Voting contract.",
            encode_permission_grant(
                target_app=contracts.lido, permission_name="STAKING_CONTROL_ROLE", grant_to=contracts.voting
            ),
        ),
        (
            "Revoke WithdrawalQueue PAUSE_ROLE from Reseal Manager.",
            (
                agent_forward(
                    [
                        (
                            contracts.withdrawal_queue.address,
                            contracts.withdrawal_queue.revokeRole.encode_input(
                                contracts.withdrawal_queue.PAUSE_ROLE(), dual_governance_contracts["resealManager"]
                            ),
                        )
                    ]
                )
            ),
        ),
        (
            "Revoke WithdrawalQueue RESUME_ROLE from Reseal Manager.",
            (
                agent_forward(
                    [
                        (
                            contracts.withdrawal_queue.address,
                            contracts.withdrawal_queue.revokeRole.encode_input(
                                contracts.withdrawal_queue.RESUME_ROLE(), dual_governance_contracts["resealManager"]
                            ),
                        )
                    ]
                )
            ),
        ),
        (
            "Grant AllowedTokensRegistry DEFAULT_ADMIN_ROLE to Agent.",
            (
                contracts.allowed_tokens_registry.address,
                contracts.allowed_tokens_registry.grantRole.encode_input(
                    contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.agent
                ),
            ),
        ),
        (
            "Revoke AllowedTokensRegistry DEFAULT_ADMIN_ROLE from Voting.",
            (
                contracts.allowed_tokens_registry.address,
                contracts.allowed_tokens_registry.revokeRole.encode_input(
                    contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.voting
                ),
            ),
        ),
        (
            "Revoke permission for RUN_SCRIPT_ROLE from DG Executor contract.",
            encode_permission_revoke(
                target_app=contracts.agent,
                permission_name="RUN_SCRIPT_ROLE",
                revoke_from=contracts.dual_governance_admin_executor,
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
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.


def start_and_execute_vote_on_fork():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id))
