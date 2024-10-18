from brownie import chain, accounts, interface
from eth_abi.abi import encode
from utils.config import (
    contracts,
)
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items
from utils.test.helpers import ZERO_ADDRESS, almostEqWithDiff

STETH_ERROR_MARGIN_WEI: int = 2


def _encode_calldata(signature, values):
    return "0x" + encode(signature, values).hex()


def create_and_enact_motion(easy_track, trusted_caller, factory, calldata, stranger):
    motions_before = easy_track.getMotions()

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    (motion_id, _, _, motion_duration, motion_start_date, _, _, _, _,)= motions[-1]

    chain.mine(1, motion_start_date + motion_duration + 1)

    easy_track.enactMotion(
        motion_id,
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )


def create_and_enact_payment_motion(
    easy_track,
    trusted_caller,
    factory,
    token,
    recievers,
    transfer_amounts,
    stranger,
):
    agent = contracts.agent
    agent_balance_before = balance_of(agent, token)
    recievers_balance_before = [balance_of(reciever, token) for reciever in recievers]

    recievers_addresses = [reciever.address for reciever in recievers]

    is_stables_factory = True
    try:
        # New TopUpFactories has a getter to return the tokens registry in contrast to the old version.
        # If the request fails, work with it as with an old factory version.
        interface.TopUpAllowedRecipients(factory).allowedTokensRegistry()
    except:
        is_stables_factory = False

    calldata = (
        _encode_calldata(["address","address[]","uint256[]"], [token.address, recievers_addresses, transfer_amounts])
        if is_stables_factory
        else _encode_calldata(["address[]","uint256[]"], [recievers_addresses, transfer_amounts])
    )

    create_and_enact_motion(easy_track, trusted_caller, factory, calldata, stranger)

    recievers_balance_after = [balance_of(reciever, token) for reciever in recievers]
    for i in range(len(recievers)):
        assert almostEqWithDiff(
            recievers_balance_after[i], recievers_balance_before[i] + transfer_amounts[i], STETH_ERROR_MARGIN_WEI
        )

    agent_balance_after = balance_of(agent, token)

    assert almostEqWithDiff(agent_balance_after, agent_balance_before - sum(transfer_amounts), STETH_ERROR_MARGIN_WEI)


def balance_of(address, token):
    if token == ZERO_ADDRESS:
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

    calldata = _encode_calldata(["address", "string"], [recipient.address, title])

    create_and_enact_motion(easy_track, trusted_caller, factory, calldata, stranger)

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

    calldata = _encode_calldata(["address"], [recipient.address])

    create_and_enact_motion(easy_track, trusted_caller, factory, calldata, stranger)

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
    assert len(registry.getAllowedRecipients()) == recipients_length_before + 1, "Wrong whitelist length"

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
    assert len(registry.getAllowedRecipients()) == recipients_length_before, "Wrong whitelist length"
