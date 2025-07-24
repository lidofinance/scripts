"""
Dual Governance Upgrade on Hoodi testnet

1.1. Set Tiebreaker activation timeout
1.2. Set Tiebreaker committee
1.3. Add Withdrawal Queue as Tiebreaker withdrawal blocker
1.4. Add Validators Exit Bus Oracle as Tiebreaker withdrawal blocker
1.5. Add Triggerable Withdrawals Gateway as Tiebreaker withdrawal blocker
1.6. Register Aragon Voting as admin proposer
1.7. Set Aragon Voting as proposals canceller
1.8. Set reseal committee
1.9. Set Emergency Protected Timelock governance to new Dual Governance contract
1.10. Set config provider for old Dual Governance contract
1.11. Verify Dual Governance state
"""

import time

from typing import Dict
from brownie import interface
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)

omnibus_provider = "0x0000000000000000000000000000000000000000"
description = "Proposal to upgrade Dual Governance contract on Hoodi testnet (Immunefi reported vulnerability fix)"


def get_vote_items():
    voting_items = interface.DGLaunchOmnibus(omnibus_provider).getVoteItems()

    vote_desc_items = []
    call_script_items = []

    for desc, call_script in voting_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    assert interface.DGLaunchOmnibus(omnibus_provider).isValidVoteScript(vote_id)

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
