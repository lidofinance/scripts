"""
Voting 10/11/2022.

1. Update allowed beacon balance increase limit to 1750


"""
import time
from typing import Dict, Optional, Tuple

from brownie.network.transaction import TransactionReceipt

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.brownie_prelude import *
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
)

ALLOWED_BEACON_BALANCE_INCREASE_LIMIT = 1750

def encode_set_allow_beacon_balance_increase_limit():
    oracle: interface.LidoOracle = contracts.lido_oracle

    return oracle.address, oracle.setAllowedBeaconBalanceAnnualRelativeIncrease.encode_input(ALLOWED_BEACON_BALANCE_INCREASE_LIMIT)

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items = [
        # 1. Update allowed beacon balance increase limit to 1750
        encode_set_allow_beacon_balance_increase_limit(),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Update allowed beacon balance increase limit to 1750",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "200 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
