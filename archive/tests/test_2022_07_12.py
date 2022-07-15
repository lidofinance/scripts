"""
Tests for voting 12/07/2022.
"""
import pytest

from scripts.vote_2022_07_12 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.lido import validate_set_fee_distribution
from utils.config import lido_dao_agent_address


def test_vote(helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, bypass_events_decoding, lido):

    assert lido.getFeeDistribution() == (0, 5000, 5000), "unexpected current fee distribution"
    assert lido.getInsuranceFund() == lido_dao_agent_address, "unexpected insurance contract address"
    assert lido.getTreasury() == lido_dao_agent_address, "unexpected treasury contract address"

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        accounts=accounts, vote_id=vote_id, dao_voting=dao_voting
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    # Validate vote items
    assert lido.getFeeDistribution() == (5000, 0, 5000)

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    validate_set_fee_distribution(evs[0], 5000, 0, 5000), "unexpected new fee distribution"
    assert lido.getInsuranceFund() == lido_dao_agent_address, "insurance contract address has changed"
    assert lido.getTreasury() == lido_dao_agent_address, "treasury contract address has changed"
