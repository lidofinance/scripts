"""
Voting 12/12/2022.

!!! Goerli only
"""

import time

from typing import Dict, Tuple, Optional

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, contracts
from utils.agent import agent_forward


def encode_wq_impl_upgrade(addr: str):
    proxy = interface.OssifiableProxy("0xB0F260CC0906197ED75A5d722890bB9efe2c506A")

    return agent_forward([(proxy.address, proxy.proxy__upgradeTo.encode_input(addr))])


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    new_impl: str = "0xc136499371e078438aE89569F7bb3146fD08e7c0"

    call_script_items = [encode_wq_impl_upgrade(new_impl)]

    vote_desc_items = ["1) Upgrade WQ0 impl to 0xc136499371e078438aE89569F7bb3146fD08e7c0"]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
