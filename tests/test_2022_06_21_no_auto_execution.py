"""
Test vote cannot be auto executed if created by 50%+ LDO holder.
"""

from brownie import accounts
from scripts.upgrade_2022_06_21 import start_vote
from utils.voting import create_vote, bake_vote_items


def create_dummy_vote(ldo_holder: str) -> int:
    """Creates an empty vote script"""
    vote_items = bake_vote_items(vote_desc_items=[], call_script_items=[])
    return create_vote(vote_items, {"from": ldo_holder}, cast_vote=True, executes_if_decided=True)[0]


def test_vote(ldo_holder, helpers, dao_voting, ldo_token, dao_token_manager, vote_id_from_env):
    # Prepare account with 50+% of LDO
    # NB: it has to be TokenManager due to `token_manager.forward` in create_vote
    ldo_mega_amount = round(ldo_token.totalSupply() * 1.1)  # to constitute at least 50%
    ldo_mega_holder = dao_token_manager.address
    ldo_token.generateTokens(ldo_mega_holder, ldo_mega_amount, {"from": dao_token_manager.address})
    assert (ldo_token.balanceOf(ldo_mega_holder) / ldo_token.totalSupply()) > 0.5

    # Check a vote is auto-executed
    dummy_vote_id = create_dummy_vote(ldo_mega_holder)
    assert helpers.is_executed(dummy_vote_id, dao_voting)

    ##
    # START VOTE
    ##
    vote_id = vote_id_from_env if vote_id_from_env is not None else start_vote({"from": ldo_holder}, silent=True)[0]

    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether")

    # Check a vote isn't auto-executed
    dummy_vote_id = create_dummy_vote(ldo_mega_holder)
    assert not helpers.is_executed(dummy_vote_id, dao_voting)
