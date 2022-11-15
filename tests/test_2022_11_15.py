"""
Tests for voting 15/11/2022.
"""
from scripts.vote_2022_11_15 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    Payout,
    validate_token_payout_event,
)
from brownie.network.transaction import TransactionReceipt
from brownie import interface


dao_agent_address = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
lido_dao_token = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"
dai_token_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"

rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
pool_maintenance_labs_address = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
argo_technology_consulting_address = "0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956"

pool_maintenance_labs_dai_payout = Payout(
    token_addr=dai_token_address,
    from_addr=dao_agent_address,
    to_addr=pool_maintenance_labs_address,
    amount=1_500_000 * (10**18),
)

pool_maintenance_labs_ldo_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=pool_maintenance_labs_address,
    amount=220_000 * (10**18),
)

argo_technology_consulting_dai_payout = Payout(
    token_addr=dai_token_address,
    from_addr=dao_agent_address,
    to_addr=argo_technology_consulting_address,
    amount=500_000 * (10**18),
)

rcc_dai_payout = Payout(
    token_addr=dai_token_address,
    from_addr=dao_agent_address,
    to_addr=rcc_multisig_address,
    amount=250_000 * (10**18),
)

rcc_ldo_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=rcc_multisig_address,
    amount=177_726 * (10**18),
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
):
    dai_token = interface.ERC20(dai_token_address)

    agent_eth_before = dao_agent.balance()
    agent_dai_before = dai_token.balanceOf(dao_agent.address)
    agent_ldo_before = ldo_token.balanceOf(dao_agent.address)

    pool_maintenance_labs_dai_before = dai_token.balanceOf(pool_maintenance_labs_address)
    pool_maintenance_labs_ldo_before = ldo_token.balanceOf(pool_maintenance_labs_address)
    argo_technology_consulting_dai_before = dai_token.balanceOf(argo_technology_consulting_address)
    rcc_dai_before = dai_token.balanceOf(rcc_multisig_address)
    rcc_ldo_before = ldo_token.balanceOf(rcc_multisig_address)

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert count_vote_items_by_events(tx, dao_voting) == 5, "Incorrect voting items count"

    # Check no unexpected balance changes
    assert dao_agent.balance() == agent_eth_before, "DAO Agent ETH balance must remain the same"

    # Check DAI payments
    assert (
        dai_token.balanceOf(pool_maintenance_labs_address)
        == pool_maintenance_labs_dai_before + pool_maintenance_labs_dai_payout.amount
    ), "DAI balance of Pool Maintenance Labs must increase by the correct amount"
    assert (
        dai_token.balanceOf(argo_technology_consulting_address)
        == argo_technology_consulting_dai_before + argo_technology_consulting_dai_payout.amount
    ), "DAI balance of Pool Maintenance Labs must increase by the correct amount"
    assert (
        dai_token.balanceOf(rcc_multisig_address) == rcc_dai_before + rcc_dai_payout.amount
    ), "DAI balance of RCC multisig must increase by the correct amount"
    assert (
        dai_token.balanceOf(dao_agent.address)
        == agent_dai_before
        - pool_maintenance_labs_dai_payout.amount
        - argo_technology_consulting_dai_payout.amount
        - rcc_dai_payout.amount
    ), "DAI balance of DAO Agent must decrease by the correct amount"

    # Check LDO payment
    assert (
        ldo_token.balanceOf(pool_maintenance_labs_address)
        == pool_maintenance_labs_ldo_before + pool_maintenance_labs_ldo_payout.amount
    ), "LDO balance of RCC multisig must increase bye the correct amount"
    assert (
        ldo_token.balanceOf(rcc_multisig_address) == rcc_ldo_before + rcc_ldo_payout.amount
    ), "LDO balance of RCC multisig must increase bye the correct amount"
    assert (
        ldo_token.balanceOf(dao_agent.address)
        == agent_ldo_before - pool_maintenance_labs_ldo_payout.amount - rcc_ldo_payout.amount
    ), "LDO balance of DAO Agent must decrease by the correct amount"

    # Check events if their decoding is available
    if bypass_events_decoding:
        return

    display_voting_events(tx)

    evs = group_voting_events(tx)
    validate_token_payout_event(evs[0], pool_maintenance_labs_dai_payout)
    validate_token_payout_event(evs[1], pool_maintenance_labs_ldo_payout)
    validate_token_payout_event(evs[2], argo_technology_consulting_dai_payout)
    validate_token_payout_event(evs[3], rcc_dai_payout)
    validate_token_payout_event(evs[4], rcc_ldo_payout)
