"""
# TODO Vote 2025_<MM>_<DD>

# TODO <a list of vote items synced with Notion Omnibus checklist>

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
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

# TODO <list all contract addresses used in a vote>

IPFS_DESCRIPTION = """
# TODO <IPFS description provided by DAO Ops>
"""


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    # TODO arrange all variables neccessary for the vote
    
    vote_desc_items, call_script_items = zip(
        # TODO <vote items group 1>
        (
            "1. TODO <vote item description 1>",
            # TODO <vote item 1>,
        ),
        (
            "2. TODO <vote item description 2>",
            # TODO <vote item 2>,
        ),

        # TODO <vote items group 2>
        (
            "3. TODO <vote item description 3>",
            # TODO <vote item 3>,
        ),
        (
            "4. TODO <vote item description 4>",
            # TODO <vote item 4>,
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(IPFS_DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(IPFS_DESCRIPTION)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
