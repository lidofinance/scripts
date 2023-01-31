"""
Tests for voting 31/01/2023.
"""

from scripts.vote_2023_01_31 import start_vote

from brownie import chain, accounts
from brownie.network.transaction import TransactionReceipt

from eth_abi.abi import encode_single

from utils.config import network_name
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.easy_track import create_permissions
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items

eth = "0x0000000000000000000000000000000000000000"


def test_vote(
    helpers,
    accounts,
    vote_id_from_env,
    bypass_events_decoding,
    unknown_person,
    interface,
    ldo_holder,
):

    dai_token = interface.ERC20("0x6B175474E89094C44Da98b954EedeAC495271d0F")

    allowed_recipients = [
        accounts.at("0xaf8aE6955d07776aB690e565Ba6Fbc79B8dE3a5d", {"force": True}),
        accounts.at("0x558247e365be655f9144e1a0140D793984372Ef3", {"force": True}),
        accounts.at("0x53773E034d9784153471813dacAFF53dBBB78E8c", {"force": True}),
        accounts.at("0xC976903918A0AF01366B31d97234C524130fc8B1", {"force": True}),
        accounts.at("0x9e2b6378ee8ad2A4A95Fe481d63CAba8FB0EBBF9", {"force": True}),
        accounts.at("0x82AF9d2Ea81810582657f6DC04B1d7d0D573F616", {"force": True}),
        accounts.at("0x586b9b2F8010b284A0197f392156f1A7Eb5e86e9", {"force": True}),
        accounts.at("0x883f91D6F3090EA26E96211423905F160A9CA01d", {"force": True}),
        accounts.at("0x351806B55e93A8Bcb47Be3ACAF71584deDEaB324", {"force": True}),
        accounts.at("0xf6502Ea7E9B341702609730583F2BcAB3c1dC041", {"force": True}),
        accounts.at("0xDB2364dD1b1A733A690Bf6fA44d7Dd48ad6707Cd", {"force": True}),
        accounts.at("0xF930EBBd05eF8b25B1797b9b2109DDC9B0d43063", {"force": True}),
        accounts.at("0x6DC9657C2D90D57cADfFB64239242d06e6103E43", {"force": True}),
        accounts.at("0x13C6eF8d45aFBCcF15ec0701567cC9fAD2b63CE8", {"force": True}),
    ]

    finance = interface.Finance("0xB9E5CBB9CA5b0d659238807E84D0176930753d86")
    dao_voting = interface.Voting("0x2e59A20f205bB85a89C53f1936454680651E618e")
    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")

    referral_dai_registry = interface.AllowedRecipientRegistry("0xa295C212B44a48D07746d70d32Aa6Ca9b09Fb846")
    referral_dai_topup_factory = interface.TopUpAllowedRecipients("0x009ffa22ce4388d2F5De128Ca8E6fD229A312450")
    referral_dai_add_recipient_factory = interface.AddAllowedRecipient("0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151")
    referral_dai_remove_recipient_factory = interface.RemoveAllowedRecipient("0xd8f9B72Cd97388f23814ECF429cd18815F6352c1")
    referral_program_multisig = accounts.at("0xe2A682A9722354D825d1BbDF372cC86B2ea82c8C", {"force": True})

    rewards_topup_factory_old = interface.IEVMScriptFactory("0x77781A93C4824d2299a38AC8bBB11eb3cd6Bc3B7")
    rewards_add_factory_old = interface.IEVMScriptFactory("0x9D15032b91d01d5c1D940eb919461426AB0dD4e3")
    rewards_remove_factory_old = interface.IEVMScriptFactory("0xc21e5e72Ffc223f02fC410aAedE3084a63963932")

    gas_funder_eth_registry = interface.AllowedRecipientRegistry("0xCf46c4c7f936dF6aE12091ADB9897E3F2363f16F")
    gas_funder_eth_topup_factory = interface.TopUpAllowedRecipients("0x41F9daC5F89092dD6061E59578A2611849317dc8")
    gas_funder_multisig = accounts.at("0x5181d5D56Af4f823b96FE05f062D7a09761a5a53", {"force": True})

    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 15

    assert referral_dai_topup_factory not in old_factories_list
    assert referral_dai_add_recipient_factory not in old_factories_list
    assert referral_dai_remove_recipient_factory not in old_factories_list

    assert rewards_topup_factory_old in old_factories_list
    assert rewards_add_factory_old in old_factories_list
    assert rewards_remove_factory_old in old_factories_list

    assert gas_funder_eth_topup_factory not in old_factories_list

    ##
    ## START VOTE
    ##

    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 16

    # 1. Add Referral program DAI top up EVM script factory 0x009ffa22ce4388d2F5De128Ca8E6fD229A312450 to Easy Track
    assert referral_dai_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        referral_program_multisig,
        referral_dai_topup_factory,
        dai_token,
        allowed_recipients,
        [10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18,10 * 10**18, 10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(referral_dai_registry, helpers, ldo_holder, dao_voting)

    # 2. Add Referral program DAI add recipient EVM script factory 0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151 to Easy Track
    assert referral_dai_add_recipient_factory in updated_factories_list
    create_and_enact_add_recipient_motion(
        easy_track,
        referral_program_multisig,
        referral_dai_registry,
        referral_dai_add_recipient_factory,
        unknown_person,
        "",
        ldo_holder,
    )

    # 3. Add Referral program DAI remove recipient EVM script factory 0xd8f9B72Cd97388f23814ECF429cd18815F6352c1 to Easy Track
    assert referral_dai_remove_recipient_factory in updated_factories_list
    create_and_enact_remove_recipient_motion(
        easy_track,
        referral_program_multisig,
        referral_dai_registry,
        referral_dai_remove_recipient_factory,
        unknown_person,
        ldo_holder,
    )

    # 4. Remove reWARDS top up EVM script factory (old ver) 0x77781A93C4824d2299a38AC8bBB11eb3cd6Bc3B7 from Easy Track
    assert rewards_topup_factory_old not in updated_factories_list

    # 5. Remove reWARDS add recipient EVM script factory (old ver) 0x9D15032b91d01d5c1D940eb919461426AB0dD4e3 from Easy Track
    assert rewards_add_factory_old not in updated_factories_list

    # 6. Remove reWARDS remove recipient EVM script factory (old ver) 0xc21e5e72Ffc223f02fC410aAedE3084a63963932 from Easy Track
    assert rewards_remove_factory_old not in updated_factories_list

    # 7. Add Gas Funder ETH top up EVM script factory 0x41F9daC5F89092dD6061E59578A2611849317dc8 to Easy Track
    assert gas_funder_eth_topup_factory in updated_factories_list
    '''create_and_enact_payment_motion(
        easy_track,
        gas_funder_multisig,
        gas_funder_eth_topup_factory,
        eth,
        [gas_funder_multisig],
        [10 * 10**18],
        unknown_person,
    )
    '''
    check_add_and_remove_recipient_with_voting(gas_funder_eth_registry, helpers, ldo_holder, dao_voting)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 7, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=referral_dai_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(referral_dai_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[1],
        EVMScriptFactoryAdded(
            factory_addr=referral_dai_add_recipient_factory,
            permissions=create_permissions(referral_dai_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[2],
        EVMScriptFactoryAdded(
            factory_addr=referral_dai_remove_recipient_factory,
            permissions=create_permissions(referral_dai_registry, "removeRecipient"),
        ),
    )
    validate_evmscript_factory_removed_event(evs[3], rewards_topup_factory_old)
    validate_evmscript_factory_removed_event(evs[4], rewards_add_factory_old)
    validate_evmscript_factory_removed_event(evs[5], rewards_remove_factory_old)



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

    recievers_balance_after = [balance_of(reciever, token)for reciever in recievers]
    for i in range(len(recievers)):
        assert recievers_balance_after[i] == recievers_balance_before[i] + transfer_amounts[i]

    agent_balance_after = balance_of(agent, token)

    assert agent_balance_after == agent_balance_before - sum(transfer_amounts)


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
