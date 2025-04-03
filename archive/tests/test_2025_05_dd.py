from archive.scripts.vote_2025_05_dd import start_vote
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
    EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
    EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
)
from configs.config_mainnet import (
    EASYTRACK_EVMSCRIPT_EXECUTOR,
)
from utils.easy_track import create_permissions
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.test.event_validators.relay_allowed_list import validate_relay_allowed_list_manager_set


def add_relay_with_voting(relay, mev_boost_allowed_list, agent):
    """
    Add relay to MEV-Boost Relay Allowed List with voting
    """
    # Create motion for adding relay
    motion_id = mev_boost_allowed_list.createMotion(
        agent,
        mev_boost_allowed_list.addRelay.encode_input(relay),
        {"from": agent},
    )

    # Enact motion
    mev_boost_allowed_list.enactMotion(motion_id, {"from": agent})


def test_vote(helpers, accounts, vote_ids_from_env, agent):
    easy_track = contracts.easy_track
    mev_boost_allowed_list = contracts.relay_allowed_list

    evm_script_factories_before = easy_track.getEVMScriptFactories()
    old_manager = contracts.relay_allowed_list.getManager()

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

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # I. EasyTrack Factories for Managing MEV-Boost Relay Allowed List
    evm_script_factories_after = easy_track.getEVMScriptFactories()

    # Check that the new factories have been added
    assert (
        len(evm_script_factories_after) == len(evm_script_factories_before) + 3
    ), "Number of EVM script factories is incorrect"

    events = []
    # Check that the new factories are present and have the correct addresses
    script_factory_added_event = vote_tx.events["EVMScriptFactoryAdded"]

    # Check that the events were emitted the correct number of times
    assert (
        vote_tx.events.count("EVMScriptFactoryAdded") == 3
    ), "EVMScriptFactoryAdded event not emitted or emitted multiple times"
    assert vote_tx.events.count("ManagerChanged") == 1, "ManagerChanged event not emitted or emitted multiple times"

    # 1. Add `AddMEVBoostRelay` EVM script factory
    assert EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY in evm_script_factories_after, "AddMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        script_factory_added_event,
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
            permissions=create_permissions(contracts.relay_allowed_list, "add_relay"),
        ),
    )

    # 2. Add `RemoveMEVBoostRelay` EVM script factory
    assert (
        EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY in evm_script_factories_after
    ), "RemoveMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        script_factory_added_event,
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
            permissions=create_permissions(contracts.relay_allowed_list, "remove_relay"),
        ),
    )

    # 3. Add `EditMEVBoostRelay` EVM script factory
    assert EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY in evm_script_factories_after, "EditMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        script_factory_added_event,
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
            permissions=create_permissions(contracts.relay_allowed_list, "edit_relay"),
        ),
    )

    # 4. Change manager role on MEV-Boost Relay Allowed List
    validate_relay_allowed_list_manager_set(
        event=vote_tx.events["ManagerChanged"],
        new_manager=EASYTRACK_EVMSCRIPT_EXECUTOR,
    )
