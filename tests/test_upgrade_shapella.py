"""
Tests for voting ??/05/2023
"""
from brownie import interface, ZERO_ADDRESS
from utils.config import (
    contracts,
    lido_dao_node_operators_registry,
    lido_dao_voting_address,
    lido_dao_steth_address,
    lido_dao_legacy_oracle,
    lido_dao_withdrawal_vault,
    ldo_holder_address_for_tests,
    deployer_eoa,
    oracle_committee,
    deposit_security_module_guardians,
    lido_dao_steth_implementation_address,
    lido_dao_node_operators_registry_implementation,
    lido_dao_legacy_oracle_implementation,
    lido_dao_template_address,
    lido_dao_lido_locator,
    lido_dao_lido_locator_implementation,
    lido_dao_burner,
    lido_dao_eip712_steth,
    lido_dao_accounting_oracle,
    lido_dao_accounting_oracle_implementation,
    lido_dao_validators_exit_bus_oracle_implementation,
    lido_dao_staking_router,
    lido_dao_staking_router_implementation,
    lido_dao_withdrawal_queue,
    lido_dao_withdrawal_queue_implementation,
    lido_dao_hash_consensus_for_accounting_oracle,
    lido_dao_hash_consensus_for_validators_exit_bus_oracle,
    gate_seal_address,
    lido_dao_deposit_security_module_address,
    lido_dao_withdrawal_vault_implementation,
    DEFAULT_ADMIN_ROLE,
    REQUEST_BURN_SHARES_ROLE,
    MANAGE_MEMBERS_AND_QUORUM_ROLE,
    PAUSE_ROLE,
    RESUME_ROLE,
    FINALIZE_ROLE,
    ORACLE_ROLE,
    STAKING_MODULE_PAUSE_ROLE,
    STAKING_MODULE_RESUME_ROLE,
    STAKING_MODULE_MANAGE_ROLE,
    REPORT_EXITED_VALIDATORS_ROLE,
    REPORT_REWARDS_MINTED_ROLE,
    STAKING_ROUTER_ROLE,
    MANAGE_FEE,
    MANAGE_WITHDRAWAL_KEY,
    MANAGE_PROTOCOL_CONTRACTS_ROLE,
    SET_EL_REWARDS_VAULT_ROLE,
    SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE,
    ADD_NODE_OPERATOR_ROLE,
    SET_NODE_OPERATOR_ACTIVE_ROLE,
    SET_NODE_OPERATOR_NAME_ROLE,
    SET_NODE_OPERATOR_ADDRESS_ROLE,
    REPORT_STOPPED_VALIDATORS_ROLE,
    MANAGE_MEMBERS,
    MANAGE_QUORUM,
    SET_BEACON_SPEC,
    SET_REPORT_BOUNDARIES,
    SET_BEACON_REPORT_RECEIVER,
    LIDO_APP_ID,
    ORACLE_APP_ID,
    NODE_OPERATORS_REGISTRY_APP_ID,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import Permission, validate_permission_create_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from scripts.upgrade_shapella_1 import start_vote as start_vote_1
from scripts.upgrade_shapella_2_revoke_roles import start_vote as start_vote_2
from utils.shapella_upgrade import (
    prepare_deploy_gate_seal,
    prepare_deploy_upgrade_template,
    prepare_upgrade_locator,
    prepare_transfer_ownership_to_template,
)


# See Aragon apps getLatest()
LIDO_APP_VERSION = (4, 0, 0)
NODE_OPERATORS_REGISTRY_APP_VERSION = (4, 0, 0)
ORACLE_APP_VERSION = (4, 0, 0)


# New parameters
STAKING_MODULE_NOR_ID = 1
STAKING_MODULE_NOR_NAME = "curated-onchain-v1"
STAKING_MODULE_NOR_TYPE = (
    "0x637572617465642d6f6e636861696e2d76310000000000000000000000000000"  # bytes32("curated-onchain-v1");
)

# 0x01...withdrawal_vault or Lido.getWithdrawalCredentials()
WITHDRAWAL_CREDENTIALS = "0x010000000000000000000000b9d7934878b5fb9610b3fe8a5e441e8fad7e293f"

LIDO_ORACLE_QUORUM = 5
DEPOSIT_SECURITY_MODULE_GUARDIANS_QUORUM = 4

# type(uint256).max
TYPE_UINT256_MAX = 2**256 - 1

# PAUSE_INFINITELY from PausableUntil.sol
PAUSE_INFINITELY = TYPE_UINT256_MAX

# Deployment parameters, see https://hackmd.io/pdix1r4yR46fXUqiHaNKyw
STUCK_PENALTY_DELAY = 432000
EPOCHS_PER_FRAME_FOR_ACCOUNTING_ORACLE = 225
EPOCHS_PER_FRAME_FOR_VALIDATORS_EXIT_BUS_ORACLE = 75

# Helper constant to mark that value of an event field is not to be checked
ANY_VALUE = None


# Roles related to vote #1
permission_staking_router = Permission(
    entity=lido_dao_staking_router,
    app=lido_dao_node_operators_registry,
    role=STAKING_ROUTER_ROLE,
)

# Roles related to vote #2
permissions_to_revoke = [
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role=MANAGE_FEE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role=MANAGE_WITHDRAWAL_KEY,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role=MANAGE_PROTOCOL_CONTRACTS_ROLE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role=SET_EL_REWARDS_VAULT_ROLE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_steth_address,
        role=SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role=ADD_NODE_OPERATOR_ROLE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role=SET_NODE_OPERATOR_ACTIVE_ROLE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role=SET_NODE_OPERATOR_NAME_ROLE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role=SET_NODE_OPERATOR_ADDRESS_ROLE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_node_operators_registry,
        role=REPORT_STOPPED_VALIDATORS_ROLE,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role=MANAGE_MEMBERS,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role=MANAGE_QUORUM,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role=SET_BEACON_SPEC,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role=SET_REPORT_BOUNDARIES,
    ),
    Permission(
        entity=lido_dao_voting_address,
        app=lido_dao_legacy_oracle,
        role=SET_BEACON_REPORT_RECEIVER,
    ),
]


