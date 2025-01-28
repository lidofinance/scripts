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


try:
    from brownie import interface
except ImportError:
    print(
        "You're probably running inside Brownie console. " "Please call:\n" "set_console_globals(interface=interface)"
    )


description = "Holesky dual governance upgrade dry-run"

dual_governance_contracts = {
    "adminExecutor": "0x936C1dC7d5fAD05E5aD9aBc48b4ab09B88850f04",
    "timelock": "0x388AB7b65605e21a75Bb50E24a1eA43DD0091fa5",
    "emergencyGovernance": "0xd67d96C6C4DF1eF12c2fb4C908a9484333cEfE60",
    "resealManager": "0x632c29848A379a7B30Ee6461ea5e7e1e92d264d0",
    "dualGovernance": "0x9F14118Fc548658660a40B351C782a22e9937b42",
    "tiebreakerCoreCommittee": "0x6093B9b951C72498EE799639D74dC701Ead3f07B",
    "tiebreakerSubCommitteeInfluencers": "0x8F4b730099BFcA35fa4bbFD84f790eD34CAa246f",
    "tiebreakerSubCommitteeNodeOperators": "0xBB259276147Af98c0e9186e783D4dbC26e82652F",
    "tiebreakerSubCommitteeProtocols": "0x485349eBc3241e0bE8eDf7149C535c0b42Fa9504",
    "temporaryEmergencyGovernance": "0xc7467FeFF717C18db08BAEF252f11A84F48e8fF7",
    # "EMERGENCY_ACTIVATION_COMMITTEE": "0x526d46eCa1d7969924e981ecDbcAa74e9f0EE566",
    # "EMERGENCY_EXECUTION_COMMITTEE": "0x526d46eCa1d7969924e981ecDbcAa74e9f0EE566",
}

def start_vote(tx_params: Dict[str, str], silent: bool = False):
    foo_contract = interface.Foo("0xC3fc22C7e0d20247B797fb6dc743BD3879217c81")
    roles_verifier = interface.RolesVerifier("0xe0144de0e89390dc469425f471527d9d6bc98b05")

    vote_desc_items, call_script_items = zip(
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
                grant_to=contracts.dual_governance_admin_executor,
            ),
        ),
        (
            "Verifiy transferred roles",
            (
                roles_verifier.address,
                roles_verifier.verify.encode_input()
            )
        ),
        (
            "Submit first dual governance proposal",
            (
                dual_governance_agent_forward(
                    [(
                        foo_contract.address,
                        foo_contract.bar.encode_input()
                    ),
                    (
                        contracts.time_constraints.address,
                        contracts.time_constraints.checkExecuteWithinDayTime.encode_input(28800, 72000)
                    )]
                )
            )
        )
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
