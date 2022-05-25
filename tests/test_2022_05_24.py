"""
Tests for voting 24/05/2022.
"""
import pytest

from brownie import interface, chain

from scripts.vote_2022_05_24 import start_vote
from tx_tracing_helpers import *
from utils.config import contracts, lido_dao_steth_address, lido_dao_oracle, lido_dao_node_operators_registry, \
    network_name
from event_validators.permission import Permission, validate_permission_create_event
from event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from event_validators.lido import (validate_set_version_event,
                                   validate_set_el_rewards_vault_event, validate_staking_resumed_event,
                                   validate_staking_limit_set)


@pytest.fixture(scope="module", autouse=True)
def deployed_contracts():
    return {
        'lido': '0x47EbaB13B806773ec2A2d16873e2dF770D130b50',
        'nos': '0x5d39ABaa161e622B99D45616afC8B837E9F19a25',
        'oracle': '0x1430194905301504e8830ce4B0b0df7187E84AbD',
        'el_rewards_vault': '0x388C818CA8B9251b393131C08a736A67ccB19297'
    }


lido_app_id = '0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320'
lido_app_version = (3, 0, 0)

nos_app_id = '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d'
nos_app_version = (3, 0, 0)

oracle_app_id = '0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93'
oracle_app_version = (3, 0, 0)

oracle_contract_version = 3

permission_elrewards_vault = Permission(entity='0x2e59A20f205bB85a89C53f1936454680651E618e',  # Voting
                                        app='0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # Lido
                                        role='0x9d68ad53a92b6f44b2e8fb18d211bf8ccb1114f6fafd56aa364515dfdf23c44f')
permission_stake_control = Permission(entity='0x2e59A20f205bB85a89C53f1936454680651E618e',  # Voting
                                      app='0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # Lido
                                      role='0xa42eee1333c0758ba72be38e728b6dadb32ea767de5b4ddbaea1dae85b1b051f')

mev_limit_points = 2
max_staking_limit = 150_000 * 10 ** 18
staking_limit_increase = 234375 * 10 ** 18 // 10 ** 4


def test_vote(
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
    assert not acl.hasPermission(*permission_elrewards_vault)
    assert not acl.hasPermission(*permission_stake_control)

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

    assert acl.hasPermission(*permission_elrewards_vault)
    assert acl.hasPermission(*permission_stake_control)

    assert lido.getELRewardsVault() == deployed_contracts['el_rewards_vault']
    assert not lido.isStakingPaused()

    stake_limit_info = lido.getStakeLimitFullInfo()
    assert not stake_limit_info[0]
    assert stake_limit_info[1]
    assert stake_limit_info[2] == max_staking_limit
    assert stake_limit_info[3] == max_staking_limit
    assert stake_limit_info[4] == 6400
    assert stake_limit_info[5] == max_staking_limit
    assert stake_limit_info[6] == chain.height

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 12, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(tx)

    validate_push_to_repo_event(evs[0], lido_app_version)
    validate_app_update_event(evs[1], lido_app_id, deployed_contracts['lido'])

    validate_push_to_repo_event(evs[2], nos_app_version)
    validate_app_update_event(evs[3], nos_app_id, deployed_contracts['nos'])

    validate_push_to_repo_event(evs[4], oracle_app_version)
    validate_app_update_event(evs[5], oracle_app_id, deployed_contracts['oracle'])

    validate_set_version_event(evs[6], oracle_contract_version)

    validate_permission_create_event(evs[7], permission_elrewards_vault)

    validate_permission_create_event(evs[8], permission_stake_control)

    validate_set_el_rewards_vault_event(evs[9], deployed_contracts['el_rewards_vault'])

    validate_staking_resumed_event(evs[10])

    validate_staking_limit_set(evs[11], max_staking_limit, staking_limit_increase)


def assert_app_update(new_app, old_app, contract_address):
    assert old_app[1] != new_app[1], "Address should change"
    assert new_app[1] == contract_address
    assert new_app[0][0] == old_app[0][0] + 1, "Version should increment"
    assert old_app[2] == new_app[2], "Content uri remains"
