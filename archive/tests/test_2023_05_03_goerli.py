"""
Tests for voting goerli_change_trp_manager.

"""
from scripts.vote_2023_05_03_goerli import start_vote

from brownie.network.transaction import TransactionReceipt
from utils.config import network_name

from utils.test.tx_tracing_helpers import *


def test_vote(
    helpers,
    accounts,
    vote_id_from_env,
    ldo_holder,
    dao_voting,
    trp_factory,
):
    if not network_name() in ("goerli", "goerli-fork"):
        return

    expected_manager_before = "0xE80efD4bA1E683DcB681715EEfDFA741B99828e8"
    expected_manager_after = "0xde0a8383c0c16c472bdf540e38ad9d85b12eff1e"

    actual_manager_before = trp_factory.manager()

    # check manager before
    assert actual_manager_before == expected_manager_before, "Incorrect manager before"

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    actual_manager_after = trp_factory.manager()

    # check manager before
    assert actual_manager_after == expected_manager_after, "Incorrect manager after"