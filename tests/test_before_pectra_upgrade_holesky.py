from scripts.before_pectra_upgrade_holesky import (
    start_vote,
    OLD_GATE_SEAL,
    NEW_GATE_SEAL,
    NEW_VOTE_DURATION,
    NEW_OBJECTION_PHASE_DURATION
)
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS
from brownie import interface, Contract
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grant_event,
    validate_permission_revoke_event,
    validate_grant_role_event,
    validate_revoke_role_event,
)
from utils.test.event_validators.voting import validate_change_vote_time_event, validate_change_objection_time_event
from utils.test.event_validators.common import validate_events_chain

# Contracts
AGENT = "0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d"
VALIDATORS_EXIT_BUS_ORACLE = "0xffDDF7025410412deaa05E3E1cE68FE53208afcb"
ACCOUNTING_ORACLE = "0x4E97A3972ce8511D87F334dA17a2C332542a5246"
CS_FEE_ORACLE = "0xaF57326C7d513085051b50912D51809ECC5d98Ee"
VOTING = "0xdA7d2573Df555002503F29aA4003e398d28cc00f"
CS_VERIFIER_ADDRESS = "0xE044427930C166670f5dd84E9154A874c4759310"
CS_VERIFIER_ADDRESS_OLD = "0x6FDAA094227CF8E1593f9fB9C1b867C1f846F916"
CSM_ADDRESS = "0x4562c3e63c2e586cD1651B958C22F88135aCAd4f"

# Roles
MANAGE_CONSENSUS_VERSION_ROLE = "0xc31b1e4b732c5173dc51d519dfa432bad95550ecc4b0f9a61c2a558a2a8e4341"
VERIFIER_ROLE = "0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09"
PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d"

# New values

# Accounting oracle
AO_CONSENSUS_VERSION = 3
# Vebo
VEBO_CONSENSUS_VERSION = 3
# CS Fee oracle
CS_FEE_ORACLE_CONSENSUS_VERSION = 2

def get_vebo():
    return interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE)


def get_ao():
    return interface.AccountingOracle(ACCOUNTING_ORACLE)


def get_cs_fee_oracle():
    return interface.CSFeeOracle(CS_FEE_ORACLE)


def get_voting():
    return interface.Voting(VOTING)


def get_csm():
    return interface.CSModule(CSM_ADDRESS)


def _check_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert contract.getRoleMember(role_bytes, 0) == holder, f"Role {role} holder on {contract} should be {holder}"


def _check_no_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert (
        not contract.getRoleMember(role_bytes, 0).lower() == holder.lower()
    ), f"Role {role} holder on {contract} should be {holder}"


def check_aragon_doesnt_have_manage_consensus_role_on_oracle(oracle):
    agent_has_manage_consensus_role = oracle.hasRole(MANAGE_CONSENSUS_VERSION_ROLE, AGENT)
    assert not agent_has_manage_consensus_role


def test_vote(helpers, accounts, vote_ids_from_env, bypass_events_decoding):
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
    # 8) Update vebo consensus version equals to 1
    assert cs_fee_oracle.getConsensusVersion() == 1
    # 10) Old CS Verifier has VERIFIER_ROLE role on CSM before voting
    assert csm.hasRole(VERIFIER_ROLE, CS_VERIFIER_ADDRESS_OLD)
    # 11) New CS Verifier doesnt have VERIFIER_ROLE role on CSM before voting
    assert not csm.hasRole(VERIFIER_ROLE, CS_VERIFIER_ADDRESS)

    # On-chain voting duration state before voting
    assert contracts.voting.voteTime() == 900
    assert contracts.voting.objectionPhaseTime() == 300

    # Check GateSeal state before voting
    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_role(vebo, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_no_role(contracts.withdrawal_queue, "PAUSE_ROLE", NEW_GATE_SEAL)
    _check_no_role(vebo, "PAUSE_ROLE", NEW_GATE_SEAL)

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
    # 8) Update vebo consensus version equals to 2 after voting
    assert cs_fee_oracle.getConsensusVersion() == 2
    # 10) Old CS Verifier has VERIFIER_ROLE role on CSM after voting
    assert not csm.hasRole(VERIFIER_ROLE, CS_VERIFIER_ADDRESS_OLD)
    # 11) New CS Verifier doesn't have VERIFIER_ROLE role on CSM after voting
    assert csm.hasRole(VERIFIER_ROLE, CS_VERIFIER_ADDRESS)

    # check verifier epoch

    # Check voting duration changed properly
    assert contracts.voting.voteTime() == NEW_VOTE_DURATION
    assert contracts.voting.objectionPhaseTime() == NEW_OBJECTION_PHASE_DURATION

    # Check GateSeal updated properly
    _check_no_role(contracts.withdrawal_queue, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_no_role(vebo, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", NEW_GATE_SEAL)
    _check_role(vebo, "PAUSE_ROLE", NEW_GATE_SEAL)

    # Events check
    display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    assert len(events) == 20

    # Validate ao consensus version set
    validate_consensus_version_update(events[:3], AO_CONSENSUS_VERSION)

    # Validate vebo consensus version set
    validate_consensus_version_update(events[3:6], VEBO_CONSENSUS_VERSION)

    # Validate CS Fee Oracle consensus version set
    validate_consensus_version_update(events[6:9], CS_FEE_ORACLE_CONSENSUS_VERSION)

    # Validate VERIFIER_ROLE role revoke from CS_VERIFIER_ADDRESS_OLD
    validate_revoke_role_event(
        events[9],
        VERIFIER_ROLE,
        CS_VERIFIER_ADDRESS_OLD,
        AGENT,
    )

    # Validate VERIFIER_ROLE role grant to CS_VERIFIER_ADDRESS_OLD
    validate_grant_role_event(
        events[10],
        VERIFIER_ROLE,
        CS_VERIFIER_ADDRESS,
        AGENT,
    )

    permission = Permission(
        entity=contracts.voting.address,
        app=contracts.voting.address,
        role=contracts.voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE(),
    )
    validate_permission_grant_event(events[12], permission)
    validate_change_vote_time_event(events[13], NEW_VOTE_DURATION)
    validate_change_objection_time_event(events[14], NEW_OBJECTION_PHASE_DURATION)
    validate_permission_revoke_event(events[15], permission)

    # Grant PAUSE_ROLE on WithdrawalQueue for the new GateSeal
    validate_grant_role_event(events[16], PAUSE_ROLE, NEW_GATE_SEAL, contracts.agent)

    # Grant PAUSE_ROLE on ValidatorExitBusOracle for the new GateSeal
    validate_grant_role_event(events[17], PAUSE_ROLE, NEW_GATE_SEAL, contracts.agent)

    # Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
    validate_revoke_role_event(events[18], PAUSE_ROLE, OLD_GATE_SEAL, contracts.agent)

    # Revoke PAUSE_ROLE on ValidatorExitBusOracle from the old GateSeal
    validate_revoke_role_event(events[19], PAUSE_ROLE, OLD_GATE_SEAL, contracts.agent)


# Events check


def validate_consensus_version_update(events: list[EventDict], version):
    validate_grant_role_event(
        events[0],
        MANAGE_CONSENSUS_VERSION_ROLE,
        AGENT,
        AGENT,
    )
    validate_consensus_version_set(events[1], version)
    validate_revoke_role_event(
        events[2],
        MANAGE_CONSENSUS_VERSION_ROLE,
        AGENT,
        AGENT,
    )


def validate_consensus_version_set(event: EventDict, version):
    _events_chain = ["LogScriptCall", "LogScriptCall", "ConsensusVersionSet", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event["ConsensusVersionSet"]["version"] == version
