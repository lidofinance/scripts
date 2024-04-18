"""
Voting 23/04/2024.

I. Gate Seal
1. Grant PAUSE_ROLE on WithdrawalQueue for the new GateSeal
2. Grant PAUSE_ROLE on ValidatorsExitBus for the new GateSeal
3. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
4. Revoke PAUSE_ROLE on ValidatorsExitBus from the old GateSeal
"""

import time

from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)
from utils.agent import agent_forward
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role

proposed_gate_seal_address = "0x79243345eDbe01A7E42EDfF5900156700d22611c"

description = """
One of the parts of Lido V2 is GateSeal. It’s been set up with an expiration date of 1 May 2024. The proposal seeks to prolong the functioning of the GateSeal mechanics for the following year.

**Proposed actions:**

1. Grant role "PAUSE_ROLE" for proposed Gate Seal contract on Withdrawal Queue ERC721 contract
2. Grant role "PAUSE_ROLE" for proposed Gate Seal contract on Validators Exit Bus Oracle contract 
3. Revoke role "PAUSE_ROLE" from expiring Gate Seal contract on Withdrawal Queue ERC721 contract
4. Revoke role "PAUSE_ROLE" from expiring Gate Seal contract on Validators Exit Bus Oracle contract

Gate Seal (proposed): https://etherscan.io/address/0x79243345eDbe01A7E42EDfF5900156700d22611c#readContract
Gate Seal (proposed to remove): https://etherscan.io/address/0x1ad5cb2955940f998081c1ef5f5f00875431aa90#readContract
Withdrawal Queue ERC721 contract: https://etherscan.io/address/0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1#readContract
Validators Exit Bus Oracle contract: https://etherscan.io/address/0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e#readContract

"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Gate Seal
        #
        (
            "1) Grant PAUSE_ROLE on WithdrawalQueue for the new GateSeal",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.withdrawal_queue,
                        role_name="PAUSE_ROLE",
                        grant_to=proposed_gate_seal_address,
                    )
                ]
            ),
        ),

                (
            "2) Grant PAUSE_ROLE on ValidatorsExitBus for the new GateSeal",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="PAUSE_ROLE",
                        grant_to=proposed_gate_seal_address,
                    )
                ]
            ),
        ),
                (
            "3) Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.withdrawal_queue,
                        role_name="PAUSE_ROLE",
                        revoke_from=contracts.gate_seal,
                    )
                ]
            ),
        ),
                (
            "4) Revoke PAUSE_ROLE on ValidatorsExitBus from the old GateSeal",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="PAUSE_ROLE",
                        revoke_from=contracts.gate_seal,
                    )
                ]
            ),
        ),

    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
