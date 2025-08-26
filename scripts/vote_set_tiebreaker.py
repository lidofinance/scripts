"""
# TODO Vote 2025_<MM>_<DD>

# TODO <a list of vote items synced with Notion Omnibus checklist>

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from brownie import chain, interface, accounts

from typing import Dict, List, Tuple

from utils.test.helpers import ETH
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from utils.balance import set_balance_in_wei

from configs.config_mainnet import (
    TIEBREAKER_VALUES,
    WSTETH_TOKEN,
    ESCROW_VETO_SIGNALLING,
    LIDO,
    DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES,
    DUAL_GOVERNANCE,
    RESEAL_MANAGER,
    WITHDRAWAL_QUEUE,
)


# ============================== Addresses ===================================
TEST_TIEBREAKER_PARTICIPANTS = [
    "0xcdF49b058D606AD34c5789FD8c3BF8B3E54bA2db",
    "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316",
    "0x2e59A20f205bB85a89C53f1936454680651E618e",
]


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    dg_items = [
        (
            TIEBREAKER_VALUES["SUB_COMMITTEES"][0]["ADDRESS"],
            interface.TiebreakerCommittee(TIEBREAKER_VALUES["SUB_COMMITTEES"][0]["ADDRESS"]).addMembers.encode_input(
                TEST_TIEBREAKER_PARTICIPANTS, 2
            ),
        ),
        (
            TIEBREAKER_VALUES["SUB_COMMITTEES"][0]["ADDRESS"],
            interface.TiebreakerCommittee(TIEBREAKER_VALUES["SUB_COMMITTEES"][0]["ADDRESS"]).removeMembers.encode_input(
                TIEBREAKER_VALUES["SUB_COMMITTEES"][0]["MEMBERS"], 2
            ),
        ),
        (
            TIEBREAKER_VALUES["SUB_COMMITTEES"][1]["ADDRESS"],
            interface.TiebreakerCommittee(TIEBREAKER_VALUES["SUB_COMMITTEES"][1]["ADDRESS"]).addMembers.encode_input(
                TEST_TIEBREAKER_PARTICIPANTS, 2
            ),
        ),
        (
            TIEBREAKER_VALUES["SUB_COMMITTEES"][1]["ADDRESS"],
            interface.TiebreakerCommittee(TIEBREAKER_VALUES["SUB_COMMITTEES"][1]["ADDRESS"]).removeMembers.encode_input(
                TIEBREAKER_VALUES["SUB_COMMITTEES"][1]["MEMBERS"], 2
            ),
        ),
    ]

    dg_call_script = submit_proposals([(dg_items, "Set tiebreaker participants")])

    vote_desc_items, call_script_items = zip(("Set tiebreaker participants for testing", dg_call_script[0]))

    return vote_desc_items, call_script_items


def set_tiebreaker_participants():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = calculate_vote_ipfs_description("Set tiebreaker participants for testing")

    vote_id, _ = confirm_vote_script(vote_items, False, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)


def enact_tie():

    if get_is_live():
        raise Exception("This script is for local testing only.")

    st_eth_token = interface.StETH(LIDO)
    st_eth_whale = accounts.at(WSTETH_TOKEN, force=True)
    set_balance_in_wei(st_eth_whale.address, ETH(10))

    tx_params = {"from": st_eth_whale}

    whale_balance = st_eth_token.balanceOf(st_eth_whale)
    st_eth_token.approve(ESCROW_VETO_SIGNALLING, whale_balance * 2, tx_params)

    interface.DualGovernanceEscrow(ESCROW_VETO_SIGNALLING).lockStETH(whale_balance, tx_params)

    chain.mine(1, chain.time() + DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_MAX_DURATION"] + 1)

    interface.DualGovernance(DUAL_GOVERNANCE).activateNextState(tx_params)

    assert interface.DualGovernance(DUAL_GOVERNANCE).getPersistedState() == 5  # TIE


def pause_withdrawal_queue():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    reseal_manager = accounts.at(RESEAL_MANAGER, force=True)
    set_balance_in_wei(reseal_manager.address, ETH(10))
    tx_params = {"from": reseal_manager}

    interface.WithdrawalQueueERC721(WITHDRAWAL_QUEUE).pauseFor(2**256 - 1, tx_params)


def propose_some_dg_proposal():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    dg_items = [
        (
            DUAL_GOVERNANCE,
            interface.DualGovernance(DUAL_GOVERNANCE).getPersistedState.encode_input(),
        ),
    ]

    dg_call_script = submit_proposals([(dg_items, "Check DG state")])

    vote_desc_items, call_script_items = zip(("Check DG state", dg_call_script[0]))
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = calculate_vote_ipfs_description("Test vote")

    vote_id, _ = confirm_vote_script(vote_items, False, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
