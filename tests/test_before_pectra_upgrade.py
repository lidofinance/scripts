from scripts.before_pectra_upgrade import start_vote
from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS
from brownie import interface, convert, Contract
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grant_event,
    validate_permission_revoke_event,
    validate_grant_role_event,
    validate_revoke_role_event,
)
from utils.easy_track import create_permissions
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded
)
from utils.test.event_validators.voting import validate_change_vote_time_event, validate_change_objection_time_event
from utils.test.event_validators.common import validate_events_chain

from scripts.before_pectra_upgrade import (
    OLD_GATE_SEAL,
    NEW_GATE_SEAL,
    OLD_CSM_GATE_SEAL,
    NEW_CSM_GATE_SEAL,
    NEW_VOTE_DURATION,
    NEW_OBJECTION_PHASE_DURATION,
    FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE,
    ECOSYSTEM_BORG_STABLE_FACTORY,
    ECOSYSTEM_BORG_STETH_FACTORY,
    ECOSYSTEM_BORG_STETH_REGISTRY,
    LABS_BORG_STABLE_FACTORY,
    LABS_BORG_STABLE_REGISTRY,
    LABS_BORG_STETH_FACTORY,
    LABS_BORG_STETH_REGISTRY,
)

from utils.config import contracts

# Contracts
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
VALIDATORS_EXIT_BUS_ORACLE = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
CS_FEE_ORACLE = "0x4D4074628678Bd302921c20573EEa1ed38DdF7FB"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
CS_VERIFIER_ADDRESS = "0xBcb61491F1859f53438918F1A5aFCA542Af9D397"  # TODO: need to set newly deployed contract address
CS_VERIFIER_ADDRESS_OLD = "0x3Dfc50f22aCA652a0a6F28a0F892ab62074b5583"
CSM_ADDRESS = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"

# Roles
MANAGE_CONSENSUS_VERSION_ROLE = "0xc31b1e4b732c5173dc51d519dfa432bad95550ecc4b0f9a61c2a558a2a8e4341"
VERIFIER_ROLE = "0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09"
PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d"

# Old values
# Vote duration
OLD_VOTE_DURATION = 259200
OLD_OBJECTION_PHASE_DURATION = 86400

# Oracle daemon config
FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_OLD_VALUE = 1350

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


def check_aragon_doesnt_have_manage_consensus_role_on_oracle(oracle):
    agent_has_manage_consensus_role = oracle.hasRole(MANAGE_CONSENSUS_VERSION_ROLE, AGENT)
    assert not agent_has_manage_consensus_role


def _check_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert contract.getRoleMember(role_bytes, 0).lower() == holder.lower(), f"Role {role} holder on {contract} should be {holder}"


