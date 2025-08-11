"""
Vote [TODO] - Submit Exit Requests Hash to ValidatorsExitBus Oracle

1. Grant SUBMIT_REPORT_HASH_ROLE to the agent
2. Submit exit requests hash to ValidatorsExitBus Oracle
3. Revoke SUBMIT_REPORT_HASH_ROLE from the agent

Vote passed & executed on [TODO], block [TODO]
"""

import time
from typing import Any, Dict, Tuple, Optional
from brownie import interface
from brownie.network.transaction import TransactionReceipt

from utils.config import contracts
from utils.voting import confirm_vote_script, create_vote
from archive.scripts.vote_tw_csm2_hoodi import prepare_proposal
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.agent import agent_forward
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role

# CID: bafkreihtr6nlijylmesqmsp3v2h7c3zbkx7bqwt5qu3jbahojnrt2qm2vy - validators data
EXIT_HASH_TO_SUBMIT = "0xd76d7dd9cb2f102583d2bafbd6deb12473838e444d0d7226773895333fe32beb"

DESCRIPTION = "Test for Validators Exiting via Voting (HOODI)"


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    validators_exit_bus = interface.ValidatorsExitBusOracle(contracts.validators_exit_bus_oracle)

    vote_desc_items, call_script_items = zip(
        (
            "1. Grant SUBMIT_REPORT_HASH_ROLE to the agent",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=validators_exit_bus,
                        role_name="SUBMIT_REPORT_HASH_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "2. Submit exit requests hash to ValidatorsExitBus Oracle",
            agent_forward(
                [
                    (
                        contracts.validators_exit_bus_oracle.address,
                        validators_exit_bus.submitExitRequestsHash.encode_input(EXIT_HASH_TO_SUBMIT),
                    )
                ]
            ),
        ),
        (
            "3. Revoke SUBMIT_REPORT_HASH_ROLE from the agent",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=validators_exit_bus,
                        role_name="SUBMIT_REPORT_HASH_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
    )

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

    dg_vote = prepare_proposal(call_script_items, DESCRIPTION)
    vote_items = {DESCRIPTION: dg_vote}

    assert confirm_vote_script(vote_items, silent, desc_ipfs)
    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.


if __name__ == "__main__":
    main()
