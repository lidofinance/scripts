"""
Vote [DATE] - Submit Exit Requests Hash to ValidatorsExitBus Oracle

1. Upgrade Lido Locator implementation
2. Grant REPORT_VALIDATOR_EXITING_STATUS_ROLE to new validator exit verifier
3. Revoke REPORT_VALIDATOR_EXITING_STATUS_ROLE from old validator exit verifier
4. Grant SUBMIT_REPORT_HASH_ROLE to the agent
5. Submit exit requests hash to ValidatorsExitBus Oracle
6. Revoke SUBMIT_REPORT_HASH_ROLE from the agent

Vote passed & executed on [DATE], block [BLOCK_NUMBER]
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

OLD_VALIDATOR_EXIT_VERIFIER = "0xFd4386A8795956f4B6D01cbb6dB116749731D7bD"
# CID: bafkreidetdrrl3zjxer6tv6qqnsxdqrldntydluorllmetpsozl4yr7pva - validators data
EXIT_HASH_TO_SUBMIT = "0x4e72449ac50f5fa83bc2d642f2c95a63f72f1b87ad292f52c0fe5c28f3cf6e47"
LIDO_LOCATOR_IMPL = "0xA656983a6686615850BE018b7d42a7C3E46DcD71"

DESCRIPTION = "TW Upgrade & Test for Validators Exiting via Voting (HOODI)"


def encode_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    validators_exit_bus = interface.ValidatorsExitBusOracle(contracts.validators_exit_bus_oracle)

    vote_desc_items, call_script_items = zip(
        (
            "1. Upgrade Lido Locator implementation",
            agent_forward([encode_proxy_upgrade_to(contracts.lido_locator, LIDO_LOCATOR_IMPL)]),
        ),
        (
            "2. Grant REPORT_VALIDATOR_EXITING_STATUS_ROLE to new validator exit verifier",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.staking_router,
                        role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                        grant_to=contracts.validator_exit_verifier,
                    )
                ]
            ),
        ),
        (
            "3. Revoke REPORT_VALIDATOR_EXITING_STATUS_ROLE from old validator exit verifier",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.staking_router,
                        role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                        revoke_from=OLD_VALIDATOR_EXIT_VERIFIER,
                    )
                ]
            ),
        ),
        (
            "4. Grant SUBMIT_REPORT_HASH_ROLE to the agent",
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
            "5. Submit exit requests hash to ValidatorsExitBus Oracle",
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
            "6. Revoke SUBMIT_REPORT_HASH_ROLE from the agent",
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
