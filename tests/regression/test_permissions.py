"""
Tests for permissions setup
"""

import pytest
import os

from tqdm import tqdm
from web3 import Web3
from brownie import interface, web3
from brownie.network.event import _decode_logs
from brownie.network.state import TxHistory

from configs.config_mainnet import CSM_COMMITTEE_MS, CURATED_MANAGE_SIGNING_KEYS_HOLDERS
from utils.test.helpers import ZERO_BYTES32
from utils.permission_parameters import ArgumentValue, Op, Param
from brownie.exceptions import EventLookupError
from utils.config import (
    contracts,
    CIRCUIT_BREAKER,
    GATE_SEAL,
    DSM_GUARDIANS,
    ORACLE_COMMITTEE,
    AGENT,
    EASYTRACK,
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
    WITHDRAWAL_VAULT,
    ORACLE_DAEMON_CONFIG,
    DEPOSIT_SECURITY_MODULE,
    ORACLE_REPORT_SANITY_CHECKER,
    HASH_CONSENSUS_FOR_VEBO,
    HASH_CONSENSUS_FOR_AO,
    VALIDATORS_EXIT_BUS_ORACLE,
    VEB_TWG_GATE_SEAL,
    ACCOUNTING_ORACLE,
    WITHDRAWAL_QUEUE,
    BURNER,
    LIDO_LOCATOR,
    LEGACY_ORACLE,
    SIMPLE_DVT,
    CSM_ADDRESS,
    CS_ACCOUNTING_ADDRESS,
    CS_EJECTOR_V3_ADDRESS,
    CS_GATE_SEAL_V2_ADDRESS,
    CS_IDENTIFIED_DVT_CLUSTER_GATE_ADDRESS,
    CS_PERMISSIONLESS_GATE_V3_ADDRESS,
    CS_VERIFIER_V2_ADDRESS,
    CS_VERIFIER_V3_ADDRESS,
    CS_FEE_DISTRIBUTOR_ADDRESS,
    CS_FEE_ORACLE_ADDRESS,
    CS_ORACLE_HASH_CONSENSUS_ADDRESS,
    CS_PERMISSIONLESS_GATE_ADDRESS,
    TRIGGERABLE_WITHDRAWALS_GATEWAY,
    TOP_UP_GATEWAY,
    TOP_UP_GATEWAY_DEPOSITOR,
    CONSOLIDATION_GATEWAY,
    CONSOLIDATION_BUS,
    CONSOLIDATION_MIGRATOR,
    CONSOLIDATION_COMMITTEE,
    VEB_TWG_GATE_SEAL,
    CS_VETTED_GATE_ADDRESS,
    CS_PARAMS_REGISTRY_ADDRESS,
    CS_STRIKES_ADDRESS,
    CS_EJECTOR_ADDRESS,
    CM_ACCOUNTING_ADDRESS,
    CM_EJECTOR_ADDRESS,
    L1_EMERGENCY_BRAKES_MULTISIG,
    DUAL_GOVERNANCE_EXECUTORS,
    RESEAL_MANAGER,
    INSURANCE_FUND,
    VAULT_HUB,
    OPERATOR_GRID,
    LAZY_ORACLE,
    ACCOUNTING,
    PREDEPOSIT_GUARANTEE,
    VAULTS_ADAPTER,
    GATE_SEAL_V3,
    L1_TOKEN_RATE_NOTIFIER,
    STAKING_VAULT_BEACON,
    TWO_PHASE_FRAME_CONFIG_UPDATE,
)


