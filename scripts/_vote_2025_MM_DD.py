"""
# TODO Vote 2025_<MM>_<DD>

# TODO <a list of vote items synced with Notion Omnibus checklist>

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals


# ============================== Addresses ===================================
# TODO <a list of addresses that should be used in the voting>


# ============================= Description ==================================
# TODO <a description for IPFS (will appear in the voting description on vote.lido.fi)>
IPFS_DESCRIPTION = ""


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:


    # TODO in case of using smart-contract based omnibus, retrieve vote items from omnibus contract
    # voting_items = brownie.interface.SmartContractOmnibus(omnibus_contract).getVoteItems()
    # vote_desc_items = []
    # call_script_items = []
    # for desc, call_script in voting_items:
    #     vote_desc_items.append(desc)
    #     call_script_items.append((call_script[0], call_script[1].hex()))


    # TODO in case of using script based omnibus, write vote items manually
    # dg_items = [
    #     # TODO 1.1. DG voting item 1 description
    #     agent_forward([
    #         (dg_item_address_1, dg_item_encoded_input_1)
    #     ]),
    #     # TODO 1.2. DG voting item 2 description
    #     agent_forward([
    #         (dg_item_address_2, dg_item_encoded_input_2)
    #     ]),
    # ]
    #
    # dg_call_script = submit_proposals([
    #     (dg_items, "TODO DG proposal description")
    # ])
    #
    # vote_desc_items, call_script_items = zip(
    #     (
    #         "TODO 1. DG submission description",
    #         dg_call_script[0]
    #     ),
    #     (
    #         "TODO 2. Voting item 2 description",
    #         calldata_2,
    #     ),
    #     (
    #         "TODO 3. Voting item 3 description",
    #         calldata_3,
    #     ),
    # )


    # TODO return vote_desc_items, call_script_items
    pass


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
