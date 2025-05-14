"""
Dual Governance Launch on Holesky testnet

Vote #568 passed & executed on 04/04/2024 at 01:59 PM UTC, block #3614343.
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

voting_contract = "0xc76b2c80dc713e99fC616b651F3509238DcD2285"
description = "Dual governance upgrade"

def get_vote_items():
    voting_items = interface.DGLaunchOmnibus(voting_contract).getVoteItems()

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

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    assert interface.DGLaunchOmnibus(voting_contract).isValidVoteScript(vote_id)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.

def start_and_execute_vote_on_fork():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id))
