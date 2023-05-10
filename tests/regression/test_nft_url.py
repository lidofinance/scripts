import requests
from utils.test.helpers import ETH
from utils.config import contracts
from utils.test.oracle_report_helpers import oracle_report


def test_nft_url(steth_holder):
    contracts.lido.approve(contracts.withdrawal_queue.address, ETH(1), {"from": steth_holder})
    contracts.withdrawal_queue.requestWithdrawals([ETH(1)], steth_holder, {"from": steth_holder})

    id = contracts.withdrawal_queue.getWithdrawalRequests(steth_holder, {"from": steth_holder})[0]

    token_uri = contracts.withdrawal_queue.tokenURI(id)

    r = requests.get(token_uri)

    assert r.status_code == 200
    body = r.json()
    assert "name" in body
    assert "description" in body
    assert "image" in body

    """ report """
    report_tx = None
    # first oracle report, requests might not get finalized due to sanity check requestTimestampMargin depending on current fork time
    report_tx = oracle_report()[0]
    # second report requests will get finalized for sure
    if not report_tx.events.count("WithdrawalsFinalized") == 1:
        report_tx = oracle_report()[0]

    token_uri = contracts.withdrawal_queue.tokenURI(id)

    r = requests.get(token_uri)

    assert r.status_code == 200
    body = r.json()
    assert "name" in body
    assert "description" in body
    assert "image" in body
