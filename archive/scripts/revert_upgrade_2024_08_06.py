"""
Revert Voting Delegation Upgrade [in case of emergency]

1. Push new Voting app version to the Voting Repo 0x4ee3118e3858e8d7164a634825bfe0f73d99c792
2. Downgrade the Aragon Voting contract implementation to 0x72fb5253ad16307b9e773d2a78cac58e309d5ba4
3. Downgrade TRP voting adapter to 0xCFda8aB0AE5F4Fa33506F9C51650B890E4871Cc1

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

downgraded_trp_voting_adapter = "0xCFda8aB0AE5F4Fa33506F9C51650B890E4871Cc1"

downgraded_voting_app = {
    "address": "0x72fb5253ad16307b9e773d2a78cac58e309d5ba4",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (5, 0, 0),
}

description = """
Revert Voting Delegation Upgrade
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Simple Delegation
        #
        (
            "1) Push previous Voting app version to the Voting Repo with incremented version number",
            add_implementation_to_voting_app_repo(
                downgraded_voting_app["version"],
                downgraded_voting_app["address"],
                downgraded_voting_app["content_uri"],
            ),
        ),
        (
            "2) Set the Aragon Voting contract implementation to the previous one",
            update_app_implementation(downgraded_voting_app["id"], downgraded_voting_app["address"]),
        ),
        (
            "3) Downgrapde TRP voting adapter",
            agent_forward(
                [
                    (
                        contracts.trp_escrow_factory.address,
                        contracts.trp_escrow_factory.update_voting_adapter.encode_input(downgraded_trp_voting_adapter),
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
