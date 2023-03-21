"""
Tests for voting ???
"""
from scripts.upgrade_shapella_goerli import start_vote
from utils.shapella_upgrade import load_shapella_deploy_config, debug_locator_addresses, prepare_for_voting
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    lido_dao_staking_router,
    lido_dao_node_operators_registry,
    ContractsLazyLoader,
    deployer_eoa,
)
from utils.test.event_validators.permission import Permission, validate_permission_create_event
from utils.test.event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from brownie.network.transaction import TransactionReceipt
from brownie import interface
from brownie import ShapellaUpgradeTemplate
from pprint import pprint
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


# STAKING_ROUTER_ROLE
permission_staking_router = Permission(
    entity=lido_dao_staking_router,
    app=lido_dao_node_operators_registry,
    role="0xbb75b874360e0bfd87f964eadd8276d8efb7c942134fc329b513032d0803e0c6",
)

lido_app_id = "0x79ac01111b462384f1b7fba84a17b9ec1f5d2fddcfcb99487d71b443832556ea"
lido_app_version = (10, 0, 0)

nos_app_id = "0x57384c8fcaf2c1c2144974769a6ea4e5cf69090d47f5327f8fc93827f8c0001a"
nos_app_version = (8, 0, 0)

oracle_app_id = "0xb2977cfc13b000b6807b9ae3cf4d938f4cc8ba98e1d68ad911c58924d6aa4f11"
oracle_app_version = (5, 0, 0)


def test_vote(
    helpers,
    bypass_events_decoding,
    accounts,
    ldo_holder,
):
    config = load_shapella_deploy_config()
    debug_locator_addresses(contracts.lido_locator.address)

    lido_new_implementation = config["app:lido"]["implementation"]
    nor_new_implementation = config["app:node-operators-registry"]["implementation"]
    oracle_new_implementation = config["app:oracle"]["implementation"]

    lido_repo: interface.Repo = contracts.lido_app_repo
    lido_old_app = lido_repo.getLatest()

    nos_repo: interface.Repo = contracts.nos_app_repo
    nos_old_app = nos_repo.getLatest()

    oracle_repo: interface.Repo = contracts.oracle_app_repo
    oracle_old_app = oracle_repo.getLatest()

    acl: interface.ACL = contracts.acl

    assert not acl.hasPermission(*permission_staking_router)

    template = prepare_for_voting(deployer_eoa)
    ContractsLazyLoader.upgrade_template = template
    template.verifyInitialState()  # reverts if the state is not correct

    # START VOTE
    vote_id, _ = start_vote({"from": ldo_holder}, True)

    # DEBUG: Uncomment if want to make part of the upgrade as a separate tx
    # template.startUpgrade({'from': contracts.voting.address})

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=contracts.voting, skip_time=3 * 60 * 60 * 24
    )
    print(f"UPGRADE TX GAS USED: {tx.gas_used}")

    # DEBUG: Uncomment if want to make part of the upgrade as a separate tx
    # template.finishUpgrade({'from': contracts.voting.address})

    #
    # Lido app upgrade checks
    #
    lido_new_app = lido_repo.getLatest()
    lido_proxy = interface.AppProxyUpgradeable(contracts.lido)
    assert_app_update(lido_new_app, lido_old_app, lido_new_implementation)
    assert lido_proxy.implementation() == lido_new_implementation, "Proxy should be updated"

    #
    # NodeOperatorsRegistry app upgrade checks
    #
    nos_new_app = nos_repo.getLatest()
    nos_proxy = interface.AppProxyUpgradeable(contracts.node_operators_registry)
    assert_app_update(nos_new_app, nos_old_app, nor_new_implementation)
    assert nos_proxy.implementation() == nor_new_implementation, "Proxy should be updated"

    #
    # LidoOracle app upgrade checks
    #
    oracle_new_app = oracle_repo.getLatest()
    oracle_proxy = interface.AppProxyUpgradeable(contracts.legacy_oracle)
    assert_app_update(oracle_new_app, oracle_old_app, oracle_new_implementation)
    assert oracle_proxy.implementation() == oracle_new_implementation, "Proxy should be updated"

    #
    # Aragon ACL checks
    #
    assert acl.hasPermission(*permission_staking_router)

    #
    # Template checks
    #
    assert template.isUpgradeFinished()

    if bypass_events_decoding:
        return

    display_voting_events(tx)
    evs = group_voting_events(tx)

    validate_push_to_repo_event(evs[0], lido_app_version)
    validate_app_update_event(evs[1], lido_app_id, lido_new_implementation)

    validate_push_to_repo_event(evs[2], nos_app_version)
    validate_app_update_event(evs[3], nos_app_id, nor_new_implementation)

    validate_push_to_repo_event(evs[4], oracle_app_version)
    validate_app_update_event(evs[5], oracle_app_id, oracle_new_implementation)

    # TODO: fix event index
    validate_permission_create_event(evs[6], permission_staking_router)


def assert_app_update(new_app, old_app, contract_address):
    assert old_app[1] != new_app[1], "Address should change"
    assert new_app[1] == contract_address, "New address should match"
    assert new_app[0][0] == old_app[0][0] + 1, "Major version should increment"

    # TODO: uncomment
    # assert old_app[2] == new_app[2], "Content uri remains"
