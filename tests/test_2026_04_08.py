from brownie import chain, interface, web3, reverts
from brownie.network.transaction import TransactionReceipt
import pytest

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events,
)
from utils.evm_script import encode_call_script
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.easy_track import create_permissions
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    validate_evmscript_factory_removed_event,
    EVMScriptFactoryAdded,
)
from utils.permission_parameters import Param, Op, ArgumentValue
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_deactivated,
    validate_node_operator_name_set_event,
    NodeOperatorNameSetItem,
    validate_node_operator_reward_address_set_event,
    NodeOperatorRewardAddressSetItem,
    validate_target_validators_count_changed_event,
    TargetValidatorsCountChanged,
)
from utils.test.event_validators.hash_consensus import (
    validate_hash_consensus_member_removed,
    validate_hash_consensus_member_added,
)
from utils.test.event_validators.proxy import validate_proxy_upgrade_event
from utils.test.event_validators.permission import Permission, validate_permission_grantp_event
from utils.test.event_validators.allowed_recipients_registry import validate_set_limit_parameter_event, validate_set_spent_amount_event
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.easy_track_helpers import create_and_enact_payment_motion, create_and_enact_motion, _encode_calldata


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2026_04_08 import (
    start_vote,
    get_vote_items,
    get_dg_items,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================

# DAO addresses
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
EASYTRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"

# Curated Module
CURATED_MODULE = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
OPERATOR_GRID = "0xC69685E89Cefc327b43B7234AC646451B27c544d"

# Proxy upgrades
LAZY_ORACLE_PROXY = "0x5DB427080200c235F2Ae8Cd17A7be87921f7AD6c"
LAZY_ORACLE_IMPL_OLD = "0x47f3a6b1E70F7Ec7dBC3CB510B1fdB948C863a5B"
LAZY_ORACLE_IMPL_NEW = "0x96c9a897D116ef660086d3aA67b3af653324aB37"
VAULT_HUB_PROXY = "0x1d201BE093d847f6446530Efb0E8Fb426d176709"
VAULT_HUB_IMPL_OLD = "0x7c7d957D0752AB732E73400624C4a1eb1cb6CF50"
VAULT_HUB_IMPL_NEW = "0x6330fE7756FBE8649adfb9A541d61C5edB8B4D70"
ZKSYNC_L1_ERC20_BRIDGE = "0x41527B2d03844dB6b0945f25702cB958b6d55989"
ZKSYNC_L1_ERC20_BRIDGE_IMPL_OLD = "0x9a810469F4a451Ebb7ef53672142053b4971587c"
ZKSYNC_L1_ERC20_BRIDGE_IMPL_NEW = "0x43a66b32c9adca1a59b273e69b61da5197c21ccd"
WSTETH = "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0"
ZKSYNC_L2_GAS_PRICE = 800  # ZkSync constant: minimum gas price per pubdata byte for L1→L2 txs
ZKSYNC_L2_BRIDGE = "0xE1D6A50E7101c8f8db77352897Ee3f1AC53f782B"
ZKSYNC_L2_TOKEN = "0x703b52F2b28fEbcB60E1372858AF5b18849FE867"
VEBO = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"

# Chorus One oracle member rotation
CHORUS_ONE_ORACLE_MEMBER_OLD = "0x285f8537e1daeedaf617e96c742f2cf36d63ccfb"
CHORUS_ONE_ORACLE_MEMBER_NEW = "0x8dB977C13CAA938BC58464bFD622DF0570564b78"
HASH_CONSENSUS_FOR_AO = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
CS_HASH_CONSENSUS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"
HASH_CONSENSUS_FOR_VEBO = "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"

# Stakefish oracle member rotation
STAKEFISH_ORACLE_MEMBER_OLD = "0x946D3b081ed19173dC83Cd974fC69e1e760B7d78"
STAKEFISH_ORACLE_MEMBER_NEW = "0x042a9e5acCfa17e28300F1b5967f20891E973922"

# Staking Router
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"

# Node operators
A41_NO_ID = 32
A41_NAME = "A41"
STAKIN_NO_ID = 14
STAKIN_NAME_OLD = "Stakin"
STAKIN_NAME_NEW = "Stakin by The Tie"
STAKIN_REWARD_ADDRESS_OLD = "0xf6b0a1B771633DB40A3e21Cc49fD2FE35669eF46"
STAKIN_REWARD_ADDRESS_NEW = "0x3e97EC699191bEfc63EF4E4275204B03E7465f30"
CHORUS_ONE_NO_ID = 3
CHORUS_ONE_NAME = "Chorus One"
CONSENSYS_NO_ID = 21
CONSENSYS_NAME = "Consensys"
CONSENSYS_MANAGE_SIGNING_KEYS_ADDRESS = "0xF45C77EadD434612fCD93db978B3E36B0D58eC99"
MANAGE_SIGNING_KEYS = web3.keccak(text="MANAGE_SIGNING_KEYS").hex()

# Gas Supply
STETH_TOKEN = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
GAS_SUPPLY_TRUSTED_CALLER = "0x5181d5D56Af4f823b96FE05f062D7a09761a5a53"
GAS_SUPPLY_TOP_UP_FACTORY = "0x200dA0b6a9905A377CF8D469664C65dB267009d1"
GAS_SUPPLY_ALLOWED_RECIPIENTS_REGISTRY = "0x49d1363016aA899bba09ae972a1BF200dDf8C55F"
GAS_SUPPLY_OLD_LIMIT = 1000 * 10**18
GAS_SUPPLY_NEW_LIMIT = 150 * 10**18
GAS_SUPPLY_PERIOD_DURATION_MONTHS = 12
GAS_SUPPLY_PERIOD_START = 1704067200  # Jan 1, 2024 00:00:00 UTC
GAS_SUPPLY_PERIOD_END = 1735689600  # Jan 1, 2025 00:00:00 UTC

GAS_SUPPLY_PERIOD_START_AFTER = 1767225600 # Jan 1, 2026 00:00:00 UTC
GAS_SUPPLY_PERIOD_END_AFTER = 1798761600 # Jan 1, 2027 00:00:00 UTC
GAS_SUPPLY_SPENT_AMOUNT_EXPECTED = 0

# Target limit mode
NO_TARGET_LIMIT_SOFT_MODE = 1

# CSM staking module update
CSM_MODULE_ID = 3
CSM_MODULE_NAME = "Community Staking"
CSM_MODULE_ADDRESS = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
CSM_STAKE_SHARE_LIMIT_BEFORE = 750
CSM_STAKE_SHARE_LIMIT_AFTER = 850
CSM_PRIORITY_EXIT_SHARE_THRESHOLD_BEFORE = 900
CSM_PRIORITY_EXIT_SHARE_THRESHOLD_AFTER = 1020
CSM_MODULE_FEE_BP = 600
CSM_TREASURY_FEE_BP = 400
CSM_MAX_DEPOSITS_PER_BLOCK = 30
CSM_MIN_DEPOSIT_BLOCK_DISTANCE = 25

# Easy Track
ST_VAULTS_COMMITTEE = "0x18A1065c81b0Cc356F1b1C843ddd5E14e4AefffF"
EASYTRACK_EVMSCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

# Easy Track factories
OLD_SDVT_SUBMIT_EXIT_HASHES_FACTORY = "0xB7668B5485d0f826B86a75b0115e088bB9ee03eE"
OLD_CURATED_SUBMIT_EXIT_HASHES_FACTORY = "0x8aa34dAaF0fC263203A15Bcfa0Ed926D466e59F3"
NEW_SDVT_SUBMIT_EXIT_HASHES_FACTORY = "0x58A59dDC6Aea9b1D5743D024E15DfA4badB56E37"
NEW_CURATED_SUBMIT_EXIT_HASHES_FACTORY = "0x4F716AD3Cc7A3A5cdA2359e5B2c84335c171dCde"
OLD_REGISTER_GROUPS_FACTORY = "0xE73842AEbEC99Dacf2aAEec61409fD01A033f478"
OLD_REGISTER_TIERS_FACTORY = "0x5292A1284e4695B95C0840CF8ea25A818751C17F"
OLD_ALTER_TIERS_FACTORY = "0x73f80240ad9363d5d3C5C3626953C351cA36Bfe9"
NEW_REGISTER_GROUPS_FACTORY = "0x17305dB55c908e84C58BbDCa57258A7D1f7eEa7c"
NEW_REGISTER_TIERS_FACTORY = "0x6b535F441F95046562406F4E2518D9AD7Db2dc0D"
NEW_ALTER_TIERS_FACTORY = "0x37d9B09EDA477a84E3913fCB4d032EFb0BF9B62E"

# Function names for permissions
OPERATOR_GRID_REGISTER_GROUP = "registerGroup"
OPERATOR_GRID_REGISTER_TIERS = "registerTiers"
OPERATOR_GRID_ALTER_TIERS = "alterTiers"
SUBMIT_EXIT_REQUESTS = "submitExitRequestsHash"


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = 199
EXPECTED_DG_PROPOSAL_ID = 9
EXPECTED_VOTE_EVENTS_COUNT = 11  # 1 DG submit + 5 factory removes + 5 factory adds
EXPECTED_DG_EVENTS_FROM_AGENT = 24
EXPECTED_DG_EVENTS_COUNT = 24
IPFS_DESCRIPTION_HASH = ""  # TODO: add
DG_PROPOSAL_METADATA = "Deactivate A41, update Stakin, upgrade LazyOracle/VaultHub/ZKSync bridge, rotate Chorus One oracle member, rotate Stakefish oracle member, set Chorus One target limit, grant MANAGE_SIGNING_KEYS to Consensys, decrease Gas Supply limit, raise CSM stake share limit and priority exit threshold"


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    dg_items = get_dg_items()

    proposal_calls = []
    for dg_item in dg_items:
        target, data = dg_item
        proposal_calls.append({"target": target, "value": 0, "data": data})

    return proposal_calls


def register_groups_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid):
    operator_addresses = [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
    ]
    share_limits = [1000, 5000]
    tiers_params_array = [
        [(500, 200, 100, 50, 40, 10), (800, 200, 100, 50, 40, 10)],
        [(800, 200, 100, 50, 40, 10), (800, 200, 100, 50, 40, 10)],
    ]

    # Check initial state
    for operator_address in operator_addresses:
        group = operator_grid.group(operator_address)
        assert group[0] == "0x0000000000000000000000000000000000000000"  # operator
        assert group[1] == 0  # shareLimit
        assert len(group[3]) == 0  # tiersId array should be empty

    create_and_enact_motion(
        easy_track,
        trusted_address,
        NEW_REGISTER_GROUPS_FACTORY,
        _encode_calldata(
            ["address[]", "uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"],
            [operator_addresses, share_limits, tiers_params_array],
        ),
        stranger,
    )

    # Check final state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == share_limits[i]  # shareLimit
        assert len(group[3]) == len(tiers_params_array[i])  # tiersId array should match tiers_params
        for j, tier_id in enumerate(group[3]):
            tier = operator_grid.tier(tier_id)
            assert tier[1] == tiers_params_array[i][j][0]  # shareLimit
            assert tier[3] == tiers_params_array[i][j][1]  # reserveRatioBP
            assert tier[4] == tiers_params_array[i][j][2]  # forcedRebalanceThresholdBP
            assert tier[5] == tiers_params_array[i][j][3]  # infraFeeBP
            assert tier[6] == tiers_params_array[i][j][4]  # liquidityFeeBP
            assert tier[7] == tiers_params_array[i][j][5]  # reservationFeeBP


