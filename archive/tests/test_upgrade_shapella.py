"""
Tests for Lido V2 (Shapella-ready) upgrade voting 12/05/2023
"""
from brownie import interface, ZERO_ADDRESS, web3  # type: ignore
from utils.config import (
    contracts,
    AGENT,
    NODE_OPERATORS_REGISTRY,
    VOTING,
    LIDO,
    LEGACY_ORACLE,
    WITHDRAWAL_VAULT,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    ORACLE_COMMITTEE,
    DSM_GUARDIANS,
    LIDO_IMPL,
    NODE_OPERATORS_REGISTRY_IMPL,
    LEGACY_ORACLE_IMPL,
    LIDO_V2_UPGRADE_TEMPLATE,
    LIDO_LOCATOR,
    LIDO_LOCATOR_IMPL,
    BURNER,
    EIP712_STETH,
    ACCOUNTING_ORACLE,
    ACCOUNTING_ORACLE_IMPL,
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    STAKING_ROUTER,
    STAKING_ROUTER_IMPL,
    WITHDRAWAL_QUEUE,
    WITHDRAWAL_QUEUE_IMPL,
    HASH_CONSENSUS_FOR_AO,
    HASH_CONSENSUS_FOR_VEBO,
    DEPOSIT_SECURITY_MODULE_V1,
    GATE_SEAL,
    DEPOSIT_SECURITY_MODULE,
    WITHDRAWAL_VAULT_IMPL,
    WITHDRAWAL_VAULT_IMPL_V1,
    SELF_OWNED_STETH_BURNER,
    LIDO_ARAGON_APP_ID,
    ORACLE_ARAGON_APP_ID,
    NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
    CURATED_STAKING_MODULE_STUCK_PENALTY_DELAY,
    AO_EPOCHS_PER_FRAME,
    VEBO_EPOCHS_PER_FRAME,
    ORACLE_QUORUM,
    DSM_GUARDIAN_QUORUM,
    WITHDRAWAL_CREDENTIALS,
    CURATED_STAKING_MODULE_ID,
    CURATED_STAKING_MODULE_NAME,
    CURATED_STAKING_MODULE_TYPE,
    WQ_ERC721_TOKEN_BASE_URI,
)
from utils.test.helpers import almostEqEth
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import (
    Permission,
    PermissionP,
    validate_grant_role_event,
    validate_permission_create_event,
    validate_permission_revoke_event,
    validate_revoke_role_event,
)
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from utils.test.event_validators.payout import Payout, validate_token_payout_event
from scripts.upgrade_shapella import start_vote


# See Aragon apps getLatest()
LIDO_APP_VERSION = (4, 0, 0)
NODE_OPERATORS_REGISTRY_APP_VERSION = (4, 0, 0)
ORACLE_APP_VERSION = (4, 0, 0)


# type(uint256).max
TYPE_UINT256_MAX = 2**256 - 1

# PAUSE_INFINITELY from PausableUntil.sol
PAUSE_INFINITELY = TYPE_UINT256_MAX

# Helper constant to mark that value of an event field is not to be checked
ANY_VALUE = None


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
STAKING_MODULE_RESUME_ROLE = "0x9a2f67efb89489040f2c48c3b2c38f719fba1276678d2ced3bd9049fb5edc6b2"
STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"
REPORT_EXITED_VALIDATORS_ROLE = "0xc23292b191d95d2a7dd94fc6436eb44338fda9e1307d9394fd27c28157c1b33c"
REPORT_REWARDS_MINTED_ROLE = "0x779e5c23cb7a5bcb9bfe1e9a5165a00057f12bcdfd13e374540fdf1a1cd91137"
# Aragon new role
STAKING_ROUTER_ROLE = "0xbb75b874360e0bfd87f964eadd8276d8efb7c942134fc329b513032d0803e0c6"
# Aragon roles to revoke
MANAGE_FEE = "0x46b8504718b48a11e89304b407879435528b3cd3af96afde67dfe598e4683bd8"
MANAGE_WITHDRAWAL_KEY = "0x96088a8483023eb2f67b12aabbaf17d1d055e6ef387e563902adc1bba1e4028b"
MANAGE_PROTOCOL_CONTRACTS_ROLE = "0xeb7bfce47948ec1179e2358171d5ee7c821994c911519349b95313b685109031"
SET_EL_REWARDS_VAULT_ROLE = "0x9d68ad53a92b6f44b2e8fb18d211bf8ccb1114f6fafd56aa364515dfdf23c44f"
SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE = "0xca7d176c2da2028ed06be7e3b9457e6419ae0744dc311989e9b29f6a1ceb1003"
DEPOSIT_ROLE = "0x2561bf26f818282a3be40719542054d2173eb0d38539e8a8d3cff22f29fd2384"
BURN_ROLE = "0xe97b137254058bd94f28d2f3eb79e2d34074ffb488d042e3bc958e0a57d2fa22"
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
MANAGE_TOKEN_URI_ROLE = web3.keccak(text="MANAGE_TOKEN_URI_ROLE").hex()

