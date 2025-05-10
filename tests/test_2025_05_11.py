import pytest

from scripts.vote_2025_05_11 import start_vote
from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS
from brownie import interface
from utils.test.tx_tracing_helpers import *
from typing import NamedTuple
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

from utils.test.event_validators.hash_consensus import (
    validate_hash_consensus_member_removed,
    validate_hash_consensus_member_added,
)

# Addresses that will not be changed

ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"

HASH_CONSENSUS_FOR_AO = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
HASH_CONSENSUS_FOR_VEBO = "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"
CS_ORACLE_HASH_CONSENSUS_ADDRESS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"

# Oracles members
old_oracle_member_to_remove = "0x140bd8fbdc884f48da7cb1c09be8a2fadfea776e"
new_oracle_member_to_add = "0xe050818F12D40b4ac8bf99a9f9F9517b07428D58"


def test_vote(
    helpers,
    accounts,
    vote_ids_from_env,
):
    csm_hash_consensus = get_csm_hash_consensus()

    # 1), 4) before vote old member is still in the quorum of ao hash consensus, new member is not in the quorum
    ao_hash_consensus = get_ao_hash_consensus()
    assert ao_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert not ao_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert ao_hash_consensus.getQuorum() == 5
    assert len(ao_hash_consensus.getMembers()[0]) == 9

    # 2), 5) before vote old member is still in the quorum of vebo hash consensus, new member is not in the quorum
    vebo_hash_consensus = get_vebo_hash_consensus()
    assert vebo_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert not vebo_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert vebo_hash_consensus.getQuorum() == 5
    assert len(vebo_hash_consensus.getMembers()[0]) == 9

    # 4), 6) before vote old member is still in the quorum of cs hash consensus, new member is not in the quorum
    assert csm_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert not csm_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert csm_hash_consensus.getQuorum() == 5
    assert len(csm_hash_consensus.getMembers()[0]) == 9

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    voting = get_voting()

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    metadata = find_metadata_by_vote_id(vote_id)
    print('ipfs id:', get_lido_vote_cid_from_str(metadata))
    assert get_lido_vote_cid_from_str(metadata) == "bafkreihy2o5c653ykrqcvsruootiwi7i4el26apnvriocfgxlosejdnt6i"

    # 1), 4) after vote old member is not in the quorum of ao hash consensus, new member is in the quorum
    assert not ao_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert ao_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert ao_hash_consensus.getQuorum() == 5
    assert len(ao_hash_consensus.getMembers()[0]) == 9

    # 2), 5) after vote old member is not in the quorum of vebo hash consensus, new member is in the quorum
    vebo_hash_consensus = get_vebo_hash_consensus()
    assert not vebo_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert vebo_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert vebo_hash_consensus.getQuorum() == 5
    assert len(vebo_hash_consensus.getMembers()[0]) == 9

    # 3), 6) after vote old member is not in the quorum of cs hash consensus, new member is in the quorum
    assert not csm_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert csm_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert csm_hash_consensus.getQuorum() == 5
    assert len(csm_hash_consensus.getMembers()[0]) == 9

    # Events check
    display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    assert len(events) == 6

    validate_hash_consensus_member_removed(events[0], old_oracle_member_to_remove, 5, new_total_members=8, emitted_by=HASH_CONSENSUS_FOR_AO)
    validate_hash_consensus_member_removed(events[1], old_oracle_member_to_remove, 5, new_total_members=8, emitted_by=HASH_CONSENSUS_FOR_VEBO)
    validate_hash_consensus_member_removed(
        events[2],
        old_oracle_member_to_remove,
        5,
        new_total_members=8,
        emitted_by=CS_ORACLE_HASH_CONSENSUS_ADDRESS
    )
    validate_hash_consensus_member_added(events[3], new_oracle_member_to_add, 5, new_total_members=9, emitted_by=HASH_CONSENSUS_FOR_AO)
    validate_hash_consensus_member_added(events[4], new_oracle_member_to_add,5, new_total_members=9, emitted_by=HASH_CONSENSUS_FOR_VEBO)
    validate_hash_consensus_member_added(
        events[5],
        new_oracle_member_to_add,
        5,
        new_total_members=9,
        emitted_by=CS_ORACLE_HASH_CONSENSUS_ADDRESS
    )

def get_voting():
    return interface.Voting(VOTING)

def get_csm_hash_consensus():
    return interface.CSHashConsensus(CS_ORACLE_HASH_CONSENSUS_ADDRESS)

def get_ao_hash_consensus():
    return interface.HashConsensus(HASH_CONSENSUS_FOR_AO)


def get_vebo_hash_consensus():
    return interface.HashConsensus(HASH_CONSENSUS_FOR_VEBO)
