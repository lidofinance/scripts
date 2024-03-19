"""
Voting 19/03/2024.

Easy Track stETH and stables top up setups for Lido stonks
1. Add TMC stETH top up EVM script factory address TBA (AllowedRecipientsRegistry address TBA)
2. Add TMC stables top up EVM script factory address TBA (AllowedRecipientsRegistry address TBA, AllowedTokensRegistry address TBA)

Vote passed & executed on XXXX-XX-XX.
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
    add_evmscript_factory,
)
from utils.allowed_recipients_registry import (
    create_top_up_allowed_recipient_permission,
)

description = """
Easy Track stETH and stables top up setups for [Lido stonks](https://research.lido.fi/t/lido-stonks-treasury-swaps-via-optimistic-governance/6860)
1. Add TMC stETH top up EVM script factory 0x6e04aED774B7c89BB43721AcDD7D03C872a51B69 (AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0)
2. Add TMC stables top up EVM script factory 0x0d2aefA542aFa8d9D1Ec35376068B88042FEF5f6 (AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368)
"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Easy Track stETH and stables top up setups for Lido stonks
        #
        (
            "1) Add TMC stETH top up EVM script factory 0x6e04aED774B7c89BB43721AcDD7D03C872a51B69 (AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0)",
            add_evmscript_factory(
                factory="0x6e04aED774B7c89BB43721AcDD7D03C872a51B69",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0"
                ),
            ),
        ),
        (
            "2) Add TMC stables top up EVM script factory 0x0d2aefA542aFa8d9D1Ec35376068B88042FEF5f6 (AllowedRecipientsRegistry <address TBA>, AllowedTokensRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368)",
            add_evmscript_factory(
                factory="0x0d2aefA542aFa8d9D1Ec35376068B88042FEF5f6",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0x3f0534CCcFb952470775C516DC2eff8396B8A368"
                ),
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
