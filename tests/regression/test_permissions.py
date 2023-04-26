"""
Tests for permissions setup
"""
import pytest

from brownie import interface, convert, web3
from utils.test.event_validators.permission import Permission
from utils.config import contracts, oracle_committee, gate_seal_address, deposit_security_module_guardians
from utils.config_mainnet import (
    lido_easytrack_evmscriptexecutor, lido_easytrack_evmscriptexecutor)


@pytest.fixture(scope="module")
def protocol_permissions():
    return {
        "LidoLocator": {
            "contract": contracts.lido_locator,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {},
        },
        "Burner": {
            "contract": contracts.burner,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "REQUEST_BURN_MY_STETH_ROLE": [],
                "RECOVER_ASSETS_ROLE": [],
                "REQUEST_BURN_SHARES_ROLE": [contracts.lido, contracts.node_operators_registry],
            },
        },
        "StakingRouter": {
            "contract": contracts.staking_router,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "MANAGE_WITHDRAWAL_CREDENTIALS_ROLE": [],
                "STAKING_MODULE_PAUSE_ROLE": [contracts.deposit_security_module],
                "STAKING_MODULE_RESUME_ROLE": [contracts.deposit_security_module],
                "STAKING_MODULE_MANAGE_ROLE": [],
                "REPORT_EXITED_VALIDATORS_ROLE": [contracts.accounting_oracle],
                "UNSAFE_SET_EXITED_VALIDATORS_ROLE": [],
                "REPORT_REWARDS_MINTED_ROLE": [contracts.lido],
            },
        },
        "WithdrawalQueue": {
            "contract": contracts.withdrawal_queue,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PAUSE_ROLE": [gate_seal_address],
                "RESUME_ROLE": [],
                "FINALIZE_ROLE": [contracts.lido],
                "ORACLE_ROLE": [contracts.accounting_oracle],
                "MANAGE_TOKEN_URI_ROLE": [],
            },
        },
        "AccountingOracle": {
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
        "ValidatorsExitBusOracle": {
            "contract": contracts.validators_exit_bus_oracle,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "SUBMIT_DATA_ROLE": [],
                "PAUSE_ROLE": [gate_seal_address],
                "RESUME_ROLE": [],
                "MANAGE_CONSENSUS_CONTRACT_ROLE": [],
                "MANAGE_CONSENSUS_VERSION_ROLE": [],
            },
        },
        "AccountingHashConsensus": {
            "contract": contracts.hash_consensus_for_accounting_oracle,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "MANAGE_MEMBERS_AND_QUORUM_ROLE": [],
                "DISABLE_CONSENSUS_ROLE": [],
                "MANAGE_FRAME_CONFIG_ROLE": [],
                "MANAGE_FAST_LANE_CONFIG_ROLE": [],
                "MANAGE_REPORT_PROCESSOR_ROLE": [],
            },
        },
        "ValidatorsExitBusHashConsensus": {
            "contract": contracts.hash_consensus_for_validators_exit_bus_oracle,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "MANAGE_MEMBERS_AND_QUORUM_ROLE": [],
                "DISABLE_CONSENSUS_ROLE": [],
                "MANAGE_FRAME_CONFIG_ROLE": [],
                "MANAGE_FAST_LANE_CONFIG_ROLE": [],
                "MANAGE_REPORT_PROCESSOR_ROLE": [],
            },
        },
        "OracleReportSanityChecker": {
            "contract": contracts.oracle_report_sanity_checker,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "ALL_LIMITS_MANAGER_ROLE": [],
                "CHURN_VALIDATORS_PER_DAY_LIMIT_MANGER_ROLE": [],
                "ONE_OFF_CL_BALANCE_DECREASE_LIMIT_MANAGER_ROLE": [],
                "ANNUAL_BALANCE_INCREASE_LIMIT_MANAGER_ROLE": [],
                "SHARE_RATE_DEVIATION_LIMIT_MANAGER_ROLE": [],
                "MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_ROLE": [],
                "MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE": [],
                "MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE": [],
                "REQUEST_TIMESTAMP_MARGIN_MANAGER_ROLE": [],
                "MAX_POSITIVE_TOKEN_REBASE_MANAGER_ROLE": [],
            },
        },
        "DepositSecurityModule": {
            "contract": contracts.deposit_security_module,
            "type": "CustomApp",
            "state": {"getOwner": contracts.agent, "getGuardians": deposit_security_module_guardians},
            "roles": {},
        },
        "Lido": {
            "contract": contracts.lido,
            "type": "AragonApp",
            "roles": {
                "PAUSE_ROLE": [contracts.voting],
                "RESUME_ROLE": [contracts.voting],
                "STAKING_PAUSE_ROLE": [contracts.voting],
                "STAKING_CONTROL_ROLE": [contracts.voting],
                "UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE": [],
            },
        },
        "NodeOperatorsRegistry": {
            "contract": contracts.node_operators_registry,
            "type": "AragonApp",
            "roles": {
                "STAKING_ROUTER_ROLE": [contracts.staking_router],
                "MANAGE_NODE_OPERATOR_ROLE": [],
                "MANAGE_SIGNING_KEYS": [contracts.voting],
                "SET_NODE_OPERATOR_LIMIT_ROLE": [contracts.voting],
                "SET_NODE_OPERATOR_LIMIT_ROLE": [lido_easytrack_evmscriptexecutor, contracts.voting]
            },
        },
        "OracleDaemonConfig": {
            "contract": contracts.oracle_daemon_config,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "CONFIG_MANAGER_ROLE": [],
            },
        },
    }


