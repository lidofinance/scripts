"""
Tests for voting 24/03/2023
"""
from scripts.upgrade_shapella_1_goerli import start_vote
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    lido_dao_staking_router,
    lido_dao_node_operators_registry,
    ContractsLazyLoader,
    lido_dao_voting_address,
    lido_dao_steth_address,
    lido_dao_legacy_oracle,
    shapella_upgrade_template,
)
from utils.test.event_validators.permission import Permission, validate_permission_create_event
from utils.test.event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from brownie.network.transaction import TransactionReceipt
from brownie import interface, ShapellaUpgradeTemplate
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


# STAKING_ROUTER_ROLE
permission_staking_router = Permission(
    entity=lido_dao_staking_router,
    app=lido_dao_node_operators_registry,
    role="0xbb75b874360e0bfd87f964eadd8276d8efb7c942134fc329b513032d0803e0c6",
)

lido_app_id = "0x79ac01111b462384f1b7fba84a17b9ec1f5d2fddcfcb99487d71b443832556ea"
lido_new_implementation = "0xEE227CC91A769881b1e81350224AEeF7587eBe76"
lido_app_version = (10, 0, 0)

nor_app_id = "0x57384c8fcaf2c1c2144974769a6ea4e5cf69090d47f5327f8fc93827f8c0001a"
nor_new_implementation = "0xCAfe9Ac6a4bE2eAfCFf949693C0da9eebF985C3B"
nor_app_version = (8, 0, 0)

oracle_app_id = "0xb2977cfc13b000b6807b9ae3cf4d938f4cc8ba98e1d68ad911c58924d6aa4f11"
oracle_new_implementation = "0xcF9d64942DC9096520a8962a2d4496e680c6403b"
oracle_app_version = (5, 0, 0)

permissions_to_revoke = [
    Permission(  # MANAGE_FEE
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role="0x46b8504718b48a11e89304b407879435528b3cd3af96afde67dfe598e4683bd8",
    ),
    Permission(  # MANAGE_WITHDRAWAL_KEY
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role="0x46b8504718b48a11e89304b407879435528b3cd3af96afde67dfe598e4683bd8",
    ),
    Permission(  # MANAGE_PROTOCOL_CONTRACTS_ROLE
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role="0xeb7bfce47948ec1179e2358171d5ee7c821994c911519349b95313b685109031",
    ),
    Permission(  # SET_EL_REWARDS_VAULT_ROLE
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role="0x9d68ad53a92b6f44b2e8fb18d211bf8ccb1114f6fafd56aa364515dfdf23c44f",
    ),
    Permission(  # SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role="0xca7d176c2da2028ed06be7e3b9457e6419ae0744dc311989e9b29f6a1ceb1003",
    ),
    Permission(  # ADD_NODE_OPERATOR_ROLE
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role="0xe9367af2d321a2fc8d9c8f1e67f0fc1e2adf2f9844fb89ffa212619c713685b2",
    ),
    Permission(  # SET_NODE_OPERATOR_ACTIVE_ROLE
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role="0xd856e115ac9805c675a51831fa7d8ce01c333d666b0e34b3fc29833b7c68936a",
    ),
    Permission(  # SET_NODE_OPERATOR_NAME_ROLE
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role="0x58412970477f41493548d908d4307dfca38391d6bc001d56ffef86bd4f4a72e8",
    ),
    Permission(  # SET_NODE_OPERATOR_ADDRESS_ROLE
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role="0xbf4b1c236312ab76e456c7a8cca624bd2f86c74a4f8e09b3a26d60b1ce492183",
    ),
    Permission(  # REPORT_STOPPED_VALIDATORS_ROLE
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role="0x18ad851afd4930ecc8d243c8869bd91583210624f3f1572e99ee8b450315c80f",
    ),
    Permission(  # MANAGE_MEMBERS
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role="0xbf6336045918ae0015f4cdb3441a2fdbfaa4bcde6558c8692aac7f56c69fb067",
    ),
    Permission(  # MANAGE_QUORUM
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role="0xa5ffa9f45fa52c446078e834e1914561bd9c2ab1e833572d62af775da092ccbc",
    ),
    Permission(  # SET_BEACON_SPEC
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role="0x16a273d48baf8111397316e6d961e6836913acb23b181e6c5fb35ec0bd2648fc",
    ),
    Permission(  # SET_REPORT_BOUNDARIES
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role="0x44adaee26c92733e57241cb0b26ffaa2d182ed7120ba3ecd7e0dce3635c01dc1",
    ),
    Permission(  # SET_BEACON_REPORT_RECEIVER
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role="0xe22a455f1bfbaf705ac3e891a64e156da92cb0b42cfc389158e6e82bd57f37be",
    ),
]


def test_vote(
    helpers,
    bypass_events_decoding,
):
    lido_repo: interface.Repo = contracts.lido_app_repo
    lido_old_app = lido_repo.getLatest()

    nos_repo: interface.Repo = contracts.nos_app_repo
    nos_old_app = nos_repo.getLatest()

    oracle_repo: interface.Repo = contracts.oracle_app_repo
    oracle_old_app = oracle_repo.getLatest()

    acl: interface.ACL = contracts.acl
    assert not acl.hasPermission(*permission_staking_router)
    for permission in permissions_to_revoke:
        assert acl.hasPermission(*permission), f"No starting role {permission.role} on {permission.entity}"

    # START VOTE
    _, vote_transactions = start_and_execute_votes(contracts.voting, helpers)
    tx = vote_transactions[0]
    print(f"UPGRADE TX GAS USED: {tx.gas_used}")

    template = ShapellaUpgradeTemplate.at(shapella_upgrade_template)

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
    for permission in permissions_to_revoke:
        assert not acl.hasPermission(*permission), f"Role {permission.role} is still on {permission.entity}"

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

    validate_push_to_repo_event(evs[2], nor_app_version)
    validate_app_update_event(evs[3], nor_app_id, nor_new_implementation)

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
