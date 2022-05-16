"""
Tests for voting 10/05/2022.
"""
import json
import pytest

from scripts.vote_2022_05_17 import start_vote, inject_contracts
from tx_tracing_helpers import *
from utils.config import network_name


@pytest.fixture(scope="module")
def deployer(accounts):
    return accounts[2]


@pytest.fixture(scope="module", autouse=True)
def autodeploy_contracts(deployer):
    if network_name() in ("goerli", "goerli-fork"):
        return
    lido_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-lido-base.json'))["data"]
    nos_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-node-operators-registry-base.json'))["data"]
    oracle_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-oracle-base.json'))["data"]
    mev_vault_tx_data = json.load(open('./utils/txs/tx-26-deploy-mev-vault.json'))["data"]

    lido_tx = deployer.transfer(data=lido_tx_data)
    nos_tx = deployer.transfer(data=nos_tx_data)
    oracle_tx = deployer.transfer(data=oracle_tx_data)
    mev_vault_tx = deployer.transfer(data=mev_vault_tx_data)

    inject_contracts(lido_tx.contract_address, nos_tx.contract_address, oracle_tx.contract_address,
                     mev_vault_tx.contract_address)


def test_2022_05_17(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding
):

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 13, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)
