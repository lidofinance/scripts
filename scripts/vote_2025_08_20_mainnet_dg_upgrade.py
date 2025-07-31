"""
Dual Governance Upgrade on Mainnet and Token transfer to the Lido Labs BORG Foundation

1.1. Set on new Dual Governance instance Tiebreaker activation timeout to 31536000 seconds (1 year) 
1.2. Set on new Dual Governance instance Tiebreaker committee to 0x0000000000000000000000000000000000000000
1.3. Add Withdrawal Queue (0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1) as Tiebreaker withdrawal blocker
1.4. Add Validators Exit Bus Oracle (0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e) as Tiebreaker withdrawal blocker
1.5. Register Aragon Voting (0x2e59A20f205bB85a89C53f1936454680651E618e) as admin proposer
1.6. Set Aragon Voting (0x2e59A20f205bB85a89C53f1936454680651E618e) as proposals canceller
1.7. Set on new Dual Governance instance Reseal committee to (0xFFe21561251c49AdccFad065C94Fb4931dF49081) 
1.8. Set on Emergency Protected Timelock (0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316) governance to new Dual Governance contract (0x0000000000000000000000000000000000000000)
1.9. Set config provider (0x0000000000000000000000000000000000000000) for old Dual Governance contract (0x4D12B9F6ACAB54FF6A3A776BA3B8724D9B77845F)
1.10. Verify Dual Governance state

2. Transferring MATIC tokens from DAO treasury to the Lido Labs BORG Foundation (0x95B521B4F55a447DB89f6a27f951713fC2035f3F)
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
from utils.mainnet_fork import pass_and_exec_dao_vote

omnibus_provider = "0x0000000000000000000000000000000000000000"
description = "Proposal to upgrade Dual Governance contract on Mainnet (Immunefi reported vulnerability fix). Token transfer to the Lido Labs BORG Foundation"


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


def start_and_execute_vote_on_fork():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
