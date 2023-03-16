"""
Tests for permissions setup
"""
import pytest

from brownie import interface, convert, web3
from utils.test.event_validators.permission import Permission, PermissionP
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from utils.config import contracts, oracle_committee, gate_seal, guardians


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(vote_id_from_env, helpers, accounts):
    if vote_id_from_env:
        helpers.execute_vote(vote_id=vote_id_from_env, accounts=accounts, voting=contracts.voting, topup="0.5 ether")
    else:
        start_and_execute_votes(helpers)


@pytest.fixture(scope="module")
def protocol_permissions():
    return {
        "LidoLocator": {
            "contract": contracts.lido_locator,
            "type": "CustomApp",
            "proxy_owner": contracts.voting,
            "roles": {},
        },
        "Burner": {
            "contract": contracts.burner,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
                "REQUEST_BURN_MY_STETH_ROLE": [],
                "RECOVER_ASSETS_ROLE": [],
                "REQUEST_BURN_SHARES_ROLE": [contracts.lido, contracts.node_operators_registry],
            },
        },
        "StakingRouter": {
            "contract": contracts.staking_router,
            "type": "CustomApp",
            "proxy_owner": contracts.voting,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
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
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
                "PAUSE_ROLE": [gate_seal],
                "RESUME_ROLE": [],
                "FINALIZE_ROLE": [contracts.lido],
                "ORACLE_ROLE": [contracts.accounting_oracle],
                "MANAGE_TOKEN_URI_ROLE": []
            }
        },
        "AccountingOracle": {
            "contract": contracts.accounting_oracle,
            "type": "CustomApp",
            "proxy_owner": contracts.voting,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
                "SUBMIT_DATA_ROLE": oracle_committee,
                "MANAGE_CONSENSUS_CONTRACT_ROLE": [],
                "MANAGE_CONSENSUS_VERSION_ROLE": [],
            },
        },
        "ValidatorsExitBusOracle": {
            "contract": contracts.validators_exit_bus_oracle,
            "type": "CustomApp",
            "proxy_owner": contracts.voting,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
                "SUBMIT_DATA_ROLE": oracle_committee,
                "PAUSE_ROLE": [gate_seal],
                "RESUME_ROLE": [],
                "MANAGE_CONSENSUS_CONTRACT_ROLE": [],
                "MANAGE_CONSENSUS_VERSION_ROLE": []
            }
        },
        "AccountingHashConsensus": {
            "contract": contracts.hash_consensus_for_accounting_oracle,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
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
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
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
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
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
            # "fields": {"getOwner": contracts.voting, "getGuardians": guardians},
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
            },
        },
    }


def test_permissions_after_vote(protocol_permissions):
    for contract_name, permissions_config in protocol_permissions.items():
        print("Contract: {0}".format(contract_name))
        if permissions_config["type"] == "AragonApp":
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

            for role, holders in permissions_config["roles"].items():
                role_keccak = web3.keccak(text=role) if role != "DEFAULT_ADMIN_ROLE" else "0x00"

                assert permissions_config["contract"].getRoleMemberCount(role_keccak) == len(
                    holders
                ), "number of {0} role holders in contract {1} mismatched".format(role, contract_name)

                for holder in holders:
                    assert permissions_config["contract"].hasRole(
                        role_keccak, holder
                    ), "account {0} isn't holder of {1}".format(holder, role)
