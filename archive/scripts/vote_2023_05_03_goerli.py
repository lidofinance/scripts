"""
Technical vote for Goerli network

1. Change TRP manager to 0xde0a8383c0c16c472bdf540e38ad9d85b12eff1e (shared QA wallet)
"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward

from utils.config import (
    get_deployer_account,
    trp_escrow_factory_address,
)

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    trp_factory = interface.VestingEscrowFactory(trp_escrow_factory_address)
    QA_shared_wallet = "0xde0a8383c0c16c472bdf540e38ad9d85b12eff1e"

    call_script_items = [
        # 1. Change TRP manager to 0xde0a8383c0c16c472bdf540e38ad9d85b12eff1e (shared QA wallet)
        agent_forward([(
            trp_factory.address,
            trp_factory.change_manager.encode_input(QA_shared_wallet),
        )])
    ]

    vote_desc_items = [
        "1. Change TRP manager to 0xde0a8383c0c16c472bdf540e38ad9d85b12eff1e (shared QA wallet)",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    print(get_deployer_account().address)
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
