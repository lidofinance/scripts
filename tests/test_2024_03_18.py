from brownie import interface, convert, Contract, web3
from scripts.vote_2024_03_18 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS
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
from utils.test.easy_track_helpers import create_and_enact_payment_motion

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

# Vote duration
NEW_VOTE_DURATION = 432000
NEW_OBJECTION_PHASE_DURATION = 172800

# Oracle daemon config
FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE = convert.to_bytes(2250, "bytes").hex()
FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_OLD_VALUE = convert.to_bytes(1350, "bytes").hex()

# GateSeals
OLD_GATE_SEAL = "0x79243345eDbe01A7E42EDfF5900156700d22611c"
NEW_GATE_SEAL = "0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178"
GATE_SEAL_COMMITTEE = "0x8772E3a2D86B9347A2688f9bc1808A6d8917760C"
GATE_SEAL_PAUSE_DURATION = 950400  # 11 days
GATE_SEAL_NEW_EXPIRY_TIMESTAMP = 1772323200  # Sun Mar 01 2026 00:00:00 GMT+0000

# CSM GateSeals
OLD_CSM_GATE_SEAL = "0x5cFCa30450B1e5548F140C24A47E36c10CE306F0"
NEW_CSM_GATE_SEAL = "0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0"
CSM_GATE_SEAL_COMMITTEE = "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f"

# EasyTrack factories
ECOSYSTEM_BORG_STABLE_FACTORY = "0xf2476f967C826722F5505eDfc4b2561A34033477"
ECOSYSTEM_BORG_STABLE_REGISTRY = "0xDAdC4C36cD8F468A398C25d0D8aaf6A928B47Ab4"
LABS_BORG_STABLE_FACTORY = "0xE1f6BaBb445F809B97e3505Ea91749461050F780"
LABS_BORG_STABLE_REGISTRY = "0x68267f3D310E9f0FF53a37c141c90B738E1133c2"

# Contracts
ACL = "0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb"
CSM = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
VEBO = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
VALIDATORS_EXIT_BUS_ORACLE = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
ORACLE_DAEMON_CONFIG = "0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09"
WITHDRAWAL_QUEUE = "0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1"
CS_ACCOUNTING = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"
CS_FEE_ORACLE = "0x4D4074628678Bd302921c20573EEa1ed38DdF7FB"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
FINANCE = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"

DAI_TOKEN = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
USDT_TOKEN = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
USDC_TOKEN = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

WITHDRAWAL_QUEUE_IMPL = "0xE42C659Dc09109566720EA8b2De186c2Be7D94D9"
VEBO_IMPL = "0xA89Ea51FddE660f67d1850e03C9c9862d33Bc42c"
CSM_IMPL = "0x8daea53b17a629918cdfab785c5c74077c1d895b"
CS_ACCOUNTING_IMPL = "0x71FCD2a6F38B644641B0F46c345Ea03Daabf2758"
CS_FEE_ORACLE_IMPL = "0x919ac5C6c62B6ef7B05cF05070080525a7B0381E"

# Roles
PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d"

# Vote duration
OLD_VOTE_DURATION = 259200
OLD_OBJECTION_PHASE_DURATION = 86400

