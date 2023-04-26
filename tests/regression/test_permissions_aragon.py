import pytest
import os
from web3 import Web3
from brownie import interface, convert
from brownie.network.event import _decode_logs
from utils.test.event_validators.permission import Permission
from utils.config import contracts
from tests.regression.test_permissions import protocol_permissions
from utils.config_mainnet import (
    lido_dao_agent_address, lido_easytrack_evmscriptexecutor, lido_dao_deposit_security_module_address_old, lido_easytrack_evmscriptexecutor)


def has_permissions(app, role, entity):
    return contracts.acl.hasPermission(entity, app, role)


def assert_has_permissions(app, role, entity):
    assert has_permissions(
        app, role, entity), f'Entity {entity} should have permission {role} for app {app}'


def assert_has_not_permissions(app, role, entity, role_name=None):
    assert not has_permissions(
        app, role, entity), f'Entity {entity} should not have permission {role_name or role} for app {app}'


def assert_has_not_permissions_in_list(app, role, entity_list, role_name=None):
    for address in entity_list:
        assert_has_not_permissions(app, role, address, role_name)


def assert_has_permissions_in_list(app, role, entity_list):
    for address in entity_list:
        assert_has_permissions(app, role, address)


def assert_not_match_with_events_in_list(app, role, entity_list, role_name=None, app_name=None):
    for address in entity_list:
        # assert not has_permissions(
        #     app, role, address), f'{address} with role {role_name or role} for app {app} does not match with permission events'
        assert_not_match_with_events(app, role, address, role_name, app_name)


def assert_not_match_with_events(app, role, entity, role_name=None, app_name=None):
    has = has_permissions(app, role, entity)
    if has == True:
        print(
            f'\033[91m {entity} with role {role_name or role} for app {app_name or app} does not match with permission events \033[0m')


def collect_permissions_from_events(permission_events):
    apps = {}
    for event in permission_events:
        if event['allowed'] == True:
            if event['app'] not in apps:
                apps[event['app']] = {str(event['role']): [event['entity']]}
            elif event['app'] in apps:
                if str(event['role']) not in apps[event['app']]:
                    apps[event['app']][str(event['role'])] = [event['entity']]
                else:
                    apps[event['app']][str(event['role'])].append(
                        event['entity'])

    return apps


