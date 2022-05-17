"""
Tests for voting 17/05/2022.

__NB!__ Use `brownie test tests/test_2022_05_17.py --network hardhat-fork -s` to run this test
because ganache fails with `Invalid string length` error
"""
import json
import pytest

from brownie import interface

from scripts.vote_2022_05_17 import start_vote, update_lido_app, update_nos_app, update_oracle_app
from tx_tracing_helpers import *
from utils.config import contracts, lido_dao_steth_address, lido_dao_oracle, lido_dao_node_operators_registry
from event_validators.permission import Permission, validate_permission_create_event
from event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from event_validators.lido import (validate_set_version_event, validate_set_mev_vault_withdrawal_limit_event,
                                   validate_set_mev_vault_event, validate_staking_resumed_event)


@pytest.fixture(scope="module")
def deployer(accounts):
    return accounts[2]


@pytest.fixture(scope="module", autouse=True)tx-26-deploy-execution-layer-rewards-vault.json
def deployed_contracts(deployer):
    if update_lido_app['new_address'] is None:
        lido_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-lido-base.json'))["data"]
        nos_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-node-operators-registry-base.json'))["data"]
        oracle_tx_data = json.load(open('./utils/txs/tx-13-1-deploy-oracle-base.json'))["data"]
        execution_layer_rewards_vault_tx_data = json.load(open('./utils/txs/tx-26-deploy-execution-layer-rewards-vault.json'))["data"]

        lido_tx = deployer.transfer(data=lido_tx_data)
        nos_tx = deployer.transfer(data=nos_tx_data)
        oracle_tx = deployer.transfer(data=oracle_tx_data)
        execution_layer_rewards_vault_tx = deployer.transfer(data=execution_layer_rewards_vault_tx_data)

        update_lido_app['new_address'] = lido_tx.contract_address
        update_lido_app['execution_layer_rewards_vault_address'] = execution_layer_rewards_vault_tx.contract_address
        update_nos_app['new_address'] = nos_tx.contract_address
        update_oracle_app['new_address'] = oracle_tx.contract_address

        return {'lido': lido_tx.contract_address,
                'nos': nos_tx.contract_address,
                'oracle': oracle_tx.contract_address,
                'mev_vault': execution_layer_rewards_vault_tx.contract_address}
    else:
        return {'lido': '',
                'nos': '',
                'oracle': '',
                'mev_vault': ''}  # Hardcode contract addresses here


lido_app_id = '0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320'
lido_app_version = (3, 0, 0)

nos_app_id = '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d'
nos_app_version = (3, 0, 0)

oracle_app_id = '0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93'
oracle_app_version = (3, 0, 0)

oracle_contract_version = 3

permission_mev_vault = Permission(entity='0x2e59A20f205bB85a89C53f1936454680651E618e',  # Voting
                                  app='0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # Lido
                                  role='0x4e4933b1d536574ff4e80f3a1969722cbb193387fc0bb7b5952dbaffb59c9f44')
permission_mev_withdrawal_limit = Permission(entity='0x2e59A20f205bB85a89C53f1936454680651E618e',  # Voting
                                             app='0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # Lido
                                             role='0x7f8796bf332967f28d4937efe7af82a13783b9380c8dc67697837baa937d0959')
permission_stake_resume = Permission(entity='0x2e59A20f205bB85a89C53f1936454680651E618e',  # Voting
                                     app='0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # Lido
                                     role='0xb7fb61d30d1ce0378ffa8842e9f240cfd41ff78cd4eec7c5fe18311f7db8a242')

mev_limit_points = 2
max_staking_limit = 150_000 * 10**18
staking_limit_increase = 23.4375 * 10**18


def test_2022_05_17(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding,
    deployed_contracts, lido,
):
    lido_repo: interface.Repo = contracts.lido_app_repo
    lido_old_app = lido_repo.getLatest()

    nos_repo: interface.Repo = contracts.nos_app_repo
    nos_old_app = nos_repo.getLatest()

    oracle_repo: interface.Repo = contracts.oracle_app_repo
    oracle_old_app = oracle_repo.getLatest()

    acl: interface.ACL = contracts.acl
    assert not acl.hasPermission(*permission_mev_vault)
    assert not acl.hasPermission(*permission_mev_withdrawal_limit)
    assert not acl.hasPermission(*permission_stake_resume)

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    lido_new_app = lido_repo.getLatest()
    assert_app_update(lido_new_app, lido_old_app, deployed_contracts['lido'])

    lido_proxy = interface.AppProxyUpgradeable(lido_dao_steth_address)
    assert lido_proxy.implementation() == deployed_contracts['lido'], 'Proxy should be updated'

    nos_new_app = nos_repo.getLatest()
    assert_app_update(nos_new_app, nos_old_app, deployed_contracts['nos'])

    nos_proxy = interface.AppProxyUpgradeable(lido_dao_node_operators_registry)
    assert nos_proxy.implementation() == deployed_contracts['nos'], 'Proxy should be updated'

    oracle_new_app = oracle_repo.getLatest()
    assert_app_update(oracle_new_app, oracle_old_app, deployed_contracts['oracle'])

    oracle_proxy = interface.AppProxyUpgradeable(lido_dao_oracle)
    assert oracle_proxy.implementation() == deployed_contracts['oracle'], 'Proxy should be updated'

    assert acl.hasPermission(*permission_mev_vault)
    assert acl.hasPermission(*permission_mev_withdrawal_limit)
    assert acl.hasPermission(*permission_stake_resume)

    assert lido.getMevTxFeeVault() == deployed_contracts['mev_vault']
    assert lido.getMevTxFeeWithdrawalLimitPoints() == 2
    assert not lido.isStakingPaused()

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 13, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    validate_push_to_repo_event(evs[0], lido_app_version)
    validate_app_update_event(evs[1], lido_app_id, deployed_contracts['lido'])

    validate_push_to_repo_event(evs[2], nos_app_version)
    validate_app_update_event(evs[3], nos_app_id, deployed_contracts['nos'])

    validate_push_to_repo_event(evs[4], oracle_app_version)
    validate_app_update_event(evs[5], oracle_app_id, deployed_contracts['oracle'])

    validate_set_version_event(evs[6], oracle_contract_version)

    validate_permission_create_event(evs[7], permission_mev_vault)

    validate_permission_create_event(evs[8], permission_mev_withdrawal_limit)

    validate_permission_create_event(evs[9], permission_stake_resume)

    validate_set_mev_vault_event(evs[10], deployed_contracts['mev_vault'])

    validate_set_mev_vault_withdrawal_limit_event(evs[11], mev_limit_points)

    validate_staking_resumed_event(evs[12], max_staking_limit, staking_limit_increase)


def assert_app_update(new_app, old_app, contract_address):
    assert old_app[1] != new_app[1], "Address should change"
    assert new_app[1] == contract_address
    assert new_app[0][0] == old_app[0][0] + 1, "Version should increment"
    assert old_app[2] == new_app[2], "Content uri remains"
