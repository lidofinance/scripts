"""
Tests for voting 20/06/2023.

!! goerli only
"""
from archive.scripts.vote_2023_06_20_goerli import start_vote

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
    if not network_name() in ("goerli", "goerli-fork"):
        return

    stETH_token = interface.ERC20("0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F")

    finance = contracts.finance
    dao_voting = contracts.voting
    easy_track = contracts.easy_track

    gas_supply_topup_factory = interface.TopUpAllowedRecipients("0x960CcA0BE6419e9684796Ce3ABE980E8a2d0cd80")
    gas_supply_add_recipient_factory = interface.AddAllowedRecipient("0xa2286d37Af8F8e84428151bF72922c5Fe5c1EeED")
    gas_supply_remove_recipient_factory = interface.RemoveAllowedRecipient("0x48D01979eD9e6CE70a6496B111F5728f9a547C96")
    gas_supply_registry = interface.AllowedRecipientRegistry("0xF08a5f00824D4554a1FBebaE726609418dc819fb")
    gas_supply_multisig = accounts.at("0xc4094c015666CBC093FffDC9BB3CF077a864ddB3", {"force": True})

    reWARDs_topup_factory = interface.TopUpAllowedRecipients("0x8180949ac41EF18e844ff8dafE604a195d86Aea9")
    reWARDs_add_recipient_factory = interface.AddAllowedRecipient("0x5560d40b00EA3a64E9431f97B3c79b04e0cdF6F2")
    reWARDs_remove_recipient_factory = interface.RemoveAllowedRecipient("0x31B68d81125E52fE1aDfe4076F8945D1014753b5")

    referral_LDO_topup_factory = interface.TopUpAllowedRecipients("0xB1E898faC74c377bEF16712Ba1CD4738606c19Ee")
    referral_LDO_add_recipient_factory = interface.AddAllowedRecipient("0xe54ca3e867C52a34d262E94606C7A9371AB820c9")
    referral_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0x2A0c343087c6cFB721fFa20608A6eD0473C71275")

    referral_DAI_topup_factory = interface.TopUpAllowedRecipients("0x9534A77029D57E249c467E5A1E0854cc26Cd75A0")
    referral_DAI_add_recipient_factory = interface.AddAllowedRecipient("0x734458219BE229F6631F083ea574EBACa2f9bEaf")
    referral_DAI_remove_recipient_factory = interface.RemoveAllowedRecipient("0x5FEC0bcd7519C4fE41eca5Fe1dD94345fA100A67")

    reWARDs_LDO_topup_factory = interface.TopUpAllowedRecipients("0xD928dC9E4DaBeE939d3237A4f41983Ff5B6308dB")
    reWARDs_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x3Ef70849FdBEe7b1F0A43179A3f788A8949b8abe")
    reWARDs_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0x6c2e12D9C1d6e3dE146A7519eCbcb79c96Fe3146")

    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 27

    assert gas_supply_topup_factory not in old_factories_list
    assert gas_supply_add_recipient_factory not in old_factories_list
    assert gas_supply_remove_recipient_factory not in old_factories_list

    assert reWARDs_topup_factory in old_factories_list
    assert reWARDs_add_recipient_factory in old_factories_list
    assert reWARDs_remove_recipient_factory in old_factories_list

    assert referral_LDO_topup_factory in old_factories_list
    assert referral_LDO_add_recipient_factory in old_factories_list
    assert referral_LDO_remove_recipient_factory in old_factories_list

    assert referral_DAI_topup_factory in old_factories_list
    assert referral_DAI_add_recipient_factory in old_factories_list
    assert referral_DAI_remove_recipient_factory in old_factories_list

    assert reWARDs_LDO_topup_factory in old_factories_list
    assert reWARDs_LDO_add_recipient_factory in old_factories_list
    assert reWARDs_LDO_remove_recipient_factory in old_factories_list

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 18

    # 1.
    assert gas_supply_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        gas_supply_multisig,
        gas_supply_topup_factory,
        stETH_token,
        [
            accounts.at("0xc4094c015666CBC093FffDC9BB3CF077a864ddB3", {"force": True}),
        ],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(gas_supply_registry, helpers, ldo_holder, dao_voting)

    # 2.
    assert gas_supply_add_recipient_factory in updated_factories_list
    create_and_enact_add_recipient_motion(
        easy_track,
        gas_supply_multisig,
        gas_supply_registry,
        gas_supply_add_recipient_factory,
        stranger,
        "New recipient",
        ldo_holder,
    )

    # 3.
    assert gas_supply_remove_recipient_factory in updated_factories_list
    create_and_enact_remove_recipient_motion(
        easy_track,
        gas_supply_multisig,
        gas_supply_registry,
        gas_supply_remove_recipient_factory,
        stranger,
        ldo_holder,
    )

    # 4-15
    assert reWARDs_topup_factory not in updated_factories_list
    assert reWARDs_add_recipient_factory not in updated_factories_list
    assert reWARDs_remove_recipient_factory not in updated_factories_list

    assert referral_LDO_topup_factory not in updated_factories_list
    assert referral_LDO_add_recipient_factory not in updated_factories_list
    assert referral_LDO_remove_recipient_factory not in updated_factories_list

    assert referral_DAI_topup_factory not in updated_factories_list
    assert referral_DAI_add_recipient_factory not in updated_factories_list
    assert referral_DAI_remove_recipient_factory not in updated_factories_list

    assert reWARDs_LDO_topup_factory not in updated_factories_list
    assert reWARDs_LDO_add_recipient_factory not in updated_factories_list
    assert reWARDs_LDO_remove_recipient_factory not in updated_factories_list

    # validate vote events
    assert count_vote_items_by_events(vote_tx, dao_voting) == 15, "Incorrect voting items count"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=gas_supply_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(gas_supply_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[1],
        EVMScriptFactoryAdded(
            factory_addr=gas_supply_add_recipient_factory,
            permissions=create_permissions(gas_supply_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[2],
        EVMScriptFactoryAdded(
            factory_addr=gas_supply_remove_recipient_factory,
            permissions=create_permissions(gas_supply_registry, "removeRecipient"),
        ),
    )
    validate_evmscript_factory_removed_event(evs[3], reWARDs_topup_factory)
    validate_evmscript_factory_removed_event(evs[4], reWARDs_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[5], reWARDs_remove_recipient_factory)

    validate_evmscript_factory_removed_event(evs[6], referral_LDO_topup_factory)
    validate_evmscript_factory_removed_event(evs[7], referral_LDO_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[8], referral_LDO_remove_recipient_factory)

    validate_evmscript_factory_removed_event(evs[9], referral_DAI_topup_factory)
    validate_evmscript_factory_removed_event(evs[10], referral_DAI_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[11], referral_DAI_remove_recipient_factory)

    validate_evmscript_factory_removed_event(evs[12], reWARDs_LDO_topup_factory)
    validate_evmscript_factory_removed_event(evs[13], reWARDs_LDO_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[14], reWARDs_LDO_remove_recipient_factory)



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
    agent = contracts.agent
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