def test_permissions_after_vote(protocol_permissions):
    for contract_name, permissions_config in protocol_permissions.items():
        print("Contract: {0}".format(contract_name))

        abi_roles_list = [
            method for method in permissions_config["contract"].signatures.keys() if method.endswith("_ROLE")
        ]

        if contract_name == "NodeOperatorsRegistry":
            abi_roles_list.append("MANAGE_SIGNING_KEYS")

        roles = permissions_config["roles"]

        assert len(abi_roles_list) == len(roles.keys()), "number of roles doesn't match. expected {} actual {}".format(
            abi_roles_list, roles.keys()
        )
        for role in set(permissions_config["roles"].keys()):
            assert role in abi_roles_list, "no {} described for contract {}".format(
                role, contract_name)

        if permissions_config["type"] == "AragonApp":
            for role, holders in permissions_config["roles"].items():
                for holder in holders:
                    permission = Permission(
                        entity=holder, app=permissions_config["contract"], role=convert.to_uint(
                            web3.keccak(text=role))
                    )
                    assert contracts.acl.hasPermission(
                        *permission
                    ), "account {0} isn't holder of role {1} at contract {2}".format(holder, role, contract_name)

        elif permissions_config["type"] == "CustomApp":
            if "proxy_owner" in permissions_config:
                assert (
                    interface.OssifiableProxy(
                        permissions_config["contract"].address).proxy__getAdmin()
                    == permissions_config["proxy_owner"]
                )

            for role, holders in permissions_config["roles"].items():
                role_keccak = web3.keccak(
                    text=role) if role != "DEFAULT_ADMIN_ROLE" else "0x00"

                assert permissions_config["contract"].getRoleMemberCount(role_keccak) == len(
                    holders
                ), "number of {0} role holders in contract {1} mismatched".format(role, contract_name)

                for holder in holders:
                    assert permissions_config["contract"].hasRole(
                        role_keccak, holder
                    ), "account {0} isn't holder of role {1} at contract {2}".format(holder, role, contract_name)

        if "state" in permissions_config:
            for method, value in permissions_config["state"].items():
                method_sig = permissions_config["contract"].signatures[method]
                actual_value = permissions_config["contract"].get_method_object(
                    method_sig)()
                assert actual_value == value, "method {} returns {} instead of {}".format(
                    method, actual_value, value)
