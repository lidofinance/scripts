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
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import Permission, validate_permission_create_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from scripts.upgrade_shapella_1 import start_vote as start_vote_1
from scripts.upgrade_shapella_2_revoke_roles import start_vote as start_vote_2
from utils.shapella_upgrade import (
    prepare_deploy_gate_seal_mock,
    prepare_deploy_upgrade_template,
    prepare_upgrade_locator,
    prepare_transfer_ownership_to_template,
)


# see Lido's proxy appId()
LIDO_APP_ID = "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320"
LIDO_IMPL = "0xAb3bcE27F31Ca36AAc6c6ec2bF3e79569105ec2c"
LIDO_APP_VERSION = (4, 0, 0)

# see NodeOperatorsRegistry's proxy appId()
NODE_OPERATORS_REGISTRY_APP_ID = "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d"
NODE_OPERATORS_REGISTRY_IMPL = "0x9cBbA6CDA09C7dadA8343C4076c21eE06CCa4836"
NODE_OPERATORS_REGISTRY_APP_VERSION = (4, 0, 0)

# see LidoOracle's proxy appId()
ORACLE_APP_ID = "0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93"
ORACLE_IMPL = "0xcA3cE6bf0CB2bbaC5dF3874232AE3F5b67C6b146"
ORACLE_APP_VERSION = (4, 0, 0)


# New addresses
TEMPLATE_ADDRESS = "0xF9a393Baab3C575c2B31166636082AB58a3dae62"
LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
LIDO_LOCATOR_IMPL = "0x7948f9cf80D99DDb7C7258Eb23a693E9dFBc97EC"
BURNER = "0xFc810b3F9acc7ee0C3820B5f7a9bb0ee88C3cBd2"
EIP_712_STETH = "0x8dF3c29C96fd4c4d496954646B8B6a48dFFcA83F"
ACCOUNTING_ORACLE = "0x9FE21EeCC385a1FeE057E58427Bfb9588E249231"
ACCOUNTING_ORACLE_IMPL = "0x115065ad19aDae715576b926CF6e26067F64e741"
VALIDATORS_EXIT_BUS_ORACLE = "0x6e7Da71eF6E0Aaa85E59554C1FAe44128fA649Ed"
VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0xfdfad30ae5e5c9Dc4fb51aC35AB60674FcBdefB3"
STAKING_ROUTER = "0x5A2a6cB5e0f57A30085A9411f7F5f07be8ad1Ec7"
STAKING_ROUTER_IMPL = "0x4384fB5DcaC0576B93e36b8af6CdfEB739888894"
WITHDRAWAL_QUEUE = "0xFb4E291D12734af4300B89585A16dF932160b840"
WITHDRAWAL_QUEUE_IMPL = "0x5EfF11Cb6bD446370FC3ce46019F2b501ba06c2D"
HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE = "0x379EBeeD117c96380034c6a6234321e4e64fCa0B"
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE = "0x2330b9F113784a58d74c7DB49366e9FB792DeABf"
GATE_SEAL = "0xD59f8Bc37BAead58cbCfD99b03997655A13f56d9"
DEPOSIT_SECURITY_MODULE = "0xe44E11BBb629Dc23e72e6eAC4e538AaCb66A0c88"
WITHDRAWAL_VAULT_IMPLEMENTATION = "0x654f166BA493551899212917d8eAa30CE977b794"

