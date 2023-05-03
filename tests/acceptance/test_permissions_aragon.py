import os
from web3 import Web3
from brownie import web3
from brownie.network.event import _decode_logs
from brownie.network.state import TxHistory
from utils.config import contracts
from tests.regression.test_permissions import protocol_permissions
from configs.config_mainnet import (
    lido_dao_agent_address, lido_easytrack_evmscriptexecutor)
from configs.config_shapella_addresses_mainnet import (
    lido_dao_evm_script_registry)
from configs.config_shapella_other_mainnet import expected_permissions_after_votes, ACL_DEPLOY_BLOCK_NUMBER


def has_permissions(app, role, entity):
    return contracts.acl.hasPermission(entity, app, role) or contracts.acl.getPermissionParamsLength(entity, app, role) > 0


def assert_has_permissions(app, role, entity, role_name=None, app_name=None):
    assert has_permissions(
        app, role, entity), f'Entity {entity} should have permission {role_name or role} for app {app_name or app}'


def assert_has_not_permissions(app, role, entity, role_name=None, app_name=None):
    assert not has_permissions(
        app, role, entity), f'Entity {entity} should not have permission {role_name or role} for app {app_name or app}'


def assert_has_not_permissions_in_list(app, role, entity_list, role_name=None, app_name=None):
    for address in entity_list:
        assert_has_not_permissions(app, role, address, role_name, app_name)


def assert_has_permissions_in_list(app, role, entity_list):
    for address in entity_list:
        assert_has_permissions(app, role, address)


def assert_not_match_with_events_in_list(app, role, entity_list, role_name=None, app_name=None):
    for address in entity_list:
        assert_not_match_with_events(app, role, address, role_name, app_name)


def assert_not_match_with_events(app, role, entity, role_name=None, app_name=None):
    assert not has_permissions(app, role, entity, role_name, app_name)


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


def test_protocol_permissions_events(protocol_permissions):
    w3 = Web3(Web3.HTTPProvider(
        f'https://mainnet.infura.io/v3/{os.getenv("WEB3_INFURA_PROJECT_ID")}'))

    event_signature_hash = w3.keccak(
        text="SetPermission(address,address,bytes32,bool)").hex()
    events_before_voting = w3.eth.filter({"address": contracts.acl.address, "fromBlock": ACL_DEPLOY_BLOCK_NUMBER, "topics": [
        event_signature_hash]}).get_all_entries()

    history = TxHistory()
    vote_block = history[0].block_number

    events_after_voting = web3.eth.filter({"address": contracts.acl.address, "fromBlock": vote_block, "topics": [
        event_signature_hash]}).get_all_entries()

    permission_events_before_voting = _decode_logs(
        events_before_voting)['SetPermission']
    permission_events_after_voting = _decode_logs(
        events_after_voting)['SetPermission']

    permission_events = []
    permission_events.extend(permission_events_before_voting)
    permission_events.extend(permission_events_after_voting)

    aragon_apps = [app for app in protocol_permissions.values()
                   if app['type'] == 'AragonApp']

    events_by_app = collect_permissions_from_events(permission_events)
    roles_after_votes = expected_permissions_after_votes

    app_names = {
        contracts.acl.address: 'Acl',
        contracts.kernel.address: 'lido_dao_kernel',
        lido_dao_evm_script_registry: 'EVMScriptRegistry',
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
        contracts.deposit_security_module_v1.address: 'OLD_DepositSecurityModule',
        contracts.finance.address: 'Finance',
        contracts.token_manager.address: 'lido_dao_token_manager_address',
        lido_easytrack_evmscriptexecutor: 'lido_easytrack_EVMScriptExecutor',
        contracts.staking_router.address: 'StakingRouter',
    }

    print('========================== ROLES after votes ==========================')
    for event_app, event_roles in events_by_app.items():
        print("App: {0}".format(app_names[event_app]))

        for event_role in event_roles:
            app = roles_after_votes.get(event_app)
            if app is None:
                assert_has_not_permissions_in_list(
                    event_app, event_role, events_by_app[event_app][event_role])
                continue

            keccak_roles = [w3.keccak(text=role).hex()
                            for role in roles_after_votes[event_app]['roles']]

            if event_role in keccak_roles:
                current_role_string = [x for x in roles_after_votes[event_app]['roles'] if w3.keccak(
                    text=x).hex() == event_role][0]

                for address in events_by_app[event_app][event_role]:
                    if address in roles_after_votes[event_app]['roles'][current_role_string]:
                        print(
                            f'     {address} {entity_names[address]} has {current_role_string}')
                        assert_has_permissions(
                            event_app, event_role, address, current_role_string, app_names[event_app])
                    else:
                        assert_has_not_permissions(
                            event_app, event_role, address, current_role_string, app_names[event_app])
            else:
                assert_has_not_permissions_in_list(
                    event_app, event_role, events_by_app[event_app][event_role])

    print('\n')
    print('========================== CHECKING ROLES with tests/regression/test_permissions.py ==========================')
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
            else:
                assert_not_match_with_events_in_list(
                    address, keccak_role, app['roles'][role], role, app_names[address])
