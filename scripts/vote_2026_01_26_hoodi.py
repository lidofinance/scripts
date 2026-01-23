"""
Voting 26/01/2026. Hoodi network.

1. Grant MANAGE_SIGNING_KEYS role for operator 0x031624fAD4E9BFC2524e7a87336C4b190E70BCA8 to 0xc8195bb2851d7129D9100af9d65Bd448A6dE11eF on Hoodi

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.permissions import encode_permission_grant_p
from utils.permission_parameters import Param, Op, ArgumentValue
from utils.mainnet_fork import pass_and_exec_dao_vote


# ============================== Addresses ===================================
NEW_MANAGER_ADDRESS = "0xc8195bb2851d7129D9100af9d65Bd448A6dE11eF"
TARGET_NO_REGISTRY = "0x682E94d2630846a503BDeE8b6810DF71C9806891"
OPERATOR_ID = 1


# ============================= Description ==================================
IPFS_DESCRIPTION = "Grant MANAGE_SIGNING_KEYS role for operator 0x031624fAD4E9BFC2524e7a87336C4b190E70BCA8 to 0xc8195bb2851d7129D9100af9d65Bd448A6dE11eF on Hoodi"


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    params = [Param(0, Op.EQ, ArgumentValue(OPERATOR_ID))]

    vote_desc_items, call_script_items = zip(
        (
            "1. Grant MANAGE_SIGNING_KEYS role for operator 0x031624fAD4E9BFC2524e7a87336C4b190E70BCA8 to 0xc8195bb2851d7129D9100af9d65Bd448A6dE11eF on Hoodi",
            encode_permission_grant_p(
                target_app=TARGET_NO_REGISTRY,
                permission_name="MANAGE_SIGNING_KEYS",
                grant_to=NEW_MANAGER_ADDRESS,
                params=params,
            ),
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
