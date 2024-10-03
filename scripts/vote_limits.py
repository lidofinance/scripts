"""
Voting 08/10/2024

"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.permission_parameters import Param, SpecialArgumentID, ArgumentValue, Op
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
)

from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
    remove_evmscript_factory
)
from utils.allowed_recipients_registry import (
    set_limit_parameters
)

from utils.agent import agent_forward

description = """
1. **Change limits
"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    alliance_ops_topup_factory = interface.TopUpAllowedRecipients("0x343fa5f0c79277e2d27e440f40420d619f962a23")
    alliance_ops_registry = interface.AllowedRecipientRegistry("0xe1ba8dee84a4df8e99e495419365d979cdb19991")

    vote_desc_items, call_script_items = zip(
        #
        # I. Change limits
        #
        (
            "1) Change limits 0xe1ba8dee84a4df8e99e495419365d979cdb19991",
            agent_forward(
                [
                set_limit_parameters(
                    registry_address=alliance_ops_registry,
                    limit=250000,
                    period_duration_months=3
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

