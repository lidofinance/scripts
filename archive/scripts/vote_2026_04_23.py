"""
Vote 2026_04_23

1. Transfer 2500 stETH 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Lido Labs Foundation operational multisig 0x95B521B4F55a447DB89f6a27f951713fC2035f3F

Vote #200 passed & executed on Apr-28-2026 08:09:59 PM UTC, block 24980862.
"""

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.finance import make_steth_payout

# ============================== Constants ===================================

PAYMENT_AMOUNT = 2500 * 10**18
LIDO_LABS_MULTISIG = "0x95B521B4F55a447DB89f6a27f951713fC2035f3F"

# ============================= IPFS Description ==================================
IPFS_DESCRIPTION = """
Transfer 2500 stETH from Aragon Agent to Lido Labs Foundation operational multisig, [as proposed on the forum](https://research.lido.fi/t/lido-dao-contribution-to-coordinated-rseth-relief-effort/11483).
"""


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    call_script_items = [
        make_steth_payout(
            target_address=LIDO_LABS_MULTISIG,
            steth_in_wei=PAYMENT_AMOUNT,
            reference="Transfer 2500 stETH from Aragon Agent to Lido Labs Foundation operational multisig",
        )
    ]
    vote_desc_items = [
        "1. Transfer 2500 stETH 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Lido Labs Foundation operational multisig 0x95B521B4F55a447DB89f6a27f951713fC2035f3F"
    ]

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
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