def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
):
    withdrawal_vault_manager = interface.WithdrawalVaultManager(lido_dao_withdrawal_vault)
    lido_old_app = contracts.lido_app_repo.getLatest()
    nor_old_app = contracts.nor_app_repo.getLatest()
    oracle_old_app = contracts.oracle_app_repo.getLatest()

    #
    # Preliminary checks
    #
    assert (
        withdrawal_vault_manager.implementation() != lido_dao_withdrawal_vault_implementation
    ), "Wrong WithdrawalVault proxy initial implementation"
    assert withdrawal_vault_manager.proxy_getAdmin() == lido_dao_voting_address

    # Vote #1 ACL checks
    assert not contracts.acl.hasPermission(*permission_staking_router)

    # Vote #2 ACL checks
    for permission in permissions_to_revoke:
        assert contracts.acl.hasPermission(*permission), f"No starting role {permission.role} on {permission.entity}"

    # START VOTE
    if len(vote_ids_from_env) > 0:
        vote_ids = vote_ids_from_env
        template = contracts.shapella_upgrade_template
    else:
        prepare_deploy_gate_seal(deployer_eoa)
        template = prepare_deploy_upgrade_template(deployer_eoa)
        prepare_upgrade_locator(deployer_eoa)
        prepare_transfer_ownership_to_template(deployer_eoa, template)
        tx_params = {"from": ldo_holder_address_for_tests}
        vote1_id, _ = start_vote_1(tx_params, silent=True)
        vote2_id, _ = start_vote_2(tx_params, silent=True)
        vote_ids = [vote1_id, vote2_id]

    vote_transactions = helpers.execute_votes(accounts, vote_ids, contracts.voting)

    gas_usages = [(vote_id, tx.gas_used) for vote_id, tx in zip(vote_ids, vote_transactions)]
    print(f"UPGRADE TXs (voteId, gasUsed): {gas_usages}")

    #
    # WithdrawalVault upgrade checks
    #
    assert (
        withdrawal_vault_manager.implementation() == lido_dao_withdrawal_vault_implementation
    ), "Wrong WithdrawalVault proxy implementation"

    #
    # Lido app upgrade checks
    #
    lido_new_app = contracts.lido_app_repo.getLatest()
    lido_proxy = interface.AppProxyUpgradeable(contracts.lido)
    assert_app_update(lido_new_app, lido_old_app, lido_dao_steth_implementation_address)
    assert lido_proxy.implementation() == lido_dao_steth_implementation_address, "Proxy should be updated"

    #
    # NodeOperatorsRegistry app upgrade checks
    #
    nor_new_app = contracts.nor_app_repo.getLatest()
    nor_proxy = interface.AppProxyUpgradeable(contracts.node_operators_registry)
    assert_app_update(nor_new_app, nor_old_app, lido_dao_node_operators_registry_implementation)
    assert nor_proxy.implementation() == lido_dao_node_operators_registry_implementation, "Proxy should be updated"

    #
    # LidoOracle app upgrade checks
    #
    oracle_new_app = contracts.oracle_app_repo.getLatest()
    oracle_proxy = interface.AppProxyUpgradeable(contracts.legacy_oracle)
    assert_app_update(oracle_new_app, oracle_old_app, lido_dao_legacy_oracle_implementation)
    assert oracle_proxy.implementation() == lido_dao_legacy_oracle_implementation, "Proxy should be updated"

    # Vote #1 ACL checks
    assert contracts.acl.hasPermission(*permission_staking_router)

    # Vote #2 ACL checks
    for permission in permissions_to_revoke:
        assert not contracts.acl.hasPermission(*permission), f"Role {permission.role} is still on {permission.entity}"

    #
    # Template checks
    #
    assert template._isUpgradeFinished()

    if bypass_events_decoding:
        return

    (vote1_tx, vote2_tx) = vote_transactions

    display_voting_events(vote1_tx)

    (
        events_withdrawal_vault_upgrade,
        events_template_start,
        events_publish_lido_app,
        events_update_lido_impl,
        events_publish_nor_app,
        events_update_nor_impl,
        events_publish_oracle_app,
        events_update_oracle_impl,
        events_grant_staking_router_role,
        events_template_finish,
    ) = group_voting_events(vote1_tx)

    validate_withdrawal_vault_manager_upgrade_events(
        events_withdrawal_vault_upgrade, lido_dao_withdrawal_vault_implementation
    )
    validate_start_upgrade_events(events_template_start)
    validate_push_to_repo_event(events_publish_lido_app, LIDO_APP_VERSION)
    validate_app_update_event(events_update_lido_impl, LIDO_APP_ID, lido_dao_steth_implementation_address)
    validate_push_to_repo_event(events_publish_nor_app, NODE_OPERATORS_REGISTRY_APP_VERSION)
    validate_app_update_event(
        events_update_nor_impl, NODE_OPERATORS_REGISTRY_APP_ID, lido_dao_node_operators_registry_implementation
    )
    validate_push_to_repo_event(events_publish_oracle_app, ORACLE_APP_VERSION)
    validate_app_update_event(events_update_oracle_impl, ORACLE_APP_ID, lido_dao_legacy_oracle_implementation)
    validate_permission_create_event(
        events_grant_staking_router_role, permission_staking_router, manager=contracts.voting
    )
    validate_finish_upgrade_events(events_template_finish)

    # TODO: fix, it fails with "brownie.exceptions.RPCRequestError: Invalid string length" at `tx._get_trace()`
    # display_voting_events(vote2_tx)
    # TODO: check vote2_tx events


