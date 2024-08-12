"""
Tests for permissions setup
"""

import pytest
import os

from web3 import Web3
from brownie import interface, convert, web3
from brownie.network.event import _decode_logs
from brownie.network.state import TxHistory
from utils.test.event_validators.permission import Permission
from utils.test.helpers import ZERO_BYTES32
from brownie.exceptions import EventLookupError
from utils.config import (
    contracts,
    GATE_SEAL,
    DSM_GUARDIANS,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    ORACLE_COMMITTEE,
    AGENT,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    ARAGON_EVMSCRIPT_REGISTRY,
    ACL_DEPLOY_BLOCK_NUMBER,
    VOTING,
    TOKEN_MANAGER,
    LIDO,
    ARAGON_KERNEL,
    ACL,
    FINANCE,
    NODE_OPERATORS_REGISTRY,
    STAKING_ROUTER,
    ORACLE_DAEMON_CONFIG,
    DEPOSIT_SECURITY_MODULE,
    ORACLE_REPORT_SANITY_CHECKER,
    HASH_CONSENSUS_FOR_VEBO,
    HASH_CONSENSUS_FOR_AO,
    VALIDATORS_EXIT_BUS_ORACLE,
    ACCOUNTING_ORACLE,
    WITHDRAWAL_QUEUE,
    BURNER,
    LIDO_LOCATOR,
    LEGACY_ORACLE,
    SIMPLE_DVT,
)


