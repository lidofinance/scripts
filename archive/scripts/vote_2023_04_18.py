"""
Voting 18/04/2023.
1. Set Staking limit for Node Operator RockLogic GmbH to 5800

Vote passed & executed on Apr-21-2023 04:02:11 PM +UTC, block 17095814
"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.config import (
    get_deployer_account,
    lido_dao_node_operators_registry,
)
from utils.node_operators import (
    encode_set_node_operator_staking_limit
)

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    NO_registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    RockLogicGmbH_id = 22
    RockLogicGmbH_limit = 5800

    call_script_items = [
        # 1. Set Staking limit for node operator RockLogic GmbH to 5800
        encode_set_node_operator_staking_limit(RockLogicGmbH_id, RockLogicGmbH_limit, NO_registry),
    ]

    vote_desc_items = [
        "1) Set Staking limit for Node Operator RockLogic GmbH to 5800",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "priority_fee": "4 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
