"""
The acceptance tests for the “LIP-10: Proxy initializations and LidoOracle upgrade”
"""
import pytest
from brownie import reverts, ZERO_ADDRESS
from tx_tracing_helpers import *
from scripts.vote_2022_05_17 import start_vote
import json


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def another_stranger(accounts):
    return accounts[1]


@pytest.fixture(scope="module")
def deployer(accounts):
    return accounts[2]


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(deployer, vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):

    lido_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-lido-base.json'))["data"]
    nos_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-node-operators-registry-base.json'))["data"]
    oracle_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-oracle-base.json'))["data"]
    mev_vault_tx_data = json.load(open('./utils/txs/tx-26-deploy-mev-vault.json'))["data"]

    lido_tx = deployer.transfer(data=lido_tx_data)
    nos_tx = deployer.transfer(data=nos_tx_data)
    oracle_tx = deployer.transfer(data=oracle_tx_data)
    mev_vault_tx = deployer.transfer(data=mev_vault_tx_data)

    params = {
        'update_lido_app': {
            'version': (3, 0, 0),
            'new_address': lido_tx.contract_address,
            'id': '0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320',
            'content_uri': '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053',
            'mevtxfee_vault_address': mev_vault_tx.contract_address,
            'mevtxfee_withdrawal_limit': 2,
            'max_staking_limit': 150_000 * 10**18,
            'staking_limit_increase': 150_000 * 10**18 * 13.5 // (24 * 60 * 60),  # 13.5s per block as a rough average
        },
        'update_nos_app': {
            'version': (3, 0, 0),
            'new_address': nos_tx.contract_address,
            'id': '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d',
            'content_uri': '0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847'
        },
        'update_oracle_app': {
            'version': (3, 0, 0),
            'new_address': oracle_tx.contract_address,
            'id': '0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93',
            'content_uri': '0x697066733a516d514d64696979653134765966724a7753594250646e68656a446f62417877584b72524e45663438735370444d'
        },
    }

    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, params=params, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    pass


def test_transfer_shares(helpers, lido, stranger, another_stranger):
    stranger.transfer(lido, 10*10**18)

    shares_to_transfer = 10**18
    stranger_shares_before = lido.sharesOf(stranger)
    another_stranger_shares_before = lido.sharesOf(another_stranger)

    tx = lido.transferShares(another_stranger, shares_to_transfer, {"from": stranger})
    
    assert lido.sharesOf(stranger) == stranger_shares_before - shares_to_transfer
    assert lido.sharesOf(another_stranger) == another_stranger_shares_before + shares_to_transfer
    
    helpers.assert_single_event_named(
        "Transfer", 
        tx, 
        {"from": stranger, "to": another_stranger, "sharesValue": lido.getPooledEthByShares(shares_to_transfer)}
    )
    helpers.assert_single_event_named(
        "TransferShares", 
        tx, 
        {"from": stranger, "to": another_stranger, "sharesValue": shares_to_transfer}
    )



def test_transfer(helpers, lido, stranger, another_stranger):
    stranger.transfer(lido, 10*10**18)

    amount_to_transfer = 10**18
    stranger_balance_before = lido.balanceOf(stranger)
    another_stranger_balance_before = lido.balanceOf(another_stranger)

    tx = lido.transfer(another_stranger, amount_to_transfer, {"from": stranger})
    
    assert lido.balanceOf(stranger) == stranger_balance_before - amount_to_transfer + 1
    assert lido.balanceOf(another_stranger) == another_stranger_balance_before + amount_to_transfer - 1

    helpers.assert_single_event_named(
        "TransferShares", 
        tx, 
        {"from": stranger, "to": another_stranger, "sharesValue": lido.getSharesByPooledEth(amount_to_transfer)}
    )
    helpers.assert_single_event_named(
        "Transfer", 
        tx, 
        {"from": stranger, "to": another_stranger, "sharesValue": amount_to_transfer}
    )
   

def test_oracle_init_reverts(oracle, stranger):
    with reverts('WRONG_BASE_VERSION'):
        oracle.finalizeUpgrade_v3({"from": stranger})


def test_oracle_version(oracle):
    assert oracle.getVersion() == 3


def test_init_v3_reverts_after_deployment(oracle, stranger):
    with reverts('WRONG_BASE_VERSION'):
        oracle.finalizeUpgrade_v3({"from": stranger})