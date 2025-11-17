"""
# Vote 2025_12_10

=== 1. DG PROPOPSAL ===
I. Lido V3 upgrade - stVaults

=== NON-DG ITEMS ===
II. Lido V3 ET factories rights

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from brownie import interface


# ============================== Addresses ===================================
OMNIBUS_CONTRACT = "0xda9D35b108f9538F8025f1c692265b9451D42f8b" # TODO replace with the actual omnibus contract address


# ============================= Description ==================================
# TODO <a description for IPFS (will appear in the voting description on vote.lido.fi)>
IPFS_DESCRIPTION = "omni nov 2025"


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    vote_desc_items = []
    call_script_items = []

    # receive DG vote items from omnibus contract
    contract_dg_items = interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).getVoteItems()

    dg_items = []
    for desc, call_script in contract_dg_items:
        dg_items.append((call_script[0], '0x' + call_script[1].hex()))

    dg_call_script = submit_proposals([
        (dg_items, "TODO DG proposal description")# TODO take from next-vote
    ])

    vote_desc_items.append("TODO DG submission description")
    call_script_items.append(dg_call_script[0])

    # receive non-DG vote items from omnibus contract
    voting_items = interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).getVotingVoteItems()

    for desc, call_script in voting_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

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

    # TODO assert interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).isValidVoteScript(vote_id, )

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
