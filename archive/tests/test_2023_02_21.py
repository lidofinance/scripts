"""
Tests for voting 21/02/2023.

"""
from scripts.vote_2023_02_21 import start_vote

from brownie import ZERO_ADDRESS, chain, accounts
from brownie.network.transaction import TransactionReceipt

from eth_abi.abi import encode

from utils.config import network_name
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_staking_limit_set_event,
    NodeOperatorStakingLimitSetItem,
)
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)
from utils.easy_track import create_permissions
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items

blockdaemon_params_before = {
    "active": True,
    "name": 'Blockdaemon',
    "rewardAddress": '0x4f42A816dC2DBa82fF927b6996c14a741DCbD902',
    "stakingLimit": 5850,
}

blockdaemon_params_after = {
    "active": True,
    "name": 'Blockdaemon',
    "rewardAddress": '0x4f42A816dC2DBa82fF927b6996c14a741DCbD902',
    "stakingLimit": 3800,
}

def check_no_params(no_params_from_registry, no_params_to_check):
    assert no_params_from_registry[0] == no_params_to_check["active"]
    assert no_params_from_registry[1] == no_params_to_check["name"]
    assert no_params_from_registry[2] == no_params_to_check["rewardAddress"]
    assert no_params_from_registry[3] == no_params_to_check["stakingLimit"]


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
    finance,
    node_operators_registry,
    dao_agent
):

    TRP_topup_factory = interface.TopUpAllowedRecipients("0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C")
    TRP_registry = interface.AllowedRecipientRegistry("0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8")
    TRP_multisig = accounts.at("0x834560F580764Bc2e0B16925F8bF229bb00cB759", {"force": True})

    Blockdaemon_id = 13


    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 15

    assert TRP_topup_factory not in old_factories_list

    check_no_params(node_operators_registry.getNodeOperator(Blockdaemon_id, True), blockdaemon_params_before)

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 16

    # 1. Add TRP LDO top up EVM script factory 0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C to Easy Track
    assert TRP_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        TRP_multisig,
        TRP_topup_factory,
        ldo_token,
        [TRP_multisig],
        [10 * 10**18],
        unknown_person,
        dao_agent
    )
    check_add_and_remove_recipient_with_voting(TRP_registry, helpers, ldo_holder, dao_voting)

    # 2. Set Staking limit for node operator Blockdaemon to 3800
    check_no_params(node_operators_registry.getNodeOperator(Blockdaemon_id, True), blockdaemon_params_after)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 2, "Incorrect voting items count"

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

    validate_node_operator_staking_limit_set_event(
        evs[1],
        NodeOperatorStakingLimitSetItem(
            id=13,
            staking_limit=blockdaemon_params_after["stakingLimit"]
        )
    )


def create_and_enact_payment_motion(
    easy_track,
    trusted_caller,
    factory,
    token,
    recievers,
    transfer_amounts,
    stranger,
    agent
):
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
        assert recievers_balance_after[i] == recievers_balance_before[i] + transfer_amounts[i]

    agent_balance_after = balance_of(agent, token)

    assert agent_balance_after == agent_balance_before - sum(transfer_amounts)


def balance_of(address, token):
    return token.balanceOf(address)


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

def _encode_calldata(signature, values):
    return "0x" + encode(signature, values).hex()
