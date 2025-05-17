from brownie import interface
from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS
from utils.test.easy_track_helpers import (
    TEST_RELAY,
    create_and_enact_add_mev_boost_relay_motion,
    create_and_enact_remove_mev_boost_relay_motion,
    create_and_enact_edit_mev_boost_relay_motion,
)
from utils.easy_track import create_permissions
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.test.tx_tracing_helpers import group_voting_events
from archive.scripts.vote_2025_05_14_hoodi import start_vote

QA_DAO_OPS_TEST_MS = "0x418B816A7c3ecA151A31d98e30aa7DAa33aBf83A"
VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"

EASYTRACK = "0x284D91a7D47850d21A6DEaaC6E538AC7E5E6fc2a"
EASYTRACK_EVMSCRIPT_EXECUTOR = "0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E"

MEV_BOOST_RELAY_ALLOWED_LIST = "0x279d3A456212a1294DaEd0faEE98675a52E8A4Bf"

EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY = "0xF02DbeaA1Bbc90226CaB995db4C190DbE25983af"
EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY = "0x7FCc2901C6C3D62784cB178B14d44445B038f736"
EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY = "0x27A99a7104190DdA297B222104A6C70A4Ca5A17e"


def test_vote(helpers, accounts, vote_ids_from_env, ldo_holder, stranger):
    voting = interface.Voting(VOTING)
    easy_track = interface.EasyTrack(EASYTRACK)
    mev_boost_allowed_list = interface.MEVBoostRelayAllowedList(MEV_BOOST_RELAY_ALLOWED_LIST)

    trusted_caller = accounts.at(QA_DAO_OPS_TEST_MS, force=True)

    evm_script_factories_before = easy_track.getEVMScriptFactories()
    old_manager = mev_boost_allowed_list.get_manager()

    # sanity check that the factories are not already present
    assert EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY not in evm_script_factories_before
    assert EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY not in evm_script_factories_before
    assert EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY not in evm_script_factories_before

    # sanity check that the manager is not already set to EasyTrackEVMScriptExecutor
    assert old_manager != EASYTRACK_EVMSCRIPT_EXECUTOR

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # I. EasyTrack Factories for Managing MEV-Boost Relay Allowed List
    evm_script_factories_after = easy_track.getEVMScriptFactories()

    # Check that the new factories have been added
    assert (
        len(evm_script_factories_after) == len(evm_script_factories_before) + 3
    ), "Number of EVM script factories is incorrect"

    # Check that the new factories are present and have the correct addresses
    events = group_voting_events(vote_tx)

    # Check that the events were emitted the correct number of times
    assert (
        vote_tx.events.count("EVMScriptFactoryAdded") == 3
    ), "EVMScriptFactoryAdded event not emitted or emitted multiple times"

    assert (
        vote_tx.events.count("ProposalSubmitted") == 2
    ), "ProposalSubmitted event not emitted or emitted multiple times"

    helpers.execute_dg_proposal(vote_tx.events["ProposalSubmitted"][1]["proposalId"])

    # 1. Add `AddMEVBoostRelay` EVM script factory
    assert EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY in evm_script_factories_after, "AddMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        events[0],
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
            permissions=create_permissions(mev_boost_allowed_list, "add_relay"),
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
        voting,
    )

    # 2. Add `RemoveMEVBoostRelay` EVM script factory
    assert (
        EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY in evm_script_factories_after
    ), "RemoveMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        events[1],
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
            permissions=create_permissions(mev_boost_allowed_list, "remove_relay"),
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
        voting,
    )

    # 3. Add `EditMEVBoostRelay` EVM script factory
    assert EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY in evm_script_factories_after, "EditMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        events[2],
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
            permissions=create_permissions(mev_boost_allowed_list, "add_relay")
            + create_permissions(mev_boost_allowed_list, "remove_relay")[2:],
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
        voting,
    )

    # 4. Change manager role on MEV-Boost Relay Allowed List
    assert mev_boost_allowed_list.get_manager() == EASYTRACK_EVMSCRIPT_EXECUTOR
