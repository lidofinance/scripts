"""
Voting 17/06/2022 for Goerli.

1. Push new voting app version to Voting Repo 0x41D65FA420bBC714686E798a0eB0Df3799cEF092.

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote, bake_vote_items
from utils.repo import add_implementation_to_voting_app_repo
from utils.config import (
    get_deployer_account,
    get_is_live,
)

update_voting_app = {
    "new_address": "0x12D103a07Ac0429519C77E96781dFD5186119582",
    "content_uri": "0x697066733a516d657369564c547931646476476f4c6e6f504367466551577446396974774e755956756661766e595761363567",
    "version": (4, 1, 0),
}


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    vote_items = bake_vote_items(
        vote_desc_items=[
            "1) Push new Voting app version to Voting Repo",
        ],
        call_script_items=[
            # 1. Push new voting app version to Voting Repo 0x41D65FA420bBC714686E798a0eB0Df3799cEF092
            add_implementation_to_voting_app_repo(
                update_voting_app["version"],
                update_voting_app["new_address"],
                update_voting_app["content_uri"],
            ),
        ],
    )

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params=tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
