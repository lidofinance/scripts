"""
# Vote 2025_11_24

=== 1. DG PROPOPSAL ===
I. Decrease Easy Track TRP limit
1.1. Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0 LDO
1.2. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 15'000'000 LDO with unchanged period duration of 12 months

II. Increase SDVT target share
1.3. Increase SDVT (MODULE_ID = 2) share limit from 400 bps to 430 bps in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999

=== NON-DG ITEMS ===
III. Transfer MATIC from Lido Treasury to Lido Labs Foundation
2. Transfer 508,106 MATIC 0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Lido Labs Foundation 0x95B521B4F55a447DB89f6a27f951713fC2035f3F

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from typing import Dict, List, Tuple

from utils.finance import make_matic_payout
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from utils.agent import agent_forward
from brownie import interface
from utils.allowed_recipients_registry import (
    unsafe_set_spent_amount,
    set_limit_parameters,
)


# ============================== Addresses ===================================
ET_TRP_REGISTRY = "0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
LIDO_LABS_MS = "0x95B521B4F55a447DB89f6a27f951713fC2035f3F"

OMNIBUS_CONTRACT = "0xA3710716965497e62bC3165Eb7DD2a1B1437f8Af" # TODO replace with the actual omnibus contract address

# ============================== Constants ===================================
SDVT_MODULE_ID = 2
SDVT_MODULE_NEW_TARGET_SHARE_BP = 430
SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP = 444
SDVT_MODULE_MODULE_FEE_BP = 800
SDVT_MODULE_TREASURY_FEE_BP = 200
SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25

TRP_PERIOD_DURATION_MONTHS = 12
TRP_NEW_LIMIT = 15_000_000 * 10**18
TRP_NEW_SPENT_AMOUNT = 0

MATIC_FOR_TRANSFER = 508_106 * 10**18


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
    for desc, call_script in contract_dg_items: # TODO looks like this descriptions are not used
        dg_items.append((call_script[0], '0x' + call_script[1].hex()))

    dg_call_script = submit_proposals([
        (dg_items, "TODO DG proposal description") # TODO looks like this description is not used
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
