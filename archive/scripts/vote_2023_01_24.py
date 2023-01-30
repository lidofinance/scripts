"""
Voting 24/01/2023.

1. Send 150,000 LDO to Lido on Polygon team 0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290 for reaching 1% share milestone

Vote passed & executed on Jan-27-2023 02:26:59 PM +UTC, block 16498740
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import (
    get_deployer_account,
    get_is_live,
)
from utils.finance import make_ldo_payout
from utils.brownie_prelude import *

polygon_team_address = "0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290"
polygon_team_incentives_amount = 150_000 * 10**18

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items = [
        # 1. Send 150,000 LDO to Lido on Polygon team 0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290 for reaching 1% share milestone
        make_ldo_payout(
            target_address=polygon_team_address,
            ldo_in_wei=polygon_team_incentives_amount,
            reference="Incentives for Lido on Polygon team 0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290 for reaching 1% share milestone",
        ),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1. Send 150,000 LDO to Lido on Polygon team 0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290 for reaching 1% share milestone",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "100 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
