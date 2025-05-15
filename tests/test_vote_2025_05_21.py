from utils.config import (
    contracts,
    AGENT,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
    EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
    EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
)
from utils.test.easy_track_helpers import (
    TEST_RELAY,
    create_and_enact_add_mev_boost_relay_motion,
    create_and_enact_remove_mev_boost_relay_motion,
    create_and_enact_edit_mev_boost_relay_motion,
)
from utils.easy_track import create_permissions
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.test.event_validators.relay_allowed_list import validate_relay_allowed_list_manager_set
from utils.test.event_validators.after_pectra import (
    EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
    APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
    INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE,
    validate_sc_exited_validators_limit_update,
    validate_appeared_validators_limit_update,
    validate_initial_slashing_and_penalties_update,
)

from utils.test.tx_tracing_helpers import (
    group_voting_events,
)

from scripts.vote_2025_05_21 import start_vote
from utils.test.tx_tracing_helpers import display_voting_events


# Old values

OLD_INITIAL_SLASHING_AMOUNT_PWEI = 1000
OLD_EXITED_VALIDATORS_PER_DAY_LIMIT = 9000
OLD_APPEARED_VALIDATORS_PER_DAY_LIMIT = 43200

# New values
NEW_INITIAL_SLASHING_AMOUNT_PWEI = 8
NEW_EXITED_VALIDATORS_PER_DAY_LIMIT = 3600
NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT = 1800

RMC_MULTISIG_ADDRESS = "0x98be4a407Bff0c125e25fBE9Eb1165504349c37d"


def test_vote(helpers, accounts, vote_ids_from_env, ldo_holder, stranger):
    easy_track = contracts.easy_track
    mev_boost_allowed_list = contracts.relay_allowed_list

    trusted_caller = accounts.at(RMC_MULTISIG_ADDRESS, force=True)

    evm_script_factories_before = easy_track.getEVMScriptFactories()
    old_manager = contracts.relay_allowed_list.get_manager()
    sanity_checker = contracts.oracle_report_sanity_checker
    sanity_checker_limits = sanity_checker.getOracleReportLimits()

    # Before voting tests

    # 1) Aragon Agent doesn't have `EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanity_checker.hasRole(EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 2) Check `exitedValidatorsPerDayLimit` sanity checker old value
    assert sanity_checker_limits["exitedValidatorsPerDayLimit"] == OLD_EXITED_VALIDATORS_PER_DAY_LIMIT
    # 3) Aragon Agent doesn't have `APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanity_checker.hasRole(APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 4) Check `appearedValidatorsPerDayLimit` sanity checker old value
    assert sanity_checker_limits["appearedValidatorsPerDayLimit"] == OLD_APPEARED_VALIDATORS_PER_DAY_LIMIT
    # 5) Aragon Agent doesn't have `INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanity_checker.hasRole(INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 6) Check `initialSlashingAmountPWei` sanity checker old value
    assert sanity_checker_limits["initialSlashingAmountPWei"] == OLD_INITIAL_SLASHING_AMOUNT_PWEI

    # 10) sanity check that the add factory is not already present
    assert EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY not in evm_script_factories_before
    # 11) sanity check that the remove factory is not already present
    assert EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY not in evm_script_factories_before
    # 12) sanity check that the edit factory is not already present
    assert EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY not in evm_script_factories_before
    # 13) sanity check that the manager is not already set to EasyTrackEVMScriptExecutor
    assert old_manager != EASYTRACK_EVMSCRIPT_EXECUTOR

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    sanity_checker_limits = sanity_checker.getOracleReportLimits()

    # After voting tests
    # 1) Aragon Agent doesn't have `EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanity_checker.hasRole(EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 2) Check `exitedValidatorsPerDayLimit` sanity checker value after voting equal to 3600
    assert sanity_checker_limits["exitedValidatorsPerDayLimit"] == NEW_EXITED_VALIDATORS_PER_DAY_LIMIT
    # 3) Aragon Agent doesn't have `APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanity_checker.hasRole(APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 4) Check `appearedValidatorsPerDayLimit` sanity checker value after voting equal to 1800
    assert sanity_checker_limits["appearedValidatorsPerDayLimit"] == NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT
    # 5) Aragon Agent doesn't have `INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = sanity_checker.hasRole(INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 6) Check `initialSlashingAmountPWei` sanity checker value to 8
    assert sanity_checker_limits["initialSlashingAmountPWei"] == NEW_INITIAL_SLASHING_AMOUNT_PWEI

    # Events check
    display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    assert len(events) == 13

    # Validate exitedValidatorsPerDayLimit sanity checker value set to `NEW_EXITED_VALIDATORS_PER_DAY_LIMIT`
    validate_sc_exited_validators_limit_update(events[:3], NEW_EXITED_VALIDATORS_PER_DAY_LIMIT)
    # Validate appearedValidatorsPerDayLimit sanity checker value set to `NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT`
    validate_appeared_validators_limit_update(events[3:6], NEW_APPEARED_VALIDATORS_PER_DAY_LIMIT)
    # Validate initialSlashingAmountPWei sanity checker value set to `NEW_INITIAL_SLASHING_AMOUNT_PWEI`
    validate_initial_slashing_and_penalties_update(events[6:9], NEW_INITIAL_SLASHING_AMOUNT_PWEI)

    check_mev_boost_relay_management_factories(
        helpers,
        ldo_holder,
        stranger,
        easy_track,
        mev_boost_allowed_list,
        trusted_caller,
        events[9:],
        evm_script_factories_before,
    )