def _check_no_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert (
        not contract.getRoleMember(role_bytes, 0).lower() == holder.lower()
    ), f"Role {role} holder on {contract} should be {holder}"


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

    # On-chain voting duration state before voting
    assert contracts.voting.voteTime() == OLD_VOTE_DURATION
    assert contracts.voting.objectionPhaseTime() == OLD_OBJECTION_PHASE_DURATION
    assert not contracts.acl.hasPermission(
        contracts.voting.address,
        contracts.voting.address,
        contracts.voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE()
    )

    # Check Oracle Config state before voting
    new_value_uint = convert.to_uint(contracts.oracle_daemon_config.get("FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT"))
    assert new_value_uint == FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_OLD_VALUE
    assert not contracts.oracle_daemon_config.hasRole(
        web3.keccak(text="CONFIG_MANAGER_ROLE").hex(),
        contracts.agent.address
    )

    # Check GateSeal state before voting
    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_role(vebo, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_no_role(contracts.withdrawal_queue, "PAUSE_ROLE", NEW_GATE_SEAL)
    _check_no_role(vebo, "PAUSE_ROLE", NEW_GATE_SEAL)

    # Check GateSeal state on CSM before voting
    _check_role(contracts.csm, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_no_role(contracts.csm, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)
    _check_role(contracts.cs_accounting, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_no_role(contracts.cs_accounting, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)
    _check_role(contracts.cs_fee_oracle, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_no_role(contracts.cs_fee_oracle, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)

    # EasyTrack factories not added check
    evm_script_factories_before = contracts.easy_track.getEVMScriptFactories()
    assert not ECOSYSTEM_BORG_STABLE_FACTORY in evm_script_factories_before
    assert not ECOSYSTEM_BORG_STETH_FACTORY in evm_script_factories_before
    assert not LABS_BORG_STABLE_FACTORY in evm_script_factories_before
    assert not LABS_BORG_STETH_FACTORY in evm_script_factories_before

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

    # On-chain voting duration state before voting
    assert contracts.voting.voteTime() == NEW_VOTE_DURATION
    assert contracts.voting.objectionPhaseTime() == NEW_OBJECTION_PHASE_DURATION
    assert not contracts.acl.hasPermission(
        contracts.voting.address,
        contracts.voting.address,
        contracts.voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE()
    )

    # Check Oracle Config updated properly
    updated_value_uint = convert.to_uint(
        contracts.oracle_daemon_config.get("FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT")
    )
    assert updated_value_uint == FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE
    assert not contracts.oracle_daemon_config.hasRole(
        web3.keccak(text="CONFIG_MANAGER_ROLE").hex(),
        contracts.agent.address
    )

    # Check GateSeal updated properly
    _check_no_role(contracts.withdrawal_queue, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_no_role(vebo, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", NEW_GATE_SEAL)
    _check_role(vebo, "PAUSE_ROLE", NEW_GATE_SEAL)

    # Check GateSeal on CSM updated properly
    _check_no_role(contracts.csm, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_role(contracts.csm, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)
    _check_no_role(contracts.cs_accounting, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_role(contracts.cs_accounting, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)
    _check_no_role(contracts.cs_fee_oracle, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_role(contracts.cs_fee_oracle, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)

    # EasyTrack factories added check
    evm_script_factories_after = contracts.easy_track.getEVMScriptFactories()
    assert ECOSYSTEM_BORG_STABLE_FACTORY in evm_script_factories_after
    assert ECOSYSTEM_BORG_STETH_FACTORY in evm_script_factories_after
    assert LABS_BORG_STABLE_FACTORY in evm_script_factories_after
    assert LABS_BORG_STETH_FACTORY in evm_script_factories_after

    # Events check
    display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    assert len(events) == 11

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
    validate_permission_grant_event(events[11], permission)
    validate_change_vote_time_event(events[12], NEW_VOTE_DURATION)
    validate_change_objection_time_event(events[13], NEW_OBJECTION_PHASE_DURATION)
    validate_permission_revoke_event(events[14], permission)

    validate_grant_role_event(
        events[15],
        contracts.oracle_daemon_config.CONFIG_MANAGER_ROLE(),
        contracts.agent.address,
        contracts.agent.address,
    )
    validate_config_value_updated(
        events[16],
        "FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT",
        FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE,
    )
    validate_revoke_role_event(
        events[17],
        contracts.oracle_daemon_config.CONFIG_MANAGER_ROLE(),
        contracts.agent.address,
        contracts.agent.address,
    )

    # GateSeal on WithdrawalQueue and ValidatorsExitBusOracle events
    # Grant PAUSE_ROLE on WithdrawalQueue for the new GateSeal
    validate_grant_role_event(events[18], PAUSE_ROLE, NEW_GATE_SEAL, contracts.agent)
    # Grant PAUSE_ROLE on ValidatorExitBusOracle for the new GateSeal
    validate_grant_role_event(events[19], PAUSE_ROLE, NEW_GATE_SEAL, contracts.agent)
    # Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
    validate_revoke_role_event(events[20], PAUSE_ROLE, OLD_GATE_SEAL, contracts.agent)
    # Revoke PAUSE_ROLE on ValidatorExitBusOracle from the old GateSeal
    validate_revoke_role_event(events[21], PAUSE_ROLE, OLD_GATE_SEAL, contracts.agent)

    # GateSeal on CSM events
    # Grant PAUSE_ROLE on CSModule for the new CSMGateSeal
    validate_grant_role_event(events[22], PAUSE_ROLE, NEW_CSM_GATE_SEAL, contracts.agent)
    # Grant PAUSE_ROLE on CSAccounting for the new CSMGateSeal
    validate_grant_role_event(events[23], PAUSE_ROLE, NEW_CSM_GATE_SEAL, contracts.agent)
    # Grant PAUSE_ROLE on CSFeeOracle from the old CSMGateSeal
    validate_grant_role_event(events[24], PAUSE_ROLE, NEW_CSM_GATE_SEAL, contracts.agent)
    # Revoke PAUSE_ROLE on CSModule from the old CSMGateSeal
    validate_revoke_role_event(events[25], PAUSE_ROLE, OLD_CSM_GATE_SEAL, contracts.agent)
    # Revoke PAUSE_ROLE on CSAccounting from the old CSMGateSeal
    validate_revoke_role_event(events[26], PAUSE_ROLE, OLD_CSM_GATE_SEAL, contracts.agent)
    # Revoke PAUSE_ROLE on CSFeeOracle from the old CSMGateSeal
    validate_revoke_role_event(events[27], PAUSE_ROLE, OLD_CSM_GATE_SEAL, contracts.agent)

    # # Validate EasyTrack events
    # validate_evmscript_factory_added_event(
    #     events[28],
    #     EVMScriptFactoryAdded(
    #         factory_addr=ecosystem_borg_stable_factory,
    #         permissions=create_permissions(contracts.finance, "newImmediatePayment")
    #         + create_permissions(
    #             interface.AllowedRecipientRegistry(ECOSYSTEM_BORG_STABLE_REGISTRY), "updateSpentAmount"
    #         )[2:],
    #     ),
    # )
    # validate_evmscript_factory_added_event(
    #     events[29],
    #     EVMScriptFactoryAdded(
    #         factory_addr=ecosystem_borg_steth_factory,
    #         permissions=create_permissions(contracts.finance, "newImmediatePayment")
    #         + create_permissions(
    #             interface.AllowedRecipientRegistry(ECOSYSTEM_BORG_STETH_REGISTRY), "updateSpentAmount"
    #         )[2:],
    #     ),
    # )
    # validate_evmscript_factory_added_event(
    #     events[30],
    #     EVMScriptFactoryAdded(
    #         factory_addr=labs_borg_stable_factory,
    #         permissions=create_permissions(contracts.finance, "newImmediatePayment")
    #         + create_permissions(interface.AllowedRecipientRegistry(LABS_BORG_STABLE_REGISTRY), "updateSpentAmount")[
    #             2:
    #         ],
    #     ),
    # )
    # validate_evmscript_factory_added_event(
    #     events[31],
    #     EVMScriptFactoryAdded(
    #         factory_addr=labs_borg_steth_factory,
    #         permissions=create_permissions(contracts.finance, "newImmediatePayment")
    #         + create_permissions(interface.AllowedRecipientRegistry(LABS_BORG_STETH_REGISTRY), "updateSpentAmount")[2:],
    #     ),
    # )


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


def validate_config_value_updated(event: EventDict, key, value):
    _events_chain = ["LogScriptCall", "LogScriptCall", "ConfigValueUpdated", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event["ConfigValueUpdated"]["key"] == key
    assert convert.to_uint(event["ConfigValueUpdated"]["value"]) == value