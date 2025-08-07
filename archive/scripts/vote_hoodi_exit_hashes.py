"""
Vote [DATE] - Grant and Revoke SUBMIT_REPORT_HASH_ROLE for ValidatorsExitBus Oracle

1. Grant SUBMIT_REPORT_HASH_ROLE to the agent
2. Perform oracle operations with predefined data
3. Revoke SUBMIT_REPORT_HASH_ROLE from the agent

Vote passed & executed on [DATE], block [BLOCK_NUMBER]
"""

import time
from typing import Dict, Tuple, Optional
from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.config import contracts

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.agent import agent_forward
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role

EXIT_HASH_TO_SUBMIT = "0x4e72449ac50f5fa83bc2d642f2c95a63f72f1b87ad292f52c0fe5c28f3cf6e47"
VOTE_DESCRIPTION = "Grant and revoke SUBMIT_REPORT_HASH_ROLE for ValidatorsExitBus Oracle operations on Hoodi"

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    
    # Grant SUBMIT_REPORT_HASH_ROLE to agent, perform operations, then revoke
    validators_exit_bus = interface.ValidatorsExitBus(contracts.validators_exit_bus_oracle)
    calldata = validators_exit_bus.submitExitRequestsHash.encode_input(EXIT_HASH_TO_SUBMIT)

    
    call_script_items = [
        # 1. Grant SUBMIT_REPORT_HASH_ROLE to the agent
        agent_forward([
            encode_oz_grant_role(
                contract=validators_exit_bus,
                role_name="SUBMIT_REPORT_HASH_ROLE",
                grant_to=contracts.agent
            )
        ]),
        
        # 2. Perform your contract calls with predefined data
        # Choose one of the two options below:
        
        # Option A: Use predefined calldata (if you already have the encoded function call)
        agent_forward([
            (contracts.validators_exit_bus_oracle.address, calldata)
        ]),
        
        # 3. Revoke SUBMIT_REPORT_HASH_ROLE from the agent
        agent_forward([
            encode_oz_revoke_role(
                contract=validators_exit_bus,
                role_name="SUBMIT_REPORT_HASH_ROLE",
                revoke_from=contracts.agent
            )
        ])
    ]
    
    encoded_call_script = encode_call_script(call_script_items)
    
    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=VOTE_DESCRIPTION,
        evm_script=encoded_call_script,
        tx_params=tx_params
    )

def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()
    
    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    
    vote_id >= 0 and print(f"Vote created: {vote_id}.")
    
    time.sleep(5)  # hack for waiting thread #2.

if __name__ == "__main__":
    main()