"""
Tests for voting 12/09/2023

"""
from scripts.vote_2023_09_12 import start_vote

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
from utils.test.event_validators.allowed_recipient_registry import (
    validate_limits_parameters_changed_event,
    validate_spent_amount_changed_event,
)


def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
):
    ## parameters
    agent = contracts.agent
    nor = contracts.node_operators_registry
    staking_router = contracts.staking_router
    target_NO_id = 1
    target_validators_count_change_request = TargetValidatorsCountChanged(
        nodeOperatorId=target_NO_id, targetValidatorsCount=0
    )

    # web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    trp_registry = interface.AllowedRecipientRegistry("0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8")

    # 1
    trp_registry_limit_before = trp_registry.getLimitParameters()
    assert trp_registry_limit_before[0] == 22_000_000 * (10**18)
    assert trp_registry_limit_before[1] == 12

    # 2
    trp_registry_state_before = trp_registry.getPeriodState()
    assert trp_registry_state_before[0] == 12_722_460 * (10**18)
    assert trp_registry_state_before[1] == 9_277_540 * (10**18)

    # 3
    assert staking_router.hasRole(STAKING_MODULE_MANAGE_ROLE, agent.address) == False

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
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 4, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)

    assert get_lido_vote_cid_from_str(metadata) == "bafkreiedn6r4hakzudovskssnzwijpu4eyesvur33ip5tvf5ajlgnqi5dy"

    assert staking_router.hasRole(STAKING_MODULE_MANAGE_ROLE, agent.address) == True

    NO_summary_after = nor.getNodeOperatorSummary(target_NO_id)
    assert NO_summary_after[0]
    assert NO_summary_after[1] == 0
    assert NO_summary_after[2] == 0
    assert NO_summary_after[3] == 0
    assert NO_summary_after[4] == 0
    assert NO_summary_after[5] == 0
    assert NO_summary_after[6] == 1000
    assert NO_summary_after[7] == 0

    # 1
    trp_registry_limit_after = trp_registry.getLimitParameters()
    assert trp_registry_limit_after[0] == 9_277_540 * (10**18)
    assert trp_registry_limit_after[1] == 12

    # 2
    trp_registry_state_after = trp_registry.getPeriodState()
    assert trp_registry_state_after[0] == 0
    assert trp_registry_state_after[1] == 9_277_540 * (10**18)
    assert trp_registry_state_after[2] == trp_registry_state_before[2]
    assert trp_registry_state_after[3] == trp_registry_state_before[3]

    assert trp_registry_state_after[1] == trp_registry_state_before[1]

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_limits_parameters_changed_event(evs[0], 9_277_540 * (10**18), 12)

    validate_spent_amount_changed_event(evs[1], 0)

    validate_grant_role_event(evs[2], STAKING_MODULE_MANAGE_ROLE, agent.address, agent.address)

    validate_target_validators_count_changed_event(evs[3], target_validators_count_change_request)

    # validate_revoke_role_event(evs[4], STAKING_MODULE_MANAGE_ROLE, agent.address, agent.address)