@pytest.fixture(scope="function")
def protocol_permissions():
    return {
        LIDO_LOCATOR: {
            "contract_name": "LidoLocator",
            "contract": contracts.lido_locator,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {},
        },
        BURNER: {
            "contract_name": "Burner",
            "contract": contracts.burner,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "REQUEST_BURN_MY_STETH_ROLE": [contracts.agent],
                "REQUEST_BURN_SHARES_ROLE": [contracts.lido, contracts.node_operators_registry, contracts.simple_dvt],
            },
        },
        STAKING_ROUTER: {
            "contract_name": "StakingRouter",
            "contract": contracts.staking_router,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "MANAGE_WITHDRAWAL_CREDENTIALS_ROLE": [],
                "STAKING_MODULE_PAUSE_ROLE": [contracts.deposit_security_module],
                "STAKING_MODULE_RESUME_ROLE": [contracts.deposit_security_module],
                "STAKING_MODULE_MANAGE_ROLE": [contracts.agent],
                "REPORT_EXITED_VALIDATORS_ROLE": [contracts.accounting_oracle],
                "UNSAFE_SET_EXITED_VALIDATORS_ROLE": [],
                "REPORT_REWARDS_MINTED_ROLE": [contracts.lido],
            },
        },
        WITHDRAWAL_QUEUE: {
            "contract_name": "WithdrawalQueue",
            "contract": contracts.withdrawal_queue,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PAUSE_ROLE": [GATE_SEAL],
                "RESUME_ROLE": [],
                "FINALIZE_ROLE": [contracts.lido],
                "ORACLE_ROLE": [contracts.accounting_oracle],
                "MANAGE_TOKEN_URI_ROLE": [],
            },
        },
        ACCOUNTING_ORACLE: {
            "contract_name": "AccountingOracle",
            "contract": contracts.accounting_oracle,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "SUBMIT_DATA_ROLE": [],
                "MANAGE_CONSENSUS_CONTRACT_ROLE": [],
                "MANAGE_CONSENSUS_VERSION_ROLE": [],
            },
        },
        VALIDATORS_EXIT_BUS_ORACLE: {
            "contract_name": "ValidatorsExitBusOracle",
            "contract": contracts.validators_exit_bus_oracle,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "SUBMIT_DATA_ROLE": [],
                "PAUSE_ROLE": [GATE_SEAL],
                "RESUME_ROLE": [],
                "MANAGE_CONSENSUS_CONTRACT_ROLE": [],
                "MANAGE_CONSENSUS_VERSION_ROLE": [],
            },
        },
        HASH_CONSENSUS_FOR_AO: {
            "contract_name": "HashConsensusForAccountingOracle",
            "contract": contracts.hash_consensus_for_accounting_oracle,
            "type": "CustomApp",
            "state": {"getMembers": (ORACLE_COMMITTEE, contracts.hash_consensus_for_accounting_oracle.getMembers()[1])},
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "MANAGE_MEMBERS_AND_QUORUM_ROLE": [contracts.agent],
                "DISABLE_CONSENSUS_ROLE": [],
                "MANAGE_FRAME_CONFIG_ROLE": [],
                "MANAGE_FAST_LANE_CONFIG_ROLE": [],
                "MANAGE_REPORT_PROCESSOR_ROLE": [],
            },
        },
        HASH_CONSENSUS_FOR_VEBO: {
            "contract_name": "HashConsensusForValidatorsExitBusOracle",
            "contract": contracts.hash_consensus_for_validators_exit_bus_oracle,
            "type": "CustomApp",
            "state": {
                "getMembers": (
                    ORACLE_COMMITTEE,
                    contracts.hash_consensus_for_validators_exit_bus_oracle.getMembers()[1],
                )
            },
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "MANAGE_MEMBERS_AND_QUORUM_ROLE": [contracts.agent],
                "DISABLE_CONSENSUS_ROLE": [],
                "MANAGE_FRAME_CONFIG_ROLE": [],
                "MANAGE_FAST_LANE_CONFIG_ROLE": [],
                "MANAGE_REPORT_PROCESSOR_ROLE": [],
            },
        },
        ORACLE_REPORT_SANITY_CHECKER: {
            "contract_name": "OracleReportSanityChecker",
            "contract": contracts.oracle_report_sanity_checker,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "ALL_LIMITS_MANAGER_ROLE": [],
                "CHURN_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE": [],
                "ONE_OFF_CL_BALANCE_DECREASE_LIMIT_MANAGER_ROLE": [],
                "ANNUAL_BALANCE_INCREASE_LIMIT_MANAGER_ROLE": [],
                "SHARE_RATE_DEVIATION_LIMIT_MANAGER_ROLE": [],
                "MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_ROLE": [],
                "MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE": [contracts.agent],
                "MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE": [contracts.agent],
                "REQUEST_TIMESTAMP_MARGIN_MANAGER_ROLE": [],
                "MAX_POSITIVE_TOKEN_REBASE_MANAGER_ROLE": [],
            },
        },
        DEPOSIT_SECURITY_MODULE: {
            "contract_name": "DepositSecurityModule",
            "contract": contracts.deposit_security_module,
            "type": "CustomApp",
            "state": {"getOwner": contracts.agent, "getGuardians": DSM_GUARDIANS},
            "roles": {},
        },
        ORACLE_DAEMON_CONFIG: {
            "contract_name": "OracleDaemonConfig",
            "contract": contracts.oracle_daemon_config,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "CONFIG_MANAGER_ROLE": [],
            },
        },
        ACL: {
            "contract_name": "ACL",
            "contract": contracts.acl,
            "type": "AragonApp",
            "roles": {"CREATE_PERMISSIONS_ROLE": [VOTING]},
        },
        ARAGON_KERNEL: {
            "contract_name": "Kernel",
            "contract": contracts.kernel,
            "type": "AragonApp",
            "roles": {"APP_MANAGER_ROLE": [VOTING]},
        },
        ARAGON_EVMSCRIPT_REGISTRY: {
            "contract_name": "EVMScriptExecutor",
            "contract": contracts.evm_script_registry,
            "type": "AragonApp",
            "roles": {
                "REGISTRY_MANAGER_ROLE": [VOTING],
                "REGISTRY_ADD_EXECUTOR_ROLE": [VOTING],
            },
        },
        TOKEN_MANAGER: {
            "contract_name": "TokenManager",
            "contract": contracts.token_manager,
            "type": "AragonApp",
            "roles": {
                "ISSUE_ROLE": [],
                "ASSIGN_ROLE": [VOTING],
                "BURN_ROLE": [],
                "MINT_ROLE": [],
                "REVOKE_VESTINGS_ROLE": [],
            },
        },
        LIDO: {
            "contract_name": "Lido",
            "contract": contracts.lido,
            "type": "AragonApp",
            "roles": {
                "PAUSE_ROLE": [VOTING],
                "STAKING_CONTROL_ROLE": [VOTING],
                "RESUME_ROLE": [VOTING],
                "STAKING_PAUSE_ROLE": [VOTING],
                "UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE": [],
            },
        },
        AGENT: {
            "contract_name": "Agent",
            "contract": contracts.agent,
            "type": "AragonApp",
            "roles": {
                "ADD_PROTECTED_TOKEN_ROLE": [],
                "SAFE_EXECUTE_ROLE": [],
                "REMOVE_PROTECTED_TOKEN_ROLE": [],
                "DESIGNATE_SIGNER_ROLE": [],
                "ADD_PRESIGNED_HASH_ROLE": [],
                "EXECUTE_ROLE": [VOTING],
                "RUN_SCRIPT_ROLE": [VOTING],
                "TRANSFER_ROLE": [FINANCE],
            },
        },
        FINANCE: {
            "contract_name": "Finance",
            "contract": contracts.finance,
            "type": "AragonApp",
            "roles": {
                "CHANGE_PERIOD_ROLE": [],
                "CHANGE_BUDGETS_ROLE": [],
                "EXECUTE_PAYMENTS_ROLE": [VOTING],
                "MANAGE_PAYMENTS_ROLE": [VOTING],
                "CREATE_PAYMENTS_ROLE": [VOTING, EASYTRACK_EVMSCRIPT_EXECUTOR],
            },
        },
        VOTING: {
            "contract_name": "Voting",
            "contract": contracts.voting,
            "type": "AragonApp",
            "roles": {
                "UNSAFELY_MODIFY_VOTE_TIME_ROLE": [],
                "MODIFY_QUORUM_ROLE": [VOTING],
                "MODIFY_SUPPORT_ROLE": [VOTING],
                "CREATE_VOTES_ROLE": [TOKEN_MANAGER],
            },
        },
        NODE_OPERATORS_REGISTRY: {
            "contract_name": "NodeOperatorsRegistry",
            "contract": contracts.node_operators_registry,
            "type": "AragonApp",
            "roles": {
                "MANAGE_SIGNING_KEYS": [VOTING],
                "MANAGE_NODE_OPERATOR_ROLE": [AGENT, VOTING],
                "SET_NODE_OPERATOR_LIMIT_ROLE": [VOTING, EASYTRACK_EVMSCRIPT_EXECUTOR],
                "STAKING_ROUTER_ROLE": [STAKING_ROUTER],
            },
        },
        SIMPLE_DVT: {
            "contract_name": "NodeOperatorsRegistry",
            "contract": contracts.simple_dvt,
            "type": "AragonApp",
            "roles": {
                "MANAGE_NODE_OPERATOR_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
                "MANAGE_SIGNING_KEYS": [EASYTRACK_EVMSCRIPT_EXECUTOR],
                "SET_NODE_OPERATOR_LIMIT_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
                "STAKING_ROUTER_ROLE": [STAKING_ROUTER, EASYTRACK_EVMSCRIPT_EXECUTOR],
            },
        },
        LEGACY_ORACLE: {
            "contract_name": "LegacyOracle",
            "contract": contracts.legacy_oracle,
            "type": "AragonApp",
            "roles": {},
        },
    }


