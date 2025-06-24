"""
Vote XX/06/2025 [HOLESKY]

1. Grant APP_MANAGER_ROLE role to the AGENT
2. Update `Sandbox Module` implementation
3. Call finalizeUpgrade_v4 on `Sandbox Module`
4. Revoke APP_MANAGER_ROLE role from the AGENT
"""
import time

from typing import Any, Dict
from typing import Tuple, Optional
from brownie import interface, web3, convert  # type: ignore
from utils.config import (
    ARAGON_KERNEL,
    AGENT,
    contracts,
    get_deployer_account,
    get_priority_fee,
    get_is_live
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.agent import dual_governance_agent_forward
from utils.voting import confirm_vote_script, create_vote

SANDBOX_APP_ID = "0x85d2fceef13a6c14c43527594f79fb91a8ef8f15024a43486efac8df2b11e632"
NODE_OPERATORS_REGISTRY_IMPL = "0x834aa47DCd21A32845099a78B4aBb17A7f0bD503"
NOR_EXIT_DEADLINE_IN_SEC = 30 * 60

DESCRIPTION = "Update Sanbox Module Implementation (HOLESKY)"

def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[Any]]:
    vote_desc_items, call_script_items = zip(
       # --- Update Sanbox Module implementation [TESTNET ONLY] ---
        (
            f"1. Grant APP_MANAGER_ROLE role to the AGENT",
            (
                contracts.acl.address,
                contracts.acl.grantPermission.encode_input(
                    AGENT,
                    ARAGON_KERNEL,
                    convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE"))
                )
            )
        ),
        (
            f"2. Update `Sandbox Module` implementation",
            (
                contracts.kernel.address,
                contracts.kernel.setApp.encode_input(
                    contracts.kernel.APP_BASES_NAMESPACE(),
                    SANDBOX_APP_ID,
                    NODE_OPERATORS_REGISTRY_IMPL
                )
            )
        ),
        (
            f"3. Call finalizeUpgrade_v4 on `Sandbox Module`",
            (
                interface.NodeOperatorsRegistry(contracts.sandbox).address,
                interface.NodeOperatorsRegistry(contracts.sandbox).finalizeUpgrade_v4.encode_input(
                    NOR_EXIT_DEADLINE_IN_SEC
                )
            )
        ),
        (
            f"4. Revoke APP_MANAGER_ROLE role from the AGENT",
            (
                contracts.acl.address,
                contracts.acl.revokePermission.encode_input(
                    AGENT,
                    ARAGON_KERNEL,
                    convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE"))
                )
            )
        ),
    )

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

    dg_desc = "\n".join(vote_desc_items)
    dg_vote = dual_governance_agent_forward(call_script_items, dg_desc)
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