# Oracle daemon config


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
    acl = interface.ACL(ACL)
    csm = interface.CSModule(CSM)
    cs_fee_oracle = interface.CSFeeOracle(CS_FEE_ORACLE)
    cs_accounting = interface.CSAccounting(CS_ACCOUNTING)
    vebo = interface.ValidatorsExitBusOracle(VEBO)
    finance = interface.Finance(FINANCE)
    agent = interface.Agent(AGENT)
    voting = interface.Voting(VOTING)
    easy_track = interface.EasyTrack(EASY_TRACK)
    withdrawal_queue = interface.WithdrawalQueue(WITHDRAWAL_QUEUE)
    oracle_daemon_config = interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)

    # On-chain voting duration state before voting
    assert voting.voteTime() == OLD_VOTE_DURATION
    assert voting.objectionPhaseTime() == OLD_OBJECTION_PHASE_DURATION
    assert not acl.hasPermission(
        voting.address,
        voting.address,
        voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE()
    )

    # Check Oracle Config state before voting
    finalization_max_negative_rebase_epoch_shift = oracle_daemon_config.get("FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT")
    assert finalization_max_negative_rebase_epoch_shift.hex() == FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_OLD_VALUE
    assert not oracle_daemon_config.hasRole(
        web3.keccak(text="CONFIG_MANAGER_ROLE").hex(),
        agent.address
    )

    # Check GateSeal state before voting
    _check_role(withdrawal_queue, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_role(vebo, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_no_role(withdrawal_queue, "PAUSE_ROLE", NEW_GATE_SEAL)
    _check_no_role(vebo, "PAUSE_ROLE", NEW_GATE_SEAL)

    # Check GateSeal state on CSM before voting
    _check_role(csm, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_no_role(csm, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)
    _check_role(cs_accounting, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_no_role(cs_accounting, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)
    _check_role(cs_fee_oracle, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_no_role(cs_fee_oracle, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)

    # EasyTrack factories not added check
    evm_script_factories_before = easy_track.getEVMScriptFactories()
    assert not ECOSYSTEM_BORG_STABLE_FACTORY in evm_script_factories_before
    assert not LABS_BORG_STABLE_FACTORY in evm_script_factories_before

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # On-chain voting duration state after voting
    assert voting.voteTime() == NEW_VOTE_DURATION
    assert voting.objectionPhaseTime() == NEW_OBJECTION_PHASE_DURATION
    assert not acl.hasPermission(
        voting.address,
        voting.address,
        voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE()
    )

    # Check Oracle Config updated properly
    finalization_max_negative_rebase_epoch_shift_updated = oracle_daemon_config.get("FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT")
    assert finalization_max_negative_rebase_epoch_shift_updated.hex() == FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE
    assert not oracle_daemon_config.hasRole(
        web3.keccak(text="CONFIG_MANAGER_ROLE").hex(),
        agent.address
    )

    # Check GateSeal updated properly
    _check_no_role(withdrawal_queue, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_no_role(vebo, "PAUSE_ROLE", OLD_GATE_SEAL)
    _check_role(withdrawal_queue, "PAUSE_ROLE", NEW_GATE_SEAL)
    _check_role(vebo, "PAUSE_ROLE", NEW_GATE_SEAL)

    # GateSeal Асceptance test
    new_gate_seal_contract = interface.GateSeal(NEW_GATE_SEAL)
    assert new_gate_seal_contract.get_sealing_committee() == GATE_SEAL_COMMITTEE
    sealables = new_gate_seal_contract.get_sealables()
    assert len(sealables) == 2
    assert vebo.address in sealables
    assert withdrawal_queue.address in sealables
    assert new_gate_seal_contract.get_seal_duration_seconds() == GATE_SEAL_PAUSE_DURATION
    assert new_gate_seal_contract.get_expiry_timestamp() == GATE_SEAL_NEW_EXPIRY_TIMESTAMP
    assert not new_gate_seal_contract.is_expired()

    # Check GateSeal on CSM updated properly
    _check_no_role(csm, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_role(csm, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)
    _check_no_role(cs_accounting, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_role(cs_accounting, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)
    _check_no_role(cs_fee_oracle, "PAUSE_ROLE", OLD_CSM_GATE_SEAL)
    _check_role(cs_fee_oracle, "PAUSE_ROLE", NEW_CSM_GATE_SEAL)

    # CSM GateSeal Асceptance test
    new_csm_gate_seal_contract = interface.GateSeal(NEW_CSM_GATE_SEAL)
    assert new_csm_gate_seal_contract.get_sealing_committee() == CSM_GATE_SEAL_COMMITTEE
    csm_sealables = new_csm_gate_seal_contract.get_sealables()
    assert len(csm_sealables) == 3
    assert csm.address in csm_sealables
    assert cs_accounting.address in csm_sealables
    assert cs_fee_oracle.address in csm_sealables
    assert new_csm_gate_seal_contract.get_seal_duration_seconds() == GATE_SEAL_PAUSE_DURATION
    assert new_csm_gate_seal_contract.get_expiry_timestamp() == GATE_SEAL_NEW_EXPIRY_TIMESTAMP
    assert not new_csm_gate_seal_contract.is_expired()

    # EasyTrack factories added check
    evm_script_factories_after = easy_track.getEVMScriptFactories()
    assert ECOSYSTEM_BORG_STABLE_FACTORY in evm_script_factories_after
    assert LABS_BORG_STABLE_FACTORY in evm_script_factories_after
    assert len(evm_script_factories_after) == len(evm_script_factories_before) + 2

    ecosystem_borg_stable_factory = interface.TopUpAllowedRecipients(ECOSYSTEM_BORG_STABLE_FACTORY)
    labs_borg_stable_factory = interface.TopUpAllowedRecipients(LABS_BORG_STABLE_FACTORY)

    for stablecoin in [DAI_TOKEN, USDT_TOKEN, USDC_TOKEN]:
        create_and_enact_payment_motion(
            easy_track=easy_track,
            trusted_caller=ecosystem_borg_stable_factory.trustedCaller(),
            factory=ecosystem_borg_stable_factory,
            token=interface.ERC20(stablecoin),
            recievers=[Contract(interface.AllowedRecipientRegistry(ECOSYSTEM_BORG_STABLE_REGISTRY).allowedRecipients(0))],
            transfer_amounts=[1 * 10**6],
            stranger=stranger,
        )
        create_and_enact_payment_motion(
            easy_track=easy_track,
            trusted_caller=labs_borg_stable_factory.trustedCaller(),
            factory=labs_borg_stable_factory,
            token=interface.ERC20(stablecoin),
            recievers=[Contract(interface.AllowedRecipientRegistry(LABS_BORG_STABLE_REGISTRY).allowedRecipients(0))],
            transfer_amounts=[1 * 10**6],
            stranger=stranger,
        )


    # Events check
    display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    metadata = find_metadata_by_vote_id(vote_id)
    print('ipfs id:', get_lido_vote_cid_from_str(metadata))
    assert get_lido_vote_cid_from_str(metadata) == "bafkreiae5ge6hszcag4cdxk3wcoqfa2ilre7rbt4f3j3eydmgip6nvvat4"

    assert len(events) == 19

    unsafely_modify_vote_time_role_permission = Permission(
        entity=voting.address,
        app=voting.address,
        role=voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE(),
    )
    validate_permission_grant_event(events[0], unsafely_modify_vote_time_role_permission)
    validate_change_vote_time_event(events[1], NEW_VOTE_DURATION)
    validate_change_objection_time_event(events[2], NEW_OBJECTION_PHASE_DURATION)
    validate_permission_revoke_event(events[3], unsafely_modify_vote_time_role_permission)

    validate_grant_role_event(
        events[4],
        oracle_daemon_config.CONFIG_MANAGER_ROLE(),
        agent.address,
        agent.address,

    )
    validate_config_value_updated(
        events[5],
        "FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT",
        FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT_NEW_VALUE,
    )
    validate_revoke_role_event(
        events[6],
        oracle_daemon_config.CONFIG_MANAGER_ROLE(),
        agent.address,
        agent.address,
    )

    # GateSeal on WithdrawalQueue and ValidatorsExitBusOracle events
    # Grant PAUSE_ROLE on WithdrawalQueue for the new GateSeal
    validate_grant_role_event(events[7], PAUSE_ROLE, NEW_GATE_SEAL, agent, WITHDRAWAL_QUEUE_IMPL)
    # Grant PAUSE_ROLE on ValidatorExitBusOracle for the new GateSeal
    validate_grant_role_event(events[8], PAUSE_ROLE, NEW_GATE_SEAL, agent, VEBO_IMPL)
    # Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
    validate_revoke_role_event(events[9], PAUSE_ROLE, OLD_GATE_SEAL, agent, WITHDRAWAL_QUEUE_IMPL)
    # Revoke PAUSE_ROLE on ValidatorExitBusOracle from the old GateSeal
    validate_revoke_role_event(events[10], PAUSE_ROLE, OLD_GATE_SEAL, agent, VEBO_IMPL)

    # GateSeal on CSM events
    # Grant PAUSE_ROLE on CSModule for the new CSMGateSeal
    validate_grant_role_event(events[11], PAUSE_ROLE, NEW_CSM_GATE_SEAL, agent, CSM_IMPL)
    # Grant PAUSE_ROLE on CSAccounting for the new CSMGateSeal
    validate_grant_role_event(events[12], PAUSE_ROLE, NEW_CSM_GATE_SEAL, agent, CS_ACCOUNTING_IMPL)
    # Grant PAUSE_ROLE on CSFeeOracle from the old CSMGateSeal
    validate_grant_role_event(events[13], PAUSE_ROLE, NEW_CSM_GATE_SEAL, agent, CS_FEE_ORACLE_IMPL)
    # Revoke PAUSE_ROLE on CSModule from the old CSMGateSeal
    validate_revoke_role_event(events[14], PAUSE_ROLE, OLD_CSM_GATE_SEAL, agent, CSM_IMPL)
    # Revoke PAUSE_ROLE on CSAccounting from the old CSMGateSeal
    validate_revoke_role_event(events[15], PAUSE_ROLE, OLD_CSM_GATE_SEAL, agent, CS_ACCOUNTING_IMPL)
    # Revoke PAUSE_ROLE on CSFeeOracle from the old CSMGateSeal
    validate_revoke_role_event(events[16], PAUSE_ROLE, OLD_CSM_GATE_SEAL, agent, CS_FEE_ORACLE_IMPL)

    # Validate EasyTrack events
    validate_evmscript_factory_added_event(
        events[17],
        EVMScriptFactoryAdded(
            factory_addr=ecosystem_borg_stable_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(
                interface.AllowedRecipientRegistry(ECOSYSTEM_BORG_STABLE_REGISTRY), "updateSpentAmount"
            )[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        events[18],
        EVMScriptFactoryAdded(
            factory_addr=labs_borg_stable_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(interface.AllowedRecipientRegistry(LABS_BORG_STABLE_REGISTRY), "updateSpentAmount")[
                2:
            ],
        ),
    )


# Events check
def validate_config_value_updated(event: EventDict, key, value):
    _events_chain = ["LogScriptCall", "LogScriptCall", "ConfigValueUpdated", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event["ConfigValueUpdated"]["key"] == key
    assert convert.to_bytes(event["ConfigValueUpdated"]["value"], 'bytes').hex() == value
