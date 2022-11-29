"""
Voting 29/11/2022.

1. Send 300,000 LDO tokens from treasury to the Token Manager 0xf73a1260d222f447210581DDf212D915c09a3249
2. Assign vested 150,000 LDO tokens to 0x3983083d7FA05f66B175f282FfD83E0d861C777A till Sat Oct 05 2024 00:00:00 +UTC
3. Assign vested 150,000 LDO tokens to 0xE22211Ba98213c866CC5DC8d7D9493b1e7EFD25A till Sat Oct 05 2024 00:00:00 +UTC
"""

import time

from typing import Dict, Tuple, Optional

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, contracts
from utils.finance import make_ldo_payout


def assign_vested(
    target_address: str, amount: int, start: int, cliff: int, vesting: int
) -> Tuple[str, str]:
    token_manager: interface.TokenManager = contracts.token_manager
    revokable: bool = False

    return (
        token_manager.address,
        token_manager.assignVested.encode_input(
            target_address, amount, start, cliff, vesting, revokable
        ),
    )


def start_vote(
    tx_params: Dict[str, str], silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    ldo_vesting_amount: int = 150_000 * 10**18
    ldo_balance_change: int = ldo_vesting_amount * 2

    # see also https://www.unixtimestamp.com/index.php for time conversions
    vesting_start: int = 1664928000  # Wed Oct 05 2022 00:00:00 +UTC
    vesting_cliff: int = 1664928000  # Wed Oct 05 2022 00:00:00 +UTC
    vesting_vesting: int = 1728086400  # Sat Oct 05 2024 00:00:00 +UTC

    destination_address_chorus: str = "0x3983083d7FA05f66B175f282FfD83E0d861C777A"
    destination_address_p2p: str = "0xE22211Ba98213c866CC5DC8d7D9493b1e7EFD25A"

    call_script_items = [
        # # 1. Send 300,000 LDO tokens from treasury to the Token Manager 0xf73a1260d222f447210581DDf212D915c09a3249 to be vested further
        make_ldo_payout(
            target_address=contracts.token_manager.address,
            ldo_in_wei=ldo_balance_change,
            reference="Send 300,000 LDO tokens from treasury to the Token Manager 0xf73a1260d222f447210581DDf212D915c09a3249",
        ),
        # # 2. Assign vested 150,000 LDO tokens to 0x3983083d7FA05f66B175f282FfD83E0d861C777A till Sat Oct 05 2024 00:00:00 +UTC
        assign_vested(
            destination_address_chorus,
            ldo_vesting_amount,
            start=vesting_start,
            cliff=vesting_cliff,
            vesting=vesting_vesting,
        ),
        # # 3. Assign vested 150,000 LDO tokens to 0xE22211Ba98213c866CC5DC8d7D9493b1e7EFD25A till Sat Oct 05 2024 00:00:00 +UTC
        assign_vested(
            destination_address_p2p,
            ldo_vesting_amount,
            start=vesting_start,
            cliff=vesting_cliff,
            vesting=vesting_vesting,
        ),
    ]

    vote_desc_items = [
        "1) Send 300,000 LDO tokens from Treasury to the Token Manager 0xf73a1260d222f447210581DDf212D915c09a3249",
        "2) Assign 150,000 LDO tokens to 0x3983083d7FA05f66B175f282FfD83E0d861C777A vested till Sat Oct 05 2024 00:00:00 +UTC",
        "3) Assign 150,000 LDO tokens to 0xE22211Ba98213c866CC5DC8d7D9493b1e7EFD25A vested till Sat Oct 05 2024 00:00:00 +UTC",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote(
        {"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"}
    )

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
