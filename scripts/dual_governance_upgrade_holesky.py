import time

from typing import Dict
from brownie import interface
from utils.agent import agent_forward, dual_governance_forward
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
    encode_permission_revoke,
    encode_permission_grant,
)
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.evm_script import encode_call_script

description = "Holesky dual governance upgrade dry-run"

dual_governance_contracts = {
    "dualGovernance": "0xE29D4d0CAD66D87a054b5A93867C708000DaE1E6",
    "adminExecutor": "0x3Cc908B004422fd66FdB40Be062Bf9B0bd5BDbed",
    "resealManager": "0x517C93bb27aD463FE3AD8f15DaFDAD56EC0bEeC3",
}

def get_vote_items():
    foo_contract = interface.Foo("0xC3fc22C7e0d20247B797fb6dc743BD3879217c81")
    roles_validator = interface.RolesValidator("0x0F8826a574BCFDC4997939076f6D82877971feB3")
    launch_verifier = interface.DualGovernanceLaunchVerifier("0xfEcF4634f6571da23C8F21bEEeA8D12788df529e")
    
    return zip(
        (
            "Grant permission for STAKING_CONTROL_ROLE to Agent contract.",
            encode_permission_grant(
                target_app=contracts.lido, permission_name="STAKING_CONTROL_ROLE", grant_to=contracts.agent
            ),
        ),
        (
            "Revoke permission for STAKING_CONTROL_ROLE from Voting contract.",
            encode_permission_revoke(
                target_app=contracts.lido, permission_name="STAKING_CONTROL_ROLE", revoke_from=contracts.voting
            ),
        ),
        (
            "Change permission manager for Lido STAKING_CONTROL_ROLE.",
            encode_permission_set_manager(contracts.lido, "STAKING_CONTROL_ROLE", contracts.agent),
        ),
        (
            "Grant WithdrawalQueue PAUSE_ROLE to Reseal Manager.",
            (
                agent_forward(
                    [
                        (
                            contracts.withdrawal_queue.address,
                            contracts.withdrawal_queue.grantRole.encode_input(
                                contracts.withdrawal_queue.PAUSE_ROLE(), dual_governance_contracts["resealManager"]
                            ),
                        )
                    ]
                )
            ),
        ),
        (
            "Grant WithdrawalQueue RESUME_ROLE to Reseal Manager.",
            (
                agent_forward(
                    [
                        (
                            contracts.withdrawal_queue.address,
                            contracts.withdrawal_queue.grantRole.encode_input(
                                contracts.withdrawal_queue.RESUME_ROLE(), dual_governance_contracts["resealManager"]
                            ),
                        )
                    ]
                )
            ),
        ),
        (
            "Grant AllowedTokensRegistry DEFAULT_ADMIN_ROLE to Voting.",
            (
                agent_forward(
                    [
                        (
                            contracts.allowed_tokens_registry.address,
                            contracts.allowed_tokens_registry.grantRole.encode_input(
                                contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.voting
                            ),
                        )
                    ]
                )
            ),
        ),
        (
            "Revoke AllowedTokensRegistry DEFAULT_ADMIN_ROLE from Agent.",
            (
                contracts.allowed_tokens_registry.address,
                contracts.allowed_tokens_registry.revokeRole.encode_input(
                    contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.agent
                ),
            ),
        ),
        (
            "Grant permission for RUN_SCRIPT_ROLE to DG Executor contract.",
            encode_permission_grant(
                target_app=contracts.agent,
                permission_name="RUN_SCRIPT_ROLE",
                grant_to=dual_governance_contracts["adminExecutor"],
            ),
        ),
        (
            "Validate transferred roles",
            (
                roles_validator.address,
                roles_validator.validate.encode_input(
                    dual_governance_contracts['adminExecutor'], dual_governance_contracts['resealManager']
                ),
            )
        ),
        (
            "Submit dual governance proposal",
            (
                dual_governance_forward(
                    [
                        agent_forward(
                            [(
                                foo_contract.address,
                                foo_contract.bar.encode_input()
                            )]
                        ),
                        (
                            contracts.time_constraints.address,
                            contracts.time_constraints.checkExecuteWithinDayTime.encode_input(28800, 72000)
                        )
                    ]
                )
            )
        ),
        (
            "Verify dual governance",
            (
                launch_verifier.address,
                launch_verifier.verify.encode_input(),
            )
        ),
    )

def start_vote(tx_params: Dict[str, str], silent: bool = False):

    vote_desc_items, call_script_items = get_vote_items()
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


def get_voting_calldata():
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))
    evm_script = encode_call_script(vote_items.values())

    new_vote_script = encode_call_script(
        [
            (
                contracts.voting.address,
                contracts.voting.newVote.encode_input(
                    evm_script,
                    description,
                    False,
                    False
                ),
            )
        ]
    )

    print(new_vote_script)