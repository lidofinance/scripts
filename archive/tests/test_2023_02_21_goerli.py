"""
Tests for voting 21/02/2023.

!! goerli only
"""
from scripts.vote_2023_02_21_goerli import start_vote

from brownie import ZERO_ADDRESS, chain, accounts
from brownie.network.transaction import TransactionReceipt

from eth_abi.abi import encode_single

from utils.config import network_name
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)
from utils.easy_track import create_permissions
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items


def test_vote(
    helpers,
    accounts,
    vote_id_from_env,
    bypass_events_decoding,
    unknown_person,
    interface,
    ldo_holder,
    dao_voting,
    ldo_token,
    easy_track,
    finance
):
    if not network_name() in ("goerli", "goerli-fork"):
        return

    TRP_topup_factory = interface.TopUpAllowedRecipients("0x43f33C52156d1Fb2eA24d82aBfD342E69835E79f")
    TRP_registry = interface.AllowedRecipientRegistry("0x8C96a6522aEc036C4a384f8B7e05D93d6f3Dae39")
    TRP_multisig = accounts.at("0xcC73e6b8F75326C86B600371576e2C7502627983", {"force": True})
    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 23

    assert TRP_topup_factory not in old_factories_list

    ##
    ## START VOTE
    ##

    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 24

    # 1. Add TRP top up EVM script factory 0x43f33C52156d1Fb2eA24d82aBfD342E69835E79f
    assert TRP_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        TRP_multisig,
        TRP_topup_factory,
        ldo_token,
        [TRP_multisig],
        [10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(TRP_registry, helpers, ldo_holder, dao_voting)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=TRP_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(TRP_registry, "updateSpentAmount")[2:],
        ),
    )



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
    agent = accounts.at("0x4333218072D5d7008546737786663c38B4D561A4", {"force": True})
    agent_balance_before = token.balanceOf(agent)
    recievers_balance_before = [token.balanceOf(reciever) for reciever in recievers]
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

    recievers_balance_after = [token.balanceOf(reciever) for reciever in recievers]
    for i in range(len(recievers)):
        assert recievers_balance_after[i] == recievers_balance_before[i] + transfer_amounts[i]

    agent_balance_after = token.balanceOf(agent)

    assert agent_balance_after == agent_balance_before - sum(transfer_amounts)



def check_add_and_remove_recipient_with_voting(registry, helpers, ldo_holder, dao_voting):
    recipient_candidate = accounts[0]
    title = "Recipient"
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
