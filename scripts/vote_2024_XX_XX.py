"""
Voting XX/XX/2024.
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
)
from utils.easy_track import (
    add_evmscript_factory, create_permissions,
)
from utils.config import contracts

description = """
**Proposed actions:**
Incorporate Easy Track Factories:

1. Add CSM EL rewards stealing penalty settling EVM script factory
"""

CSM_EL_REWARDS_STEALING_PENALTY_FACTORY = "0x..."


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        (
            f"1) Add CSM EL rewards stealing penalty settling EVM script factory {CSM_EL_REWARDS_STEALING_PENALTY_FACTORY}",
            add_evmscript_factory(
                factory=CSM_EL_REWARDS_STEALING_PENALTY_FACTORY,
                permissions=create_permissions(contracts.cs_module, "settleELRewardsStealingPenalty"),
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
