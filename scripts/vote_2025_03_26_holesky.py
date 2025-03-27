"""
Voting 27/03/2025

I. Remove Easy Track setups for funding Lido Ecosystem & Lido Labs BORGs’ Operational Expenses Multisigs on holesky
1. Remove an Easy Track EVM script factory 0x4F2dA002a7bD5F7C63B62d4C9e4b762c689Dd8Ac for funding the Lido Ecosystem BORG Foundation’s operational multisig (AllowedRecipientsRegistry 0x193d0bA65cf3a2726e12c5568c068D1B3ea51740)
2. Remove an Easy Track EVM script factory 0xef0Df040B76252cC7fa31a5fc2f36e85c1C8c4f9 for funding the Lido Labs BORG Foundation’s operational multisig (AllowedRecipientsRegistry 0x02CD05c1cBa16113680648a8B3496A5aE312a935)
"""

import time
import eth_abi

from brownie import interface, web3, accounts
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    AGENT,
    network_name,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)
from utils.easy_track import  remove_evmscript_factory

DESCRIPTION = """
1. Remove an Easy Track setup for funding Lido Ecosystem BORG’s Operational Expenses Multisigs on holesky
2. Remove an Easy Track setup for funding Lido Labs BORG’s Operational Expenses Multisigs on holesky
"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:

    ecosystem_ops_allowed_recipient_registry = interface.AllowedRecipientRegistry("0x193d0bA65cf3a2726e12c5568c068D1B3ea51740")
    ecosystem_ops_top_up_allowed_recipients = interface.TopUpAllowedRecipients("0x4F2dA002a7bD5F7C63B62d4C9e4b762c689Dd8Ac")

    labs_ops_allowed_recipient_registry = interface.AllowedRecipientRegistry("0x02CD05c1cBa16113680648a8B3496A5aE312a935")
    labs_ops_top_up_allowed_recipients = interface.TopUpAllowedRecipients("0xef0Df040B76252cC7fa31a5fc2f36e85c1C8c4f9")

    vote_desc_items, call_script_items = zip(
        # I. Remove Easy Track setups for funding Lido Ecosystem & Lido Labs BORGs’ Operational Expenses Multisigs on holesky
        (
            "1. Remove an Easy Track EVM script factory 0x4F2dA002a7bD5F7C63B62d4C9e4b762c689Dd8Ac for funding the Lido Ecosystem BORG Foundation’s operational multisig (AllowedRecipientsRegistry 0x193d0bA65cf3a2726e12c5568c068D1B3ea51740)",
            remove_evmscript_factory(
                factory=ecosystem_ops_top_up_allowed_recipients,
            )
        ),
        (
            "2. Remove an Easy Track EVM script factory 0xef0Df040B76252cC7fa31a5fc2f36e85c1C8c4f9 for funding the Lido Labs BORG Foundation’s operational multisig (AllowedRecipientsRegistry 0x02CD05c1cBa16113680648a8B3496A5aE312a935)",
            remove_evmscript_factory(
                factory=labs_ops_top_up_allowed_recipients,
            )
        )
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

def main():
    tx_params = {"from": get_deployer_account()}
    print('account depl')
    print(get_deployer_account())
    print('account brown', accounts[0])
    print('balance', accounts[0].balance())
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
