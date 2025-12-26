"""
Vote 2025_12_27

1. Revoke vesting (ID = 0) of 48,934,690.0011 LDO from 0xa8107de483f9623390d543b77c8e4bbb6f7af752 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249
2. Vest 10,000,000 LDO to 0xED3D9bAC1B26610A6f8C42F4Fd2c741a16647056 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
3. Vest 5,000,000 LDO to 0x7bd77405a7c28F50a1010e2185297A25165FD5C6 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
4. Vest 5,000,000 LDO to 0x7E363142293cc25F96F94d5621ea01bCCe2890E8 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
5. Vest 5,000,000 LDO to 0xECE4e341EbcC2B57c40FCf74f47bc61DfDC87fe2 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
6. Vest 5,000,000 LDO to 0x7F514FC631Cca86303e20575592143DD2E253175 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
7. Vest 5,000,000 LDO to 0xdCdeC1fce45e76fE82E036344DE19061d1f0aA31 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
8. Vest 5,000,000 LDO to 0x3d56d86a60b92132b37f226EA5A23F84C805Ce29 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
9. Vest 5,000,000 LDO to 0x28562FBe6d078d2526A0A8d1489245fF74fcA7eB via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
10. Vest 2,000,000 LDO to 0xf930e6d88ecd10788361517fc45C986c0a1b10e5 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
11. Vest 1,934,690.0011 LDO to 0x00E78b7770D8a41A0f37f2d206e65f9Cd391cf0a via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)
12. Revoke role 0xe97b137254058bd94f28d2f3eb79e2d34074ffb488d042e3bc958e0a57d2fa22 on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 from contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364
13. Revoke role 0x2406f1e99f79cea012fb88c5c36566feaeefee0f4b98d3a376b49310222b53c4 on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 from contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364
14. Revoke role 0xf5a08927c847d7a29dc35e105208dbde5ce951392105d712761cc5d17440e2ff on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 from contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364

TODO Vote #{vote_num} passed & executed on ${date+time}, block ${block}.
"""

from typing import Dict, List, Tuple
from brownie import interface

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.permissions import encode_permission_revoke


# ============================== Addresses ===================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
TOKEN_MANAGER = "0xf73a1260d222f447210581DDf212D915c09a3249"
REVESTING_CONTRACT = "0xc2f50d3277539fbd54346278e7b92faa76dc7364"

SOURCE_ADDRESS = "0xa8107de483f9623390d543b77c8e4bbb6f7af752"
SOURCE_ADDRESS_VESTING_ID = 0
SOURCE_LDO = 48_934_690_0011 * 10**14  # 48,934,690.0011 LDO

TARGET_ADDRESSES = [
    "0xED3D9bAC1B26610A6f8C42F4Fd2c741a16647056",
    "0x7bd77405a7c28F50a1010e2185297A25165FD5C6",
    "0x7E363142293cc25F96F94d5621ea01bCCe2890E8",
    "0xECE4e341EbcC2B57c40FCf74f47bc61DfDC87fe2",
    "0x7F514FC631Cca86303e20575592143DD2E253175",
    "0xdCdeC1fce45e76fE82E036344DE19061d1f0aA31",
    "0x3d56d86a60b92132b37f226EA5A23F84C805Ce29",
    "0x28562FBe6d078d2526A0A8d1489245fF74fcA7eB",
    "0xf930e6d88ecd10788361517fc45C986c0a1b10e5",
    "0x00E78b7770D8a41A0f37f2d206e65f9Cd391cf0a",
]
TARGET_LDOS = [
    10_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    2_000_000 * 10**18,
    1_934_690_0011 * 10**14,
]

VESTING_START = 1767225600 # Thu Jan 01 2026 00:00:00 GMT+0000
VESTING_CLIFF = 1798761600 # Fri Jan 01 2027 00:00:00 GMT+0000
VESTING_TOTAL = VESTING_CLIFF
IS_REVOKABLE = True


# ============================= Description ==================================
IPFS_DESCRIPTION = "Execute asset recovery proposal with a 1-year long cliff"


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    token_manager = interface.TokenManager(TOKEN_MANAGER)
    
    vote_desc_items, call_script_items = zip(
        (
            "1. Revoke vesting (ID = 0) of 48,934,690.0011 LDO from 0xa8107de483f9623390d543b77c8e4bbb6f7af752 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249",
            (
                token_manager.address,
                token_manager.revokeVesting.encode_input(
                    SOURCE_ADDRESS,
                    SOURCE_ADDRESS_VESTING_ID,
                )
            )
        ),
        (
            "2. Vest 10,000,000 LDO to 0xED3D9bAC1B26610A6f8C42F4Fd2c741a16647056 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
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
            "3. Vest 5,000,000 LDO to 0x7bd77405a7c28F50a1010e2185297A25165FD5C6 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
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
            "4. Vest 5,000,000 LDO to 0x7E363142293cc25F96F94d5621ea01bCCe2890E8 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
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
            "5. Vest 5,000,000 LDO to 0xECE4e341EbcC2B57c40FCf74f47bc61DfDC87fe2 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
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
            "6. Vest 5,000,000 LDO to 0x7F514FC631Cca86303e20575592143DD2E253175 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
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
        (
            "7. Vest 5,000,000 LDO to 0xdCdeC1fce45e76fE82E036344DE19061d1f0aA31 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[5],
                    TARGET_LDOS[5],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "8. Vest 5,000,000 LDO to 0x3d56d86a60b92132b37f226EA5A23F84C805Ce29 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[6],
                    TARGET_LDOS[6],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "9. Vest 5,000,000 LDO to 0x28562FBe6d078d2526A0A8d1489245fF74fcA7eB via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[7],
                    TARGET_LDOS[7],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "10. Vest 2,000,000 LDO to 0xf930e6d88ecd10788361517fc45C986c0a1b10e5 via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[8],
                    TARGET_LDOS[8],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "11. Vest 1,934,690.0011 LDO to 0x00E78b7770D8a41A0f37f2d206e65f9Cd391cf0a via TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 (start = Jan 01 2026 00:00:00 GMT+0; cliff = total = Jan 01 2027 00:00:00 GMT+0; revokable)",
            (
                token_manager.address,
                token_manager.assignVested.encode_input(
                    TARGET_ADDRESSES[9],
                    TARGET_LDOS[9],
                    VESTING_START,
                    VESTING_CLIFF,
                    VESTING_TOTAL,
                    IS_REVOKABLE
                )
            ),
        ),
        (
            "12. Revoke role 0xe97b137254058bd94f28d2f3eb79e2d34074ffb488d042e3bc958e0a57d2fa22 on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 from contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364",
            encode_permission_revoke(
                target_app=TOKEN_MANAGER,
                permission_name="BURN_ROLE",
                revoke_from=REVESTING_CONTRACT,
            ),
        ),
        (
            "13. Revoke role 0x2406f1e99f79cea012fb88c5c36566feaeefee0f4b98d3a376b49310222b53c4 on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 from contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364",
            encode_permission_revoke(
                target_app=TOKEN_MANAGER,
                permission_name="ISSUE_ROLE",
                revoke_from=REVESTING_CONTRACT,
            ),
        ),
        (
            "14. Revoke role 0xf5a08927c847d7a29dc35e105208dbde5ce951392105d712761cc5d17440e2ff on TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249 from contract 0xc2f50d3277539fbd54346278e7b92faa76dc7364",
            encode_permission_revoke(
                target_app=TOKEN_MANAGER,
                permission_name="ASSIGN_ROLE",
                revoke_from=REVESTING_CONTRACT,
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
