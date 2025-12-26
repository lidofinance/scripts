"""
Vote 2025_12_26

1. Grant role BURN_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364
2. Grant role ISSUE_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364
3. Grant role ASSIGN_ROLE on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364

Vote #196 passed & executed on Dec-25-2025 01:14:59 PM UTC, block 24089870.
"""

from typing import Dict, List, Tuple
from brownie import interface

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.permissions import encode_permission_grant, encode_permission_revoke


# ============================== Addresses ===================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
TOKEN_MANAGER = "0xf73a1260d222f447210581DDf212D915c09a3249"

SOURCE_ADDRESS = "0xa8107de483f9623390d543b77c8e4bbb6f7af752"
SOURCE_LDO = 48_934_690_0011 * 10**14  # 48,934,690.0011 LDO

TARGET_ADDRESSES = [
    "0x396343362be2a4da1ce0c1c210945346fb82aa49",
    "0xbcb61ad7b2d7949ecaefc77adbd5914813aeeffa",
    "0x1b5662b2a1831cc9f743101d15ab5900512c82a4",
    "0xb79645264d73ad520a1ba87e5d69a15342a6270f",
    "0x28c61ce51e4c3ada729a903628090fa90dc21d60",
]
TARGET_LDOS = [
    10_000_000 * 10**18,
    10_000_000 * 10**18,
    10_000_000 * 10**18,
    10_000_000 * 10**18,
    8_934_690_0011 * 10**14,
]

VESTING_START = 1767200400 # Wed Dec 31 2025 17:00:00 GMT+0000
VESTING_CLIFF = 1798736400 # Thu Dec 31 2026 17:00:00 GMT+0000
VESTING_TOTAL = VESTING_CLIFF
IS_REVOKABLE = False


# ============================= Description ==================================
IPFS_DESCRIPTION = "Add a limited mechanism for applying vesting to the certain contributors’ LDO tokens."


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    # sanity checks
    assert len(TARGET_ADDRESSES) == len(TARGET_LDOS)
    assert all(ldo > 0 for ldo in TARGET_LDOS)
    assert sum(TARGET_LDOS) == SOURCE_LDO

    token_manager = interface.TokenManager(TOKEN_MANAGER)
    
    vote_desc_items, call_script_items = zip(
        (
            "1. Temporarily grant role 0xe97b137254058bd94f28d2f3eb79e2d34074ffb488d042e3bc958e0a57d2fa22 on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            encode_permission_grant(
                target_app=TOKEN_MANAGER,
                permission_name="BURN_ROLE",
                grant_to=VOTING,
            ),
        ),
        (
            "2. Burn 48,934,690.0011 LDO from address 0xa8107de483f9623390d543b77c8e4bbb6f7af752 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249",
            (
                token_manager.address,
                token_manager.burn.encode_input(
                    SOURCE_ADDRESS, SOURCE_LDO
                )
            ),
        ),
        (
            "3. Revoke role 0xe97b137254058bd94f28d2f3eb79e2d34074ffb488d042e3bc958e0a57d2fa22 on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            encode_permission_revoke(
                target_app=TOKEN_MANAGER,
                permission_name="BURN_ROLE",
                revoke_from=VOTING,
            ),
        ),
        (
            "4. Temporarily grant role 0x2406f1e99f79cea012fb88c5c36566feaeefee0f4b98d3a376b49310222b53c4 on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            encode_permission_grant(
                target_app=TOKEN_MANAGER,
                permission_name="ISSUE_ROLE",
                grant_to=VOTING,
            ),
        ),
        (
            "5. Issue 48,934,690.0011 LDO via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249",
            (
                token_manager.address,
                token_manager.issue.encode_input(
                    SOURCE_LDO
                )
            )
        ),
        (
            "6. Revoke role 0x2406f1e99f79cea012fb88c5c36566feaeefee0f4b98d3a376b49310222b53c4 on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            encode_permission_revoke(
                target_app=TOKEN_MANAGER,
                permission_name="ISSUE_ROLE",
                revoke_from=VOTING,
            ),
        ),
        (
            "7. Vest 10,000,000 LDO to 0x396343362be2a4da1ce0c1c210945346fb82aa49 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Wed Dec 31 2025 17:00:00 GMT+0000; cliff = total = Thu Dec 31 2026 17:00:00 GMT+0000; non-revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[0],
                    TARGET_LDOS[0],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "8. Vest 10,000,000 LDO to 0xbcb61ad7b2d7949ecaefc77adbd5914813aeeffa via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Wed Dec 31 2025 17:00:00 GMT+0000; cliff = total = Thu Dec 31 2026 17:00:00 GMT+0000; non-revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[1],
                    TARGET_LDOS[1],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "9. Vest 10,000,000 LDO to 0x1b5662b2a1831cc9f743101d15ab5900512c82a4 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Wed Dec 31 2025 17:00:00 GMT+0000; cliff = total = Thu Dec 31 2026 17:00:00 GMT+0000; non-revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[2],
                    TARGET_LDOS[2],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "10. Vest 10,000,000 LDO to 0xb79645264d73ad520a1ba87e5d69a15342a6270f via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Wed Dec 31 2025 17:00:00 GMT+0000; cliff = total = Thu Dec 31 2026 17:00:00 GMT+0000; non-revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[3],
                    TARGET_LDOS[3],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "11. Vest 8,934,690.0011 LDO to 0x28c61ce51e4c3ada729a903628090fa90dc21d60 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Wed Dec 31 2025 17:00:00 GMT+0000; cliff = total = Thu Dec 31 2026 17:00:00 GMT+0000; non-revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[4],
                    TARGET_LDOS[4],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
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