def check_mev_boost_relay_management_factories(
    helpers,
    ldo_holder,
    stranger,
    easy_track,
    mev_boost_allowed_list,
    trusted_caller,
    events,
    evm_script_factories_before,
):
    # II. EasyTrack Factories for Managing MEV-Boost Relay Allowed List
    evm_script_factories_after = easy_track.getEVMScriptFactories()

    # Check that the new factories have been added
    assert (
        len(evm_script_factories_after) == len(evm_script_factories_before) + 3
    ), "Number of EVM script factories is incorrect"

    # 10. Add `AddMEVBoostRelay` EVM script factory
    assert EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY in evm_script_factories_after, "AddMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        events[0],
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
            permissions=create_permissions(contracts.relay_allowed_list, "add_relay"),
        ),
    )

    create_and_enact_add_mev_boost_relay_motion(
        easy_track,
        trusted_caller,
        mev_boost_allowed_list,
        EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
        TEST_RELAY,
        stranger,
        helpers,
        ldo_holder,
        contracts.voting,
    )

    # 11. Add `RemoveMEVBoostRelay` EVM script factory
    assert (
        EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY in evm_script_factories_after
    ), "RemoveMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        events[1],
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
            permissions=create_permissions(contracts.relay_allowed_list, "remove_relay"),
        ),
    )

    create_and_enact_remove_mev_boost_relay_motion(
        easy_track,
        trusted_caller,
        mev_boost_allowed_list,
        EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
        TEST_RELAY[0],
        stranger,
        helpers,
        ldo_holder,
        contracts.voting,
    )

    # 12. Add `EditMEVBoostRelay` EVM script factory
    assert EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY in evm_script_factories_after, "EditMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        events[2],
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
            permissions=create_permissions(contracts.relay_allowed_list, "add_relay")
            + create_permissions(contracts.relay_allowed_list, "remove_relay")[2:],
        ),
    )

    create_and_enact_edit_mev_boost_relay_motion(
        easy_track,
        trusted_caller,
        mev_boost_allowed_list,
        EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
        (TEST_RELAY[0], "Dolor Sit Amet Operator", TEST_RELAY[2], TEST_RELAY[3]),
        stranger,
        helpers,
        ldo_holder,
        contracts.voting,
    )

    # 13. Change manager role on MEV-Boost Relay Allowed List
    assert mev_boost_allowed_list.get_manager() == EASYTRACK_EVMSCRIPT_EXECUTOR
    validate_relay_allowed_list_manager_set(
        event=events[3],
        new_manager=EASYTRACK_EVMSCRIPT_EXECUTOR,
    )