GAS_FUNDER_MSIG = "0x5181d5D56Af4f823b96FE05f062D7a09761a5a53"

LIDO_ARAGON_CONTENT_URI="0x697066733a516d525358415a724632785235726762556445724456364c47746a7151315434415a677336796f586f734d516333"
NOR_ARAGON_CONTENT_URI="0x697066733a516d54346a64693146684d454b5576575351316877786e33365748394b6a656743755a7441684a6b6368526b7a70"
ORACLE_ARAGON_CONTENT_URI="0x697066733a516d575461635041557251614376414d5663716e5458766e7239544c666a57736861736334786a536865717a3269"

fund_payout = Payout(
    token_addr=LIDO,
    from_addr=AGENT,
    to_addr=GAS_FUNDER_MSIG,
    amount=50 * (10 ** 18)
)

# Roles related to vote #1
permission_staking_router = Permission(
    entity=STAKING_ROUTER,
    app=NODE_OPERATORS_REGISTRY,
    role=STAKING_ROUTER_ROLE,
)

# Roles related to vote #2
permissions_to_revoke = [
    Permission(
        entity=VOTING,
        app=LIDO,
        role=MANAGE_FEE,
    ),
    Permission(
        entity=VOTING,
        app=LIDO,
        role=MANAGE_WITHDRAWAL_KEY,
    ),
    Permission(
        entity=VOTING,
        app=LIDO,
        role=MANAGE_PROTOCOL_CONTRACTS_ROLE,
    ),
    Permission(
        entity=VOTING,
        app=LIDO,
        role=SET_EL_REWARDS_VAULT_ROLE,
    ),
    Permission(
        entity=VOTING,
        app=LIDO,
        role=SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE,
    ),
    Permission(
        entity=DEPOSIT_SECURITY_MODULE_V1,
        app=LIDO,
        role=DEPOSIT_ROLE,
    ),
    PermissionP(
        entity=SELF_OWNED_STETH_BURNER,
        app=LIDO,
        role=BURN_ROLE,
        # See 4th arg of vote item 8 of https://vote.lido.fi/vote/130 (need to convert from in to hex)
        params=["0x000100000000000000000000B280E33812c0B09353180e92e27b8AD399B07f26"],
    ),
    Permission(
        entity=VOTING,
        app=NODE_OPERATORS_REGISTRY,
        role=ADD_NODE_OPERATOR_ROLE,
    ),
    Permission(
        entity=VOTING,
        app=NODE_OPERATORS_REGISTRY,
        role=SET_NODE_OPERATOR_ACTIVE_ROLE,
    ),
    Permission(
        entity=VOTING,
        app=NODE_OPERATORS_REGISTRY,
        role=SET_NODE_OPERATOR_NAME_ROLE,
    ),
    Permission(
        entity=VOTING,
        app=NODE_OPERATORS_REGISTRY,
        role=SET_NODE_OPERATOR_ADDRESS_ROLE,
    ),
    Permission(
        entity=VOTING,
        app=NODE_OPERATORS_REGISTRY,
        role=REPORT_STOPPED_VALIDATORS_ROLE,
    ),
    Permission(
        entity=VOTING,
        app=LEGACY_ORACLE,
        role=MANAGE_MEMBERS,
    ),
    Permission(
        entity=VOTING,
        app=LEGACY_ORACLE,
        role=MANAGE_QUORUM,
    ),
    Permission(
        entity=VOTING,
        app=LEGACY_ORACLE,
        role=SET_BEACON_SPEC,
    ),
    Permission(
        entity=VOTING,
        app=LEGACY_ORACLE,
        role=SET_REPORT_BOUNDARIES,
    ),
    Permission(
        entity=VOTING,
        app=LEGACY_ORACLE,
        role=SET_BEACON_REPORT_RECEIVER,
    ),
]

