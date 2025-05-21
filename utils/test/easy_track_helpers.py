from brownie import chain, accounts, interface
from eth_abi.abi import encode
from utils.config import (
    contracts,
    network_name,
)
from utils.agent import agent_forward, dual_governance_agent_forward
from utils.voting import create_vote, bake_vote_items
from utils.test.helpers import ZERO_ADDRESS, almostEqWithDiff

STETH_ERROR_MARGIN_WEI: int = 2
MEV_BOOST_ALLOWED_LIST_MAX_RELAY_COUNT: int = 40

TEST_RELAY = ("https://0xaaccee.example.com", "Lorem Ipsum Operator", True, "Description of the relay")


def _encode_calldata(signature, values):
    return "0x" + encode(signature, values).hex()


def create_and_enact_motion(easy_track, trusted_caller, factory, calldata, stranger):
    motions_before = easy_track.getMotions()

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    (
        motion_id,
        _,
        _,
        motion_duration,
        motion_start_date,
        _,
        _,
        _,
        _,
    ) = motions[-1]

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
        _encode_calldata(["address", "address[]", "uint256[]"], [token.address, recievers_addresses, transfer_amounts])
        if is_stables_factory
        else _encode_calldata(["address[]", "uint256[]"], [recievers_addresses, transfer_amounts])
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
    )

    assert registry.isRecipientAllowed(recipient_candidate)
    assert len(registry.getAllowedRecipients()) == recipients_length_before + 1, "Wrong whitelist length"
    vote_input = [
        (
            registry.address,
            registry.removeRecipient.encode_input(recipient_candidate),
        )
    ]
    is_hoodi_testnet = network_name() in ["hoodi", "hoodi-fork"]

    call_script_items = [(dual_governance_agent_forward(vote_input) if is_hoodi_testnet else agent_forward(vote_input))]
    vote_desc_items = ["Remove recipient"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    vote_tx = helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
    )
    if is_hoodi_testnet:
        # Execute the proposal
        helpers.execute_dg_proposal(vote_tx.events["ProposalSubmitted"][1]["proposalId"])

    assert not registry.isRecipientAllowed(recipient_candidate)
    assert len(registry.getAllowedRecipients()) == recipients_length_before, "Wrong whitelist length"


def check_and_add_mev_boost_relay_with_voting(mev_boost_allowed_list, mev_boost_relay, helpers, ldo_holder, dao_voting):
    relays = mev_boost_allowed_list.get_relays()

    assert type(mev_boost_relay) == tuple
    assert mev_boost_relay not in relays

    is_hoodi_testnet = network_name() in ["hoodi", "hoodi-fork"]

    vote_input = [
        (
            mev_boost_allowed_list.address,
            mev_boost_allowed_list.add_relay.encode_input(*mev_boost_relay),
        )
    ]

    # Add MEV-Boost relay with voting
    call_script_items = [(dual_governance_agent_forward(vote_input) if is_hoodi_testnet else agent_forward(vote_input))]
    vote_desc_items = ["Add MEV-Boost relay"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    vote_tx = helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
    )

    if is_hoodi_testnet:
        # Execute the proposal
        helpers.execute_dg_proposal(vote_tx.events["ProposalSubmitted"][1]["proposalId"])

    relays_after = mev_boost_allowed_list.get_relays()

    assert mev_boost_relay in relays_after
    assert len(relays_after) == len(relays) + 1, "Wrong allowed list length"


def check_and_remove_mev_boost_relay_with_voting(
    mev_boost_allowed_list, mev_boost_relay, helpers, ldo_holder, dao_voting
):
    relays = mev_boost_allowed_list.get_relays()

    assert mev_boost_relay in relays

    # Remove MEV-Boost relay with voting
    call_script_items = [
        agent_forward(
            [
                (
                    mev_boost_allowed_list.address,
                    mev_boost_allowed_list.remove_relay.encode_input(mev_boost_relay),
                )
            ]
        )
    ]
    vote_desc_items = ["Remove MEV-Boost relay"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    vote_tx = helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
    )

    relays_after = mev_boost_allowed_list.get_relays()

    assert mev_boost_relay not in relays_after
    assert len(relays_after) == len(relays) - 1, "Wrong allowed list length"


def create_and_enact_add_mev_boost_relay_motion(
    easy_track,
    trusted_caller,
    mev_boost_allowed_list,
    factory,
    stranger,
    helpers,
    ldo_holder,
    dao_voting,
):
    relays = mev_boost_allowed_list.get_relays()

    # Check if there is enough space in the list, if not, remove the first relay
    if len(relays) >= MEV_BOOST_ALLOWED_LIST_MAX_RELAY_COUNT:
        check_and_remove_mev_boost_relay_with_voting(mev_boost_allowed_list, relays[0], helpers, ldo_holder, dao_voting)

    relays_count = len(relays)
    assert TEST_RELAY not in relays

    calldata = "0x" + encode(["(string,string,bool,string)[]"], [[TEST_RELAY]]).hex()

    create_and_enact_motion(easy_track, trusted_caller, factory, calldata, stranger)

    assert len(mev_boost_allowed_list.get_relays()) == relays_count + 1
    assert TEST_RELAY in mev_boost_allowed_list.get_relays()


def create_and_enact_remove_mev_boost_relay_motion(
    easy_track,
    trusted_caller,
    mev_boost_allowed_list,
    factory,
    stranger,
    helpers,
    ldo_holder,
    dao_voting,
):
    relay_uri = TEST_RELAY[0]

    # If relay is not in the list, add it first, or else the motion will fail
    if relay_uri not in [x[0] for x in mev_boost_allowed_list.get_relays()]:
        check_and_add_mev_boost_relay_with_voting(mev_boost_allowed_list, TEST_RELAY, helpers, ldo_holder, dao_voting)
    
    # get the list of relays before the motion
    relays_before = mev_boost_allowed_list.get_relays()
    calldata = "0x" + encode(["string[]"], [[relay_uri]]).hex()

    create_and_enact_motion(easy_track, trusted_caller, factory, calldata, stranger)

    relays_after = mev_boost_allowed_list.get_relays()

    # Check if the relay is not present in the list after the motion
    assert len(relays_after) ==  len(relays_before) - 1
    assert relay_uri not in relays_after


def create_and_enact_edit_mev_boost_relay_motion(
    easy_track,
    trusted_caller,
    mev_boost_allowed_list,
    factory,
    stranger,
    helpers,
    ldo_holder,
    dao_voting,
):
    # If relay is not in the list, add it first, or else the motion will fail
    if TEST_RELAY[0] not in [x[0] for x in mev_boost_allowed_list.get_relays()]:
        check_and_add_mev_boost_relay_with_voting(mev_boost_allowed_list, TEST_RELAY, helpers, ldo_holder, dao_voting)

    new_operator = TEST_RELAY[1] + " new value"

    relays_before = mev_boost_allowed_list.get_relays()
    relay = (TEST_RELAY[0], new_operator, TEST_RELAY[2], TEST_RELAY[3])

    assert relay not in relays_before
    assert relay[1] != TEST_RELAY[1]

    calldata = "0x" + encode(["(string,string,bool,string)[]"], [[relay]]).hex()

    create_and_enact_motion(easy_track, trusted_caller, factory, calldata, stranger)

    relays_after = mev_boost_allowed_list.get_relays()

    assert len(relays_after) == len(relays_before)
    assert relay in relays_after

    # Last sanity check that relay is updated 
    relay_from_list = mev_boost_allowed_list.get_relay_by_uri(relay[0])
    assert relay_from_list[0] == relay[0]
    assert relay_from_list[1] == new_operator
