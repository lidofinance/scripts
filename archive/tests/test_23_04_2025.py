from archive.scripts.vote_23_04_2025 import start_vote
from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS
from brownie import interface, Contract
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import (
    validate_grant_role_event,
    validate_revoke_role_event,
)
from utils.test.event_validators.common import validate_events_chain
from brownie import convert

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

# Contracts
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
VEBO = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
VEBO_IMPL = "0xA89Ea51FddE660f67d1850e03C9c9862d33Bc42c"
AO = "0x852deD011285fe67063a08005c71a85690503Cee"
AO_IMPL = "0x0e65898527E77210fB0133D00dd4C0E86Dc29bC7"
CS_FEE_ORACLE = "0x4D4074628678Bd302921c20573EEa1ed38DdF7FB"
CS_FEE_ORACLE_IMPL = "0x919ac5C6c62B6ef7B05cF05070080525a7B0381E"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
CS_VERIFIER_ADDRESS = "0x0c345dFa318f9F4977cdd4f33d80F9D0ffA38e8B"
CS_VERIFIER_ADDRESS_OLD = "0x3Dfc50f22aCA652a0a6F28a0F892ab62074b5583"
CSM_ADDRESS = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
CSM_IMPL = "0x8daEa53b17a629918CDFAB785C5c74077c1D895B"

# Roles
MANAGE_CONSENSUS_VERSION_ROLE = "0xc31b1e4b732c5173dc51d519dfa432bad95550ecc4b0f9a61c2a558a2a8e4341"
VERIFIER_ROLE = "0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09"

# New values

# Accounting oracle
AO_CONSENSUS_VERSION = 3
# Vebo
VEBO_CONSENSUS_VERSION = 3
# CS Fee oracle
CS_FEE_ORACLE_CONSENSUS_VERSION = 2


def get_vebo():
    return interface.ValidatorsExitBusOracle(VEBO)


def get_ao():
    return interface.AccountingOracle(AO)


def get_cs_fee_oracle():
    return interface.CSFeeOracle(CS_FEE_ORACLE)


def get_voting():
    return interface.Voting(VOTING)


def get_csm():
    return interface.CSModule(CSM_ADDRESS)


def check_aragon_doesnt_have_manage_consensus_role_on_oracle(oracle):
    agent_has_manage_consensus_role = oracle.hasRole(MANAGE_CONSENSUS_VERSION_ROLE, AGENT)
    assert not agent_has_manage_consensus_role


def test_vote(helpers, accounts, vote_ids_from_env, bypass_events_decoding, stranger):
    vebo = get_vebo()
    ao = get_ao()
    cs_fee_oracle = get_cs_fee_oracle()
    csm = get_csm()

    # Before voting tests
    # 1),3) Aragon agent doesnt have MANAGE_CONSENSUS_VERSION_ROLE on AO
    check_aragon_doesnt_have_manage_consensus_role_on_oracle(ao)
    # 2) Accounting Oracle consensus version equals to 2 before voting
    assert ao.getConsensusVersion() == 2
    # 4),6) Aragon agent doesnt have MANAGE_CONSENSUS_VERSION_ROLE on Vebo
    check_aragon_doesnt_have_manage_consensus_role_on_oracle(vebo)
    # 5) Vebo consensus version equals to 2 before voting
    assert vebo.getConsensusVersion() == 2
    # 7),9) Aragon agent doesnt have MANAGE_CONSENSUS_VERSION_ROLE on CS Fee oracle
    check_aragon_doesnt_have_manage_consensus_role_on_oracle(cs_fee_oracle)
    # 8) CS fee oracle consensus version equals to 1 before voting
    assert cs_fee_oracle.getConsensusVersion() == 1
    # 10) Old CS Verifier has VERIFIER_ROLE role on CSM before voting
    assert csm.hasRole(VERIFIER_ROLE, CS_VERIFIER_ADDRESS_OLD)
    # 11) New CS Verifier doesn't have VERIFIER_ROLE role on CSM before voting
    assert not csm.hasRole(VERIFIER_ROLE, CS_VERIFIER_ADDRESS)

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    voting = get_voting()

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # After voting tests
    # 1),3) Aragon agent doesnt have MANAGE_CONSENSUS_VERSION_ROLE on AO
    check_aragon_doesnt_have_manage_consensus_role_on_oracle(ao)
    # 2) Accounting Oracle consensus version equals to 3 after voting
    assert ao.getConsensusVersion() == 3
    # 4),6) Aragon agent doesnt have MANAGE_CONSENSUS_VERSION_ROLE on Vebo
    check_aragon_doesnt_have_manage_consensus_role_on_oracle(vebo)
    # 5) Vebo consensus version equals to 3 after voting
    assert vebo.getConsensusVersion() == 3
    # 7),9) Aragon agent doesnt have MANAGE_CONSENSUS_VERSION_ROLE on CS Fee oracle
    check_aragon_doesnt_have_manage_consensus_role_on_oracle(cs_fee_oracle)
    # 8) CS fee oracle consensus version equals to 2 after voting
    assert cs_fee_oracle.getConsensusVersion() == 2
    # 10) Old CS Verifier doesn't have VERIFIER_ROLE role on CSM after voting
    assert not csm.hasRole(VERIFIER_ROLE, CS_VERIFIER_ADDRESS_OLD)
    # 11) New CS Verifier has VERIFIER_ROLE role on CSM after voting
    assert csm.hasRole(VERIFIER_ROLE, CS_VERIFIER_ADDRESS)

    # Events check
    display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == "bafkreifxv3nmowbp3trdwzb3ybyrlhbjccchesmweaoicmua25lqto2xte"

    assert len(events) == 11

    # Validate ao consensus version set
    validate_consensus_version_update(events[:3], AO_CONSENSUS_VERSION, AO_IMPL)

    # Validate vebo consensus version set
    validate_consensus_version_update(events[3:6], VEBO_CONSENSUS_VERSION, VEBO_IMPL)

    # Validate CS Fee Oracle consensus version set
    validate_consensus_version_update(events[6:9], CS_FEE_ORACLE_CONSENSUS_VERSION, CS_FEE_ORACLE_IMPL)

    # Validate VERIFIER_ROLE role revoke from CS_VERIFIER_ADDRESS_OLD
    validate_revoke_role_event(events[9], VERIFIER_ROLE, CS_VERIFIER_ADDRESS_OLD, AGENT, CSM_IMPL)

    # Validate VERIFIER_ROLE role grant to CS_VERIFIER_ADDRESS_OLD
    validate_grant_role_event(events[10], VERIFIER_ROLE, CS_VERIFIER_ADDRESS, AGENT, CSM_IMPL)


# Events check


def validate_consensus_version_update(events: list[EventDict], version, emitted_by):
    validate_grant_role_event(events[0], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, emitted_by)
    validate_consensus_version_set(events[1], version, emitted_by)
    validate_revoke_role_event(events[2], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT, emitted_by)


def validate_consensus_version_set(event: EventDict, version, emitted_by):
    _events_chain = ["LogScriptCall", "LogScriptCall", "ConsensusVersionSet", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event["ConsensusVersionSet"]["version"] == version
    assert convert.to_address(event["ConsensusVersionSet"]["_emitted_by"]) == convert.to_address(
            emitted_by
        ), "Wrong event emitter"
