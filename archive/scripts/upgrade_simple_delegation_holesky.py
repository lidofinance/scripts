"""
Voting 23/04/2024.

1. Push new Voting app version to the Voting Repo 0x2997EA0D07D79038D83Cb04b3BB9A2Bc512E3fDA
2. Upgrade the Aragon Voting contract implementation 0xcB738a79baeA44C93Ee46c02EF0FA975Bc4d058f
3. Upgrade TRP voting adapter 0x1dF997832b44b7ED00597f103165920537c980D4

"""

import time

from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)
from utils.repo import add_implementation_to_voting_app_repo
from utils.kernel import update_app_implementation
from utils.agent import agent_forward

updated_trp_voting_adapter = "0x1dF997832b44b7ED00597f103165920537c980D4"

updated_voting_app = {
    "address": "0xcB738a79baeA44C93Ee46c02EF0FA975Bc4d058f",
    "content_uri": "0x",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (2, 0, 0),
}

description = """
Simple delegation test voting
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Simple Delegation
        #
        (
            "1) Push new Voting app version to the Voting Repo",
            add_implementation_to_voting_app_repo(
                updated_voting_app["version"],
                updated_voting_app["address"],
                updated_voting_app["content_uri"],
            ),
        ),
        (
            "2) Upgrade the Aragon Voting contract implementation",
            update_app_implementation(updated_voting_app["id"], updated_voting_app["address"]),
        ),
        (
            "3) Upgrade TRP voting adapter",
            agent_forward(
                [
                    (
                        contracts.trp_escrow_factory.address,
                        contracts.trp_escrow_factory.update_voting_adapter.encode_input(updated_trp_voting_adapter),
                    )
                ]
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
