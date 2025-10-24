"""
# Vote 2025_11_17

=== 1. DG PROPOPSAL ===
I. Decrease Easy Track TRP limit
1.1. Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to TODO XXX
1.2. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to TODO XXX

II. Increase SDVT target share
1.3. Increase SDVT (MODULE_ID = 2) share limit from 400 bps to 410 bps in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999

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


# ============================== Constants ===================================
SDVT_MODULE_ID = 2
SDVT_MODULE_NEW_TARGET_SHARE_BP = 410
SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP = 444
SDVT_MODULE_MODULE_FEE_BP = 800
SDVT_MODULE_TREASURY_FEE_BP = 200
SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25

MATIC_FOR_TRANSFER = 508_106 * 10**18


# ============================= Description ==================================
# TODO <a description for IPFS (will appear in the voting description on vote.lido.fi)>
IPFS_DESCRIPTION = "omni nov 2025"


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    staking_router = interface.StakingRouter(STAKING_ROUTER)

    dg_items = [
        agent_forward([
            # 1.1. Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to TODO XXX
            unsafe_set_spent_amount(spent_amount=0, registry_address=ET_TRP_REGISTRY),
        ]),
        agent_forward([
            # 1.2. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to TODO XXX
            set_limit_parameters(
                limit=11_000_000 * 10**18,
                period_duration_months=12,
                registry_address=ET_TRP_REGISTRY,
            ),
        ]),
        agent_forward([
            # 1.3. Increase SDVT (MODULE_ID = 2) share limit from 400 bps to 410 bps in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
            (
                staking_router.address,
                staking_router.updateStakingModule.encode_input(
                    SDVT_MODULE_ID,
                    SDVT_MODULE_NEW_TARGET_SHARE_BP,
                    SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP,
                    SDVT_MODULE_MODULE_FEE_BP,
                    SDVT_MODULE_TREASURY_FEE_BP,
                    SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK,
                    SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                ),
            ),
        ])
    ]
    
    dg_call_script = submit_proposals([
        (dg_items, "TODO DG proposal description")
    ])
    
    vote_desc_items, call_script_items = zip(
        (
            "TODO 1. DG submission description",
            dg_call_script[0]
        ),
        (
            "2. Transfer 508,106 MATIC 0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Lido Labs Foundation 0x95B521B4F55a447DB89f6a27f951713fC2035f3F",
            make_matic_payout(
                target_address=LIDO_LABS_MS,
                matic_in_wei=MATIC_FOR_TRANSFER,
                reference="Transfer 508,106 MATIC from Treasury to Lido Labs Foundation multisig",
            ),
        )
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
