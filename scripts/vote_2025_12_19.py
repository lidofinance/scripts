"""
Vote 2025_12_19

1. Grant role BURN_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract `Y` TODO
2. Grant role ISSUE_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract `Y` TODO
3. Grant role ASSIGN_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract `Y` TODO

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.permissions import encode_permission_grant


# ============================== Addresses ===================================
TOKEN_MANAGER = "0xf73a1260d222f447210581DDf212D915c09a3249"
VESTING_CONTRACT = "0xb9d7934878b5fb9610b3fe8a5e441e8fad7e293f" # TODO replace with actual address


# ============================= Description ==================================
IPFS_DESCRIPTION = "Enable a dedicated vesting contract to apply vesting schedules to LDO tokens held on contributor addresses, where the contract can only remint the same amount of tokens that were previously held on the address, but under vesting."


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    
    vote_desc_items, call_script_items = zip(
        (
            "1. Grant role BURN_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract `Y` TODO",
            encode_permission_grant(
                target_app=TOKEN_MANAGER,
                permission_name="BURN_ROLE",
                grant_to=VESTING_CONTRACT,
            ),
        ),
        (
            "2. Grant role ISSUE_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract `Y` TODO",
            encode_permission_grant(
                target_app=TOKEN_MANAGER,
                permission_name="ISSUE_ROLE",
                grant_to=VESTING_CONTRACT,
            ),
        ),
        (
            "3. Grant role ASSIGN_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract `Y` TODO",
            encode_permission_grant(
                target_app=TOKEN_MANAGER,
                permission_name="ASSIGN_ROLE",
                grant_to=VESTING_CONTRACT,
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
