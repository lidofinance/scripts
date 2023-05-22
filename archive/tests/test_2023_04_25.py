"""
Tests for voting 25/04/2023.

"""
from scripts.vote_2023_04_25 import start_vote

from brownie.network.transaction import TransactionReceipt

from utils.config import network_name
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    validate_node_operator_reward_address_set_event,
    NodeOperatorNameSetItem,
    NodeOperatorRewardAddressSetItem,
)
from utils.test.event_validators.easy_track import (
    validate_motions_count_limit_changed_event
)

def test_vote(
    helpers,
    accounts,
    vote_id_from_env,
    bypass_events_decoding,
    ldo_holder,
    dao_voting,
    node_operators_registry,
    easy_track
):

    CertusOne_Jumpcrypto_id = 1
    CertusOne_Jumpcrypto_name_before = "Certus One"
    CertusOne_Jumpcrypto_name_after = "jumpcrypto"

    ConsenSysCodefi_Consensys_id = 21
    ConsenSysCodefi_Consensys_name_before = "ConsenSys Codefi"
    ConsenSysCodefi_Consensys_name_after = "Consensys"

    SkillZ_Kiln_id = 8
    SkillZ_Kiln_name_before = "SkillZ"
    SkillZ_Kiln_name_after = "Kiln"
    SkillZ_Kiln_address_before = "0xe080E860741b7f9e8369b61645E68AD197B1e74C"
    SkillZ_Kiln_address_after = "0xD6B7d52E15678B9195F12F3a6D6cb79dcDcCb690"

    motionsCountLimit_before = 12
    motionsCountLimit_after = 20

    # NO's data indexes
    active_index = 0
    name_index = 1
    rewardAddress_index = 2
    stakingLimit_index = 3
    stoppedValidators_index = 4

    # get NO's data before
    CertusOne_Jumpcrypto_data_before = node_operators_registry.getNodeOperator(CertusOne_Jumpcrypto_id, True)
    ConsenSysCodefi_Consensys_data_before = node_operators_registry.getNodeOperator(ConsenSysCodefi_Consensys_id, True)
    SkillZ_Kiln_data_before = node_operators_registry.getNodeOperator(SkillZ_Kiln_id, True)

    # check names before
    assert CertusOne_Jumpcrypto_data_before[name_index] == CertusOne_Jumpcrypto_name_before, "Incorrect NO#1 name before"
    assert ConsenSysCodefi_Consensys_data_before[name_index] == ConsenSysCodefi_Consensys_name_before, "Incorrect NO#21 name before"
    assert SkillZ_Kiln_data_before[name_index] == SkillZ_Kiln_name_before, "Incorrect NO#8 name before"

    # check SkillZ_Kiln reward address before
    assert SkillZ_Kiln_data_before[rewardAddress_index] == SkillZ_Kiln_address_before, "Incorrect NO#8 reward address before"

    # check Easy Track motions count limit before
    easy_track.motionsCountLimit() == motionsCountLimit_before, "Incorrect motions count limit before"

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # get NO's data before
    CertusOne_Jumpcrypto_data_after = node_operators_registry.getNodeOperator(CertusOne_Jumpcrypto_id, True)
    ConsenSysCodefi_Consensys_data_after = node_operators_registry.getNodeOperator(ConsenSysCodefi_Consensys_id, True)
    SkillZ_Kiln_data_after = node_operators_registry.getNodeOperator(SkillZ_Kiln_id, True)

    # compare NO#1 (CertusOne -> Jumpcrypto) data before and after
    assert CertusOne_Jumpcrypto_data_before[active_index] == CertusOne_Jumpcrypto_data_after[active_index] # active
    assert CertusOne_Jumpcrypto_name_after == CertusOne_Jumpcrypto_data_after[name_index] # name
    assert CertusOne_Jumpcrypto_data_before[rewardAddress_index] == CertusOne_Jumpcrypto_data_after[rewardAddress_index] # rewardAddress
    assert CertusOne_Jumpcrypto_data_before[stakingLimit_index] == CertusOne_Jumpcrypto_data_after[stakingLimit_index] # stakingLimit
    assert CertusOne_Jumpcrypto_data_before[stoppedValidators_index] == CertusOne_Jumpcrypto_data_after[stoppedValidators_index] # stoppedValidators

    # compare NO#21 (ConsenSysCodefi -> Consensys) data before and after
    assert ConsenSysCodefi_Consensys_data_before[active_index] == ConsenSysCodefi_Consensys_data_after[active_index] # active
    assert ConsenSysCodefi_Consensys_name_after == ConsenSysCodefi_Consensys_data_after[name_index] # name
    assert ConsenSysCodefi_Consensys_data_before[rewardAddress_index] == ConsenSysCodefi_Consensys_data_after[rewardAddress_index] # rewardAddress
    assert ConsenSysCodefi_Consensys_data_before[stakingLimit_index] == ConsenSysCodefi_Consensys_data_after[stakingLimit_index] # stakingLimit
    assert ConsenSysCodefi_Consensys_data_before[stoppedValidators_index] == ConsenSysCodefi_Consensys_data_after[stoppedValidators_index] # stoppedValidators

    # compare NO#8 (SkillZ -> Kiln) data before and after
    assert SkillZ_Kiln_data_before[active_index] == SkillZ_Kiln_data_after[active_index] # active
    assert SkillZ_Kiln_name_after == SkillZ_Kiln_data_after[name_index] # name
    assert SkillZ_Kiln_address_after == SkillZ_Kiln_data_after[rewardAddress_index] # rewardAddress
    assert SkillZ_Kiln_data_before[stakingLimit_index] == SkillZ_Kiln_data_after[stakingLimit_index] # stakingLimit
    assert SkillZ_Kiln_data_before[stoppedValidators_index] == SkillZ_Kiln_data_after[stoppedValidators_index] # stoppedValidators

    # check Easy Track motions count limit after
    easy_track.motionsCountLimit() == motionsCountLimit_after, "Incorrect motions count limit after"

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 5, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(tx)


    validate_motions_count_limit_changed_event(
        evs[0],
        motionsCountLimit_after
    )
    validate_node_operator_name_set_event(
        evs[1],
        NodeOperatorNameSetItem(
            id=1,
            name=CertusOne_Jumpcrypto_name_after
        )
    )
    validate_node_operator_name_set_event(
        evs[2],
        NodeOperatorNameSetItem(
            id=21,
            name=ConsenSysCodefi_Consensys_name_after
        )
    )
    validate_node_operator_name_set_event(
        evs[3],
        NodeOperatorNameSetItem(
            id=8,
            name=SkillZ_Kiln_name_after
        )
    )
    validate_node_operator_reward_address_set_event(
        evs[4],
        NodeOperatorRewardAddressSetItem(
            id=8,
            reward_address=SkillZ_Kiln_address_after
        )
    )
