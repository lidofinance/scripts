"""
Tests for voting 16/08/2022.
"""
from scripts.vote_2022_08_16 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    Payout,
    validate_token_payout_event,
    validate_agent_execute_ether_wrap_event,
)
from utils.finance import ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt


dao_agent_address = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
lido_dao_token = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"
weth_token = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"

rcc_ldo_payout = Payout(
    token_addr=lido_dao_token, from_addr=dao_agent_address, to_addr=rcc_multisig_address, amount=67_017.32 * (10**18)
)

rcc_weth_payout = Payout(
    token_addr=weth_token, from_addr=dao_agent_address, to_addr=rcc_multisig_address, amount=620 * (10**18)
)

eth_wrap_deposit = Payout(
    token_addr=ZERO_ADDRESS, from_addr=dao_agent_address, to_addr=weth_token, amount=rcc_weth_payout.amount
)


def test_vote(
    helpers,
    accounts,
    ldo_holder,
    dao_voting,
    vote_id_from_env,
    bypass_events_decoding,
    ldo_token,
    dao_agent,
    weth_token,
):
    rcc_multisig = accounts.at(rcc_multisig_address, force=True)

    rcc_eth_before = rcc_multisig.balance()
    agent_eth_before = dao_agent.balance()

    rcc_weth_before = weth_token.balanceOf(rcc_multisig_address)
    agent_weth_before = weth_token.balanceOf(dao_agent.address)

    rcc_ldo_before = ldo_token.balanceOf(rcc_multisig_address)
    agent_ldo_before = ldo_token.balanceOf(dao_agent.address)

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert count_vote_items_by_events(tx, dao_voting) == 3, "Incorrect voting items count"

    assert rcc_multisig.balance() == rcc_eth_before, "RCC multisig ETH balance must remain the same"
    assert (
        dao_agent.balance() == agent_eth_before - rcc_weth_payout.amount
    ), "Agent ETH balance must decrease by the correct amount"

    assert (
        weth_token.balanceOf(rcc_multisig_address) == rcc_weth_before + rcc_weth_payout.amount
    ), "Incorrect WETH amount on RCC multisig"
    assert weth_token.balanceOf(dao_agent.address) == agent_weth_before, "Incorrect WETH amount on DAO Agent"

    assert (
        ldo_token.balanceOf(rcc_multisig_address) == rcc_ldo_before + rcc_ldo_payout.amount
    ), "Incorrect LDO amount on RCC multisig"
    assert (
        ldo_token.balanceOf(dao_agent.address) == agent_ldo_before - rcc_ldo_payout.amount
    ), "Incorrect LDO amount on DAO Agent"

    # Check events if their decoding is available
    if bypass_events_decoding:
        return

    display_voting_events(tx)

    evs = group_voting_events(tx)
    validate_agent_execute_ether_wrap_event(evs[0], eth_wrap_deposit)
    validate_token_payout_event(evs[1], rcc_weth_payout)
    validate_token_payout_event(evs[2], rcc_ldo_payout)
