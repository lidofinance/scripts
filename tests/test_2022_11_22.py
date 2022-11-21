"""
Tests for voting 22/11/2022.
"""

from brownie.network.transaction import TransactionReceipt
from scripts.vote_2022_11_22 import start_vote

from utils.test.event_validators.permission import (
    Permission,
)

from utils.test.event_validators.token_manager import (
    validate_ldo_vested_event,
    Issue,
    Vested,
)
from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_voting_events,
    group_voting_events,
)
from utils.test.event_validators.payout import validate_token_payout_event, Payout


lido_dao_token = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"
dao_agent_address = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
token_manager = "0xf73a1260d222f447210581DDf212D915c09a3249"


start: int = 1662249600  # Sun Sep 04 2022 00:00:00 +UTC
cliff: int = 1662249600  # Sun Sep 04 2022 00:00:00 +UTC
vesting: int = 1725408000  # Wed Sep 04 2024 00:00:00 +UTC

ldo_vesting_amount: int = 150_000 * 10**18
ldo_balance_change: int = ldo_vesting_amount * 2
destination_address_chorus: str = "0x3983083d7FA05f66B175f282FfD83E0d861C777A"
destination_address_p2p: str = "0xE22211Ba98213c866CC5DC8d7D9493b1e7EFD25A"

create_permission: Permission = Permission(
    entity="0x2e59A20f205bB85a89C53f1936454680651E618e",  # Voting
    app="0xf73a1260d222f447210581DDf212D915c09a3249",  # Token Manager
    role="0x2406f1e99f79cea012fb88c5c36566feaeefee0f4b98d3a376b49310222b53c4",  # keccak256('ISSUE_ROLE')
)

issue: Issue = Issue(token_manager_addr=create_permission.app, amount=ldo_balance_change)

vested_chorus: Vested = Vested(
    destination_addr=destination_address_chorus,
    amount=ldo_vesting_amount,
    start=start,
    cliff=cliff,
    vesting=vesting,
    revokable=False,
)

vested_p2p: Vested = Vested(
    destination_addr=destination_address_p2p,
    amount=ldo_vesting_amount,
    start=start,
    cliff=cliff,
    vesting=vesting,
    revokable=False,
)

token_manager_ldo_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=token_manager,
    amount=ldo_balance_change,
)


def test_2022_11_22(
    dao_agent,
    helpers,
    accounts,
    ldo_holder,
    dao_voting,
    ldo_token,
    dao_token_manager,
    vote_id_from_env,
    bypass_events_decoding,
):
    agent_ldo_before = ldo_token.balanceOf(dao_agent.address)
    destination_balance_before_chorus = ldo_token.balanceOf(destination_address_chorus)
    destination_balance_before_p2p = ldo_token.balanceOf(destination_address_p2p)
    token_manager_balance_before = ldo_token.balanceOf(dao_token_manager)

    vestings_before_chorus = dao_token_manager.vestingsLengths(destination_address_chorus)
    vestings_before_p2p = dao_token_manager.vestingsLengths(destination_address_p2p)

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )
    assert count_vote_items_by_events(tx, dao_voting) == 3, "Incorrect voting items count"

    agent_ldo_after = ldo_token.balanceOf(dao_agent.address)
    destination_balance_after_chorus = ldo_token.balanceOf(destination_address_chorus)
    destination_balance_after_p2p = ldo_token.balanceOf(destination_address_p2p)
    token_manager_balance_after = ldo_token.balanceOf(dao_token_manager)

    vestings_after_chours = dao_token_manager.vestingsLengths(destination_address_chorus)
    vestings_after_p2p = dao_token_manager.vestingsLengths(destination_address_p2p)

    assigned_vesting_chorus = dao_token_manager.getVesting(
        destination_address_chorus, vestings_before_chorus
    )
    assigned_vesting_p2p = dao_token_manager.getVesting(
        destination_address_p2p, vestings_before_p2p
    )

    assert assigned_vesting_chorus["amount"] == vested_chorus.amount
    assert assigned_vesting_chorus["start"] == vested_chorus.start
    assert assigned_vesting_chorus["cliff"] == vested_chorus.cliff
    assert assigned_vesting_chorus["vesting"] == vested_chorus.vesting
    assert assigned_vesting_chorus["revokable"] == vested_chorus.revokable

    assert assigned_vesting_p2p["amount"] == vested_p2p.amount
    assert assigned_vesting_p2p["start"] == vested_p2p.start
    assert assigned_vesting_p2p["cliff"] == vested_p2p.cliff
    assert assigned_vesting_p2p["vesting"] == vested_p2p.vesting
    assert assigned_vesting_p2p["revokable"] == vested_p2p.revokable

    assert (
        destination_balance_after_chorus == destination_balance_before_chorus + ldo_vesting_amount
    ), "Incorrect LDO amount"
    assert (
        destination_balance_after_p2p == destination_balance_before_p2p + ldo_vesting_amount
    ), "Incorrect LDO amount"

    assert agent_ldo_after + ldo_balance_change == agent_ldo_before
    assert token_manager_balance_before == token_manager_balance_after, "Incorrect LDO amount"

    assert vestings_after_chours == vestings_before_chorus + 1, "Incorrect vestings length"
    assert vestings_after_p2p == vestings_before_p2p + 1, "Incorrect vestings length"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    validate_token_payout_event(evs[0], token_manager_ldo_payout)
    validate_ldo_vested_event(evs[1], vested_chorus)
    validate_ldo_vested_event(evs[2], vested_p2p)
