"""
Tests for voting 25/10/2022.
"""
from scripts.vote_2022_10_25 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    Payout,
    validate_token_payout_event,
    validate_agent_execute_ether_wrap_event,
)
from utils.finance import ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt
from brownie import interface


dao_agent_address = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
lido_dao_token = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"
weth_token = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
dai_token_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"

rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
bloxroute_address = "0xea48ba2edefae9e4ddd43ea565aa8b9aa22baf08"

rcc_dai_payout = Payout(
    token_addr=dai_token_address,
    from_addr=dao_agent_address,
    to_addr=rcc_multisig_address,
    amount=732_710 * (10**18),
)

rcc_ldo_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=rcc_multisig_address,
    amount=50_311 * (10**18),
)

bloxroute_weth_payout = Payout(
    token_addr=weth_token,
    from_addr=dao_agent_address,
    to_addr=bloxroute_address,
    amount=11 * (10**18),
)

eth_wrap_deposit = Payout(
    token_addr=ZERO_ADDRESS,
    from_addr=dao_agent_address,
    to_addr=weth_token,
    amount=bloxroute_weth_payout.amount,
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
    dai_token = interface.ERC20(dai_token_address)
    rcc_multisig = accounts.at(rcc_multisig_address, force=True)
    bloxroute = accounts.at(bloxroute_address, force=True)

    agent_eth_before = dao_agent.balance()
    agent_dai_before = dai_token.balanceOf(dao_agent.address)
    agent_weth_before = weth_token.balanceOf(dao_agent.address)
    agent_ldo_before = ldo_token.balanceOf(dao_agent.address)

    rcc_eth_before = rcc_multisig.balance()
    rcc_dai_before = dai_token.balanceOf(rcc_multisig_address)
    rcc_ldo_before = ldo_token.balanceOf(rcc_multisig_address)
    bloxroute_weth_before = weth_token.balanceOf(bloxroute_address)
    bloxroute_eth_before = bloxroute.balance()

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert count_vote_items_by_events(tx, dao_voting) == 4, "Incorrect voting items count"

    # Check no unexpected balance changes
    assert rcc_multisig.balance() == rcc_eth_before, "RCC multisig ETH balance must remain the same"
    assert bloxroute.balance() == bloxroute_eth_before, "bloXroute ETH balance must remain the same"
    assert weth_token.balanceOf(dao_agent.address) == agent_weth_before, "Agent WETH amount must remain the same"

    # Check DAI payment
    assert (
        dai_token.balanceOf(rcc_multisig_address) == rcc_dai_before + rcc_dai_payout.amount
    ), "DAI balance of RCC multisig must increase by the correct amount"
    assert (
        dai_token.balanceOf(dao_agent.address) == agent_dai_before - rcc_dai_payout.amount
    ), "DAI balance of DAO Agent must decrease by the correct amount"

    # Check LDO payment
    assert (
        ldo_token.balanceOf(rcc_multisig_address) == rcc_ldo_before + rcc_ldo_payout.amount
    ), "LDO balance of RCC multisig must increase bye the correct amount"
    assert (
        ldo_token.balanceOf(dao_agent.address) == agent_ldo_before - rcc_ldo_payout.amount
    ), "LDO balance of DAO Agent must decrease by the correct amount"

    # Check ETH/WETH payment
    assert (
        weth_token.balanceOf(bloxroute_address) == bloxroute_weth_before + bloxroute_weth_payout.amount
    ), "WETH balance of bloXroute address must increase by the correct amount"
    assert (
        dao_agent.balance() == agent_eth_before - bloxroute_weth_payout.amount
    ), "Agent ETH balance must decrease by the correct amount"

    # Check events if their decoding is available
    if bypass_events_decoding:
        return

    display_voting_events(tx)

    evs = group_voting_events(tx)
    validate_token_payout_event(evs[0], rcc_dai_payout)
    validate_token_payout_event(evs[1], rcc_ldo_payout)
    validate_agent_execute_ether_wrap_event(evs[2], eth_wrap_deposit)
    validate_token_payout_event(evs[3], bloxroute_weth_payout)
