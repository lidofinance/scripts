"""
Tests for voting 24/03/2022.
"""

from brownie import Contract, interface
from brownie.network import chain
from eth_abi import encode_single

from event_validators.payout import Payout, validate_payout_event
from event_validators.easy_track import EVMScriptFactoryAdded, validate_evmscript_factory_added_event

from scripts.vote_2022_03_24 import start_vote
from tx_tracing_helpers import *

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
hyperelliptic_rockx_multisig = '0x3A043ce95876683768D3D3FB80057be2ee3f2814'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

one_inch_reward_manager = "0xf5436129Cf9d8fa2a1cb6e591347155276550635"
tokens_recoverer = '0x1bdfFe0EBef3FEAdF2723D3330727D73f538959C'

factories_to_add_with_vote = [
    EVMScriptFactoryAdded(
        factory_addr='0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51',
        permissions=('0xfCaD241D9D2A2766979A2de208E8210eDf7b7D4F' + 'fa508cef')
    ),
    EVMScriptFactoryAdded(
        factory_addr='0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C',
        permissions=('0xfCaD241D9D2A2766979A2de208E8210eDf7b7D4F' + '945233e2')
    ),
    EVMScriptFactoryAdded(
        factory_addr='0x54058ee0E0c87Ad813C002262cD75B98A7F59218',
        permissions=('0xB9E5CBB9CA5b0d659238807E84D0176930753d86' + 'f6364846')
    )
]

hyperelliptic_rockx_comp = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=hyperelliptic_rockx_multisig,
    amount=350_000 * (10 ** 18)
)

def test_2022_03_24(
    helpers, accounts, ldo_holder, dao_voting, ldo_token,
    vote_id_from_env, bypass_events_decoding, easy_track
):
    dao_balance_before = ldo_token.balanceOf(dao_agent_address)
    hr_multisig_balance_before = ldo_token.balanceOf(hyperelliptic_rockx_multisig)
    rewards_manager_balance_before = ldo_token.balanceOf(one_inch_reward_manager)

    # if rewards manager has no tokens transfer it from ldo_holder
    if rewards_manager_balance_before == 0:
        ldo_token.transfer(one_inch_reward_manager, 1 * 10 ** 18, {"from": ldo_holder})
    rewards_manager_balance_before = ldo_token.balanceOf(one_inch_reward_manager)
    assert rewards_manager_balance_before > 0

    factories_before = easy_track.getEVMScriptFactories()

    for f in factories_to_add_with_vote:
        assert f.factory_addr not in factories_before

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    factories_after = easy_track.getEVMScriptFactories()

    rewards_manager_balance_after = ldo_token.balanceOf(one_inch_reward_manager)
    hr_multisig_balance_after = ldo_token.balanceOf(hyperelliptic_rockx_multisig)
    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    assert hr_multisig_balance_after - hr_multisig_balance_before == hyperelliptic_rockx_comp.amount
    assert rewards_manager_balance_after == 0

    assert dao_balance_before - dao_balance_after == \
        hyperelliptic_rockx_comp.amount + (rewards_manager_balance_after - rewards_manager_balance_before)

    for f in factories_to_add_with_vote:
        assert f.factory_addr in factories_after

    _check_factories_sanity(accounts[5], accounts[6], ldo_token, easy_track)

    ### validate vote events
    # assert count_vote_items_by_events(tx) == 6, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_evmscript_factory_added_event(evs[0], factories_to_add_with_vote[0])

    # asserts on vote item 2
    validate_evmscript_factory_added_event(evs[1], factories_to_add_with_vote[1])

    # asserts on vote item 3
    validate_evmscript_factory_added_event(evs[2], factories_to_add_with_vote[2])

    # asserts on vote item 4
    validate_payout_event(evs[3], hyperelliptic_rockx_comp)

def test_2022_03_24_zero_ldo_to_recover(
    helpers, accounts, ldo_holder, dao_voting, ldo_token,
    vote_id_from_env, bypass_events_decoding, easy_track,
    dao_agent
):
    assert dao_agent.address == dao_agent_address

    rewards_manager_balance_before = ldo_token.balanceOf(one_inch_reward_manager)
    rewards_manager = interface.RewardsManager(one_inch_reward_manager)
    dao_balance_before = ldo_token.balanceOf(dao_agent_address)

    # if rewards manager has no tokens transfer it from agent
    if rewards_manager_balance_before > 0:
        rewards_manager.recover_erc20(ldo_token, rewards_manager_balance_before, {"from": dao_agent})

    assert ldo_token.balanceOf(one_inch_reward_manager) == 0

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    rewards_manager_balance_after = ldo_token.balanceOf(one_inch_reward_manager)
    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    assert dao_balance_before - dao_balance_after == hyperelliptic_rockx_comp.amount - rewards_manager_balance_before
    assert rewards_manager_balance_after == 0


def _encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()

def _check_factories_sanity(
    reward_program_addr: str,
    stranger: str,
    ldo: Contract,
    easy_track: Contract
):
    reward_program = reward_program_addr
    reward_program_title = "Our Reward Program"

    add_reward_program = interface.AddRewardProgram(factories_to_add_with_vote[0].factory_addr)
    remove_reward_program = interface.RemoveRewardProgram(factories_to_add_with_vote[1].factory_addr)
    top_up_reward_programs = interface.TopUpRewardPrograms(factories_to_add_with_vote[2].factory_addr)

    reward_programs_registry = interface.RewardProgramsRegistry('0xfCaD241D9D2A2766979A2de208E8210eDf7b7D4F')
    trusted_address = '0xe2A682A9722354D825d1BbDF372cC86B2ea82c8C'

    add_reward_program_calldata = _encode_calldata(
        "(address,string)", [
            reward_program.address,
            reward_program_title
        ]
    )

    forked_motions = easy_track.getMotions()

    tx = easy_track.createMotion(
        add_reward_program,
        add_reward_program_calldata,
        {"from": trusted_address}
    )

    motions = easy_track.getMotions()
    assert len(motions) == len(forked_motions) + 1

    chain.sleep(72 * 60 * 60 + 100)

    easy_track.enactMotion(
        motions[len(motions) - 1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == len(forked_motions)

    reward_programs = reward_programs_registry.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == reward_program

    # create new motion to top up reward program
    tx = easy_track.createMotion(
        top_up_reward_programs,
        encode_single("(address[],uint256[])", [[reward_program.address], [int(5e18)]]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == len(forked_motions) + 1

    chain.sleep(72 * 60 * 60 + 100)

    assert ldo.balanceOf(reward_program) == 0

    easy_track.enactMotion(
        motions[len(motions) - 1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(easy_track.getMotions()) == len(forked_motions)
    assert ldo.balanceOf(reward_program) == 5e18

    # create new motion to remove a reward program
    tx = easy_track.createMotion(
        remove_reward_program,
        encode_single("(address)", [reward_program.address]),
        {"from": trusted_address},
    )

    motions = easy_track.getMotions()
    assert len(motions) == len(forked_motions) + 1

    chain.sleep(72 * 60 * 60 + 100)

    easy_track.enactMotion(
        motions[len(motions) - 1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == len(forked_motions)
    assert len(reward_programs_registry.getRewardPrograms()) == 0