#
# Roles section
# NB: role hash calculated as keccak256 of constant name, e.g. DEFAULT_ADMIN_ROLE = keccak256("DEFAULT_ADMIN_ROLE")
#
# Default OpenZeppelin roles
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"
# Burner roles
REQUEST_BURN_SHARES_ROLE = "0x4be29e0e4eb91f98f709d98803cba271592782e293b84a625e025cbb40197ba8"
# HashConsensus roles
MANAGE_MEMBERS_AND_QUORUM_ROLE = "0x66a484cf1a3c6ef8dfd59d24824943d2853a29d96f34a01271efc55774452a51"
# AccountingOracle and ValidatorsExitBusOracle pausable roles
PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d"
RESUME_ROLE = "0x2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7"
# WithdrawalQueue roles
FINALIZE_ROLE = "0x485191a2ef18512555bd4426d18a716ce8e98c80ec2de16394dcf86d7d91bc80"
ORACLE_ROLE = "0x68e79a7bf1e0bc45d0a330c573bc367f9cf464fd326078812f301165fbda4ef1"
# StakingRouter roles
STAKING_MODULE_PAUSE_ROLE = "0x00b1e70095ba5bacc3202c3db9faf1f7873186f0ed7b6c84e80c0018dcc6e38e"
STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"
REPORT_EXITED_VALIDATORS_ROLE = "0xc23292b191d95d2a7dd94fc6436eb44338fda9e1307d9394fd27c28157c1b33c"
REPORT_REWARDS_MINTED_ROLE = "0x779e5c23cb7a5bcb9bfe1e9a5165a00057f12bcdfd13e374540fdf1a1cd91137"
# Aragon new role
STAKING_ROUTER_ROLE = "0xbb75b874360e0bfd87f964eadd8276d8efb7c942134fc329b513032d0803e0c6"
# Aragon roles to revoke
MANAGE_FEE = "0x46b8504718b48a11e89304b407879435528b3cd3af96afde67dfe598e4683bd8"
MANAGE_WITHDRAWAL_KEY = "0x46b8504718b48a11e89304b407879435528b3cd3af96afde67dfe598e4683bd8"
MANAGE_PROTOCOL_CONTRACTS_ROLE = "0xeb7bfce47948ec1179e2358171d5ee7c821994c911519349b95313b685109031"
SET_EL_REWARDS_VAULT_ROLE = "0x9d68ad53a92b6f44b2e8fb18d211bf8ccb1114f6fafd56aa364515dfdf23c44f"
SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE = "0xca7d176c2da2028ed06be7e3b9457e6419ae0744dc311989e9b29f6a1ceb1003"
ADD_NODE_OPERATOR_ROLE = "0xe9367af2d321a2fc8d9c8f1e67f0fc1e2adf2f9844fb89ffa212619c713685b2"
SET_NODE_OPERATOR_ACTIVE_ROLE = "0xd856e115ac9805c675a51831fa7d8ce01c333d666b0e34b3fc29833b7c68936a"
SET_NODE_OPERATOR_NAME_ROLE = "0x58412970477f41493548d908d4307dfca38391d6bc001d56ffef86bd4f4a72e8"
SET_NODE_OPERATOR_ADDRESS_ROLE = "0xbf4b1c236312ab76e456c7a8cca624bd2f86c74a4f8e09b3a26d60b1ce492183"
REPORT_STOPPED_VALIDATORS_ROLE = "0x18ad851afd4930ecc8d243c8869bd91583210624f3f1572e99ee8b450315c80f"
MANAGE_MEMBERS = "0xbf6336045918ae0015f4cdb3441a2fdbfaa4bcde6558c8692aac7f56c69fb067"
MANAGE_QUORUM = "0xa5ffa9f45fa52c446078e834e1914561bd9c2ab1e833572d62af775da092ccbc"
SET_BEACON_SPEC = "0x16a273d48baf8111397316e6d961e6836913acb23b181e6c5fb35ec0bd2648fc"
SET_REPORT_BOUNDARIES = "0x44adaee26c92733e57241cb0b26ffaa2d182ed7120ba3ecd7e0dce3635c01dc1"
SET_BEACON_REPORT_RECEIVER = "0xe22a455f1bfbaf705ac3e891a64e156da92cb0b42cfc389158e6e82bd57f37be"

# New parameters
STAKING_MODULE_NOR_ID = 1
STAKING_MODULE_NOR_NAME = "curated-onchain-v1"
STAKING_MODULE_NOR_TYPE = (
    "0x637572617465642d6f6e636861696e2d76310000000000000000000000000000"  # bytes32("curated-onchain-v1");
)

LIDO_ORACLE_QUORUM = 5
LIDO_ORACLE_COMMITTEE_MEMBERS = (
    "0x140Bd8FbDc884f48dA7cb1c09bE8A2fAdfea776E",
    "0x1d0813bf088BE3047d827D98524fBf779Bc25F00",
    "0x404335BcE530400a5814375E7Ec1FB55fAff3eA2",
    "0x946D3b081ed19173dC83Cd974fC69e1e760B7d78",
    "0x007DE4a5F7bc37E2F26c0cb2E8A95006EE9B89b5",
    "0xEC4BfbAF681eb505B94E4a7849877DC6c600Ca3A",
    "0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8",
    "0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d",
    "0xA7410857ABbf75043d61ea54e07D57A6EB6EF186",
)

DEPOSIT_SECURITY_MODULE_GUARDIANS = (
    "0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1",
    "0x7912Fa976BcDe9c2cf728e213e892AD7588E6AaF",
    "0x14D5d5B71E048d2D75a39FfC5B407e3a3AB6F314",
    "0xf82D88217C249297C6037BA77CE34b3d8a90ab43",
    "0xa56b128Ea2Ea237052b0fA2a96a387C0E43157d8",
    "0xd4EF84b638B334699bcf5AF4B0410B8CCD71943f",
)
DEPOSIT_SECURITY_MODULE_GUARDIANS_QUORUM = 4