def register_tiers_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid, accounts):
    operator_addresses = [
        "0x0000000000000000000000000000000000000003",
        "0x0000000000000000000000000000000000000004",
    ]
    tiers_params_array = [
        [(500, 200, 100, 50, 40, 10), (300, 150, 75, 25, 20, 5)],
        [(800, 250, 125, 60, 50, 15), (400, 180, 90, 30, 25, 8)],
    ]

    executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
    for operator_address in operator_addresses:
        operator_grid.registerGroup(operator_address, 1000, {"from": executor})
        group = operator_grid.group(operator_address)
        assert len(group[3]) == 0  # no tiers yet

    create_and_enact_motion(
        easy_track,
        trusted_address,
        NEW_REGISTER_TIERS_FACTORY,
        _encode_calldata(
            ["address[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"],
            [operator_addresses, tiers_params_array],
        ),
        stranger,
    )

    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert len(group[3]) == len(tiers_params_array[i])
        for j, tier_id in enumerate(group[3]):
            tier = operator_grid.tier(tier_id)
            assert tier[1] == tiers_params_array[i][j][0]  # shareLimit
            assert tier[3] == tiers_params_array[i][j][1]  # reserveRatioBP
            assert tier[4] == tiers_params_array[i][j][2]  # forcedRebalanceThresholdBP
            assert tier[5] == tiers_params_array[i][j][3]  # infraFeeBP
            assert tier[6] == tiers_params_array[i][j][4]  # liquidityFeeBP
            assert tier[7] == tiers_params_array[i][j][5]  # reservationFeeBP


