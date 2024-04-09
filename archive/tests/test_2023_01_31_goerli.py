"""
Tests for voting 31/01/2023.

!! goerli only
"""
from scripts.vote_2023_01_31_goerli import start_vote

from brownie import ZERO_ADDRESS, chain, accounts
from brownie.network.transaction import TransactionReceipt

from eth_abi.abi import encode

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
):
    if not network_name() in ("goerli", "goerli-fork"):
        return

    dai_token = interface.ERC20("0x11fe4b6ae13d2a6055c8d9cf65c55bac32b5d844")

    finance = interface.Finance("0x75c7b1D23f1cad7Fb4D60281d7069E46440BC179")
    dao_voting = interface.Voting("0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db")
    easy_track = interface.EasyTrack("0xAf072C8D368E4DD4A9d4fF6A76693887d6ae92Af")

    rewards_topup_factory = interface.TopUpAllowedRecipients("0x9534A77029D57E249c467E5A1E0854cc26Cd75A0")
    rewards_add_recipient_factory = interface.AddAllowedRecipient("0x734458219BE229F6631F083ea574EBACa2f9bEaf")
    rewards_remove_recipient_factory = interface.RemoveAllowedRecipient("0x5FEC0bcd7519C4fE41eca5Fe1dD94345fA100A67")
    rewards_registry = interface.AllowedRecipientRegistry("0x8fB566b1e78e603a86b97ada5FcA858764dF4088")
    rewards_multisig = accounts.at("0xc4094c015666CBC093FffDC9BB3CF077a864ddB3", {"force": True})
    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 20

    assert rewards_topup_factory not in old_factories_list
    assert rewards_add_recipient_factory not in old_factories_list
    assert rewards_remove_recipient_factory not in old_factories_list

    ##
    ## START VOTE
    ##

    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 23

    # 1. Add reWARDS top up EVM script factory 0x9534A77029D57E249c467E5A1E0854cc26Cd75A0
    assert rewards_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        rewards_multisig,
        rewards_topup_factory,
        dai_token,
        [
            accounts.at("0x1ce2E546CA7dF74ab63eC09BF48dD1C35E8c7739", {"force": True}),
            accounts.at("0x2f0EA53F92252167d658963f334a91de0824e322", {"force": True}),
        ],
        [10 * 10**18, 10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(rewards_registry, helpers, ldo_holder, dao_voting)

    # 2. Add reWARDS add recipient EVM script factory 0x734458219BE229F6631F083ea574EBACa2f9bEaf
    assert rewards_add_recipient_factory in updated_factories_list
    create_and_enact_add_recipient_motion(
        easy_track,
        rewards_multisig,
        rewards_registry,
        rewards_add_recipient_factory,
        unknown_person,
        "New recipient",
        ldo_holder,
    )

    # 3. Add reWARDS remove recipient EVM script factory 0x5FEC0bcd7519C4fE41eca5Fe1dD94345fA100A67
    assert rewards_remove_recipient_factory in updated_factories_list
    create_and_enact_remove_recipient_motion(
        easy_track,
        rewards_multisig,
        rewards_registry,
        rewards_remove_recipient_factory,
        unknown_person,
        ldo_holder,
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 3, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=rewards_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(rewards_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[1],
        EVMScriptFactoryAdded(
            factory_addr=rewards_add_recipient_factory,
            permissions=create_permissions(rewards_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[2],
        EVMScriptFactoryAdded(
            factory_addr=rewards_remove_recipient_factory,
            permissions=create_permissions(rewards_registry, "removeRecipient"),
        ),
    )


def _encode_calldata(signature, values):
    return "0x" + encode(signature, values).hex()


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
