import pytest

from scripts.vote_2022_10_04 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.lido import validate_set_fee_distribution
from utils.config import lido_dao_agent_address


def test_vote(helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, bypass_events_decoding, lido):
    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(accounts=accounts, vote_id=vote_id, dao_voting=dao_voting)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 2, "Incorrect voting items count"

    assert lido.getInsurance() == "0x8B3f33234ABD88493c0Cd28De33D583B70beDe35"
    assert lido.sharesOf("0x8B3f33234ABD88493c0Cd28De33D583B70beDe35") == 5466.46 * 10**18
