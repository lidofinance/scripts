"""
Voting 23/04/2024.

1. Grant PAUSE_ROLE on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 for the new GateSeal 0x79243345eDbe01A7E42EDfF5900156700d22611c
2. Grant PAUSE_ROLE on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e for the new GateSeal 0x79243345eDbe01A7E42EDfF5900156700d22611c
3. Revoke PAUSE_ROLE on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 from the old GateSeal 0x1ad5cb2955940f998081c1ef5f5f00875431aa90
4. Revoke PAUSE_ROLE on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e from the old GateSeal 0x1ad5cb2955940f998081c1ef5f5f00875431aa90
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
old_gate_seal = "0x1aD5cb2955940F998081c1eF5f5F00875431aA90"

description = """
The vote is intended to change the current **GateSeal for the WithdrawalQueue and ValidatorExitBusOracle** contracts, which expires on May 1, 2024, with a new one that will **expire on April 1, 2025**. The GateSeal enables a one-time, immediate emergency pause of these contracts for 6 days.

The new GateSeal contract was deployed using the GateSeal Factory from the GateSeal Blueprint. [statemind.io](https://statemind.io/) audited the initial Factory and Blueprint ([report](https://github.com/lidofinance/audits/?tab=readme-ov-file#04-2023-statemind-gateseals-audit)) and [verified](https://github.com/lidofinance/audits/blob/main/Statemind%20GateSeal%20Deployment%20Validation%2004-2024.pdf) that the new GateSeal is identical to the Blueprint and has the correct parameters.

More information on the [Research forum](https://research.lido.fi/t/renew-gateseal-for-the-withdrawal-queue-and-validator-exit-bus-oracle/7081)
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        (
            "1) Grant PAUSE_ROLE on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 for the new GateSeal 0x79243345eDbe01A7E42EDfF5900156700d22611c",
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
            "2) Grant PAUSE_ROLE on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e for the new GateSeal 0x79243345eDbe01A7E42EDfF5900156700d22611c",
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
            "3) Revoke PAUSE_ROLE on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 from the old GateSeal 0x1ad5cb2955940f998081c1ef5f5f00875431aa90",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.withdrawal_queue,
                        role_name="PAUSE_ROLE",
                        revoke_from=old_gate_seal,
                    )
                ]
            ),
        ),
        (
            "4) Revoke PAUSE_ROLE on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e from the old GateSeal 0x1ad5cb2955940f998081c1ef5f5f00875431aa90",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="PAUSE_ROLE",
                        revoke_from=old_gate_seal,
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
