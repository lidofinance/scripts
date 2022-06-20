"""
TODO
"""

from brownie import accounts, interface, reverts
from scripts.upgrade_2022_06_21 import start_vote
from utils.config import (
    lido_dao_voting_repo,
    lido_dao_lido_repo,
    lido_dao_voting_address,
    lido_dao_steth_address,
    network_name,
)

from utils.voting import create_vote, bake_vote_items
from utils.evm_script import EMPTY_CALLSCRIPT

from utils.test.tx_tracing_helpers import *


def create_dummy_vote(ldo_holder: str) -> int:
    vote_items = bake_vote_items(
        vote_desc_items=[],
        call_script_items=[],
    )

    tx_params = {"from": ldo_holder}

    vote_id, _ = create_vote(vote_items, tx_params, cast_vote=True, executes_if_decided=True)
    return vote_id


def test_vote(ldo_holder, helpers, dao_voting, ldo_token, dao_token_manager):
    ldo_mega_amount = round(ldo_token.totalSupply() * 1.1)  # to constitute at least 51+%
    ldo_token.generateTokens(dao_token_manager.address, ldo_mega_amount, {"from": dao_token_manager.address})

    assert (ldo_token.balanceOf(dao_token_manager.address) / ldo_token.totalSupply()) > 0.51

    tx = dao_voting.newVote(EMPTY_CALLSCRIPT, "", True, True, {"from": dao_token_manager.address})

    dummy_vote_id = tx.events["StartVote"]["voteId"]

    print(dummy_vote_id)

    snapshot_block = dao_voting.getVote(dummy_vote_id)[3]
    assert ldo_token.balanceOfAt(ldo_holder, snapshot_block) == ldo_token.balanceOf(ldo_holder)

    # TODO: why, why zero "yea" votes and not executed?
    assert dao_voting.getVote(dummy_vote_id)[6] > 0, 'there are NO votes "yea"'
    assert helpers.is_executed(dummy_vote_id, dao_voting)

    # ##
    # # START VOTE
    # ##
    # vote_id = start_vote({"from": ldo_holder}, silent=True)[0]

    # tx: TransactionReceipt = helpers.execute_vote(
    #     vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether"
    # )

    # TODO: check the other vote isn't auto-executed
