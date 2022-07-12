"""
Voting 12/07/2022.

1. Swap treasury and insurance fees: set treasury fee to 5000 bp and insurance fee to 0 bp

"""
# noinspection PyUnresolvedReferences

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, get_is_live, contracts
from utils.brownie_prelude import *


def encode_swap_treasury_and_insurance_fees() -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido

    treasury_bp = 5000
    insurance_bp = 0
    operators_bp = 5000

    return lido.address, lido.setFeeDistribution.encode_input(
        treasury_bp,
        insurance_bp,
        operators_bp
    )


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items = [
        # 1. Swap treasury and insurance fees: set treasury fee to 5000 bp and insurance fee to 0 bp
        encode_swap_treasury_and_insurance_fees(),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Swap treasury and insurance fees: set treasury fee to 5000 bp and insurance fee to 0 bp",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
