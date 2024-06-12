"""
Tests for voting XX/07/2024

"""

from brownie import Contract, web3, chain  # type: ignore
from brownie import reverts, accounts, interface
from configs.config_holesky import LDO_HOLDER_ADDRESS_FOR_TESTS
from scripts.vote_2024_07_XX import start_vote
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import (
    LIDO_LOCATOR_IMPL,
    contracts,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event


def test_vote(helpers, vote_ids_from_env, bypass_events_decoding, accounts):

    # assert interface.OssifiableProxy(contracts.lido_locator).proxy__getImplementation() == LIDO_LOCATOR_IMPL

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}  # LDO_HOLDER_ADDRESS_FOR_TESTS
        vote_id, _ = start_vote(tx_params, silent=True)

    print("accounts... ", accounts[0])
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    assert interface.OssifiableProxy(contracts.lido_locator).proxy__getImplementation() == LIDO_LOCATOR_IMPL