def test_protocol_permissions(protocol_permissions):
    aragon_acl_active_permissions = active_aragon_roles(protocol_permissions)

    for contract_address, permissions_config in protocol_permissions.items():
        print("Contract: {0} {1}".format(contract_address, permissions_config["contract_name"]))

        abi_roles_list = [
            method for method in permissions_config["contract"].signatures.keys() if method.endswith("_ROLE")
        ]

        if contract_address in [NODE_OPERATORS_REGISTRY, SIMPLE_DVT]:
            abi_roles_list.append("MANAGE_SIGNING_KEYS")

        roles = permissions_config["roles"]

        assert len(abi_roles_list) == len(
            roles.keys()
        ), "Contract {} . number of roles doesn't match. expected {} actual {}".format(
            permissions_config["contract_name"], abi_roles_list, roles.keys()
        )
        for role in set(permissions_config["roles"].keys()):
            assert role in abi_roles_list, "no {} described for contract {}".format(
                role, permissions_config["contract_name"]
            )

        if permissions_config["type"] == "AragonApp":
            for role, holders in permissions_config["roles"].items():
                current_holders = (
                    aragon_acl_active_permissions[contract_address][role]
                    if role in aragon_acl_active_permissions[contract_address]
                    else []
                )

                # temp ugly hack to exclude parametrized role members (OP managers) for SIMPLE_DVT
                if contract_address == SIMPLE_DVT and role == "MANAGE_SIGNING_KEYS":
                    current_holders = [h for h in current_holders if h == EASYTRACK_EVMSCRIPT_EXECUTOR]

                assert len(current_holders) == len(
                    holders
                ), "number of {} role holders in contract {} mismatched expected {} , actual {} ".format(
                    role, permissions_config["contract_name"], holders, current_holders
                )

                for holder in holders:
                    assert holder in current_holders, "Entity {} has no role {} at {}".format(
                        holder, role, permissions_config["contract_name"]
                    )

                for holder in current_holders:
                    assert holder in holders, "Unexpected entity {} has role {} at {}".format(
                        holder, role, permissions_config["contract_name"]
                    )

        elif permissions_config["type"] == "CustomApp":
            if "proxy_owner" in permissions_config:
                assert (
                    interface.OssifiableProxy(permissions_config["contract"].address).proxy__getAdmin()
                    == permissions_config["proxy_owner"]
                )

            for role, holders in permissions_config["roles"].items():
                role_keccak = web3.keccak(text=role).hex() if role != "DEFAULT_ADMIN_ROLE" else ZERO_BYTES32.hex()

                role_signature = permissions_config["contract"].signatures[role]
                assert permissions_config["contract"].get_method_object(role_signature)() == role_keccak

                assert permissions_config["contract"].getRoleMemberCount(role_keccak) == len(
                    holders
                ), "number of {0} role holders in contract {1} mismatched".format(
                    role, permissions_config["contract_name"]
                )

                for holder in holders:
                    assert permissions_config["contract"].hasRole(
                        role_keccak, holder
                    ), "account {0} isn't holder of role {1} at contract {2}".format(
                        holder, role, permissions_config["contract_name"]
                    )

        if "state" in permissions_config:
            for method, value in permissions_config["state"].items():
                method_sig = permissions_config["contract"].signatures[method]
                actual_value = permissions_config["contract"].get_method_object(method_sig)()
                assert actual_value == value, "method {} returns {} instead of {}".format(method, actual_value, value)