def alter_tiers_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid, accounts):
    initial_tier_params = [(1000, 200, 100, 50, 40, 10), (1000, 200, 100, 50, 40, 10)]
    new_tier_params = [(2000, 300, 150, 75, 60, 20), (3000, 400, 200, 100, 80, 30)]

    executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
    operator_address = "0x0000000000000000000000000000000000000005"
    operator_grid.registerGroup(operator_address, 10000, {"from": executor})
    operator_grid.registerTiers(operator_address, initial_tier_params, {"from": executor})

    tiers_count = operator_grid.tiersCount()
    tier_ids = [tiers_count - 2, tiers_count - 1]

    # Check initial state
    for i, tier_id in enumerate(tier_ids):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == initial_tier_params[i][0]  # shareLimit
        assert tier[3] == initial_tier_params[i][1]  # reserveRatioBP
        assert tier[4] == initial_tier_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == initial_tier_params[i][3]  # infraFeeBP
        assert tier[6] == initial_tier_params[i][4]  # liquidityFeeBP
        assert tier[7] == initial_tier_params[i][5]  # reservationFeeBP

    create_and_enact_motion(
        easy_track,
        trusted_address,
        NEW_ALTER_TIERS_FACTORY,
        _encode_calldata(
            ["uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[]"],
            [tier_ids, new_tier_params],
        ),
        stranger,
    )

    # Check final state
    for i, tier_id in enumerate(tier_ids):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == new_tier_params[i][0]  # shareLimit
        assert tier[3] == new_tier_params[i][1]  # reserveRatioBP
        assert tier[4] == new_tier_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == new_tier_params[i][3]  # infraFeeBP
        assert tier[6] == new_tier_params[i][4]  # liquidityFeeBP
        assert tier[7] == new_tier_params[i][5]  # reservationFeeBP


def zksync_bridge_smoke_test(stranger, bridge):
    l1_token = bridge.l1Token()
    assert l1_token == WSTETH
    l2_bridge = bridge.l2Bridge()
    assert l2_bridge == ZKSYNC_L2_BRIDGE
    l2_token = bridge.l2Token()
    assert l2_token == ZKSYNC_L2_TOKEN
    l1_wsteth = interface.WstETH(l1_token)
    deposit_amount = 10**15  # 0.001 wstETH

    chain.snapshot()

    stranger.transfer(l1_token, "0.01 ether")
    assert l1_wsteth.balanceOf(stranger) >= deposit_amount

    l1_wsteth.approve(ZKSYNC_L1_ERC20_BRIDGE, deposit_amount, {"from": stranger})
    bridge_balance_before = l1_wsteth.balanceOf(ZKSYNC_L1_ERC20_BRIDGE)

    deposit_tx = bridge.deposit(
        stranger.address,
        l1_token,
        deposit_amount,
        300_000, # gas limit
        ZKSYNC_L2_GAS_PRICE,
        {"from": stranger, "value": "0.01 ether"},
    )

    assert "DepositInitiated" in deposit_tx.events
    deposit_evt = deposit_tx.events["DepositInitiated"]
    assert deposit_evt["from"] == stranger.address
    assert deposit_evt["to"] == stranger.address
    assert deposit_evt["l1Token"] == l1_token
    assert deposit_evt["amount"] == deposit_amount
    assert l1_wsteth.balanceOf(ZKSYNC_L1_ERC20_BRIDGE) == bridge_balance_before + deposit_amount

    chain.revert()


