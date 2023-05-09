"""
Tests for voting ??/05/2023
"""
import pytest

from brownie import web3, interface, convert
from utils.config import (
    contracts,
    VOTING,
    WITHDRAWAL_VAULT_IMPL_V1,
    LIDO_LOCATOR_IMPL,
    DUMMY_IMPL,
)
from utils.test.event_validators.permission import Permission


@pytest.fixture(scope="module")
def protocol_preliminary_permissions(shapella_upgrade_template):
    template = shapella_upgrade_template.address
    return {
        "Withdrawal_vault": {
            "contract": interface.WithdrawalVaultManager(contracts.withdrawal_vault.address),
            "type": "WithdrawalsManagerProxy",
            "state": {
                "implementation": WITHDRAWAL_VAULT_IMPL_V1,
                "proxy_getAdmin": VOTING,
            },
        },
        # empty proxies _assertAdminsOfProxies
        "LidoLocator": {
            "contract": interface.OssifiableProxy(contracts.lido_locator.address),
            "type": "Proxy",
            "proxy_owner": template,
            "state": {"proxy__getImplementation": LIDO_LOCATOR_IMPL},
        },
        "StakingRouter": {
            "contract": interface.OssifiableProxy(contracts.staking_router.address),
            "type": "CustomApp",
            "proxy_owner": template,
            "state": {"proxy__getImplementation": DUMMY_IMPL},
        },
        "WithdrawalQueue": {
            "contract": interface.OssifiableProxy(contracts.withdrawal_queue.address),
            "type": "Proxy",
            "proxy_owner": template,
            "state": {"proxy__getImplementation": DUMMY_IMPL},
        },
        "AccountingOracle": {
            "contract": interface.OssifiableProxy(contracts.accounting_oracle.address),
            "type": "Proxy",
            "proxy_owner": template,
            "state": {"proxy__getImplementation": DUMMY_IMPL},
        },
        "ValidatorsExitBusOracle": {
            "contract": interface.OssifiableProxy(contracts.validators_exit_bus_oracle.address),
            "type": "Proxy",
            "proxy_owner": template,
            "state": {"proxy__getImplementation": DUMMY_IMPL},
        },
        # _depositSecurityModule.getOwner()
        "DepositSecurityModule": {
            "contract": contracts.deposit_security_module,
            "type": "CustomApp",
            "state": {"getOwner": template, "getGuardians": []},
            "roles": {},
        },
        # _assertOracleDaemonConfigRoles
        "OracleDaemonConfig": {
            "contract": contracts.oracle_daemon_config,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "CONFIG_MANAGER_ROLE": [],
            },
        },
        # _assertOracleReportSanityCheckerRoles
        "OracleReportSanityChecker": {
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
                "MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE": [],
                "MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE": [],
                "REQUEST_TIMESTAMP_MARGIN_MANAGER_ROLE": [],
                "MAX_POSITIVE_TOKEN_REBASE_MANAGER_ROLE": [],
            },
        },
        # IBurner burner = _burner;
        "Burner": {
            "contract": contracts.burner,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [template],
                "REQUEST_BURN_MY_STETH_ROLE": [],
                "REQUEST_BURN_SHARES_ROLE": [contracts.lido],
            },
        },
        #  _assertSingleOZRoleHolder(_hashConsensusForAccountingOracle,
        "AccountingHashConsensus": {
            "contract": contracts.hash_consensus_for_accounting_oracle,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [template],
                "MANAGE_MEMBERS_AND_QUORUM_ROLE": [],
                "DISABLE_CONSENSUS_ROLE": [],
                "MANAGE_FRAME_CONFIG_ROLE": [],
                "MANAGE_FAST_LANE_CONFIG_ROLE": [],
                "MANAGE_REPORT_PROCESSOR_ROLE": [],
            },
        },
        #  _assertSingleOZRoleHolder(_hashConsensusForValidatorsExitBusOracle,
        "ValidatorsExitBusHashConsensus": {
            "contract": contracts.hash_consensus_for_validators_exit_bus_oracle,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [template],
                "MANAGE_MEMBERS_AND_QUORUM_ROLE": [],
                "DISABLE_CONSENSUS_ROLE": [],
                "MANAGE_FRAME_CONFIG_ROLE": [],
                "MANAGE_FAST_LANE_CONFIG_ROLE": [],
                "MANAGE_REPORT_PROCESSOR_ROLE": [],
            },
        },
        # additional checks
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
                "STAKING_ROUTER_ROLE": [],
                "MANAGE_NODE_OPERATOR_ROLE": [],
                "MANAGE_SIGNING_KEYS": [contracts.voting],
                "SET_NODE_OPERATOR_LIMIT_ROLE": [contracts.voting],
            },
        },
    }


def test_permissions_before_vote(protocol_preliminary_permissions):
    for contract_name, permissions_config in protocol_preliminary_permissions.items():
        print("Contract: {0}".format(contract_name))

        abi_roles_list = [
            method for method in permissions_config["contract"].signatures.keys() if method.endswith("_ROLE")
        ]

        if contract_name == "NodeOperatorsRegistry":
            abi_roles_list.append("MANAGE_SIGNING_KEYS")

        if "roles" in permissions_config:
            roles = permissions_config["roles"]

            assert len(abi_roles_list) == len(
                roles.keys()
            ), "number of roles doesn't match. expected {} actual {}".format(abi_roles_list, roles.keys())
            for role in set(permissions_config["roles"].keys()):
                assert role in abi_roles_list, "no {} described for contract {}".format(role, contract_name)

        if permissions_config["type"] == "AragonApp" and "roles" in permissions_config:
            for role, holders in permissions_config["roles"].items():
                for holder in holders:
                    permission = Permission(
                        entity=holder, app=permissions_config["contract"], role=convert.to_uint(web3.keccak(text=role))
                    )
                    assert contracts.acl.hasPermission(*permission), "account {0} isn't holder of {1}".format(
                        holder, role
                    )

        elif permissions_config["type"] == "CustomApp":
            if "proxy_owner" in permissions_config:
                assert (
                    interface.OssifiableProxy(permissions_config["contract"].address).proxy__getAdmin()
                    == permissions_config["proxy_owner"]
                )

            if "roles" in permissions_config:
                for role, holders in permissions_config["roles"].items():
                    role_keccak = web3.keccak(text=role) if role != "DEFAULT_ADMIN_ROLE" else "0x00"

                    assert permissions_config["contract"].getRoleMemberCount(role_keccak) == len(
                        holders
                    ), "number of {0} role holders in contract {1} mismatched".format(role, contract_name)

                    for holder in holders:
                        assert permissions_config["contract"].hasRole(
                            role_keccak, holder
                        ), "account {0} isn't holder of {1}".format(holder, role)
        elif permissions_config["type"] == "Proxy":
            if "proxy_owner" in permissions_config:
                assert (
                    interface.OssifiableProxy(permissions_config["contract"].address).proxy__getAdmin()
                    == permissions_config["proxy_owner"]
                )

        if "state" in permissions_config:
            for method, value in permissions_config["state"].items():
                method_sig = permissions_config["contract"].signatures[method]
                actual_value = permissions_config["contract"].get_method_object(method_sig)()
                assert actual_value == value, "method {} returns {} instead of {}".format(method, actual_value, value)
