"""
Voting 19/03/2024.

Easy Track stETH and stables top up setups for Lido stonks
1. Add TMC stETH top up EVM script factory address TBA (AllowedRecipientsRegistry address TBA)
2. Add TMC stables top up EVM script factory address TBA (AllowedRecipientsRegistry address TBA, AllowedTokensRegistry address TBA)

Vote passed & executed on XXXX-XX-XX.
"""

import time

from typing import Dict, NamedTuple
from brownie import ZERO_ADDRESS
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
from configs.config_mainnet import DAI_TOKEN, LDO_TOKEN, LIDO, USDC_TOKEN, USDT_TOKEN
from utils.allowed_recipients_registry import (
    create_top_up_allowed_recipient_permission,
)


class TokenLimit(NamedTuple):
    address: str
    limit: int


ldo_limit = TokenLimit(LDO_TOKEN, 5_000_000 * (10**18))
eth_limit = TokenLimit(ZERO_ADDRESS, 1_000 * 10**18)
steth_limit = TokenLimit(LIDO, 1_000 * (10**18))
dai_limit = TokenLimit(DAI_TOKEN, 2_000_000 * (10**18))
usdc_limit = TokenLimit(USDC_TOKEN, 2_000_000 * (10**6))
usdt_limit = TokenLimit(USDT_TOKEN, 2_000_000 * (10**6))

description = """
Easy Track stETH and stables top up setups for [Lido stonks](https://research.lido.fi/t/lido-stonks-treasury-swaps-via-optimistic-governance/6860)
1. **Add TMC stETH top up EVM script factory** <address TBA> (AllowedRecipientsRegistry <address TBA>)
2. **Add TMC stables top up EVM script factory** <address TBA> (AllowedRecipientsRegistry <address TBA>, AllowedTokensRegistry <address TBA>)
"""


HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Easy Track stETH and stables top up setups for Lido stonks
        #
        (
            "1) Add TMC stETH top up EVM script factory <address TBA> (AllowedRecipientsRegistry <address TBA>)",
            add_evmscript_factory(
                factory="<address TBA>",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="<address TBA>"
                ),
            ),
        ),
        (
            "2) Add TMC stables top up EVM script factory <address TBA> (AllowedRecipientsRegistry <address TBA>, AllowedTokensRegistry <address TBA>)",
            add_evmscript_factory(
                factory="<address TBA>",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="<address TBA>"
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