@pytest.fixture(scope="function")
def protocol_permissions():
    is_csm_v3 = contracts.csm.getInitializedVersion() >= 3
    csm_pause_manager = CIRCUIT_BREAKER
    cs_ejector_address = CS_EJECTOR_V3_ADDRESS if is_csm_v3 else CS_EJECTOR_ADDRESS
    cs_permissionless_gate_address = CS_PERMISSIONLESS_GATE_V3_ADDRESS if is_csm_v3 else CS_PERMISSIONLESS_GATE_ADDRESS
    cs_verifier = (
        interface.Verifier(CS_VERIFIER_V3_ADDRESS) if is_csm_v3 else interface.CSVerifierV2(CS_VERIFIER_V2_ADDRESS)
    )
    cs_verifier_address = cs_verifier.address
    burner_request_burn_my_steth_holders = [CS_ACCOUNTING_ADDRESS, CM_ACCOUNTING_ADDRESS] if is_csm_v3 else []
    burner_request_burn_shares_holders = [contracts.accounting]
    if not is_csm_v3:
        burner_request_burn_shares_holders.append(CS_ACCOUNTING_ADDRESS)
    csm_create_node_operator_holders = [cs_permissionless_gate_address, CS_VETTED_GATE_ADDRESS]
    if is_csm_v3:
        csm_create_node_operator_holders.append(CS_IDENTIFIED_DVT_CLUSTER_GATE_ADDRESS)
    cs_accounting_set_bond_curve_holders = [CS_VETTED_GATE_ADDRESS, CSM_COMMITTEE_MS]
    if is_csm_v3:
        cs_accounting_set_bond_curve_holders.append(CS_IDENTIFIED_DVT_CLUSTER_GATE_ADDRESS)
    twg_full_withdrawal_request_holders = [VALIDATORS_EXIT_BUS_ORACLE, cs_ejector_address]
    if is_csm_v3:
        twg_full_withdrawal_request_holders.append(CM_EJECTOR_ADDRESS)
    csm_roles = {
        "DEFAULT_ADMIN_ROLE": [contracts.agent],
        "STAKING_ROUTER_ROLE": [STAKING_ROUTER],
        "PAUSE_ROLE": [csm_pause_manager, RESEAL_MANAGER],
        "REPORT_EL_REWARDS_STEALING_PENALTY_ROLE": [] if is_csm_v3 else [CSM_COMMITTEE_MS],
        "SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE": [] if is_csm_v3 else [EASYTRACK_EVMSCRIPT_EXECUTOR],
        "CREATE_NODE_OPERATOR_ROLE": csm_create_node_operator_holders,
        "VERIFIER_ROLE": [cs_verifier_address],
        "RESUME_ROLE": [RESEAL_MANAGER],
        "RECOVERER_ROLE": [],
    }
    if is_csm_v3:
        csm_roles.update(
            {
                "MANAGE_TOP_UP_QUEUE_ROLE": [],
                "REWIND_TOP_UP_QUEUE_ROLE": [],
                "OPERATOR_ADDRESSES_ADMIN_ROLE": [],
                "REPORT_GENERAL_DELAYED_PENALTY_ROLE": [CSM_COMMITTEE_MS],
                "SETTLE_GENERAL_DELAYED_PENALTY_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
                "REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE": [cs_verifier_address],
                "REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
            }
        )
    csm_ignored_abi_roles = set()
    if not is_csm_v3:
        csm_ignored_abi_roles.update(
            {
                "MANAGE_TOP_UP_QUEUE_ROLE",
                "REWIND_TOP_UP_QUEUE_ROLE",
                "OPERATOR_ADDRESSES_ADMIN_ROLE",
                "REPORT_GENERAL_DELAYED_PENALTY_ROLE",
                "SETTLE_GENERAL_DELAYED_PENALTY_ROLE",
                "REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                "REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE",
            }
        )
    csm_role_preimages = {
        "REPORT_EL_REWARDS_STEALING_PENALTY_ROLE": "REPORT_EL_REWARDS_STEALING_PENALTY_ROLE",
        "SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE": "SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE",
    }
    if is_csm_v3:
        csm_role_preimages.update(
            {
                "REPORT_GENERAL_DELAYED_PENALTY_ROLE": "REPORT_GENERAL_DELAYED_PENALTY_ROLE",
                "SETTLE_GENERAL_DELAYED_PENALTY_ROLE": "SETTLE_GENERAL_DELAYED_PENALTY_ROLE",
                "REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE": "REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                "REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE": "REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE",
            }
        )
    vetted_gate_roles = {
        "DEFAULT_ADMIN_ROLE": [contracts.agent],
        "PAUSE_ROLE": [csm_pause_manager, RESEAL_MANAGER],
        "RESUME_ROLE": [RESEAL_MANAGER],
        "RECOVERER_ROLE": [],
        "SET_TREE_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
    }
    if not is_csm_v3:
        vetted_gate_roles.update(
            {
                "START_REFERRAL_SEASON_ROLE": [contracts.agent],
                "END_REFERRAL_SEASON_ROLE": [CSM_COMMITTEE_MS],
            }
        )
    vetted_gate_role_preimages = {}
    if not is_csm_v3:
        vetted_gate_role_preimages.update(
            {
                "START_REFERRAL_SEASON_ROLE": "START_REFERRAL_SEASON_ROLE",
                "END_REFERRAL_SEASON_ROLE": "END_REFERRAL_SEASON_ROLE",
            }
        )
    cs_parameters_registry_roles = {
        "DEFAULT_ADMIN_ROLE": [contracts.agent],
        "MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE": [CSM_COMMITTEE_MS] if is_csm_v3 else [],
        "MANAGE_KEYS_LIMIT_ROLE": [],
        "MANAGE_QUEUE_CONFIG_ROLE": [],
        "MANAGE_PERFORMANCE_PARAMETERS_ROLE": [],
        "MANAGE_REWARD_SHARE_ROLE": [],
        "MANAGE_VALIDATOR_EXIT_PARAMETERS_ROLE": [],
        "MANAGE_CURVE_PARAMETERS_ROLE": [],
    }

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
                "REQUEST_BURN_MY_STETH_ROLE": burner_request_burn_my_steth_holders,
                "REQUEST_BURN_SHARES_ROLE": burner_request_burn_shares_holders,
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
                "STAKING_MODULE_UNVETTING_ROLE": [contracts.deposit_security_module],
                "STAKING_MODULE_MANAGE_ROLE": [contracts.agent],
                "STAKING_MODULE_SHARE_MANAGE_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
                "REPORT_EXITED_VALIDATORS_ROLE": [contracts.accounting_oracle],
                "UNSAFE_SET_EXITED_VALIDATORS_ROLE": [],
                "REPORT_REWARDS_MINTED_ROLE": [contracts.accounting],
                "REPORT_VALIDATOR_EXITING_STATUS_ROLE": [contracts.validator_exit_verifier],
                "REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE": [contracts.triggerable_withdrawals_gateway],
            },
        },
        WITHDRAWAL_QUEUE: {
            "contract_name": "WithdrawalQueue",
            "contract": contracts.withdrawal_queue,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PAUSE_ROLE": [CIRCUIT_BREAKER, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
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
                "PAUSE_ROLE": [CIRCUIT_BREAKER, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
                "MANAGE_CONSENSUS_CONTRACT_ROLE": [],
                "MANAGE_CONSENSUS_VERSION_ROLE": [],
                "EXIT_REQUEST_LIMIT_MANAGER_ROLE": [],
                "SUBMIT_REPORT_HASH_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
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
                "EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE": [],
                "APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE": [],
                "ANNUAL_BALANCE_INCREASE_LIMIT_MANAGER_ROLE": [],
                "SHARE_RATE_DEVIATION_LIMIT_MANAGER_ROLE": [],
                "MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_ROLE": [],
                "MAX_ITEMS_PER_EXTRA_DATA_TRANSACTION_ROLE": [],
                "MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_ROLE": [],
                "REQUEST_TIMESTAMP_MARGIN_MANAGER_ROLE": [],
                "MAX_POSITIVE_TOKEN_REBASE_MANAGER_ROLE": [],
                "SECOND_OPINION_MANAGER_ROLE": [],
                "INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE": [],
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
            "roles": {"CREATE_PERMISSIONS_ROLE": [AGENT]},
        },
        ARAGON_KERNEL: {
            "contract_name": "Kernel",
            "contract": contracts.kernel,
            "type": "AragonApp",
            "roles": {"APP_MANAGER_ROLE": []},
        },
        ARAGON_EVMSCRIPT_REGISTRY: {
            "contract_name": "EVMScriptRegistry",
            "contract": contracts.evm_script_registry,
            "type": "AragonApp",
            "roles": {
                "REGISTRY_MANAGER_ROLE": [],
                "REGISTRY_ADD_EXECUTOR_ROLE": [],
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
                "MINT_ROLE": [VOTING],
                "REVOKE_VESTINGS_ROLE": [VOTING],
            },
        },
        LIDO: {
            "contract_name": "Lido",
            "contract": contracts.lido,
            "type": "AragonApp",
            "roles": {
                "PAUSE_ROLE": [],
                "STAKING_CONTROL_ROLE": [],
                "RESUME_ROLE": [],
                "STAKING_PAUSE_ROLE": [],
                "UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE": [],
                "BUFFER_RESERVE_MANAGER_ROLE": [contracts.agent],
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
                "EXECUTE_ROLE": [DUAL_GOVERNANCE_EXECUTORS[0]],
                "RUN_SCRIPT_ROLE": [DUAL_GOVERNANCE_EXECUTORS[0]],
                "TRANSFER_ROLE": [FINANCE],
            },
        },
        FINANCE: {
            "contract_name": "Finance",
            "contract": contracts.finance,
            "type": "AragonApp",
            "roles": {
                "CHANGE_PERIOD_ROLE": [VOTING],
                "CHANGE_BUDGETS_ROLE": [VOTING],
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
                "MANAGE_SIGNING_KEYS": [],
                "MANAGE_NODE_OPERATOR_ROLE": [AGENT],
                "SET_NODE_OPERATOR_LIMIT_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
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
        CSM_ADDRESS: {
            "contract_name": "CSModule",
            "contract": contracts.csm,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": csm_roles,
            "role_preimages": csm_role_preimages,
            "ignored_abi_roles": csm_ignored_abi_roles,
        },
        CS_ACCOUNTING_ADDRESS: {
            "contract_name": "Accounting",
            "contract": contracts.cs_accounting,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "SET_BOND_CURVE_ROLE": cs_accounting_set_bond_curve_holders,
                "PAUSE_ROLE": [csm_pause_manager, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
                "MANAGE_BOND_CURVES_ROLE": [],
                "RECOVERER_ROLE": [],
            },
        },
        CS_FEE_DISTRIBUTOR_ADDRESS: {
            "contract_name": "FeeDistributor",
            "contract": contracts.cs_fee_distributor,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "RECOVERER_ROLE": [],
            },
        },
        CS_FEE_ORACLE_ADDRESS: {
            "contract_name": "FeeOracle",
            "contract": contracts.cs_fee_oracle,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "MANAGE_CONSENSUS_CONTRACT_ROLE": [],
                "MANAGE_CONSENSUS_VERSION_ROLE": [],
                "PAUSE_ROLE": [csm_pause_manager, RESEAL_MANAGER],
                "SUBMIT_DATA_ROLE": [],
                "RESUME_ROLE": [RESEAL_MANAGER],
                "RECOVERER_ROLE": [],
            },
        },
        CS_ORACLE_HASH_CONSENSUS_ADDRESS: {
            "contract_name": "HashConsensus",
            "contract": contracts.csm_hash_consensus,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "MANAGE_MEMBERS_AND_QUORUM_ROLE": [contracts.agent],
                "DISABLE_CONSENSUS_ROLE": [],
                "MANAGE_FRAME_CONFIG_ROLE": [],
                "MANAGE_FAST_LANE_CONFIG_ROLE": [],
                "MANAGE_REPORT_PROCESSOR_ROLE": [],
            },
        },
        cs_verifier_address: {
            "contract_name": "Verifier",
            "contract": cs_verifier,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PAUSE_ROLE": [csm_pause_manager, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
            },
        },
        CS_PARAMS_REGISTRY_ADDRESS: {
            "contract_name": "ParametersRegistry",
            "contract": contracts.cs_parameters_registry,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": cs_parameters_registry_roles,
        },
        CS_STRIKES_ADDRESS: {
            "contract_name": "ValidatorStrikes",
            "contract": contracts.cs_strikes,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
            },
        },
        cs_ejector_address: {
            "contract_name": "Ejector",
            "contract": interface.Ejector(cs_ejector_address),
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PAUSE_ROLE": [csm_pause_manager, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
                "RECOVERER_ROLE": [],
            },
        },
        CS_VETTED_GATE_ADDRESS: {
            "contract_name": "VettedGate",
            "contract": contracts.cs_vetted_gate,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": vetted_gate_roles,
            "role_preimages": vetted_gate_role_preimages,
        },
        cs_permissionless_gate_address: {
            "contract_name": "PermissionlessGate",
            "contract": interface.PermissionlessGate(cs_permissionless_gate_address),
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "RECOVERER_ROLE": [],
            },
        },
        # TODO: add Curated Module v2 permission matrix once scripts has CMv2 interfaces and config bindings.
        TOP_UP_GATEWAY: {
            "contract_name": "TopUpGateway",
            "contract": interface.TopUpGateway(TOP_UP_GATEWAY),
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PAUSE_ROLE": [CIRCUIT_BREAKER, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
                "TOP_UP_ROLE": [TOP_UP_GATEWAY_DEPOSITOR],
                "MANAGE_LIMITS_ROLE": [],
            },
        },
        CONSOLIDATION_GATEWAY: {
            "contract_name": "ConsolidationGateway",
            "contract": interface.ConsolidationGateway(CONSOLIDATION_GATEWAY),
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PAUSE_ROLE": [CIRCUIT_BREAKER, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
                "ADD_CONSOLIDATION_REQUEST_ROLE": [CONSOLIDATION_BUS],
                "EXIT_LIMIT_MANAGER_ROLE": [],
            },
        },
        CONSOLIDATION_BUS: {
            "contract_name": "ConsolidationBus",
            "contract": interface.ConsolidationBus(CONSOLIDATION_BUS),
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PUBLISH_ROLE": [CONSOLIDATION_MIGRATOR],
                "REMOVE_ROLE": [CONSOLIDATION_COMMITTEE],
                "MANAGE_ROLE": [],
            },
        },
        CONSOLIDATION_MIGRATOR: {
            "contract_name": "ConsolidationMigrator",
            "contract": interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR),
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "ALLOW_PAIR_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR],
                "DISALLOW_PAIR_ROLE": [CONSOLIDATION_COMMITTEE],
            },
        },
        TRIGGERABLE_WITHDRAWALS_GATEWAY: {
            "contract_name": "TriggerableWithdrawalsGateway",
            "contract": contracts.triggerable_withdrawals_gateway,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "ADD_FULL_WITHDRAWAL_REQUEST_ROLE": twg_full_withdrawal_request_holders,
                "PAUSE_ROLE": [csm_pause_manager, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
                "TW_EXIT_LIMIT_MANAGER_ROLE": [contracts.agent],
            },
        },
        INSURANCE_FUND: {
            "contract_name": "InsuranceFund",
            "contract": contracts.insurance_fund,
            "type": "CustomApp",
            "state": {"owner": contracts.voting},
            "roles": {},
        },
        WITHDRAWAL_VAULT: {
            "contract_name": "WithdrawalVault",
            "contract": interface.WithdrawalContractProxy(WITHDRAWAL_VAULT),
            "type": "CustomApp",
            "state": {"proxy_getAdmin": contracts.agent},
            "roles": {},
        },
        EASYTRACK: {
            "contract_name": "EasyTrack",
            "contract": contracts.easy_track,
            "type": "CustomApp",
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.voting],
                "CANCEL_ROLE": [contracts.voting],
                "PAUSE_ROLE": [contracts.voting, L1_EMERGENCY_BRAKES_MULTISIG],
                "UNPAUSE_ROLE": [contracts.voting],
            },
        },
        VAULT_HUB: {
            "contract_name": "VaultHub",
            "contract": contracts.vault_hub,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "VAULT_MASTER_ROLE": [],
                "REDEMPTION_MASTER_ROLE": [],
                "VALIDATOR_EXIT_ROLE": [VAULTS_ADAPTER],
                "BAD_DEBT_MASTER_ROLE": [VAULTS_ADAPTER],
                "PAUSE_ROLE": [CIRCUIT_BREAKER, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
            },
            "role_preimages": {
                "VAULT_MASTER_ROLE": "vaults.VaultHub.VaultMasterRole",
                "REDEMPTION_MASTER_ROLE": "vaults.VaultHub.RedemptionMasterRole",
                "VALIDATOR_EXIT_ROLE": "vaults.VaultHub.ValidatorExitRole",
                "BAD_DEBT_MASTER_ROLE": "vaults.VaultHub.BadDebtMasterRole",
                "PAUSE_ROLE": "PausableUntilWithRoles.PauseRole",
                "RESUME_ROLE": "PausableUntilWithRoles.ResumeRole",
            },
        },
        OPERATOR_GRID: {
            "contract_name": "OperatorGrid",
            "contract": contracts.operator_grid,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "REGISTRY_ROLE": [EASYTRACK_EVMSCRIPT_EXECUTOR, VAULTS_ADAPTER],
            },
            "role_preimages": {
                "REGISTRY_ROLE": "vaults.OperatorsGrid.Registry",
            },
        },
        LAZY_ORACLE: {
            "contract_name": "LazyOracle",
            "contract": contracts.lazy_oracle,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "UPDATE_SANITY_PARAMS_ROLE": [],
            },
            "role_preimages": {
                "UPDATE_SANITY_PARAMS_ROLE": "vaults.LazyOracle.UpdateSanityParams",
            },
        },
        ACCOUNTING: {
            "contract_name": "Accounting",
            "contract": contracts.accounting,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {},
        },
        PREDEPOSIT_GUARANTEE: {
            "contract_name": "PredepositGuarantee",
            "contract": contracts.predeposit_guarantee,
            "type": "CustomApp",
            "proxy_owner": contracts.agent,
            "roles": {
                "DEFAULT_ADMIN_ROLE": [contracts.agent],
                "PAUSE_ROLE": [CIRCUIT_BREAKER, RESEAL_MANAGER],
                "RESUME_ROLE": [RESEAL_MANAGER],
            },
            "role_preimages": {
                "PAUSE_ROLE": "PausableUntilWithRoles.PauseRole",
                "RESUME_ROLE": "PausableUntilWithRoles.ResumeRole",
            },
        },
        L1_TOKEN_RATE_NOTIFIER: {
            "contract_name": "TokenRateNotifier",
            "contract": contracts.token_rate_notifier,
            "type": "CustomApp",
            "state": {"owner": contracts.agent},
            "roles": {},
        },
        STAKING_VAULT_BEACON: {
            "contract_name": "UpgradeableBeacon",
            "contract": contracts.staking_vault_beacon,
            "type": "CustomApp",
            "state": {"owner": contracts.agent},
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
        abi_roles = set(abi_roles_list)
        configured_roles = set(permissions_config["roles"])
        custom_role_preimages = set(permissions_config.get("role_preimages", {}))
        ignored_abi_roles = set(permissions_config.get("ignored_abi_roles", {}))

        if contract_address in [NODE_OPERATORS_REGISTRY, SIMPLE_DVT]:
            abi_roles_list.append("MANAGE_SIGNING_KEYS")
            abi_roles.add("MANAGE_SIGNING_KEYS")

        roles = permissions_config["roles"]

        assert (abi_roles - ignored_abi_roles).issubset(
            configured_roles
        ), "Contract {} has undescribed ABI roles {}".format(
            permissions_config["contract_name"], abi_roles - configured_roles - ignored_abi_roles
        )
        assert configured_roles.issubset(
            abi_roles | custom_role_preimages
        ), "Contract {} has configured roles absent from ABI and role_preimages {}".format(
            permissions_config["contract_name"], configured_roles - abi_roles - custom_role_preimages
        )

        if permissions_config["type"] == "AragonApp":
            for role, holders in permissions_config["roles"].items():
                current_holders = (
                    aragon_acl_active_permissions[contract_address][role]
                    if role in aragon_acl_active_permissions[contract_address]
                    else []
                )

                if contract_address == NODE_OPERATORS_REGISTRY and role == "MANAGE_SIGNING_KEYS":
                    assert_curated_manage_signing_keys_permission(permissions_config, current_holders)
                    continue

                if contract_address == SIMPLE_DVT and role == "MANAGE_SIGNING_KEYS":
                    assert_sdvt_manage_signing_keys_permission(permissions_config, holders, current_holders)
                    continue

                assert_expected_role_holders(role, holders, current_holders, permissions_config["contract_name"])

        elif permissions_config["type"] == "CustomApp":
            if "proxy_owner" in permissions_config:
                assert (
                    interface.OssifiableProxy(permissions_config["contract"].address).proxy__getAdmin()
                    == permissions_config["proxy_owner"]
                )

            for role, holders in permissions_config["roles"].items():
                # Use custom preimage if specified, otherwise use role name
                role_preimage = role
                if "role_preimages" in permissions_config and role in permissions_config["role_preimages"]:
                    role_preimage = permissions_config["role_preimages"][role]

                role_keccak = (
                    web3.keccak(text=role_preimage).hex() if role != "DEFAULT_ADMIN_ROLE" else ZERO_BYTES32.hex()
                )

                if role in permissions_config["contract"].signatures:
                    role_signature = permissions_config["contract"].signatures[role]
                    assert permissions_config["contract"].get_method_object(role_signature)() == role_keccak

                try:
                    role_member_count = permissions_config["contract"].getRoleMemberCount(role_keccak)
                except Exception as e:
                    print(
                        "Unable to count role members for {0} at {1}: {2}".format(
                            role, permissions_config["contract_name"], e
                        )
                    )
                    role_member_count = None
                finally:
                    if role_member_count is not None:
                        assert role_member_count == len(
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


def assert_expected_role_holders(role, expected_holders, current_holders, contract_name):
    assert len(current_holders) == len(
        expected_holders
    ), "number of {} role holders in contract {} mismatched expected {} , actual {} ".format(
        role, contract_name, expected_holders, current_holders
    )

    for holder in expected_holders:
        assert holder in current_holders, "Entity {} has no role {} at {}".format(holder, role, contract_name)

    for holder in current_holders:
        assert holder in expected_holders, "Unexpected entity {} has role {} at {}".format(holder, role, contract_name)


def get_acl_permission_params(entity, app, role):
    params_length = contracts.acl.getPermissionParamsLength(entity, app, role)
    return [
        Param(param_id, Op(op), ArgumentValue(value))
        for index in range(params_length)
        for param_id, op, value in [contracts.acl.getPermissionParam(entity, app, role, index)]
    ]


def assert_curated_manage_signing_keys_permission(permissions_config, current_holders):
    role = "MANAGE_SIGNING_KEYS"
    role_hash = web3.keccak(text=role).hex()
    contract_address = permissions_config["contract"].address
    contract_name = permissions_config["contract_name"]

    expected_holders = list(CURATED_MANAGE_SIGNING_KEYS_HOLDERS.values())
    assert_expected_role_holders(role, expected_holders, current_holders, contract_name)

    for holder in current_holders:
        assert not contracts.acl.hasPermission(
            holder, contract_address, role_hash
        ), "Unexpected unparameterized {} holder {} at {}".format(role, holder, contract_name)

    for node_operator_id, holder in CURATED_MANAGE_SIGNING_KEYS_HOLDERS.items():
        expected_params = [Param(0, Op.EQ, ArgumentValue(node_operator_id))]
        actual_params = get_acl_permission_params(holder, contract_address, role_hash)
        assert (
            actual_params == expected_params
        ), "Unexpected params for {} holder {} at {}. expected {}, actual {}".format(
            role, holder, contract_name, expected_params, actual_params
        )


def assert_sdvt_manage_signing_keys_permission(permissions_config, regular_holders, current_holders):
    """Validate regular holders, skip per-operator parametrized holders managed via EasyTrack."""
    role = "MANAGE_SIGNING_KEYS"
    contract_name = permissions_config["contract_name"]

    normalized_regular_holders = {holder.lower() for holder in regular_holders}
    current_regular_holders = [holder for holder in current_holders if holder.lower() in normalized_regular_holders]

    assert_expected_role_holders(role, regular_holders, current_regular_holders, contract_name)


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


def get_http_w3_provider_url():
    if os.getenv("WEB3_INFURA_PROJECT_ID") is not None:
        return f'https://mainnet.infura.io/v3/{os.getenv("WEB3_INFURA_PROJECT_ID")}'

    if os.getenv("WEB3_ALCHEMY_PROJECT_ID") is not None:
        return f'https://eth-mainnet.g.alchemy.com/v2/{os.getenv("WEB3_ALCHEMY_PROJECT_ID")}'

    if os.getenv("ETH_RPC_URL") is not None:
        return os.getenv("ETH_RPC_URL")

    assert False, "Web3 HTTP Provider token env var not found"


def get_http_provider_timeout():
    """
    HTTP provider timeout in seconds for remote RPC calls.
    Can be overridden via WEB3_HTTP_PROVIDER_TIMEOUT env var.
    """
    if os.getenv("WEB3_HTTP_PROVIDER_TIMEOUT") is not None:
        return float(os.getenv("WEB3_HTTP_PROVIDER_TIMEOUT"))
    # use higher default than requests' 10s to reduce flaky ReadTimeouts in CI
    return 300.0


def get_max_log_range():
    if os.getenv("MAX_GET_LOGS_RANGE") is not None:
        return int(os.getenv("MAX_GET_LOGS_RANGE"))
    return 10000


def active_aragon_roles(protocol_permissions):
    local_rpc_provider = web3
    remote_rpc_provider = Web3(
        Web3.HTTPProvider(
            get_http_w3_provider_url(),
            request_kwargs={"timeout": get_http_provider_timeout()},
        )
    )
    max_range = get_max_log_range()

    event_signature_hash = remote_rpc_provider.keccak(text="SetPermission(address,address,bytes32,bool)").hex()

    def fetch_events_in_batches(start_block, end_block, provider=local_rpc_provider, step=max_range):
        """Fetch events in batches of `step` blocks with a progress bar."""
        events = []
        total_batches = (end_block - start_block) // step + 1
        with tqdm(total=total_batches, desc="Fetching Events") as pbar:
            for batch_start in range(start_block, end_block, step):
                batch_end = min(batch_start + step - 1, end_block)

                batch_events = provider.eth.get_logs(
                    {
                        "address": contracts.acl.address,
                        "fromBlock": batch_start,
                        "toBlock": batch_end,
                        "topics": [event_signature_hash],
                    }
                )

                events.extend(batch_events)
                pbar.update(1)
        return events

    events_before_voting = fetch_events_in_batches(
        ACL_DEPLOY_BLOCK_NUMBER, remote_rpc_provider.eth.block_number, remote_rpc_provider
    )

    permission_events = _decode_logs(events_before_voting)["SetPermission"]._ordered

    history = TxHistory()
    if len(history) > 0:
        vote_block = history[0].block_number

        events_after_voting = fetch_events_in_batches(vote_block, remote_rpc_provider.eth.block_number)

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
                [remote_rpc_provider.keccak(text=role).hex() for role in protocol_permissions[event_app]["roles"]],
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
