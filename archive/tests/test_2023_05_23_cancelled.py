"""
Tests for voting 25/04/2023.

"""
from archive.scripts.vote_2023_05_23_cancelled import start_vote

from brownie import chain, accounts
from brownie.network.transaction import TransactionReceipt
from eth_abi.abi import encode_single

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    validate_node_operator_reward_address_set_event,
    NodeOperatorNameSetItem,
    NodeOperatorRewardAddressSetItem,
)
from utils.test.event_validators.easy_track import (
    validate_motions_count_limit_changed_event,
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.easy_track import create_permissions
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items
import math

#####
# CONSTANTS
#####

STETH_ERROR_MARGIN = 2
eth = "0x0000000000000000000000000000000000000000"

def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
    ldo_holder,
    stranger,

):

    ## parameters
    finance = contracts.finance

    # 1.
    easy_track = contracts.easy_track
    motionsCountLimit_before = 12
    motionsCountLimit_after = 20

    # 2-4.
    stETH_token = interface.ERC20("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
    reWARDS_stETH_allowed_recipients = [
        accounts.at("0x87D93d9B2C672bf9c9642d853a8682546a5012B5", {"force": True}),
    ]
    reWARDS_stETH_registry = interface.AllowedRecipientRegistry("0x48c4929630099b217136b64089E8543dB0E5163a")
    reWARDS_stETH_topup_factory = interface.TopUpAllowedRecipients("0x1F2b79FE297B7098875930bBA6dd17068103897E")
    reWARDS_stETH_add_recipient_factory = interface.AddAllowedRecipient("0x935cb3366Faf2cFC415B2099d1F974Fd27202b77")
    reWARDS_stETH_remove_recipient_factory = interface.RemoveAllowedRecipient("0x22010d1747CaFc370b1f1FBBa61022A313c5693b")
    reWARDS_stETH_multisig = accounts.at("0x87D93d9B2C672bf9c9642d853a8682546a5012B5", {"force": True})

    # 5-7.
    reWARDS_LDO_topup_factory = interface.TopUpAllowedRecipients("0x85d703B2A4BaD713b596c647badac9A1e95bB03d")
    reWARDS_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C")
    reWARDS_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E")

    # 8-10 Remove LDO referral program from Easy Track
    referral_program_LDO_topup_factory = interface.TopUpAllowedRecipients("0x54058ee0E0c87Ad813C002262cD75B98A7F59218")
    referral_program_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51")
    referral_program_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C")

    # 11-13 Remove LDO referral program from Easy Track
    referral_program_DAI_topup_factory = interface.TopUpAllowedRecipients("0x009ffa22ce4388d2F5De128Ca8E6fD229A312450")
    referral_program_DAI_add_recipient_factory = interface.AddAllowedRecipient("0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151")
    referral_program_DAI_remove_recipient_factory = interface.RemoveAllowedRecipient("0xd8f9B72Cd97388f23814ECF429cd18815F6352c1")


    ## check vote items parameters before voting
    factories_list_before_voting = easy_track.getEVMScriptFactories()
    assert len(factories_list_before_voting) == 16

    # 1.
    easy_track.motionsCountLimit() == motionsCountLimit_before, "Incorrect motions count limit before"

    # 2-4.
    assert reWARDS_stETH_topup_factory not in factories_list_before_voting
    assert reWARDS_stETH_add_recipient_factory not in factories_list_before_voting
    assert reWARDS_stETH_remove_recipient_factory not in factories_list_before_voting

    # 5-7.
    assert reWARDS_LDO_topup_factory in factories_list_before_voting
    assert reWARDS_LDO_add_recipient_factory in factories_list_before_voting
    assert reWARDS_LDO_remove_recipient_factory in factories_list_before_voting

    # 8-10.
    assert referral_program_LDO_topup_factory in factories_list_before_voting
    assert referral_program_LDO_add_recipient_factory in factories_list_before_voting
    assert referral_program_LDO_remove_recipient_factory in factories_list_before_voting

    # 11-13.
    assert referral_program_DAI_topup_factory in factories_list_before_voting
    assert referral_program_DAI_add_recipient_factory in factories_list_before_voting
    assert referral_program_DAI_remove_recipient_factory in factories_list_before_voting


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

     # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 13, "Incorrect voting items count"

    display_voting_events(vote_tx)

    # check amount of Easy Track factories
    factories_list_after_voting = easy_track.getEVMScriptFactories()
    assert len(factories_list_after_voting) == len(factories_list_before_voting) + 3 - 3 -3 -3

    # 1. check Easy Track motions count limit after
    easy_track.motionsCountLimit() == motionsCountLimit_after, "Incorrect motions count limit after"

    # 2.
    assert reWARDS_stETH_topup_factory in factories_list_after_voting
    create_and_enact_payment_motion(
        easy_track,
        reWARDS_stETH_multisig,
        reWARDS_stETH_topup_factory,
        stETH_token,
        reWARDS_stETH_allowed_recipients,
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(reWARDS_stETH_registry, helpers, ldo_holder, contracts.voting)

    # 3.
    assert reWARDS_stETH_add_recipient_factory in factories_list_after_voting
    create_and_enact_add_recipient_motion(
        easy_track,
        reWARDS_stETH_multisig,
        reWARDS_stETH_registry,
        reWARDS_stETH_add_recipient_factory,
        stranger,
        "",
        ldo_holder,
    )

    # 4.
    assert reWARDS_stETH_remove_recipient_factory in factories_list_after_voting
    create_and_enact_remove_recipient_motion(
        easy_track,
        reWARDS_stETH_multisig,
        reWARDS_stETH_registry,
        reWARDS_stETH_remove_recipient_factory,
        stranger,
        ldo_holder,
    )

    # 5.
    assert reWARDS_LDO_topup_factory not in factories_list_after_voting
    # 6.
    assert reWARDS_LDO_add_recipient_factory not in factories_list_after_voting
    # 7.
    assert reWARDS_LDO_remove_recipient_factory not in factories_list_after_voting

    # 8.
    assert referral_program_LDO_topup_factory not in factories_list_after_voting
    # 9.
    assert referral_program_LDO_add_recipient_factory not in factories_list_after_voting
    # 10.
    assert referral_program_LDO_remove_recipient_factory not in factories_list_after_voting

    # 11.
    assert referral_program_DAI_topup_factory not in factories_list_after_voting
    # 12.
    assert referral_program_DAI_add_recipient_factory not in factories_list_after_voting
    # 13.
    assert referral_program_DAI_remove_recipient_factory not in factories_list_after_voting


    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)


    validate_motions_count_limit_changed_event(
        evs[0],
        motionsCountLimit_after
    )
    validate_evmscript_factory_added_event(
        evs[1],
        EVMScriptFactoryAdded(
            factory_addr=reWARDS_stETH_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(reWARDS_stETH_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[2],
        EVMScriptFactoryAdded(
            factory_addr=reWARDS_stETH_add_recipient_factory,
            permissions=create_permissions(reWARDS_stETH_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[3],
        EVMScriptFactoryAdded(
            factory_addr=reWARDS_stETH_remove_recipient_factory,
            permissions=create_permissions(reWARDS_stETH_registry, "removeRecipient"),
        ),
    )
    validate_evmscript_factory_removed_event(evs[4], reWARDS_LDO_topup_factory)
    validate_evmscript_factory_removed_event(evs[5], reWARDS_LDO_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[6], reWARDS_LDO_remove_recipient_factory)
    validate_evmscript_factory_removed_event(evs[7], referral_program_LDO_topup_factory)
    validate_evmscript_factory_removed_event(evs[8], referral_program_LDO_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[9], referral_program_LDO_remove_recipient_factory)
    validate_evmscript_factory_removed_event(evs[10], referral_program_DAI_topup_factory)
    validate_evmscript_factory_removed_event(evs[11], referral_program_DAI_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[12], referral_program_DAI_remove_recipient_factory)


def _encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()


def create_and_enact_payment_motion(
    easy_track,
    trusted_caller,
    factory,
    token,
    recievers,
    transfer_amounts,
    stranger,
):
    agent = accounts.at("0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c", {"force": True})
    agent_balance_before = balance_of(agent, token)
    recievers_balance_before = [balance_of(reciever, token) for reciever in recievers]
    motions_before = easy_track.getMotions()

    recievers_addresses = [reciever.address for reciever in recievers]

    calldata = _encode_calldata("(address[],uint256[])", [recievers_addresses, transfer_amounts])

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    recievers_balance_after = [balance_of(reciever, token) for reciever in recievers]
    for i in range(len(recievers)):
        assert math.isclose(recievers_balance_after[i], recievers_balance_before[i] + transfer_amounts[i], abs_tol=STETH_ERROR_MARGIN)

    agent_balance_after = balance_of(agent, token)

    assert math.isclose(agent_balance_after, agent_balance_before - sum(transfer_amounts), abs_tol=STETH_ERROR_MARGIN)


def balance_of(address, token):
    if token == eth:
        return address.balance()
    else:
        return token.balanceOf(address)


def create_and_enact_add_recipient_motion(
    easy_track,
    trusted_caller,
    registry,
    factory,
    recipient,
    title,
    stranger,
):
    recipients_count = len(registry.getAllowedRecipients())
    assert not registry.isRecipientAllowed(recipient)
    motions_before = easy_track.getMotions()

    calldata = _encode_calldata("(address,string)", [recipient.address, title])

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(registry.getAllowedRecipients()) == recipients_count + 1
    assert registry.isRecipientAllowed(recipient)


def create_and_enact_remove_recipient_motion(
    easy_track,
    trusted_caller,
    registry,
    factory,
    recipient,
    stranger,
):
    recipients_count = len(registry.getAllowedRecipients())
    assert registry.isRecipientAllowed(recipient)
    motions_before = easy_track.getMotions()

    calldata = _encode_calldata("(address)", [recipient.address])

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(registry.getAllowedRecipients()) == recipients_count - 1
    assert not registry.isRecipientAllowed(recipient)


def check_add_and_remove_recipient_with_voting(registry, helpers, ldo_holder, dao_voting):
    recipient_candidate = accounts[0]
    title = ""
    recipients_length_before = len(registry.getAllowedRecipients())

    assert not registry.isRecipientAllowed(recipient_candidate)

    call_script_items = [
        agent_forward(
            [
                (
                    registry.address,
                    registry.addRecipient.encode_input(recipient_candidate, title),
                )
            ]
        )
    ]
    vote_desc_items = ["Add recipient"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )

    assert registry.isRecipientAllowed(recipient_candidate)
    assert len(registry.getAllowedRecipients()) == recipients_length_before + 1, 'Wrong whitelist length'

    call_script_items = [
        agent_forward(
            [
                (
                    registry.address,
                    registry.removeRecipient.encode_input(recipient_candidate),
                )
            ]
        )
    ]
    vote_desc_items = ["Remove recipient"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )

    assert not registry.isRecipientAllowed(recipient_candidate)
    assert len(registry.getAllowedRecipients()) == recipients_length_before, 'Wrong whitelist length'