def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
):
    withdrawal_vault_manager = interface.WithdrawalVaultManager(WITHDRAWAL_VAULT)
    lido_old_app = contracts.lido_app_repo.getLatest()
    nor_old_app = contracts.nor_app_repo.getLatest()
    oracle_old_app = contracts.oracle_app_repo.getLatest()

    #
    # Preliminary checks
    #
    assert (
        withdrawal_vault_manager.implementation() == WITHDRAWAL_VAULT_IMPL_V1
    ), "Wrong WithdrawalVault proxy initial implementation"
    assert withdrawal_vault_manager.proxy_getAdmin() == VOTING

    # ACL grant checks
    assert not contracts.acl.hasPermission(*permission_staking_router)

    # ACL revoke checks
    for permission in permissions_to_revoke:
        assert acl_has_permission(permission), f"No starting role {permission.role} on {permission.entity}"

    depositor_multisig_balance_before = contracts.lido.balanceOf(GAS_FUNDER_MSIG)
    dao_balance_before = contracts.lido.balanceOf(AGENT)

    # START VOTE
    if len(vote_ids_from_env) > 0:
        assert len(vote_ids_from_env) == 1, "This test script supports only single vote id"
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"UPGRADE TX voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    depositor_multisig_balance_after = contracts.lido.balanceOf(GAS_FUNDER_MSIG)
    dao_balance_after = contracts.lido.balanceOf(AGENT)

    assert almostEqEth(depositor_multisig_balance_after - depositor_multisig_balance_before, fund_payout.amount)
    assert almostEqEth(dao_balance_before - dao_balance_after, fund_payout.amount)

    #
    # WithdrawalVault upgrade checks
    #
    assert (
        withdrawal_vault_manager.implementation() == WITHDRAWAL_VAULT_IMPL
    ), "Wrong WithdrawalVault proxy implementation"

    #
    # Lido app upgrade checks
    #
    lido_new_app = contracts.lido_app_repo.getLatest()
    lido_proxy = interface.AppProxyUpgradeable(contracts.lido)
    assert_app_update(lido_new_app, lido_old_app, LIDO_IMPL, LIDO_ARAGON_CONTENT_URI)
    assert lido_proxy.implementation() == LIDO_IMPL, "Proxy should be updated"

    #
    # NodeOperatorsRegistry app upgrade checks
    #
    nor_new_app = contracts.nor_app_repo.getLatest()
    nor_proxy = interface.AppProxyUpgradeable(contracts.node_operators_registry)
    assert_app_update(nor_new_app, nor_old_app, NODE_OPERATORS_REGISTRY_IMPL, NOR_ARAGON_CONTENT_URI)
    assert nor_proxy.implementation() == NODE_OPERATORS_REGISTRY_IMPL, "Proxy should be updated"

    #
    # LidoOracle app upgrade checks
    #
    oracle_new_app = contracts.oracle_app_repo.getLatest()
    oracle_proxy = interface.AppProxyUpgradeable(contracts.legacy_oracle)
    assert_app_update(oracle_new_app, oracle_old_app, LEGACY_ORACLE_IMPL, ORACLE_ARAGON_CONTENT_URI)
    assert oracle_proxy.implementation() == LEGACY_ORACLE_IMPL, "Proxy should be updated"

    # ACL grant checks
    assert contracts.acl.hasPermission(*permission_staking_router)

    # ACL revoke checks
    for permission in permissions_to_revoke:
        assert not acl_has_permission(permission), f"Role {permission.role} is still on {permission.entity}"

    #
    # Template checks
    #
    assert contracts.shapella_upgrade_template._isUpgradeFinished()

    if bypass_events_decoding:
        return

    display_voting_events(vote_tx)

    grouped_voting_events: List[EventDict] = group_voting_events(vote_tx)
    assert len(grouped_voting_events) == 31

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
        *remaining_events,
    ) = grouped_voting_events

    revoke_roles_events = remaining_events[:17]
    (
        events_grant_base_uri_manager_role,
        events_set_base_uri,
        events_revoke_base_uri_manager_role,
        events_fund_gas_funder
    ) = remaining_events[17:]

    validate_withdrawal_vault_manager_upgrade_events(events_withdrawal_vault_upgrade, WITHDRAWAL_VAULT_IMPL)
    validate_start_upgrade_events(events_template_start)
    validate_push_to_repo_event(events_publish_lido_app, LIDO_APP_VERSION)
    validate_app_update_event(events_update_lido_impl, LIDO_ARAGON_APP_ID, LIDO_IMPL)
    validate_push_to_repo_event(events_publish_nor_app, NODE_OPERATORS_REGISTRY_APP_VERSION)
    validate_app_update_event(
        events_update_nor_impl, NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL
    )
    validate_push_to_repo_event(events_publish_oracle_app, ORACLE_APP_VERSION)
    validate_app_update_event(events_update_oracle_impl, ORACLE_ARAGON_APP_ID, LEGACY_ORACLE_IMPL)
    validate_permission_create_event(
        events_grant_staking_router_role, permission_staking_router, manager=contracts.voting
    )
    validate_finish_upgrade_events(events_template_finish)

    for e, permission in zip(revoke_roles_events, permissions_to_revoke):
        validate_permission_revoke_event(e, permission)

    validate_grant_role_event(
        events_grant_base_uri_manager_role, MANAGE_TOKEN_URI_ROLE, contracts.voting, contracts.agent.address
    )
    validate_set_base_uri_event(events_set_base_uri, WQ_ERC721_TOKEN_BASE_URI)
    validate_revoke_role_event(
        events_revoke_base_uri_manager_role, MANAGE_TOKEN_URI_ROLE, contracts.voting, contracts.agent.address
    )
    validate_token_payout_event(events_fund_gas_funder, fund_payout, is_steth=True)


