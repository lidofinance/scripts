"""
Vote 2025-09-02 - TW Upgrade Validator Exit Verifier

1. Upgrade Lido Locator implementation
2. Grant REPORT_VALIDATOR_EXITING_STATUS_ROLE to new validator exit verifier
3. Revoke REPORT_VALIDATOR_EXITING_STATUS_ROLE from old validator exit verifier

Vote passed & executed on Sep 02, 2025, 03:47 PM GMT+2, block 1130827
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

OLD_VALIDATOR_EXIT_VERIFIER = "0x7990A2F4E16E3c0D651306D26084718DB5aC9947"
LIDO_LOCATOR_IMPL = "0x47975A61067a4CE41BeB730cf6c57378E55b849A"

DESCRIPTION = "TW Upgrade Validator Exit Verifier (HOODI)"


def encode_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

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
    )

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

    dg_desc = "\n".join(vote_desc_items)
    dg_vote = prepare_proposal(call_script_items, dg_desc)
    vote_items = {dg_desc: dg_vote}
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
