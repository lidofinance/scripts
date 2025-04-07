from tests.regression.test_permissions import (protocol_permissions_list)
from brownie import web3, interface
from web3 import Web3
from brownie.network.event import _decode_logs
from utils.test.helpers import ZERO_BYTES32
import os

from utils.config import (
    contracts,
    ACL_DEPLOY_BLOCK_NUMBER
)

def main():
    """
    Fetches all aragon roles from the ACL contract
    """
    permissions_state_from_test = protocol_permissions_list()
    aragon_managers = fetch_list_of_aragon_role_managers()
    aragon_roles = fetch_list_of_aragon_roles()
    oz_roles = fetch_oz_roles(permissions_state_from_test)
    proxy_owners = fetch_proxy_owners(permissions_state_from_test)

    print ("### Aragon Roles Managers")
    for app in aragon_managers:
        print(f"#### App: {permissions_state_from_test[app]['contract_name']} {app}")
        print("| Role | Manager |")
        print("|------|---------|")
        for role, manager in aragon_managers[app].items():
            for role_name in permissions_state_from_test[app]['roles']:
                if web3.keccak(text=role_name).hex() in role:
                    role = role_name
            print(f"| {role} | {manager} |")

    print ("### Aragon Roles")
    for app in aragon_roles:
        print(f"#### App: {permissions_state_from_test[app]['contract_name']} {app}")
        print("| Role | Entities |")
        print("|------|---------|")
        for role, entities in aragon_roles[app].items():
            for role_name in permissions_state_from_test[app]['roles']:
                if web3.keccak(text=role_name).hex() in role:
                    role = role_name
            entities_str = ", ".join(entities)
            print(f"| {role} | {entities_str} |")
    
    print ("### OpenZeppelin Roles")
    for app in oz_roles:
        print(f"#### App: {permissions_state_from_test[app]['contract_name']} {app}")
        print("| Role | Entities |")
        print("|------|---------|")
        for role, entities in oz_roles[app].items():
            for role_name in permissions_state_from_test[app]['roles']:
                if web3.keccak(text=role_name).hex() in role:
                    role = role_name
            entities_str = ", ".join(entities)
            print(f"| {role} | {entities_str} |")
    
    print ("### Proxy Owners")
    for app in proxy_owners:
        print(f"| Proxy | Proxy Owner |")
        print("|------|---------|")
        print(f"| {permissions_state_from_test[app]['contract_name']} {app} | {proxy_owners[app]} |")

    
def fetch_list_of_aragon_role_managers():
    aragon_managers = {}

    w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{os.getenv("WEB3_INFURA_PROJECT_ID")}'))

    event_signature_hash = w3.keccak(text="ChangePermissionManager(address,bytes32,address)").hex()
    events = w3.eth.filter(
        {"address": contracts.acl.address, "fromBlock": ACL_DEPLOY_BLOCK_NUMBER, "topics": [event_signature_hash]}
    ).get_all_entries()

    set_manager_events = _decode_logs(events)["ChangePermissionManager"]._ordered

    for event in set_manager_events:
        if event["app"] in aragon_managers:
            aragon_managers[event["app"]][str(event["role"])] = event["manager"]
        else:
            aragon_managers[event["app"]] = {str(event["role"]): event["manager"]}

    return aragon_managers

def fetch_list_of_aragon_roles():
    aragon_roles = {}

    w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{os.getenv("WEB3_INFURA_PROJECT_ID")}'))

    event_signature_hash = w3.keccak(text="SetPermission(address,address,bytes32,bool)").hex()
    events = w3.eth.filter(
        {"address": contracts.acl.address, "fromBlock": ACL_DEPLOY_BLOCK_NUMBER, "topics": [event_signature_hash]}
    ).get_all_entries()

    set_permission_events = _decode_logs(events)["SetPermission"]._ordered

    for event in set_permission_events:
        if event["allowed"]:
            if event["app"] in aragon_roles:
                if str(event["role"]) not in aragon_roles[str(event["app"])]:
                    aragon_roles[str(event["app"])][str(event["role"])] = [event["entity"]]
                else:
                    aragon_roles[str(event["app"])][str(event["role"])].append(event["entity"])
            else:
                aragon_roles[str(event["app"])] = {str(event["role"]): [event["entity"]]}
        else:
            if event["entity"] not in aragon_roles[str(event["app"])][str(event["role"])]:
                print(f"Entity {event['entity']} with role {event['role']} not found  in app {event['app']}")
                continue
            aragon_roles[str(event["app"])][str(event["role"])].remove(event["entity"])

    # Remove empty roles
    for app in list(aragon_roles.keys()):
        for role in list(aragon_roles[app].keys()):
            if not aragon_roles[app][role]:
                del aragon_roles[app][role]
        if not aragon_roles[app]:
            del aragon_roles[app]

    return aragon_roles

def fetch_oz_roles(permissions_state):
    oz_roles = {}

    for app in permissions_state:
        if permissions_state[app]["type"] == "CustomApp": 
            for role in permissions_state[app]["roles"]:
                role_keccak = web3.keccak(text=role).hex() if role != "DEFAULT_ADMIN_ROLE" else ZERO_BYTES32.hex()

                permission_holders_count = permissions_state[app]["contract"].getRoleMemberCount(role_keccak)
                if permission_holders_count > 0:
                    permission_holders = []
                    for i in range(permission_holders_count):
                        permission_holders.append(permissions_state[app]["contract"].getRoleMember(role_keccak, i))
                    oz_roles[permissions_state[app]["contract"].address] = {role: permission_holders}
    
    return oz_roles

def fetch_proxy_owners(permission_state):
    proxy_owners = {}

    for app in permission_state:
        if "proxy_owner" in permission_state[app]:
            proxy_owners[app] = interface.OssifiableProxy(permission_state[app]["contract"].address).proxy__getAdmin()

    return proxy_owners