def has_permissions(app, role, entity):
    return (
        contracts.acl.hasPermission(entity, app, role) or contracts.acl.getPermissionParamsLength(entity, app, role) > 0
    )


def collect_permissions_from_events(permission_events):
    apps = {}
    for event in permission_events:
        if event["allowed"] == True:
            if event["app"] not in apps:
                apps[event["app"]] = {str(event["role"]): [event["entity"]]}
            elif event["app"] in apps:
                if str(event["role"]) not in apps[event["app"]]:
                    apps[event["app"]][str(event["role"])] = [event["entity"]]
                else:
                    apps[event["app"]][str(event["role"])].append(event["entity"])

    return apps


def active_aragon_roles(protocol_permissions):
    w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{os.getenv("WEB3_INFURA_PROJECT_ID")}'))

    event_signature_hash = w3.keccak(text="SetPermission(address,address,bytes32,bool)").hex()
    events_before_voting = w3.eth.filter(
        {"address": contracts.acl.address, "fromBlock": ACL_DEPLOY_BLOCK_NUMBER, "topics": [event_signature_hash]}
    ).get_all_entries()

    permission_events = _decode_logs(events_before_voting)["SetPermission"]._ordered

    history = TxHistory()
    if len(history) > 0:
        vote_block = history[0].block_number

        events_after_voting = web3.eth.filter(
            {"address": contracts.acl.address, "fromBlock": vote_block, "topics": [event_signature_hash]}
        ).get_all_entries()

        try:
            permission_events_after_voting = _decode_logs(events_after_voting)["SetPermission"]._ordered
            permission_events.extend(permission_events_after_voting)
        except EventLookupError as e:
            print(e)
    events_by_app = collect_permissions_from_events(permission_events)

    active_permissions = {}
    for event_app, event_roles in events_by_app.items():
        active_permissions[event_app] = {}
        keccak_roles = dict(
            zip(
                [w3.keccak(text=role).hex() for role in protocol_permissions[event_app]["roles"]],
                protocol_permissions[event_app]["roles"],
            )
        )

        for event_role in event_roles:
            event_entities = event_roles[event_role]
            active_entities = []

            for event_entity in event_entities:
                if has_permissions(app=event_app, role=event_role, entity=event_entity):
                    active_entities.append(event_entity)

            if len(active_entities) > 0:
                active_permissions[event_app][keccak_roles[event_role]] = list(set(active_entities))

    return active_permissions
