"""
Voting 03/04/2025 [HOLESKY].

I. Change the limits & period for ET for LOL
1: - Increase the limit from 210 to 500 USDC/USDT/DAI - set 500 limit on LOL registry `0x55B304a585D540421F1fD3579Ef12Abab7304492`
   - Increase the period from 3 months to 6 months - set 6 months period on LOL registry `0x55B304a585D540421F1fD3579Ef12Abab7304492`

"""

import time

from typing import Dict

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description

from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)

from utils.allowed_recipients_registry import (
    set_limit_parameters,
)

from utils.agent import agent_forward

description = """
I. Change the limits & period for ET for LOL
1: - Increase the limit from 210 to 500 USDC/USDT/DAI - set 500 limit on LOL registry `0x55B304a585D540421F1fD3579Ef12Abab7304492`
   - Increase the period from 3 months to 6 months - set 6 months period on LOL registry `0x55B304a585D540421F1fD3579Ef12Abab7304492`
"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    lol_registry = interface.AllowedRecipientRegistry("0x55B304a585D540421F1fD3579Ef12Abab7304492")

    vote_desc_items, call_script_items = zip(
        #
        # I. Change the limits & period for ET for LOL
        #
        (
            """1: - Increase the limit from 210 to 500 USDC/USDT/DAI - set 500 limit on LOL registry `0x55B304a585D540421F1fD3579Ef12Abab7304492`
   - Increase the period from 3 months to 6 months - set 6 months period on LOL registry `0x55B304a585D540421F1fD3579Ef12Abab7304492`""",
            agent_forward(
                [
                set_limit_parameters(
                    registry_address=lol_registry,
                    limit=500 * 10 ** 18,
                    period_duration_months=6
                ),
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
