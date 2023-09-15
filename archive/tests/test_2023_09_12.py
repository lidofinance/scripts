"""
Tests for voting 12/09/2023

"""
from archive.scripts.vote_2023_09_12 import start_vote

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.tx_tracing_helpers import *

from utils.test.event_validators.node_operators_registry import (
    validate_target_validators_count_changed_event,
    TargetValidatorsCountChanged,
)
from utils.test.event_validators.permission import validate_grant_role_event


def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
):
    # params
    agent = contracts.agent
    nor = contracts.node_operators_registry
    staking_router = contracts.staking_router
    target_NO_id = 1
    target_validators_count_change_request = TargetValidatorsCountChanged(
        nodeOperatorId=target_NO_id, targetValidatorsCount=0
    )

    # web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    # 1)
    assert staking_router.hasRole(STAKING_MODULE_MANAGE_ROLE, agent.address) == False

    # 2)
    NO_summary_before = nor.getNodeOperatorSummary(target_NO_id)
    assert NO_summary_before[0] == False
    assert NO_summary_before[1] == 0
    assert NO_summary_before[2] == 0
    assert NO_summary_before[3] == 0
    assert NO_summary_before[4] == 0
    assert NO_summary_before[5] == 0
    assert NO_summary_before[6] == 1000
    assert NO_summary_before[7] == 0

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 2, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)

    assert get_lido_vote_cid_from_str(metadata) == "bafkreiapvuobyrudww3oqhfopbs2fdmtebi6jnvpeb3plxkajnhafw25im"
    # 1)
    assert staking_router.hasRole(STAKING_MODULE_MANAGE_ROLE, agent.address) == True

    # 2)
    NO_summary_after = nor.getNodeOperatorSummary(target_NO_id)
    assert NO_summary_after[0] == True
    assert NO_summary_after[1] == 0
    assert NO_summary_after[2] == 0
    assert NO_summary_after[3] == 0
    assert NO_summary_after[4] == 0
    assert NO_summary_after[5] == 0
    assert NO_summary_after[6] == 1000
    assert NO_summary_after[7] == 0

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_grant_role_event(evs[0], STAKING_MODULE_MANAGE_ROLE, agent.address, agent.address)

    validate_target_validators_count_changed_event(evs[1], target_validators_count_change_request)
