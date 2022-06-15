"""
! Downgrade voting 21/06/2022 [in case of emergency].

1. Downgrade voting app through the Voting Repo to 0x41D65FA420bBC714686E798a0eB0Df3799cEF092.
2. Downgrade the DAO Voting 0x41D65FA420bBC714686E798a0eB0Df3799cEF092 contract implementation.
"""

import time

from typing import Dict, Tuple, List, Optional, Any

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote, bake_vote_items
from utils.repo import add_implementation_to_voting_app_repo
from utils.kernel import update_app_implementation
from utils.config import get_deployer_account, get_is_live

old_good_voting_app: Dict[str, Any] = {
    "new_address": "0x41D65FA420bBC714686E798a0eB0Df3799cEF092",
    "content_uri": "0x697066733a516d514d64696979653134765966724a7753594250646e68656a446f62417877584b72524e45663438735370444d",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (3, 0, 0),  # Still need to bump version number even if it's revert
}


def start_vote(
    tx_params: Dict[str, str], silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items: List[Tuple[str, str]] = [
        # 1. Downgrade voting app version through the Voting Repo
        add_implementation_to_voting_app_repo(
            old_good_voting_app["version"],
            old_good_voting_app["new_address"],
            old_good_voting_app["content_uri"],
        ),
        # 2. Downgrade the DAO Voting to contract 0x41D65FA420bBC714686E798a0eB0Df3799cEF092 implementation
        update_app_implementation(
            old_good_voting_app["id"], old_good_voting_app["new_address"]
        ),
    ]

    vote_desc_items: List[str] = [
        "Downgrade voting app through the Voting Repo to 0x41D65FA420bBC714686E798a0eB0Df3799cEF092",
        "Downgrade the DAO Voting 0x41D65FA420bBC714686E798a0eB0Df3799cEF092 contract implementation",
    ]

    vote_items: Dict[str, Tuple[str, str]] = bake_vote_items(
        vote_desc_items, call_script_items
    )

    return confirm_vote_script(vote_items, silent) and create_vote(
        vote_items, tx_params
    )


def main():
    tx_params: Dict[str, Any] = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
