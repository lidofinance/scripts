"""
Voting 23/04/2024.

I. Simple Delegation
1. Push new Voting app version to the Voting Repo 0x4ee3118e3858e8d7164a634825bfe0f73d99c792
2. Upgrade the Aragon Voting contract implementation 0x63C7F17210f6a7061e887D05BBF5412085e9DF43
3. Upgrade TRP voting adapter 0x5Ea73d6AE9B2E57eF865A3059bdC5C06b8e46072

II. Gate Seal
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
from utils.repo import add_implementation_to_voting_app_repo
from utils.kernel import update_app_implementation
from utils.agent import agent_forward
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role

updated_trp_voting_adapter = "0x5Ea73d6AE9B2E57eF865A3059bdC5C06b8e46072"

updated_voting_app = {
    "address": "0x63C7F17210f6a7061e887D05BBF5412085e9DF43",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (4, 0, 0),
}

proposed_gate_seal_address = "0x79243345eDbe01A7E42EDfF5900156700d22611c"

description = """
aboba
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Simple Delegation
        #
        (
            "1) Push new Voting app version to the Voting Repo",
            add_implementation_to_voting_app_repo(
                updated_voting_app["version"],
                updated_voting_app["address"],
                updated_voting_app["content_uri"],
            ),
        ),
        (
            "2) Upgrade the Aragon Voting contract implementation",
            update_app_implementation(updated_voting_app["id"], updated_voting_app["address"]),
        ),
        (
            "3) Upgrade TRP voting adapter",
            agent_forward(
                [
                    (
                        contracts.trp_escrow_factory.address,
                        contracts.trp_escrow_factory.update_voting_adapter.encode_input(updated_trp_voting_adapter),
                    )
                ]
            ),
        ),
        #
        # II. Gate Seal
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
