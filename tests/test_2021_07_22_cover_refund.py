from scripts.vote_2021_07_22_cover_refund import (start_vote)

def test_set_operators_limit(ldo_holder, helpers, accounts, dao_voting):

    refund_address = '0xD089cc83f5B803993E266ACEB929e52A993Ca2C8'
    refund_acc = accounts.at(refund_address, force=True)
    refund_balance_before = refund_acc.balance()

    (vote_id, _) = start_vote({"from": ldo_holder}, silent=True)
    print(f'Vote {vote_id} created')
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting)
    print(f'Vote {vote_id} executed')

    refund_balance_after = refund_acc.balance()

    assert refund_balance_after - refund_balance_before == 79837990169609360000