def acl_has_permission(permission):
    if isinstance(permission, Permission):
        return contracts.acl.hasPermission(*permission)
    elif isinstance(permission, PermissionP):
        return contracts.acl.hasPermission["address,address,bytes32,uint[]"](*permission)
    else:
        assert False, "unexpected permission type structure"


def assert_app_update(new_app, old_app, contract_address, new_content_uri):
    assert old_app[1] != new_app[1], "Address should change"
    assert new_app[1] == contract_address, "New address should match"
    assert new_app[0][0] == old_app[0][0] + 1, "Major version should increment"
    assert old_app[2] != new_app[2], "Content uri must change"
    assert new_app[2] == new_content_uri, "Content uri should match"


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


def validate_set_base_uri_event(events: EventDict, base_uri: str):
    _events_chain = ["LogScriptCall", "BaseURISet"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("BaseURISet") == 1
    assert events["BaseURISet"]["baseURI"] == base_uri, "Wrong base uri"


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
                        "account": LIDO_V2_UPGRADE_TEMPLATE,
                        "sender": LIDO_V2_UPGRADE_TEMPLATE,
                    },
                ),
                (
                    "MemberAdded",
                    {"addr": ORACLE_COMMITTEE[0], "newTotalMembers": 1, "newQuorum": ORACLE_QUORUM},
                ),
                ("QuorumSet", {"newQuorum": ORACLE_QUORUM, "totalMembers": 1, "prevQuorum": 0}),
            ]
            + [
                (
                    "MemberAdded",
                    {
                        "addr": ORACLE_COMMITTEE[i],
                        "newTotalMembers": i + 1,
                        "newQuorum": ORACLE_QUORUM,
                    },
                )
                for i in range(1, len(ORACLE_COMMITTEE))
            ]
            + [
                (
                    "RoleRevoked",
                    {
                        "role": MANAGE_MEMBERS_AND_QUORUM_ROLE,
                        "account": LIDO_V2_UPGRADE_TEMPLATE,
                        "sender": LIDO_V2_UPGRADE_TEMPLATE,
                    },
                ),
            ]
        )

    expected_events = (
        [
            # Vote item start
            (
                "LogScriptCall",
                {"sender": ANY_VALUE, "src": VOTING, "dst": LIDO_V2_UPGRADE_TEMPLATE},
            ),
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
            ("OracleCommitteeMigrated", {"members": ORACLE_COMMITTEE, "quorum": ORACLE_QUORUM}),
            # AccountingOracle + HashConsensus initialization
            (
                "FrameConfigSet",
                {"newInitialEpoch": ANY_VALUE, "newEpochsPerFrame": AO_EPOCHS_PER_FRAME},
            ),
            (
                "RoleGranted",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            ("ContractVersionSet", {"version": 1}),
            (
                "ConsensusHashContractSet",
                {"addr": HASH_CONSENSUS_FOR_AO, "prevAddr": ZERO_ADDRESS},
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
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            (
                "RoleRevoked",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
        ]

    expected_events = (
        [
            # Vote item start
            (
                "LogScriptCall",
                {"sender": ANY_VALUE, "src": VOTING, "dst": LIDO_V2_UPGRADE_TEMPLATE},
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
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            ("InitializedV1", {"_admin": LIDO_V2_UPGRADE_TEMPLATE}),
            (
                "RoleGranted",
                {"role": PAUSE_ROLE, "account": GATE_SEAL, "sender": LIDO_V2_UPGRADE_TEMPLATE},
            ),
            (
                "RoleGranted",
                {"role": FINALIZE_ROLE, "account": contracts.lido.address, "sender": LIDO_V2_UPGRADE_TEMPLATE},
            ),
            (
                "RoleGranted",
                {
                    "role": ORACLE_ROLE,
                    "account": ACCOUNTING_ORACLE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            # Resume WithdrawalQueue
            (
                "RoleGranted",
                {
                    "role": RESUME_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            ("Resumed", {}),
            (
                "RoleRevoked",
                {
                    "role": RESUME_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            # Initialize HashConsensus + ValidatorsExitBusOracle
            (
                "FrameConfigSet",
                {"newInitialEpoch": ANY_VALUE, "newEpochsPerFrame": VEBO_EPOCHS_PER_FRAME},
            ),
            (
                "RoleGranted",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            ("Paused", {"duration": PAUSE_INFINITELY}),
            ("ContractVersionSet", {"version": 1}),
            (
                "ConsensusHashContractSet",
                {"addr": HASH_CONSENSUS_FOR_VEBO, "prevAddr": ZERO_ADDRESS},
            ),
            ("ConsensusVersionSet", {"version": 1, "prevVersion": 0}),
            (
                "RoleGranted",
                {"role": PAUSE_ROLE, "account": GATE_SEAL, "sender": LIDO_V2_UPGRADE_TEMPLATE},
            ),
            # Resume ValidatorsExitBusOracle
            (
                "RoleGranted",
                {
                    "role": RESUME_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            ("Resumed", {}),
            (
                "RoleRevoked",
                {
                    "role": RESUME_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            # Initialize StakingRouter
            ("ContractVersionSet", {"version": 1}),
            (
                "RoleGranted",
                {
                    "role": DEFAULT_ADMIN_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            (
                "WithdrawalCredentialsSet",
                {"withdrawalCredentials": WITHDRAWAL_CREDENTIALS, "setBy": LIDO_V2_UPGRADE_TEMPLATE},
            ),
            (
                "RoleGranted",
                {
                    "role": STAKING_MODULE_PAUSE_ROLE,
                    "account": DEPOSIT_SECURITY_MODULE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            (
                "RoleGranted",
                {
                    "role": STAKING_MODULE_RESUME_ROLE,
                    "account": DEPOSIT_SECURITY_MODULE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            (
                "RoleGranted",
                {
                    "role": REPORT_EXITED_VALIDATORS_ROLE,
                    "account": ACCOUNTING_ORACLE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            (
                "RoleGranted",
                {
                    "role": REPORT_REWARDS_MINTED_ROLE,
                    "account": contracts.lido.address,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            # finalizeUpgrade LegacyOracle
            ("ContractVersionSet", {"version": 4}),
            # finalizeUpgrade Lido
            ("ContractVersionSet", {"version": 2}),
            ("EIP712StETHInitialized", {"eip712StETH": EIP712_STETH}),
            ("Approval", {"owner": WITHDRAWAL_QUEUE, "spender": BURNER, "value": TYPE_UINT256_MAX}),
            ("LidoLocatorSet", {"lidoLocator": LIDO_LOCATOR}),
            # Grant burner role
            (
                "RoleGranted",
                {
                    "role": REQUEST_BURN_SHARES_ROLE,
                    "account": contracts.node_operators_registry.address,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            # finalizeUpgrade NodeOperatorsRegistry
            ("ContractVersionSet", {"version": 2}),
            ("StuckPenaltyDelayChanged", {"stuckPenaltyDelay": CURATED_STAKING_MODULE_STUCK_PENALTY_DELAY}),
            (
                "Approval",
                {
                    "owner": contracts.node_operators_registry.address,
                    "spender": BURNER,
                    "value": TYPE_UINT256_MAX,
                },
            ),
            ("LocatorContractSet", {"locatorAddress": LIDO_LOCATOR}),
            ("StakingModuleTypeSet", {"moduleType": CURATED_STAKING_MODULE_TYPE}),
            ("KeysOpIndexSet", {"keysOpIndex": ANY_VALUE}),
            ("NonceChanged", {"nonce": ANY_VALUE}),
            (
                "RoleGranted",
                {
                    "role": STAKING_MODULE_MANAGE_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            ("StakingRouterETHDeposited", {"stakingModuleId": CURATED_STAKING_MODULE_ID, "amount": 0}),
            (
                "StakingModuleAdded",
                {
                    "stakingModuleId": CURATED_STAKING_MODULE_ID,
                    "stakingModule": contracts.node_operators_registry.address,
                    "name": CURATED_STAKING_MODULE_NAME,
                    "createdBy": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            (
                "StakingModuleTargetShareSet",
                {
                    "stakingModuleId": CURATED_STAKING_MODULE_ID,
                    "targetShare": 10000,
                    "setBy": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            (
                "StakingModuleFeesSet",
                {
                    "stakingModuleId": CURATED_STAKING_MODULE_ID,
                    "stakingModuleFee": 500,
                    "treasuryFee": 500,
                    "setBy": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
            (
                "RoleRevoked",
                {
                    "role": STAKING_MODULE_MANAGE_ROLE,
                    "account": LIDO_V2_UPGRADE_TEMPLATE,
                    "sender": LIDO_V2_UPGRADE_TEMPLATE,
                },
            ),
        ]
        # Migrate DepositSecurityModule
        + [("GuardianAdded", {"guardian": guardian}) for guardian in DSM_GUARDIANS]
        + [
            ("GuardianQuorumChanged", {"newValue": DSM_GUARDIAN_QUORUM}),
        ]
        # Transfer OZ admin roles for 7 contracts: HC for VEBO, HC for AO, Burner, SR, AO, VEBO, WQ
        + 7 * transfer_oz_admin_from_template_to_agent()
        # Change proxy admin for proxies of: Locator, SR, AO, VEBO, WQ
        + 5 * [("AdminChanged", {"previousAdmin": LIDO_V2_UPGRADE_TEMPLATE, "newAdmin": contracts.agent.address})]
        + [
            # Change DepositSecurityModule owner
            ("OwnerChanged", {"newValue": contracts.agent.address}),
            # UpgradeFinished
            ("UpgradeFinished", {}),
        ]
    )

    assert_events_equal(events, expected_events)