@pytest.mark.skipif(condition=not os.getenv("INFURA_TEST_PROVIDER"), reason="No votes")
def test_protocol_permissions_events(protocol_permissions):
    w3 = Web3(Web3.HTTPProvider(os.getenv("INFURA_TEST_PROVIDER")))

    event_signature_hash = w3.keccak(
        text="SetPermission(address,address,bytes32,bool)").hex()
    events = w3.eth.filter({"address": contracts.acl.address, "fromBlock": 11473216, "topics": [
        event_signature_hash]}).get_all_entries()

    decoded_events = _decode_logs(events)
    permission_events = decoded_events['SetPermission']

    aragon_apps = [app for app in protocol_permissions.values()
                   if app['type'] == 'AragonApp']

    events_by_app = collect_permissions_from_events(permission_events)

    exceptions = {
        contracts.acl.address: {
            'roles': {
                'CREATE_PERMISSIONS_ROLE': [contracts.voting.address]
            }
        },
        contracts.kernel.address: {
            'roles': {
                'APP_MANAGER_ROLE': [contracts.voting.address]
            }
        },
        '0x853cc0D5917f49B57B8e9F89e491F5E18919093A': {
            'roles': {
                'REGISTRY_MANAGER_ROLE': [contracts.voting.address],
                'REGISTRY_ADD_EXECUTOR_ROLE': [contracts.voting.address]
            }
        },
        contracts.token_manager.address: {
            'roles': {
                'ASSIGN_ROLE': [contracts.voting.address]
            }
        },
        contracts.lido.address: {
            'roles': {
                'PAUSE_ROLE': [contracts.voting.address],
                'STAKING_CONTROL_ROLE': [contracts.voting.address],
                'RESUME_ROLE': [contracts.voting.address],
                'STAKING_PAUSE_ROLE': [contracts.voting.address],
                'DEPOSIT_ROLE': [contracts.deposit_security_module_v1.address]
            }
        },
        lido_dao_agent_address: {
            'roles': {
                'EXECUTE_ROLE': [contracts.voting.address],
                'RUN_SCRIPT_ROLE': [contracts.voting.address],
                'TRANSFER_ROLE': [contracts.finance.address]
            }
        },
        contracts.finance.address: {
            'roles': {
                'EXECUTE_PAYMENTS_ROLE': [contracts.voting.address],
                'MANAGE_PAYMENTS_ROLE': [contracts.voting.address],
                'CREATE_PAYMENTS_ROLE': [contracts.voting.address]
            }
        },
        contracts.voting.address: {
            'roles': {
                'MODIFY_QUORUM_ROLE': [contracts.voting.address],
                'MODIFY_SUPPORT_ROLE': [contracts.voting.address],
                'CREATE_VOTES_ROLE': [contracts.token_manager.address]
            }
        },
        contracts.node_operators_registry.address: {
            'roles': {
                'MANAGE_SIGNING_KEYS': [contracts.voting.address],
                'SET_NODE_OPERATOR_LIMIT_ROLE': [contracts.voting.address, lido_easytrack_evmscriptexecutor]
            }
        }
    }

    # {
    #     'app': {'role': ['entity', 'entity']},
    #     'app': {'role': ['entity', 'entity']},
    # }

    app_names = {
        contracts.acl.address: 'Acl',
        contracts.kernel.address: 'lido_dao_kernel',
        '0x853cc0D5917f49B57B8e9F89e491F5E18919093A': 'EVMScriptRegistry',
        contracts.token_manager.address: 'lido_dao_token_manager_address',
        contracts.lido.address: 'Lido',
        lido_dao_agent_address: 'lido_dao_agent',
        contracts.finance.address: 'Finance',
        contracts.voting.address: 'Voting',
        contracts.legacy_oracle.address: 'LegacyOracle',
        contracts.node_operators_registry.address: 'NodeOperatorsRegistry',
    }
    entity_names = {
        contracts.voting.address: 'Voting',
        lido_dao_deposit_security_module_address_old: 'OLD_DepositSecurityModule',
        contracts.finance.address: 'Finance',
        contracts.token_manager.address: 'lido_dao_token_manager_address',
        lido_easytrack_evmscriptexecutor: 'lido_easytrack_EVMScriptExecutor',
    }

    for event_app, event_roles in events_by_app.items():
        print("App: {0}".format(app_names[event_app]))

        for event_role in event_roles:
            app = exceptions.get(event_app)
            if app is None:
                assert_has_not_permissions_in_list(
                    event_app, event_role, events_by_app[event_app][event_role])
                continue

            keccak_roles = [w3.keccak(text=role).hex()
                            for role in exceptions[event_app]['roles']]

            if event_role in keccak_roles:
                current_role_string = [x for x in exceptions[event_app]['roles'] if w3.keccak(
                    text=x).hex() == event_role][0]

                for address in events_by_app[event_app][event_role]:
                    if address in exceptions[event_app]['roles'][current_role_string]:
                        print(
                            f'     {address} {entity_names[address]} has {current_role_string}')
                        assert_has_permissions(
                            event_app, event_role, address)
                    else:
                        assert_has_not_permissions(
                            event_app, event_role, address)
            else:
                assert_has_not_permissions_in_list(
                    event_app, event_role, events_by_app[event_app][event_role])

    # check what events_by_app matches with aragon_apps
    for app in aragon_apps:
        address = app['contract'].address
        print("Aragon App: {0}".format(app_names[address]))

        events_data = events_by_app[address]

        for role in app['roles']:
            keccak_role = w3.keccak(text=role).hex()
            if keccak_role in events_data:
                for entity in events_data[keccak_role]:
                    if entity in app['roles'][role]:
                        assert_has_permissions(
                            address, keccak_role, entity)
                    else:
                        assert_not_match_with_events(
                            address, keccak_role, entity, role, app_names[address])
                    # assert address in app['roles'][role], f'{address} {entity_names[address]} has {role}'
                    # if address not in app['roles'][role]:
                    #     print(
                    #         f'\033[91m     {address} {entity_names[address]} has {role} but not in protocol_permissions file\033[0m')
                    # print('--', role, address, entity_names[address])
            else:
                assert_not_match_with_events_in_list(
                    address, keccak_role, app['roles'][role], role, app_names[address])