def et_gas_supply_limit_test(easy_track, gas_supply_registry, stranger, accounts):
    chain.snapshot()
    trusted_caller_account = accounts.at(GAS_SUPPLY_TRUSTED_CALLER, force=True)
    steth = interface.ERC20(STETH_TOKEN)
    spendable_left = 10  # wei
    to_spend = GAS_SUPPLY_NEW_LIMIT - spendable_left  # leave 10 wei to check spendable balance after motion enact

    create_and_enact_payment_motion(
        easy_track,
        GAS_SUPPLY_TRUSTED_CALLER,
        GAS_SUPPLY_TOP_UP_FACTORY,
        steth,
        [trusted_caller_account],
        [to_spend],
        stranger,
    )

    (
        gas_supply_already_spent,
        gas_supply_spendable,
        gas_supply_period_start,
        gas_supply_period_end,
    ) = gas_supply_registry.getPeriodState()
    assert gas_supply_already_spent == to_spend
    assert gas_supply_spendable == spendable_left
    assert gas_supply_period_start == GAS_SUPPLY_PERIOD_START_AFTER
    assert gas_supply_period_end == GAS_SUPPLY_PERIOD_END_AFTER

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            GAS_SUPPLY_TRUSTED_CALLER,
            GAS_SUPPLY_TOP_UP_FACTORY,
            steth,
            [trusted_caller_account],
            [spendable_left + 1],  # try to spend more than the spendable balance
            stranger,
        )
    chain.revert()


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    acl = interface.ACL(ACL)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    easy_track = interface.EasyTrack(EASYTRACK)

    no_registry = interface.NodeOperatorsRegistry(CURATED_MODULE)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    lazy_oracle_proxy = interface.OssifiableProxy(LAZY_ORACLE_PROXY)
    vault_hub_proxy = interface.OssifiableProxy(VAULT_HUB_PROXY)
    zksync_bridge_proxy = interface.OssifiableProxy(ZKSYNC_L1_ERC20_BRIDGE)
    zksync_bridge = interface.ZkSyncL1ERC20Bridge(ZKSYNC_L1_ERC20_BRIDGE)
    hash_consensus_for_ao = interface.HashConsensus(HASH_CONSENSUS_FOR_AO)
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    hash_consensus_for_vebo = interface.HashConsensus(HASH_CONSENSUS_FOR_VEBO)
    gas_supply_registry = interface.AllowedRecipientRegistry(GAS_SUPPLY_ALLOWED_RECIPIENTS_REGISTRY)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    vebo = interface.ValidatorsExitBusOracle(VEBO)

    perm_param = Param(0, Op.EQ, ArgumentValue(CONSENSYS_NO_ID))
    perm_param_uint = perm_param.to_uint256()

    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        if EXPECTED_VOTE_ID is not None:
            assert vote_id == EXPECTED_VOTE_ID
    elif EXPECTED_VOTE_ID is not None and voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
    onchain_script = voting.getVote(vote_id)["script"]
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()

    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        initial_factories = easy_track.getEVMScriptFactories()
        initial_factories_len = len(initial_factories)
        # Items 2-11: Old ET factories present, new ones absent
        assert OLD_SDVT_SUBMIT_EXIT_HASHES_FACTORY in initial_factories
        assert OLD_CURATED_SUBMIT_EXIT_HASHES_FACTORY in initial_factories
        assert OLD_REGISTER_GROUPS_FACTORY in initial_factories
        assert OLD_REGISTER_TIERS_FACTORY in initial_factories
        assert OLD_ALTER_TIERS_FACTORY in initial_factories

        assert NEW_SDVT_SUBMIT_EXIT_HASHES_FACTORY not in initial_factories
        assert NEW_CURATED_SUBMIT_EXIT_HASHES_FACTORY not in initial_factories
        assert NEW_REGISTER_GROUPS_FACTORY not in initial_factories
        assert NEW_REGISTER_TIERS_FACTORY not in initial_factories
        assert NEW_ALTER_TIERS_FACTORY not in initial_factories

        # assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH  # TODO: uncomment after IPFS upload

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        new_factories = easy_track.getEVMScriptFactories()
        assert len(new_factories) == initial_factories_len
        # Items 2-11: Old ET factories removed, new ones added
        assert OLD_SDVT_SUBMIT_EXIT_HASHES_FACTORY not in new_factories
        assert OLD_CURATED_SUBMIT_EXIT_HASHES_FACTORY not in new_factories
        assert NEW_SDVT_SUBMIT_EXIT_HASHES_FACTORY in new_factories
        assert NEW_CURATED_SUBMIT_EXIT_HASHES_FACTORY in new_factories
        assert OLD_REGISTER_GROUPS_FACTORY not in new_factories
        assert OLD_REGISTER_TIERS_FACTORY not in new_factories
        assert OLD_ALTER_TIERS_FACTORY not in new_factories
        assert NEW_REGISTER_GROUPS_FACTORY in new_factories
        assert NEW_REGISTER_TIERS_FACTORY in new_factories
        assert NEW_ALTER_TIERS_FACTORY in new_factories

        # Happy path: new OperatorGrid ET factories work correctly
        st_vaults_trusted_caller = accounts.at(ST_VAULTS_COMMITTEE, force=True)
        chain.snapshot()
        register_groups_in_operator_grid_test(easy_track, st_vaults_trusted_caller, stranger, operator_grid)
        register_tiers_in_operator_grid_test(easy_track, st_vaults_trusted_caller, stranger, operator_grid, accounts)
        alter_tiers_in_operator_grid_test(easy_track, st_vaults_trusted_caller, stranger, operator_grid, accounts)
        chain.revert()

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            # DG submit event
            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata=DG_PROPOSAL_METADATA,
                proposal_calls=dual_governance_proposal_calls,
            )

        # ET factories events
        validate_evmscript_factory_removed_event(
            vote_events[1], factory_addr=OLD_SDVT_SUBMIT_EXIT_HASHES_FACTORY, emitted_by=easy_track
        )
        validate_evmscript_factory_removed_event(
            vote_events[2], factory_addr=OLD_CURATED_SUBMIT_EXIT_HASHES_FACTORY, emitted_by=easy_track
        )
        validate_evmscript_factory_added_event(
            event=vote_events[3],
            p=EVMScriptFactoryAdded(
                factory_addr=NEW_SDVT_SUBMIT_EXIT_HASHES_FACTORY,
                permissions=create_permissions(vebo, SUBMIT_EXIT_REQUESTS),
            ),
            emitted_by=easy_track,
        )
        validate_evmscript_factory_added_event(
            event=vote_events[4],
            p=EVMScriptFactoryAdded(
                factory_addr=NEW_CURATED_SUBMIT_EXIT_HASHES_FACTORY,
                permissions=create_permissions(vebo, SUBMIT_EXIT_REQUESTS),
            ),
            emitted_by=easy_track,
        )
        validate_evmscript_factory_removed_event(
            vote_events[5], factory_addr=OLD_REGISTER_GROUPS_FACTORY, emitted_by=easy_track
        )
        validate_evmscript_factory_removed_event(
            vote_events[6], factory_addr=OLD_REGISTER_TIERS_FACTORY, emitted_by=easy_track
        )
        validate_evmscript_factory_removed_event(
            vote_events[7], factory_addr=OLD_ALTER_TIERS_FACTORY, emitted_by=easy_track
        )
        validate_evmscript_factory_added_event(
            event=vote_events[8],
            p=EVMScriptFactoryAdded(
                factory_addr=NEW_REGISTER_GROUPS_FACTORY,
                permissions=create_permissions(operator_grid, OPERATOR_GRID_REGISTER_GROUP)
                + create_permissions(operator_grid, OPERATOR_GRID_REGISTER_TIERS)[2:],
            ),
            emitted_by=easy_track,
        )
        validate_evmscript_factory_added_event(
            event=vote_events[9],
            p=EVMScriptFactoryAdded(
                factory_addr=NEW_REGISTER_TIERS_FACTORY,
                permissions=create_permissions(operator_grid, OPERATOR_GRID_REGISTER_TIERS),
            ),
            emitted_by=easy_track,
        )
        validate_evmscript_factory_added_event(
            event=vote_events[10],
            p=EVMScriptFactoryAdded(
                factory_addr=NEW_ALTER_TIERS_FACTORY,
                permissions=create_permissions(operator_grid, OPERATOR_GRID_ALTER_TIERS),
            ),
            emitted_by=easy_track,
        )

    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================

            # 1.1 A41 should be active before
            a41_data_before = no_registry.getNodeOperator(A41_NO_ID, True)
            assert a41_data_before["name"] == A41_NAME
            assert a41_data_before["active"]

            # 1.2 Stakin name and reward address before
            stakin_data_before = no_registry.getNodeOperator(STAKIN_NO_ID, True)
            assert stakin_data_before["name"] == STAKIN_NAME_OLD
            assert stakin_data_before["rewardAddress"] == STAKIN_REWARD_ADDRESS_OLD

            # 1.3 LazyOracle proxy implementation before
            assert lazy_oracle_proxy.proxy__getImplementation() == LAZY_ORACLE_IMPL_OLD

            # 1.4 VaultHub proxy implementation before
            assert vault_hub_proxy.proxy__getImplementation() == VAULT_HUB_IMPL_OLD

            # 1.5 ZKSync bridge proxy implementation before
            assert zksync_bridge_proxy.proxy__getImplementation() == ZKSYNC_L1_ERC20_BRIDGE_IMPL_OLD

            # 1.6 ZKSync bridge deposits disabled before
            assert not zksync_bridge.isDepositsEnabled()
            zksync_bridge_withdrawals_enabled = zksync_bridge.isWithdrawalsEnabled()
            assert zksync_bridge_withdrawals_enabled

            # 1.7-1.9 Chorus One old member is present in all hash consensus contracts
            assert hash_consensus_for_ao.getIsMember(CHORUS_ONE_ORACLE_MEMBER_OLD)
            assert cs_hash_consensus.getIsMember(CHORUS_ONE_ORACLE_MEMBER_OLD)
            assert hash_consensus_for_vebo.getIsMember(CHORUS_ONE_ORACLE_MEMBER_OLD)

            # 1.10-1.12 Chorus One new member is not present
            assert not hash_consensus_for_ao.getIsMember(CHORUS_ONE_ORACLE_MEMBER_NEW)
            assert not cs_hash_consensus.getIsMember(CHORUS_ONE_ORACLE_MEMBER_NEW)
            assert not hash_consensus_for_vebo.getIsMember(CHORUS_ONE_ORACLE_MEMBER_NEW)

            # 1.13-1.15 Stakefish old member is present in all hash consensus contracts
            assert hash_consensus_for_ao.getIsMember(STAKEFISH_ORACLE_MEMBER_OLD)
            assert cs_hash_consensus.getIsMember(STAKEFISH_ORACLE_MEMBER_OLD)
            assert hash_consensus_for_vebo.getIsMember(STAKEFISH_ORACLE_MEMBER_OLD)

            # 1.16-1.18 Stakefish new member is not present
            assert not hash_consensus_for_ao.getIsMember(STAKEFISH_ORACLE_MEMBER_NEW)
            assert not cs_hash_consensus.getIsMember(STAKEFISH_ORACLE_MEMBER_NEW)
            assert not hash_consensus_for_vebo.getIsMember(STAKEFISH_ORACLE_MEMBER_NEW)

            # 1.19 Chorus One target limit mode before
            chorus_one_data_before = no_registry.getNodeOperator(CHORUS_ONE_NO_ID, True)
            assert chorus_one_data_before["name"] == CHORUS_ONE_NAME
            chorus_one_summary_before = no_registry.getNodeOperatorSummary(CHORUS_ONE_NO_ID)
            assert chorus_one_summary_before["targetLimitMode"] != NO_TARGET_LIMIT_SOFT_MODE

            # 1.20 Consensys MANAGE_SIGNING_KEYS role not granted
            consensys_data_before = no_registry.getNodeOperator(CONSENSYS_NO_ID, True)
            assert consensys_data_before["name"] == CONSENSYS_NAME
            assert not acl.hasPermission["address,address,bytes32,uint[]"](
                CONSENSYS_MANAGE_SIGNING_KEYS_ADDRESS, CURATED_MODULE, MANAGE_SIGNING_KEYS, [perm_param_uint]
            )
            assert not no_registry.canPerform(
                CONSENSYS_MANAGE_SIGNING_KEYS_ADDRESS, MANAGE_SIGNING_KEYS, [perm_param_uint]
            )

            # 1.21-1.22 Gas Supply limit before
            limit_before, duration_before = gas_supply_registry.getLimitParameters()
            assert limit_before == GAS_SUPPLY_OLD_LIMIT
            assert duration_before == GAS_SUPPLY_PERIOD_DURATION_MONTHS
            (
                gas_supply_already_spent_before,
                gas_supply_spendable_before,
                gas_supply_period_start_before,
                gas_supply_period_end_before,
            ) = gas_supply_registry.getPeriodState()
            assert gas_supply_spendable_before == limit_before - gas_supply_already_spent_before
            assert gas_supply_period_start_before == GAS_SUPPLY_PERIOD_START
            assert gas_supply_period_end_before == GAS_SUPPLY_PERIOD_END

            # 1.23 CSM stake share limit and priority exit threshold before
            csm_module_before = staking_router.getStakingModule(CSM_MODULE_ID)
            assert csm_module_before["name"] == CSM_MODULE_NAME
            assert csm_module_before["stakingModuleAddress"] == CSM_MODULE_ADDRESS
            assert csm_module_before["stakeShareLimit"] == CSM_STAKE_SHARE_LIMIT_BEFORE
            assert csm_module_before["priorityExitShareThreshold"] == CSM_PRIORITY_EXIT_SHARE_THRESHOLD_BEFORE
            assert csm_module_before["stakingModuleFee"] == CSM_MODULE_FEE_BP
            assert csm_module_before["treasuryFee"] == CSM_TREASURY_FEE_BP
            assert csm_module_before["maxDepositsPerBlock"] == CSM_MAX_DEPOSITS_PER_BLOCK
            assert csm_module_before["minDepositBlockDistance"] == CSM_MIN_DEPOSIT_BLOCK_DISTANCE

            ao_quorum_before = hash_consensus_for_ao.getQuorum()
            ao_members_before = len(hash_consensus_for_ao.getMembers()[0])
            csm_quorum_before = cs_hash_consensus.getQuorum()
            csm_members_before = len(cs_hash_consensus.getMembers()[0])
            vebo_quorum_before = hash_consensus_for_vebo.getQuorum()
            vebo_members_before = len(hash_consensus_for_vebo.getMembers()[0])

            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)

                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

                # Validate all DG events
                # 1.1. Deactivate A41
                validate_node_operator_deactivated(dg_events[0], A41_NO_ID, emitted_by=CURATED_MODULE)

                # 1.2. Stakin name change
                validate_node_operator_name_set_event(
                    dg_events[1],
                    NodeOperatorNameSetItem(nodeOperatorId=STAKIN_NO_ID, name=STAKIN_NAME_NEW),
                    emitted_by=CURATED_MODULE,
                )
                # 1.2. Stakin reward address change
                validate_node_operator_reward_address_set_event(
                    dg_events[2],
                    NodeOperatorRewardAddressSetItem(
                        nodeOperatorId=STAKIN_NO_ID, reward_address=STAKIN_REWARD_ADDRESS_NEW
                    ),
                    emitted_by=CURATED_MODULE,
                )

                # 1.3. LazyOracle proxy upgrade
                validate_proxy_upgrade_event(dg_events[3], LAZY_ORACLE_IMPL_NEW, emitted_by=LAZY_ORACLE_PROXY)

                # 1.4. VaultHub proxy upgrade
                validate_proxy_upgrade_event(dg_events[4], VAULT_HUB_IMPL_NEW, emitted_by=VAULT_HUB_PROXY)

                # 1.5. ZKSync bridge proxy upgrade
                validate_proxy_upgrade_event(
                    dg_events[5], ZKSYNC_L1_ERC20_BRIDGE_IMPL_NEW, emitted_by=ZKSYNC_L1_ERC20_BRIDGE
                )

                # 1.6. enableDeposits on ZKSync bridge
                assert "DepositsEnabled" in dg_events[6]
                assert dg_events[6]["DepositsEnabled"]["_emitted_by"].lower() == ZKSYNC_L1_ERC20_BRIDGE.lower()

                # 1.7. Remove Chorus One from AO HashConsensus
                validate_hash_consensus_member_removed(
                    dg_events[7],
                    CHORUS_ONE_ORACLE_MEMBER_OLD,
                    new_quorum=ao_quorum_before,
                    new_total_members=ao_members_before - 1,
                    emitted_by=HASH_CONSENSUS_FOR_AO,
                )

                # 1.8. Remove Chorus One from CSM HashConsensus
                validate_hash_consensus_member_removed(
                    dg_events[8],
                    CHORUS_ONE_ORACLE_MEMBER_OLD,
                    new_quorum=csm_quorum_before,
                    new_total_members=csm_members_before - 1,
                    emitted_by=CS_HASH_CONSENSUS,
                )

                # 1.9. Remove Chorus One from VEB HashConsensus
                validate_hash_consensus_member_removed(
                    dg_events[9],
                    CHORUS_ONE_ORACLE_MEMBER_OLD,
                    new_quorum=vebo_quorum_before,
                    new_total_members=vebo_members_before - 1,
                    emitted_by=HASH_CONSENSUS_FOR_VEBO,
                )

                # 1.10. Add new Chorus One to AO HashConsensus
                validate_hash_consensus_member_added(
                    dg_events[10],
                    CHORUS_ONE_ORACLE_MEMBER_NEW,
                    new_quorum=ao_quorum_before,
                    new_total_members=ao_members_before,
                    emitted_by=HASH_CONSENSUS_FOR_AO,
                )

                # 1.11. Add new Chorus One to CSM HashConsensus
                validate_hash_consensus_member_added(
                    dg_events[11],
                    CHORUS_ONE_ORACLE_MEMBER_NEW,
                    new_quorum=csm_quorum_before,
                    new_total_members=csm_members_before,
                    emitted_by=CS_HASH_CONSENSUS,
                )

                # 1.12. Add new Chorus One to VEB HashConsensus
                validate_hash_consensus_member_added(
                    dg_events[12],
                    CHORUS_ONE_ORACLE_MEMBER_NEW,
                    new_quorum=vebo_quorum_before,
                    new_total_members=vebo_members_before,
                    emitted_by=HASH_CONSENSUS_FOR_VEBO,
                )

                # 1.13. Remove Stakefish from AO HashConsensus
                validate_hash_consensus_member_removed(
                    dg_events[13],
                    STAKEFISH_ORACLE_MEMBER_OLD,
                    new_quorum=ao_quorum_before,
                    new_total_members=ao_members_before - 1,
                    emitted_by=HASH_CONSENSUS_FOR_AO,
                )

                # 1.14. Remove Stakefish from CSM HashConsensus
                validate_hash_consensus_member_removed(
                    dg_events[14],
                    STAKEFISH_ORACLE_MEMBER_OLD,
                    new_quorum=csm_quorum_before,
                    new_total_members=csm_members_before - 1,
                    emitted_by=CS_HASH_CONSENSUS,
                )

                # 1.15. Remove Stakefish from VEB HashConsensus
                validate_hash_consensus_member_removed(
                    dg_events[15],
                    STAKEFISH_ORACLE_MEMBER_OLD,
                    new_quorum=vebo_quorum_before,
                    new_total_members=vebo_members_before - 1,
                    emitted_by=HASH_CONSENSUS_FOR_VEBO,
                )

                # 1.16. Add new Stakefish to AO HashConsensus
                validate_hash_consensus_member_added(
                    dg_events[16],
                    STAKEFISH_ORACLE_MEMBER_NEW,
                    new_quorum=ao_quorum_before,
                    new_total_members=ao_members_before,
                    emitted_by=HASH_CONSENSUS_FOR_AO,
                )

                # 1.17. Add new Stakefish to CSM HashConsensus
                validate_hash_consensus_member_added(
                    dg_events[17],
                    STAKEFISH_ORACLE_MEMBER_NEW,
                    new_quorum=csm_quorum_before,
                    new_total_members=csm_members_before,
                    emitted_by=CS_HASH_CONSENSUS,
                )

                # 1.18. Add new Stakefish to VEB HashConsensus
                validate_hash_consensus_member_added(
                    dg_events[18],
                    STAKEFISH_ORACLE_MEMBER_NEW,
                    new_quorum=vebo_quorum_before,
                    new_total_members=vebo_members_before,
                    emitted_by=HASH_CONSENSUS_FOR_VEBO,
                )

                # 1.19. Set Chorus One target validators limit
                validate_target_validators_count_changed_event(
                    dg_events[19],
                    TargetValidatorsCountChanged(
                        nodeOperatorId=CHORUS_ONE_NO_ID,
                        targetValidatorsCount=0,
                        targetLimitMode=NO_TARGET_LIMIT_SOFT_MODE,
                    ),
                    emitted_by=CURATED_MODULE,
                )

                # 1.20. Grant MANAGE_SIGNING_KEYS to Consensys
                validate_permission_grantp_event(
                    dg_events[20],
                    p=Permission(
                        entity=CONSENSYS_MANAGE_SIGNING_KEYS_ADDRESS,
                        app=CURATED_MODULE,
                        role=MANAGE_SIGNING_KEYS,
                    ),
                    params=[perm_param],
                    emitted_by=ACL,
                )

                # 1.21. Gas Supply limit decrease
                validate_set_limit_parameter_event(
                    dg_events[21],
                    limit=GAS_SUPPLY_NEW_LIMIT,
                    period_duration_month=GAS_SUPPLY_PERIOD_DURATION_MONTHS,
                    period_start_timestamp=GAS_SUPPLY_PERIOD_START_AFTER,
                    emitted_by=GAS_SUPPLY_ALLOWED_RECIPIENTS_REGISTRY,
                )

                # 1.22. Gas Supply spent amount reset
                validate_set_spent_amount_event(
                    dg_events[22],
                    new_spent_amount=GAS_SUPPLY_SPENT_AMOUNT_EXPECTED,
                    emitted_by=GAS_SUPPLY_ALLOWED_RECIPIENTS_REGISTRY,
                )

                # 1.23. CSM stake share limit and priority exit threshold update
                validate_staking_module_update_event(
                    dg_events[23],
                    StakingModuleItem(
                        id=CSM_MODULE_ID,
                        name=CSM_MODULE_NAME,
                        address=CSM_MODULE_ADDRESS,
                        target_share=CSM_STAKE_SHARE_LIMIT_AFTER,
                        module_fee=CSM_MODULE_FEE_BP,
                        treasury_fee=CSM_TREASURY_FEE_BP,
                        priority_exit_share=CSM_PRIORITY_EXIT_SHARE_THRESHOLD_AFTER,
                    ),
                    emitted_by=STAKING_ROUTER,
                )

        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # 1.1 A41 deactivated
        a41_data_after = no_registry.getNodeOperator(A41_NO_ID, True)
        assert not a41_data_after["active"]

        # 1.2 Stakin name and reward address updated
        stakin_data_after = no_registry.getNodeOperator(STAKIN_NO_ID, True)
        assert stakin_data_after["name"] == STAKIN_NAME_NEW
        assert stakin_data_after["rewardAddress"] == STAKIN_REWARD_ADDRESS_NEW

        # 1.3 LazyOracle proxy upgraded
        assert lazy_oracle_proxy.proxy__getImplementation() == LAZY_ORACLE_IMPL_NEW

        # 1.4 VaultHub proxy upgraded
        assert vault_hub_proxy.proxy__getImplementation() == VAULT_HUB_IMPL_NEW

        # 1.5 ZKSync bridge proxy upgraded
        assert zksync_bridge_proxy.proxy__getImplementation() == ZKSYNC_L1_ERC20_BRIDGE_IMPL_NEW

        # 1.6 ZKSync bridge deposits enabled; withdrawals unaffected by the upgrade
        zksync_bridge = interface.ZkSyncL1ERC20Bridge(ZKSYNC_L1_ERC20_BRIDGE)
        assert zksync_bridge.isDepositsEnabled()
        assert zksync_bridge.isWithdrawalsEnabled() == zksync_bridge_withdrawals_enabled
        zksync_bridge_smoke_test(stranger, zksync_bridge)

        # 1.7-1.9 Old Chorus One member removed
        assert not hash_consensus_for_ao.getIsMember(CHORUS_ONE_ORACLE_MEMBER_OLD)
        assert not cs_hash_consensus.getIsMember(CHORUS_ONE_ORACLE_MEMBER_OLD)
        assert not hash_consensus_for_vebo.getIsMember(CHORUS_ONE_ORACLE_MEMBER_OLD)

        # 1.10-1.12 New Chorus One member added
        assert hash_consensus_for_ao.getIsMember(CHORUS_ONE_ORACLE_MEMBER_NEW)
        assert cs_hash_consensus.getIsMember(CHORUS_ONE_ORACLE_MEMBER_NEW)
        assert hash_consensus_for_vebo.getIsMember(CHORUS_ONE_ORACLE_MEMBER_NEW)

        # 1.13-1.15 Old Stakefish member removed
        assert not hash_consensus_for_ao.getIsMember(STAKEFISH_ORACLE_MEMBER_OLD)
        assert not cs_hash_consensus.getIsMember(STAKEFISH_ORACLE_MEMBER_OLD)
        assert not hash_consensus_for_vebo.getIsMember(STAKEFISH_ORACLE_MEMBER_OLD)

        # 1.16-1.18 New Stakefish member added
        assert hash_consensus_for_ao.getIsMember(STAKEFISH_ORACLE_MEMBER_NEW)
        assert cs_hash_consensus.getIsMember(STAKEFISH_ORACLE_MEMBER_NEW)
        assert hash_consensus_for_vebo.getIsMember(STAKEFISH_ORACLE_MEMBER_NEW)

        # 1.19 Chorus One target validators limit set to 0
        chorus_one_summary = no_registry.getNodeOperatorSummary(CHORUS_ONE_NO_ID)
        assert chorus_one_summary["targetLimitMode"] == NO_TARGET_LIMIT_SOFT_MODE
        assert chorus_one_summary["targetValidatorsCount"] == 0

        # 1.20 Consensys MANAGE_SIGNING_KEYS granted
        assert acl.hasPermission["address,address,bytes32,uint[]"](
            CONSENSYS_MANAGE_SIGNING_KEYS_ADDRESS, CURATED_MODULE, MANAGE_SIGNING_KEYS, [perm_param_uint]
        )
        assert no_registry.canPerform(CONSENSYS_MANAGE_SIGNING_KEYS_ADDRESS, MANAGE_SIGNING_KEYS, [perm_param_uint])

        # 1.21-1.22 Gas Supply limit decreased
        limit_after, duration_after = gas_supply_registry.getLimitParameters()
        assert limit_after == GAS_SUPPLY_NEW_LIMIT
        assert duration_after == GAS_SUPPLY_PERIOD_DURATION_MONTHS
        (
            gas_supply_already_spent_after,
            gas_supply_spendable_after,
            gas_supply_period_start_after,
            gas_supply_period_end_after,
        ) = gas_supply_registry.getPeriodState()
        assert gas_supply_already_spent_after == GAS_SUPPLY_SPENT_AMOUNT_EXPECTED
        assert gas_supply_spendable_after == GAS_SUPPLY_NEW_LIMIT
        assert gas_supply_period_start_after == GAS_SUPPLY_PERIOD_START_AFTER
        assert gas_supply_period_end_after == GAS_SUPPLY_PERIOD_END_AFTER
        et_gas_supply_limit_test(easy_track, gas_supply_registry, stranger, accounts)

        # 1.23 CSM stake share limit and priority exit threshold raised
        csm_module_after = staking_router.getStakingModule(CSM_MODULE_ID)
        assert csm_module_after["stakeShareLimit"] == CSM_STAKE_SHARE_LIMIT_AFTER
        assert csm_module_after["priorityExitShareThreshold"] == CSM_PRIORITY_EXIT_SHARE_THRESHOLD_AFTER
        assert csm_module_after["stakingModuleFee"] == CSM_MODULE_FEE_BP
        assert csm_module_after["treasuryFee"] == CSM_TREASURY_FEE_BP
        assert csm_module_after["maxDepositsPerBlock"] == CSM_MAX_DEPOSITS_PER_BLOCK
        assert csm_module_after["minDepositBlockDistance"] == CSM_MIN_DEPOSIT_BLOCK_DISTANCE

        ao_quorum_after = hash_consensus_for_ao.getQuorum()
        ao_members_after = len(hash_consensus_for_ao.getMembers()[0])
        csm_quorum_after = cs_hash_consensus.getQuorum()
        csm_members_after = len(cs_hash_consensus.getMembers()[0])
        vebo_quorum_after = hash_consensus_for_vebo.getQuorum()
        vebo_members_after = len(hash_consensus_for_vebo.getMembers()[0])

        # Quorum and member count verification after oracle member rotation
        assert ao_quorum_after == ao_quorum_before
        assert ao_members_after == ao_members_before
        assert csm_quorum_after == csm_quorum_before
        assert csm_members_after == csm_members_before
        assert vebo_quorum_after == vebo_quorum_before
        assert vebo_members_after == vebo_members_before