def assert_app_update(new_app, old_app, contract_address):
    assert old_app[1] != new_app[1], "Address should change"
    assert new_app[1] == contract_address, "New address should match"
    assert new_app[0][0] == old_app[0][0] + 1, "Major version should increment"
    assert old_app[2] != new_app[2], "Content uri must change"


def assert_single_event_equal(actual, expected):
    expected_name, expected_data = expected
    assert actual.name == expected_name
    assert len(actual.items()) == len(expected_data), f"Number of data fields differ for event {actual.name}"
    for field_name, field_data in actual.items():
        # Check parameter-wise, skipping values with expected ANY_VALUE
        if field_name in expected_data and expected_data[field_name] is ANY_VALUE:
            continue
        assert (
            field_data == expected_data[field_name]
        ), f"Event data field {field_name} differ for event '{actual.name}'"


def assert_events_equal(actual_events, expected_events):
    assert len(expected_events) == len(actual_events)
    for actual, expected in zip(actual_events, expected_events):
        assert_single_event_equal(actual, expected)


def validate_withdrawal_vault_manager_upgrade_events(events: EventDict, implementation: str):
    _events_chain = ["LogScriptCall", "Upgraded"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("Upgraded") == 1
    assert events["Upgraded"]["implementation"] == implementation, "Wrong withdrawal vault proxy implementation"


def validate_start_upgrade_events(events: EventDict):
    def hash_consensus_migration_events():
        return (
            [
                (
                    "RoleGranted",
                    {
                        "role": MANAGE_MEMBERS_AND_QUORUM_ROLE,
                        "account": lido_dao_template_address,
                        "sender": lido_dao_template_address,
                    },
                ),
                (
                    "MemberAdded",
                    {"addr": oracle_committee[0], "newTotalMembers": 1, "newQuorum": LIDO_ORACLE_QUORUM},
                ),
                ("QuorumSet", {"newQuorum": LIDO_ORACLE_QUORUM, "totalMembers": 1, "prevQuorum": 0}),
            ]
            + [
                (
                    "MemberAdded",
                    {
                        "addr": oracle_committee[i],
                        "newTotalMembers": i + 1,
                        "newQuorum": LIDO_ORACLE_QUORUM,
                    },
                )
                for i in range(1, len(oracle_committee))
            ]
            + [
                (
                    "RoleRevoked",
                    {
                        "role": MANAGE_MEMBERS_AND_QUORUM_ROLE,
                        "account": lido_dao_template_address,
                        "sender": lido_dao_template_address,
                    },
                ),
            ]
        )

    expected_events = (
        [
            # Vote item start
            (
                "LogScriptCall",
                {"sender": ANY_VALUE, "src": lido_dao_voting_address, "dst": lido_dao_template_address},
            ),
            # Proxy upgrades
            ("Upgraded", {"implementation": lido_dao_lido_locator_implementation}),
            ("Upgraded", {"implementation": lido_dao_accounting_oracle_implementation}),
            ("Upgraded", {"implementation": lido_dao_validators_exit_bus_oracle_implementation}),
            ("Upgraded", {"implementation": lido_dao_staking_router_implementation}),
            ("Upgraded", {"implementation": lido_dao_withdrawal_queue_implementation}),
        ]
        # Migrate oracle committee for HashConsensus for AccountingOracle
        + hash_consensus_migration_events()
        # Migrate oracle committee for HashConsensus for ValidatorsExitBusOracle
        + hash_consensus_migration_events()
        + [
            # Template reports committee migrated
            ("OracleCommitteeMigrated", {"members": oracle_committee, "quorum": LIDO_ORACLE_QUORUM}),
            # AccountingOracle + HashConsensus initialization
            (
                "FrameConfigSet",
                {"newInitialEpoch": ANY_VALUE, "newEpochsPerFrame": EPOCHS_PER_FRAME_FOR_ACCOUNTING_ORACLE},
            ),
            (
                "RoleGranted",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            ("ContractVersionSet", {"version": 1}),
            (
                "ConsensusHashContractSet",
                {"addr": lido_dao_hash_consensus_for_accounting_oracle, "prevAddr": ZERO_ADDRESS},
            ),
            ("ConsensusVersionSet", {"version": 1, "prevVersion": 0}),
            (
                "AccountingOracleInitialized",
                {"lastCompletedEpochId": ANY_VALUE, "nextExpectedFrameInitialEpochId": ANY_VALUE},
            ),
            ("UpgradeStarted", {}),
        ]
    )

    assert_events_equal(events, expected_events)


def validate_finish_upgrade_events(events: EventDict):
    def transfer_oz_admin_from_template_to_agent():
        return [
            (
                "RoleGranted",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": contracts.agent.address,
                    "sender": lido_dao_template_address,
                },
            ),
            (
                "RoleRevoked",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
        ]

    expected_events = (
        [
            # Vote item start
            (
                "LogScriptCall",
                {"sender": ANY_VALUE, "src": lido_dao_voting_address, "dst": lido_dao_template_address},
            ),
            # Initialize WithdrawalVault
            ("ContractVersionSet", {"version": 1}),
            # Initialize WithdrawalQueue
            ("Paused", {"duration": PAUSE_INFINITELY}),
            ("ContractVersionSet", {"version": 1}),
            (
                "RoleGranted",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            ("InitializedV1", {"_admin": lido_dao_template_address}),
            (
                "RoleGranted",
                {"role": PAUSE_ROLE, "account": gate_seal_address, "sender": lido_dao_template_address},
            ),
            (
                "RoleGranted",
                {"role": FINALIZE_ROLE, "account": contracts.lido.address, "sender": lido_dao_template_address},
            ),
            (
                "RoleGranted",
                {
                    "role": ORACLE_ROLE,
                    "account": lido_dao_accounting_oracle,
                    "sender": lido_dao_template_address,
                },
            ),
            # Resume WithdrawalQueue
            (
                "RoleGranted",
                {
                    "role": RESUME_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            ("Resumed", {}),
            (
                "RoleRevoked",
                {
                    "role": RESUME_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            # Initialize HashConsensus + ValidatorsExitBusOracle
            (
                "FrameConfigSet",
                {"newInitialEpoch": ANY_VALUE, "newEpochsPerFrame": EPOCHS_PER_FRAME_FOR_VALIDATORS_EXIT_BUS_ORACLE},
            ),
            (
                "RoleGranted",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            ("Paused", {"duration": PAUSE_INFINITELY}),
            ("ContractVersionSet", {"version": 1}),
            (
                "ConsensusHashContractSet",
                {"addr": lido_dao_hash_consensus_for_validators_exit_bus_oracle, "prevAddr": ZERO_ADDRESS},
            ),
            ("ConsensusVersionSet", {"version": 1, "prevVersion": 0}),
            (
                "RoleGranted",
                {"role": PAUSE_ROLE, "account": gate_seal_address, "sender": lido_dao_template_address},
            ),
            # Resume ValidatorsExitBusOracle
            (
                "RoleGranted",
                {
                    "role": RESUME_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            ("Resumed", {}),
            (
                "RoleRevoked",
                {
                    "role": RESUME_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            # Initialize StakingRouter
            ("ContractVersionSet", {"version": 1}),
            (
                "RoleGranted",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            (
                "WithdrawalCredentialsSet",
                {"withdrawalCredentials": WITHDRAWAL_CREDENTIALS, "setBy": lido_dao_template_address},
            ),
            (
                "RoleGranted",
                {
                    "role": STAKING_MODULE_PAUSE_ROLE,
                    "account": lido_dao_deposit_security_module_address,
                    "sender": lido_dao_template_address,
                },
            ),
            (
                "RoleGranted",
                {
                    "role": STAKING_MODULE_RESUME_ROLE,
                    "account": lido_dao_deposit_security_module_address,
                    "sender": lido_dao_template_address,
                },
            ),
            (
                "RoleGranted",
                {
                    "role": REPORT_EXITED_VALIDATORS_ROLE,
                    "account": lido_dao_accounting_oracle,
                    "sender": lido_dao_template_address,
                },
            ),
            (
                "RoleGranted",
                {
                    "role": REPORT_REWARDS_MINTED_ROLE,
                    "account": contracts.lido.address,
                    "sender": lido_dao_template_address,
                },
            ),
            # finalizeUpgrade LegacyOracle
            ("ContractVersionSet", {"version": 4}),
            # finalizeUpgrade Lido
            ("ContractVersionSet", {"version": 2}),
            ("EIP712StETHInitialized", {"eip712StETH": lido_dao_eip712_steth}),
            ("Approval", {"owner": lido_dao_withdrawal_queue, "spender": lido_dao_burner, "value": TYPE_UINT256_MAX}),
            ("LidoLocatorSet", {"lidoLocator": lido_dao_lido_locator}),
            # Grant burner role
            (
                "RoleGranted",
                {
                    "role": REQUEST_BURN_SHARES_ROLE,
                    "account": contracts.node_operators_registry.address,
                    "sender": lido_dao_template_address,
                },
            ),
            # finalizeUpgrade NodeOperatorsRegistry
            ("ContractVersionSet", {"version": 2}),
            ("StuckPenaltyDelayChanged", {"stuckPenaltyDelay": STUCK_PENALTY_DELAY}),
            (
                "Approval",
                {
                    "owner": contracts.node_operators_registry.address,
                    "spender": lido_dao_burner,
                    "value": TYPE_UINT256_MAX,
                },
            ),
            ("LocatorContractSet", {"locatorAddress": lido_dao_lido_locator}),
            ("StakingModuleTypeSet", {"moduleType": STAKING_MODULE_NOR_TYPE}),
            ("KeysOpIndexSet", {"keysOpIndex": ANY_VALUE}),
            ("NonceChanged", {"nonce": ANY_VALUE}),
            (
                "RoleGranted",
                {
                    "role": STAKING_MODULE_MANAGE_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
            ("StakingRouterETHDeposited", {"stakingModuleId": STAKING_MODULE_NOR_ID, "amount": 0}),
            (
                "StakingModuleAdded",
                {
                    "stakingModuleId": STAKING_MODULE_NOR_ID,
                    "stakingModule": contracts.node_operators_registry.address,
                    "name": STAKING_MODULE_NOR_NAME,
                    "createdBy": lido_dao_template_address,
                },
            ),
            (
                "StakingModuleTargetShareSet",
                {
                    "stakingModuleId": STAKING_MODULE_NOR_ID,
                    "targetShare": 10000,
                    "setBy": lido_dao_template_address,
                },
            ),
            (
                "StakingModuleFeesSet",
                {
                    "stakingModuleId": STAKING_MODULE_NOR_ID,
                    "stakingModuleFee": 500,
                    "treasuryFee": 500,
                    "setBy": lido_dao_template_address,
                },
            ),
            (
                "RoleRevoked",
                {
                    "role": STAKING_MODULE_MANAGE_ROLE,
                    "account": lido_dao_template_address,
                    "sender": lido_dao_template_address,
                },
            ),
        ]
        # Migrate DepositSecurityModule
        + [("GuardianAdded", {"guardian": guardian}) for guardian in deposit_security_module_guardians]
        + [
            ("GuardianQuorumChanged", {"newValue": DEPOSIT_SECURITY_MODULE_GUARDIANS_QUORUM}),
        ]
        # Transfer OZ admin roles for 7 contracts: HC for VEBO, HC for AO, Burner, SR, AO, VEBO, WQ
        + 7 * transfer_oz_admin_from_template_to_agent()
        # Change proxy admin for proxies of: Locator, SR, AO, VEBO, WQ
        + 5 * [("AdminChanged", {"previousAdmin": lido_dao_template_address, "newAdmin": contracts.agent.address})]
        + [
            # Change DepositSecurityModule owner
            ("OwnerChanged", {"newValue": contracts.agent.address}),
            # UpgradeFinished
            ("UpgradeFinished", {}),
        ]
    )

    assert_events_equal(events, expected_events)
