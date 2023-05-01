"""
Voting 10/01/2023.

!!! Goerli only
1. Grant Relay Maintenance Committee 0xf1A6BD3193F93331C38828a3EBeE2fCa374ABACe the manager role
   in the MEV Boost Relay Allowed List smart contract 0xeabe95ac5f3d64ae16acbb668ed0efcd81b721bc

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, get_is_live, network_name, contracts
from utils.agent import agent_forward
from utils.brownie_prelude import *

new_manager: str = "0xf1A6BD3193F93331C38828a3EBeE2fCa374ABACe"

def encode_set_manager(new_manager: str) -> Tuple[str, str]:
    manager: interface.MEVBoostRelayAllowedList = contracts.relay_allowed_list

    return agent_forward([(manager.address, manager.set_manager.encode_input(new_manager))])


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    if network_name() not in ("goerli", "goerli-fork"):
        raise EnvironmentError("Unexpected network")

    call_script_items = [
        # 1. Grant Relay Maintenance Committee 0xf1A6BD3193F93331C38828a3EBeE2fCa374ABACe
        # the manager role in the MEV Boost Relay Allowed List smart contract 0xeabe95ac5f3d64ae16acbb668ed0efcd81b721bc
        encode_set_manager(new_manager),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Grant 0xf1A6BD3193F93331C38828a3EBeE2fCa374ABACe the manager role in MEVBoostRelayAllowedList 0xeabe95ac5f3d64ae16acbb668ed0efcd81b721bc",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account(), "gasPrice": 100000000000000000}

    if get_is_live():
        tx_params["max_fee"] = "200 gwei"
        tx_params["priority_fee"] = "2 gwei"
        tx_params["gas_limit"] = "2000000"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
