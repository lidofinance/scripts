"""
Voting 02/12/2021

1. Grant CREATE_PAYMENTS_ROLE role on the finance contract 0xb9e5cbb9ca5b0d659238807e84d0176930753d86
    to the EVMScriptExecutor contract 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
2. Grant SET_NODE_OPERATOR_LIMIT_ROLE role on the node operators registry contract
    0x55032650b14df07b85bf18a3a3ec8e0af2e028d5 to the EVMScriptExecutor
    contract 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
"""
import time
from typing import Dict, Tuple, Optional
from utils import permissions, config, evm_script, voting
from brownie.network.transaction import TransactionReceipt

try:
    from brownie import interface
except ImportError:
    print(
        "You're probably running inside Brownie console. "
        "Please call:\n"
        "set_console_globals(interface=interface)"
    )

EVM_SCRIPT_EXECUTOR_ADDRESS = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"


def main():
    from_account = config.get_deployer_account()
    print("Deployer:", from_account)
    vote_id, _ = start_vote(
        {
            "from": from_account,
            "max_fee": "3 gwei",
            "priority_fee": "2 gwei",
        }
    )
    print(f"Vote created: {vote_id}.")
    time.sleep(5)  # hack for waiting thread #2.


def start_vote(
    tx_params: Dict[str, str], silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    acl = interface.ACL(config.lido_dao_acl_address)
    encoded_call_script = evm_script.encode_call_script(
        [
            permissions.encode_permission_grant(
                acl=acl,
                target_app=interface.Finance(config.lido_dao_finance_address),
                permission_name="CREATE_PAYMENTS_ROLE",
                grant_to=EVM_SCRIPT_EXECUTOR_ADDRESS,
            ),
            permissions.encode_permission_grant(
                acl=acl,
                target_app=interface.NodeOperatorsRegistry(
                    config.lido_dao_node_operators_registry
                ),
                permission_name="SET_NODE_OPERATOR_LIMIT_ROLE",
                grant_to=EVM_SCRIPT_EXECUTOR_ADDRESS,
            ),
        ]
    )
    human_readable_script = evm_script.decode_evm_script(
        encoded_call_script, verbose=False, specific_net="mainnet", repeat_is_error=True
    )

    if not silent:
        print("\nPoints of voting:")
        total = len(human_readable_script)
        print(human_readable_script)
        for ind, call in enumerate(human_readable_script):
            print(f"Point #{ind + 1}/{total}.")
            print(evm_script.calls_info_pretty_print(call))
            print("---------------------------")

        print("Does it look good?")
        resume = config.prompt_bool()
        while resume is None:
            resume = config.prompt_bool()

        if not resume:
            print("Exit without running.")
            return -1, None

    return voting.create_vote(
        voting=interface.Voting(config.lido_dao_voting_address),
        token_manager=interface.TokenManager(config.lido_dao_token_manager_address),
        vote_desc=(
            "Omnibus vote: "
            "1) Grant CREATE_PAYMENTS_ROLE role to the EVMScriptExecutor contract;"
            "2) Grant SET_NODE_OPERATOR_LIMIT_ROLE role to the EVMScriptExecutor contract."
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params,
    )
