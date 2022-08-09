"""
Tests for voting 09/08/2022.
"""
from scripts.vote_2022_08_09 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import Payout, validate_token_payout_event
from brownie import interface, chain, reverts
from brownie.network.transaction import TransactionReceipt


eth_amount: int = 663 * 10 ** 18

rcc_multisig_address = '0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437'
dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'

lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

rcc_ldo_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=rcc_multisig_address,
    amount=67_017.32 * (10 ** 18)
)


def test_vote(helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, bypass_events_decoding, ldo_token, dao_agent, lido):
    rcc_multisig = accounts.at(rcc_multisig_address, force=True)

    rcc_eth_before = rcc_multisig.balance()
    agent_eth_before = dao_agent.balance()
    rcc_ldo_before = ldo_token.balanceOf(rcc_multisig_address)
    agent_ldo_before = ldo_token.balanceOf(dao_agent.address)

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"


    # 1. Check ETH transfer
    assert rcc_eth_before == rcc_multisig.balance() + eth_amount
    assert agent_eth_before == dao_agent.balance() - eth_amount

    # 2. Check LDO payout
    assert ldo_token.balanceOf(rcc_multisig_address) == rcc_ldo_before + rcc_ldo_payout.amount,\
        "Incorrect LDO amount on RCC multisig"
    assert ldo_token.balanceOf(dao_agent.address) == agent_ldo_before - rcc_ldo_payout.amount,\
        "Incorrect LDO amount on DAO Agent"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # TODO: validate eth transfer events
    validate_token_payout_event(evs[1], rcc_ldo_payout)