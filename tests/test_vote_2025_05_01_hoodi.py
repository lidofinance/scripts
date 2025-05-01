"""
Tests for voting 01/05/2025. Hoodi network.

"""

from brownie import interface
from scripts.vote_2025_05_01_hoodi import start_vote
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
)
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grant_event,
)
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)
from utils.easy_track import create_permissions
from utils.voting import find_metadata_by_vote_id


def test_vote(helpers, accounts, vote_ids_from_env):
    # new code
    easy_track = contracts.easy_track
    voting = contracts.voting
    finance = contracts.finance

    add_allowed_recipient_evm_script_factory = "0x056561d0F1314CB3932180b3f0B3C03174F2642B"
    remove_allowed_recipient_evm_script_factory = "0xc84251D2959E976AfE95201E1e2B88dB56Bc0a69"
    top_up_allowed_recipient_evm_script_factory = "0x8D9Fd9cD208f57c6735174B848180B53A0F7F560"

    registry = interface.AllowedRecipientRegistry("0xd57FF1ce54F572F4E8DaF0cB7038F1Bd6049cAa8")
    trusted_caller = "0x418B816A7c3ecA151A31d98e30aa7DAa33aBf83A"
    token_registry = "0xA51b9ecfa754F619971f3Dc58Def517F267F84dB"

    evm_script_factories_before = easy_track.getEVMScriptFactories()

    assert add_allowed_recipient_evm_script_factory not in evm_script_factories_before
    assert remove_allowed_recipient_evm_script_factory not in evm_script_factories_before
    assert top_up_allowed_recipient_evm_script_factory not in evm_script_factories_before

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # I. EasyTrack factories
    evm_script_factories = easy_track.getEVMScriptFactories()

    assert add_allowed_recipient_evm_script_factory in evm_script_factories
    assert remove_allowed_recipient_evm_script_factory in evm_script_factories
    assert top_up_allowed_recipient_evm_script_factory in evm_script_factories

    removeRecipientsContract = interface.RemoveAllowedRecipient(remove_allowed_recipient_evm_script_factory)
    addRecipientsContract = interface.AddAllowedRecipient(add_allowed_recipient_evm_script_factory)
    topUpRecipientsContract = interface.TopUpAllowedRecipients(top_up_allowed_recipient_evm_script_factory)

    assert removeRecipientsContract.allowedRecipientsRegistry() == registry
    assert removeRecipientsContract.trustedCaller() == trusted_caller

    assert addRecipientsContract.allowedRecipientsRegistry() == registry
    assert addRecipientsContract.trustedCaller() == trusted_caller

    assert topUpRecipientsContract.allowedRecipientsRegistry() == registry
    assert topUpRecipientsContract.trustedCaller() == trusted_caller
    assert topUpRecipientsContract.finance() == contracts.finance
    assert topUpRecipientsContract.easyTrack() == easy_track

    # validate vote events
    assert count_vote_items_by_events(vote_tx, voting) == 4, "Incorrect voting items count"
    metadata = find_metadata_by_vote_id(vote_id)
    print("metadata", metadata)

    evs = group_voting_events_from_receipt(vote_tx)

    # Grant permissions to make operational changes to EasyTrack module
    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=remove_allowed_recipient_evm_script_factory,
            permissions=create_permissions(registry, "removeRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[1],
        EVMScriptFactoryAdded(
            factory_addr=add_allowed_recipient_evm_script_factory,
            permissions=create_permissions(registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[2],
        EVMScriptFactoryAdded(
            factory_addr=top_up_allowed_recipient_evm_script_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(registry, "updateSpentAmount")[2:],
        ),
    )

    permission = Permission(
        entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
        app=finance,
        role="0x5de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc",
    )  # keccak256('CREATE_PAYMENTS_ROLE')

    validate_permission_grant_event(evs[3], permission)
