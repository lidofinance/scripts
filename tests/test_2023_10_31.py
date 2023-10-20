"""
Tests for voting 31/10/2023

"""
from scripts.vote_2023_10_31 import start_vote

from eth_abi.abi import encode_single
from brownie import chain, accounts

from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.easy_track import create_permissions
from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    validate_evmscript_factory_removed_event,
    EVMScriptFactoryAdded
)

eth = "0x0000000000000000000000000000000000000000"
aragonAgentProxy = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"

def test_vote(
    helpers,
    accounts,
    interface,
    vote_ids_from_env,
    stranger
):
    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")
    dao_voting = interface.Voting("0x2e59A20f205bB85a89C53f1936454680651E618e")
    dai_token = interface.ERC20("0x6B175474E89094C44Da98b954EedeAC495271d0F")

    rcc_trusted_caller_and_recepient = accounts.at("0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437", {"force": True})
    pml_trusted_caller_and_recepient = accounts.at("0x17F6b2C738a63a8D3A113a228cfd0b373244633D", {"force": True})
    atc_trusted_caller_and_recepient = accounts.at("0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956", {"force": True})

    rcc_dai_topup_factory_old = interface.IEVMScriptFactory("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_dai_topup_factory_old = interface.IEVMScriptFactory("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_dai_topup_factory_old = interface.IEVMScriptFactory("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    # todo: change addresses
    rcc_stable_topup_factory = interface.TopUpAllowedRecipients("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_stable_topup_factory = interface.TopUpAllowedRecipients("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_stable_topup_factory = interface.TopUpAllowedRecipients("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    # todo: change addresses
    rcc_stable_registry = interface.AllowedRecipientRegistry("0xDc1A0C7849150f466F07d48b38eAA6cE99079f80")
    pml_stable_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    atc_stable_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")

    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 16

    # todo: uncomment when u get new factories address
    # assert rcc_stable_topup_factory not in old_factories_list
    # assert pml_stable_topup_factory not in old_factories_list
    # assert atc_stable_topup_factory not in old_factories_list

    assert rcc_dai_topup_factory_old in old_factories_list
    assert pml_dai_topup_factory_old in old_factories_list
    assert atc_dai_topup_factory_old in old_factories_list

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 16

    ## todo: uncomment tests
    # 1. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
    # assert rcc_dai_topup_factory_old not in updated_factories_list
    # 2. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
    # assert pml_dai_topup_factory_old not in updated_factories_list
    # 3. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
    # assert atc_dai_topup_factory_old not in updated_factories_list

    # 4. Add RCC stable top up EVM script factory 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e to Easy Track
    assert rcc_stable_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        rcc_trusted_caller_and_recepient,
        rcc_stable_topup_factory,
        dai_token,
        [rcc_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(rcc_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, dao_voting)

    # 5. Add PML stable top up EVM script factory 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD to Easy Track
    assert pml_stable_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        pml_trusted_caller_and_recepient,
        pml_stable_topup_factory,
        dai_token,
        [pml_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(pml_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, dao_voting)

    # 6. Add ATC stable top up EVM script factory 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 to Easy Track
    assert atc_stable_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        atc_trusted_caller_and_recepient,
        atc_stable_topup_factory,
        dai_token,
        [atc_trusted_caller_and_recepient],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(atc_stable_registry, helpers, LDO_HOLDER_ADDRESS_FOR_TESTS, dao_voting)

    # validate vote events
    assert count_vote_items_by_events(vote_tx, dao_voting) == 6, "Incorrect voting items count"

    display_voting_events(vote_tx)

    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_removed_event(evs[0], rcc_dai_topup_factory_old)
    validate_evmscript_factory_removed_event(evs[1], pml_dai_topup_factory_old)
    validate_evmscript_factory_removed_event(evs[2], atc_dai_topup_factory_old)
    validate_evmscript_factory_added_event(
        evs[3],
        EVMScriptFactoryAdded(
            factory_addr=rcc_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rcc_stable_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[4],
        EVMScriptFactoryAdded(
            factory_addr=pml_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(pml_stable_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[5],
        EVMScriptFactoryAdded(
            factory_addr=atc_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(atc_stable_registry, "updateSpentAmount")[2:],
        ),
    )

# todo: move to utils
def create_and_enact_payment_motion(
    easy_track,
    trusted_caller,
    factory,
    token,
    recievers,
    transfer_amounts,
    stranger,
):
    agent = accounts.at(aragonAgentProxy, {"force": True})
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

def _encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()

def balance_of(address, token):
    if token == eth:
        return address.balance()
    else:
        return token.balanceOf(address)
    
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
