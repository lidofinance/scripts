"""
Tests for voting 12/04/2022.
"""

from event_validators.payout import Payout, validate_payout_event

from utils.finance import ZERO_ADDRESS
from scripts.vote_2022_04_12 import start_vote
from tx_tracing_helpers import *

finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
depositor_multisig_address = '0x5181d5D56Af4f823b96FE05f062D7a09761a5a53'
dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'

refund_payout = Payout(
    token_addr=ZERO_ADDRESS,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=254_684_812_629_886_507_249
)

fund_payout = Payout(
    token_addr=ZERO_ADDRESS,
    from_addr=dao_agent_address,
    to_addr=depositor_multisig_address,
    amount=130 * (10 ** 18)
)

def test_2022_04_12(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding
):
    finance_multisig_account = accounts.at(finance_multisig_address, force=True)
    depositor_multisig_account = accounts.at(depositor_multisig_address, force=True)
    dao_agent_account = accounts.at(dao_agent_address, force=True)

    finance_multisig_balance_before = finance_multisig_account.balance()
    depositor_multisig_balance_before = depositor_multisig_account.balance()
    dao_balance_before = dao_agent_account.balance()

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    finance_multisig_balance_after = finance_multisig_account.balance()
    depositor_multisig_balance_after = depositor_multisig_account.balance()
    dao_balance_after = dao_agent_account.balance()

    assert finance_multisig_balance_after - finance_multisig_balance_before == refund_payout.amount
    assert depositor_multisig_balance_after - depositor_multisig_balance_before == fund_payout.amount
    assert dao_balance_after - dao_balance_before == refund_payout.amount + fund_payout.amount

    ### validate vote events
    assert count_vote_items_by_events(tx) == 2, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_payout_event(evs[0], refund_payout)

    # asserts on vote item 2
    validate_payout_event(evs[1], fund_payout)