# type(uint256).max
TYPE_UINT256_MAX = 2**256 - 1

# PAUSE_INFINITELY from PausableUntil.sol
PAUSE_INFINITELY = TYPE_UINT256_MAX

# 0x01...withdrawal_vault or Lido.getWithdrawalCredentials()
WITHDRAWAL_CREDENTIALS = "0x010000000000000000000000b9d7934878b5fb9610b3fe8a5e441e8fad7e293f"


# Deployment parameters, see https://hackmd.io/pdix1r4yR46fXUqiHaNKyw
STUCK_PENALTY_DELAY = 432000
EPOCHS_PER_FRAME_FOR_ACCOUNTING_ORACLE = 225
EPOCHS_PER_FRAME_FOR_VALIDATORS_EXIT_BUS_ORACLE = 56

# Helper constant to mark that value of an event field is not checked
ANY_VALUE = None


# Roles related to vote #1
permission_staking_router = Permission(
    entity=STAKING_ROUTER,
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
        withdrawal_vault_manager.implementation() != WITHDRAWAL_VAULT_IMPLEMENTATION
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
        prepare_deploy_gate_seal_mock(deployer_eoa)
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
        withdrawal_vault_manager.implementation() == WITHDRAWAL_VAULT_IMPLEMENTATION
    ), "Wrong WithdrawalVault proxy implementation"

    #
    # Lido app upgrade checks
    #
    lido_new_app = contracts.lido_app_repo.getLatest()
    lido_proxy = interface.AppProxyUpgradeable(contracts.lido)
    assert_app_update(lido_new_app, lido_old_app, LIDO_IMPL)
    assert lido_proxy.implementation() == LIDO_IMPL, "Proxy should be updated"

    #
    # NodeOperatorsRegistry app upgrade checks
    #
    nor_new_app = contracts.nor_app_repo.getLatest()
    nor_proxy = interface.AppProxyUpgradeable(contracts.node_operators_registry)
    assert_app_update(nor_new_app, nor_old_app, NODE_OPERATORS_REGISTRY_IMPL)
    assert nor_proxy.implementation() == NODE_OPERATORS_REGISTRY_IMPL, "Proxy should be updated"

    #
    # LidoOracle app upgrade checks
    #
    oracle_new_app = contracts.oracle_app_repo.getLatest()
    oracle_proxy = interface.AppProxyUpgradeable(contracts.legacy_oracle)
    assert_app_update(oracle_new_app, oracle_old_app, ORACLE_IMPL)
    assert oracle_proxy.implementation() == ORACLE_IMPL, "Proxy should be updated"

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

    validate_withdrawal_vault_manager_upgrade_events(events_withdrawal_vault_upgrade, WITHDRAWAL_VAULT_IMPLEMENTATION)
    validate_start_upgrade_events(events_template_start)
    validate_push_to_repo_event(events_publish_lido_app, LIDO_APP_VERSION)
    validate_app_update_event(events_update_lido_impl, LIDO_APP_ID, LIDO_IMPL)
    validate_push_to_repo_event(events_publish_nor_app, NODE_OPERATORS_REGISTRY_APP_VERSION)
    validate_app_update_event(events_update_nor_impl, NODE_OPERATORS_REGISTRY_APP_ID, NODE_OPERATORS_REGISTRY_IMPL)
    validate_push_to_repo_event(events_publish_oracle_app, ORACLE_APP_VERSION)
    validate_app_update_event(events_update_oracle_impl, ORACLE_APP_ID, ORACLE_IMPL)
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
                    {"role": MANAGE_MEMBERS_AND_QUORUM_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS},
                ),
                (
                    "MemberAdded",
                    {"addr": LIDO_ORACLE_COMMITTEE_MEMBERS[0], "newTotalMembers": 1, "newQuorum": LIDO_ORACLE_QUORUM},
                ),
                ("QuorumSet", {"newQuorum": LIDO_ORACLE_QUORUM, "totalMembers": 1, "prevQuorum": 0}),
            ]
            + [
                (
                    "MemberAdded",
                    {
                        "addr": LIDO_ORACLE_COMMITTEE_MEMBERS[i],
                        "newTotalMembers": i + 1,
                        "newQuorum": LIDO_ORACLE_QUORUM,
                    },
                )
                for i in range(1, len(LIDO_ORACLE_COMMITTEE_MEMBERS))
            ]
            + [
                (
                    "RoleRevoked",
                    {"role": MANAGE_MEMBERS_AND_QUORUM_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS},
                ),
            ]
        )

    expected_events = (
        [
            # Vote item start
            ("LogScriptCall", {"sender": ANY_VALUE, "src": lido_dao_voting_address, "dst": TEMPLATE_ADDRESS}),
            # Proxy upgrades
            ("Upgraded", {"implementation": LIDO_LOCATOR_IMPL}),
            ("Upgraded", {"implementation": ACCOUNTING_ORACLE_IMPL}),
            ("Upgraded", {"implementation": VALIDATORS_EXIT_BUS_ORACLE_IMPL}),
            ("Upgraded", {"implementation": STAKING_ROUTER_IMPL}),
            ("Upgraded", {"implementation": WITHDRAWAL_QUEUE_IMPL}),
        ]
        # Migrate oracle committee for HashConsensus for AccountingOracle
        + hash_consensus_migration_events()
        # Migrate oracle committee for HashConsensus for ValidatorsExitBusOracle
        + hash_consensus_migration_events()
        + [
            # Template reports committee migrated
            ("OracleCommitteeMigrated", {"members": LIDO_ORACLE_COMMITTEE_MEMBERS, "quorum": LIDO_ORACLE_QUORUM}),
            # AccountingOracle + HashConsensus initialization
            (
                "FrameConfigSet",
                {"newInitialEpoch": ANY_VALUE, "newEpochsPerFrame": EPOCHS_PER_FRAME_FOR_ACCOUNTING_ORACLE},
            ),
            ("RoleGranted", {"role": DEFAULT_ADMIN_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
            ("ContractVersionSet", {"version": 1}),
            ("ConsensusHashContractSet", {"addr": HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE, "prevAddr": ZERO_ADDRESS}),
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
                {"role": DEFAULT_ADMIN_ROLE, "account": contracts.agent.address, "sender": TEMPLATE_ADDRESS},
            ),
            ("RoleRevoked", {"role": DEFAULT_ADMIN_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
        ]

    expected_events = (
        [
            # Vote item start
            ("LogScriptCall", {"sender": ANY_VALUE, "src": lido_dao_voting_address, "dst": TEMPLATE_ADDRESS}),
            # Initialize WithdrawalVault
            ("ContractVersionSet", {"version": 1}),
            # Initialize WithdrawalQueue
            ("Paused", {"duration": PAUSE_INFINITELY}),
            ("ContractVersionSet", {"version": 1}),
            ("RoleGranted", {"role": DEFAULT_ADMIN_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
            ("InitializedV1", {"_admin": TEMPLATE_ADDRESS}),
            ("RoleGranted", {"role": PAUSE_ROLE, "account": GATE_SEAL, "sender": TEMPLATE_ADDRESS}),
            ("RoleGranted", {"role": FINALIZE_ROLE, "account": contracts.lido.address, "sender": TEMPLATE_ADDRESS}),
            ("RoleGranted", {"role": ORACLE_ROLE, "account": ACCOUNTING_ORACLE, "sender": TEMPLATE_ADDRESS}),
            # Resume WithdrawalQueue
            ("RoleGranted", {"role": RESUME_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
            ("Resumed", {}),
            ("RoleRevoked", {"role": RESUME_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
            # Initialize HashConsensus + ValidatorsExitBusOracle
            (
                "FrameConfigSet",
                {"newInitialEpoch": ANY_VALUE, "newEpochsPerFrame": EPOCHS_PER_FRAME_FOR_VALIDATORS_EXIT_BUS_ORACLE},
            ),
            ("RoleGranted", {"role": DEFAULT_ADMIN_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
            ("Paused", {"duration": PAUSE_INFINITELY}),
            ("ContractVersionSet", {"version": 1}),
            (
                "ConsensusHashContractSet",
                {"addr": HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE, "prevAddr": ZERO_ADDRESS},
            ),
            ("ConsensusVersionSet", {"version": 1, "prevVersion": 0}),
            ("RoleGranted", {"role": PAUSE_ROLE, "account": GATE_SEAL, "sender": TEMPLATE_ADDRESS}),
            # Resume ValidatorsExitBusOracle
            ("RoleGranted", {"role": RESUME_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
            ("Resumed", {}),
            ("RoleRevoked", {"role": RESUME_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
            # Initialize StakingRouter
            ("ContractVersionSet", {"version": 1}),
            ("RoleGranted", {"role": DEFAULT_ADMIN_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS}),
            ("WithdrawalCredentialsSet", {"withdrawalCredentials": WITHDRAWAL_CREDENTIALS, "setBy": TEMPLATE_ADDRESS}),
            (
                "RoleGranted",
                {"role": STAKING_MODULE_PAUSE_ROLE, "account": DEPOSIT_SECURITY_MODULE, "sender": TEMPLATE_ADDRESS},
            ),
            (
                "RoleGranted",
                {"role": REPORT_EXITED_VALIDATORS_ROLE, "account": ACCOUNTING_ORACLE, "sender": TEMPLATE_ADDRESS},
            ),
            (
                "RoleGranted",
                {"role": REPORT_REWARDS_MINTED_ROLE, "account": contracts.lido.address, "sender": TEMPLATE_ADDRESS},
            ),
            # finalizeUpgrade LegacyOracle
            ("ContractVersionSet", {"version": 4}),
            # finalizeUpgrade Lido
            ("ContractVersionSet", {"version": 2}),
            ("EIP712StETHInitialized", {"eip712StETH": EIP_712_STETH}),
            ("Approval", {"owner": WITHDRAWAL_QUEUE, "spender": BURNER, "value": TYPE_UINT256_MAX}),
            ("LidoLocatorSet", {"lidoLocator": LIDO_LOCATOR}),
            # Grant burner role
            (
                "RoleGranted",
                {
                    "role": REQUEST_BURN_SHARES_ROLE,
                    "account": contracts.node_operators_registry.address,
                    "sender": TEMPLATE_ADDRESS,
                },
            ),
            # finalizeUpgrade NodeOperatorsRegistry
            ("ContractVersionSet", {"version": 2}),
            ("StuckPenaltyDelayChanged", {"stuckPenaltyDelay": STUCK_PENALTY_DELAY}),
            (
                "Approval",
                {"owner": contracts.node_operators_registry.address, "spender": BURNER, "value": TYPE_UINT256_MAX},
            ),
            ("LocatorContractSet", {"locatorAddress": LIDO_LOCATOR}),
            ("StakingModuleTypeSet", {"moduleType": STAKING_MODULE_NOR_TYPE}),
            ("KeysOpIndexSet", {"keysOpIndex": ANY_VALUE}),
            ("NonceChanged", {"nonce": ANY_VALUE}),
            (
                "RoleGranted",
                {"role": STAKING_MODULE_MANAGE_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS},
            ),
            ("StakingRouterETHDeposited", {"stakingModuleId": STAKING_MODULE_NOR_ID, "amount": 0}),
            (
                "StakingModuleAdded",
                {
                    "stakingModuleId": STAKING_MODULE_NOR_ID,
                    "stakingModule": contracts.node_operators_registry.address,
                    "name": STAKING_MODULE_NOR_NAME,
                    "createdBy": TEMPLATE_ADDRESS,
                },
            ),
            (
                "StakingModuleTargetShareSet",
                {"stakingModuleId": STAKING_MODULE_NOR_ID, "targetShare": 10000, "setBy": TEMPLATE_ADDRESS},
            ),
            (
                "StakingModuleFeesSet",
                {
                    "stakingModuleId": STAKING_MODULE_NOR_ID,
                    "stakingModuleFee": 500,
                    "treasuryFee": 500,
                    "setBy": TEMPLATE_ADDRESS,
                },
            ),
            (
                "RoleRevoked",
                {"role": STAKING_MODULE_MANAGE_ROLE, "account": TEMPLATE_ADDRESS, "sender": TEMPLATE_ADDRESS},
            ),
        ]
        # Migrate DepositSecurityModule
        + [("GuardianAdded", {"guardian": guardian}) for guardian in DEPOSIT_SECURITY_MODULE_GUARDIANS]
        + [
            ("GuardianQuorumChanged", {"newValue": DEPOSIT_SECURITY_MODULE_GUARDIANS_QUORUM}),
        ]
        # Transfer OZ admin roles for 7 contracts: HC for VEBO, HC for AO, Burner, SR, AO, VEBO, WQ
        + 7 * transfer_oz_admin_from_template_to_agent()
        # Change proxy admin for proxies of: Locator, SR, AO, VEBO, WQ
        + 5 * [("AdminChanged", {"previousAdmin": TEMPLATE_ADDRESS, "newAdmin": contracts.agent.address})]
        + [
            # Change DepositSecurityModule owner
            ("OwnerChanged", {"newValue": contracts.agent.address}),
            # UpgradeFinished
            ("UpgradeFinished", {}),
        ]
    )

    assert_events_equal(events, expected_events)
