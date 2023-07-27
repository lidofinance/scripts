

"""
Tests for voting 08/08/2023.

!! goerli only
"""
from scripts.vote_2023_08_08_goerli import start_vote

from brownie import ZERO_ADDRESS, chain, accounts
from brownie.network.transaction import TransactionReceipt

from eth_abi.abi import encode_single

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.easy_track import create_permissions
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items

from utils.test.easy_track_helpers import (
    create_and_enact_payment_motion,
    create_and_enact_add_recipient_motion,
    create_and_enact_remove_recipient_motion,
    check_add_and_remove_recipient_with_voting,
)

#####
# CONSTANTS
#####

def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
    ldo_holder,
    stranger,

):

    if not network_name() in ("goerli", "goerli-fork"):
        return

    stETH_token = interface.ERC20("0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F")

    finance = contracts.finance
    voting = contracts.voting
    easy_track = contracts.easy_track

    rewards_share_topup_factory = interface.TopUpAllowedRecipients("0x5Bb391170899A7b8455A442cca65078ff3E1639C")
    rewards_share_add_recipient_factory = interface.AddAllowedRecipient("0x51916FC3D24CbE19c5e981ae8650668A1F5cF19B")
    rewards_share_remove_recipient_factory = interface.RemoveAllowedRecipient("0x932aab3D6057ed2Beef95471414831C4535600E9")
    rewards_share_registry = interface.AllowedRecipientRegistry("0x8b59609f4bEa230E565Ae0C3C7b6913746Df1cF2")
    rewards_share_multisig = accounts.at("0xc4094c015666CBC093FffDC9BB3CF077a864ddB3", {"force": True})

    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 18

    assert rewards_share_topup_factory not in old_factories_list
    assert rewards_share_add_recipient_factory not in old_factories_list
    assert rewards_share_remove_recipient_factory not in old_factories_list

    # START VOTE
    vote_ids = []
    if len(vote_ids_from_env) > 0:
        vote_ids = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
        vote_ids = [vote_id]

    (vote_tx, _) = helpers.execute_votes(accounts, vote_ids, contracts.voting)

    print(f"voteId = {vote_ids}, gasUsed = {vote_tx.gas_used}")

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 13

    assert rewards_share_topup_factory in updated_factories_list
    assert rewards_share_add_recipient_factory in updated_factories_list
    assert rewards_share_remove_recipient_factory in updated_factories_list

    '''create_and_enact_payment_motion(
        easy_track,
        rewards_share_multisig,
        rewards_share_topup_factory,
        stETH_token,
        [rewards_share_multisig],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(rewards_share_registry, helpers, ldo_holder, voting)
    create_and_enact_add_recipient_motion(
        easy_track,
        rewards_share_multisig,
        rewards_share_registry,
        rewards_share_add_recipient_factory,
        stranger,
        "New recipient",
        ldo_holder,
    )
    create_and_enact_remove_recipient_motion(
        easy_track,
        rewards_share_multisig,
        rewards_share_registry,
        rewards_share_remove_recipient_factory,
        stranger,
        ldo_holder,
    )
    '''
    # validate vote events
    assert count_vote_items_by_events(vote_tx, voting) == 3, "Incorrect voting items count"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=rewards_share_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(rewards_share_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[1],
        EVMScriptFactoryAdded(
            factory_addr=rewards_share_add_recipient_factory,
            permissions=create_permissions(rewards_share_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[2],
        EVMScriptFactoryAdded(
            factory_addr=rewards_share_remove_recipient_factory,
            permissions=create_permissions(rewards_share_registry, "removeRecipient"),
        ),
    )
