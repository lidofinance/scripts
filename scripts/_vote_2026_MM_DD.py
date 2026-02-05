"""
TODO Vote 2026_MM_DD

TODO <list of items synced with Notion>

TODO (after vote) Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from brownie import interface
from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals

from utils.agent import agent_forward


# ============================== Constants ===================================
# TODO list of constants


# ============================= IPFS Description ==================================
# TODO IPFS description text
IPFS_DESCRIPTION = """
"""


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    # TODO set up interface objects

    return [
        # TODO 1.1. item description
        agent_forward([
            (
                <ADDRESS>,
                <METHOD>.encode_input(<PARAMS>)
            )
        ]),

        # TODO 1.2. item description
        agent_forward([
            <UTILS_METHOD>(<PARAMS>)
        ]),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    # TODO set up interface objects

    # TODO in case of using smart-contract based omnibus, retrieve vote items from omnibus contract
    # voting_items = brownie.interface.SmartContractOmnibus(omnibus_contract).getVoteItems()
    # vote_desc_items = []
    # call_script_items = []
    # for desc, call_script in voting_items:
    #     vote_desc_items.append(desc)
    #     call_script_items.append((call_script[0], call_script[1].hex()))
    # return vote_desc_items, call_script_items
    #
    # OR
    #
    # vote_desc_items = []
    # call_script_items = []
    # # 1. receive DG vote items from omnibus contract
    # contract_dg_items = interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).getVoteItems()
    # dg_items = []
    # for _, call_script in contract_dg_items:
    #     dg_items.append((call_script[0], call_script[1].hex()))
    # dg_call_script = submit_proposals([
    #     (dg_items, DG_PROPOSAL_DESCRIPTION)
    # ])
    # vote_desc_items.append(DG_SUBMISSION_DESCRIPTION)
    # call_script_items.append(dg_call_script[0])
    # # 2. receive non-DG vote items from omnibus contract
    # voting_items = interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).getVotingVoteItems()
    # for desc, call_script in voting_items:
    #     vote_desc_items.append(desc)
    #     call_script_items.append((call_script[0], call_script[1].hex()))
    # return vote_desc_items, call_script_items

    dg_items = get_dg_items()

    dg_call_script = submit_proposals([
        # TODO DG proposal description
        (dg_items, "DG proposal description")
    ])

    vote_desc_items, call_script_items = zip(
        (
            # TODO DG proposal description
            "1. DG proposal submition description",
            dg_call_script[0]
        ),
        (
            # TODO item description
            "2. Item description",
            (
                <ADDRESS>,
                <METHOD>.encode_input(<PARAMS>)
            )
        ),
        (
            # TODO item description
            "3. Item description",
            <UTILS_METHOD>(<PARAMS>)
        ),
    )

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
