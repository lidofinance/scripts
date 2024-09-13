"""
Tests for voting 01/10/2024.

!! Holesky only
"""
from scripts.vote_2024_10_01_holesky import start_vote

from brownie import ZERO_ADDRESS, chain, accounts
from brownie.network.transaction import TransactionReceipt

from eth_abi.abi import encode

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
    # create_and_enact_add_recipient_motion,
    # create_and_enact_remove_recipient_motion,
    # check_add_and_remove_recipient_with_voting,
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

    if not network_name() in ("holesky", "holesky-fork"):
        return

    stETH_token = interface.ERC20("0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F") # todo

    finance = contracts.finance
    voting = contracts.voting
    easy_track = contracts.easy_track # todo: проверить адрес контракта easytrack для holesky

    rewards_share_topup_factory = interface.TopUpAllowedRecipients("0x79e0286a8f60276293a7D29f53979642CcBD4Fff")
    # rewards_share_add_recipient_factory = interface.AddAllowedRecipient("0x51916FC3D24CbE19c5e981ae8650668A1F5cF19B")
    # rewards_share_remove_recipient_factory = interface.RemoveAllowedRecipient("0x932aab3D6057ed2Beef95471414831C4535600E9")
    rewards_share_registry = interface.AllowedRecipientRegistry("0x94499410c47FF7572560Ef8CBAf68bCdd0F38D08")
    rewards_share_multisig = accounts.at("0x92ABC000698374B44206148596AcD8a934687E66", {"force": True})

    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 18

    assert rewards_share_topup_factory not in old_factories_list
    # assert rewards_share_add_recipient_factory not in old_factories_list
    # assert rewards_share_remove_recipient_factory not in old_factories_list

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 21

    assert rewards_share_topup_factory in updated_factories_list
    # assert rewards_share_add_recipient_factory in updated_factories_list
    # assert rewards_share_remove_recipient_factory in updated_factories_list

    '''
    check_add_and_remove_recipient_with_voting(
        rewards_share_registry, 
        helpers, ldo_holder, 
        voting,
    )'''

    '''
    create_and_enact_add_recipient_motion(
        easy_track,
        rewards_share_multisig,
        rewards_share_registry,
        rewards_share_add_recipient_factory,
        stranger,
        "New recipient",
        ldo_holder,
    )
    '''

    create_and_enact_payment_motion(
        easy_track,
        rewards_share_multisig,
        rewards_share_topup_factory,
        stETH_token,
        [stranger],
        [10 * 10**18], # todo: обновить баланс?
        stranger,
    )

    '''
    create_and_enact_remove_recipient_motion(
        easy_track,
        rewards_share_multisig,
        rewards_share_registry,
        rewards_share_remove_recipient_factory,
        stranger,
        ldo_holder,
    )
    '''

    # validate vote events, спросить про количество
    assert count_vote_items_by_events(vote_tx, voting) == 2, "Incorrect voting items count" 

    display_voting_events(vote_tx)

    '''
    if bypass_events_decoding or network_name() in ("holesky", "holesky-fork"):
        return
    '''

    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=rewards_share_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(rewards_share_registry, "updateSpentAmount")[2:],
        ),
    )
    
    '''
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
    '''
