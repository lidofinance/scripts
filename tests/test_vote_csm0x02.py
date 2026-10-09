"""Test the CSM 0x02 activation vote, following tests/_test_2026_MM_DD.py.

Check the initial state, each vote/DG item's events, and the resulting state.
Expected mainnet parameters are independent from the vote script.
"""

import pytest
from brownie import ZERO_ADDRESS, chain, convert, history, interface, reverts, web3
from brownie.network.transaction import TransactionReceipt

from utils.config import contracts
from utils.dual_governance import PROPOSAL_STATUS, process_pending_proposals, process_proposals
from utils.evm_script import encode_call_script
from utils.import_current_votes import is_there_any_upgrade_scripts, is_there_any_vote_scripts
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.easy_track_helpers import (
    _encode_calldata,
    assert_create_evm_script_reverts,
    create_and_enact_payment_motion,
)
from utils.test.event_validators.circuit_breaker import validate_register_pauser_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.easy_track import EVMScriptFactoryAdded, validate_evmscript_factory_added_event
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.staking_router import StakingModuleItem, validate_staking_module_update_event
from utils.test.event_validators.time_constraints import validate_dg_time_constraints_executed_within_day_time_event
from utils.test.governance_helpers import execute_vote_and_process_dg_proposals
from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_dg_events,
    display_voting_events,
    group_dg_events_from_receipt,
    group_voting_events_from_receipt,
)
from utils.voting import find_metadata_by_vote_id


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_csm0x02 import get_dg_items, get_vote_items, start_vote


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
# Mainnet governance
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
FINANCE = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"
LDO_TOKEN = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
DUAL_GOVERNANCE_TIME_CONSTRAINTS = "0x2a30F5aC03187674553024296bed35Aa49749DDa"

# Vote targets
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
BURNER = "0xE76c52750019b80B43E36DF30bf4060EB73F573a"
TRIGGERABLE_WITHDRAWALS_GATEWAY = "0xDC00116a0D3E064427dA2600449cfD2566B3037B"
CIRCUIT_BREAKER = "0x6019CB557978296BA3C08a7B73225C0975DFB2F7"
CSM_COMMITTEE = "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f"

# https://github.com/lidofinance/staking-modules/pull/899
CSM0X02 = "0x792Cd25e4aE3578375031FB55e048E163A804F7B"
CSM0X02_ACCOUNTING = "0x3696dDd942A9e156F5D4728505D1b9a32dCef900"
CSM0X02_FEE_ORACLE = "0x0fB5EC09Cc975d8E1aF43063e51882798814f311"
CSM0X02_HASH_CONSENSUS = "0xd5a965FAab2d02D3cC2286A9da42d09F0F2aE210"
CSM0X02_VERIFIER = "0x69b4C32a43565e768794D41b4A265F86dE61b861"
CSM0X02_EJECTOR = "0x2EE500885870b020e84E86a09A5d26D1EEec3E5E"

# https://github.com/lidofinance/easy-track/pull/139#pullrequestreview-5410616152
REPORT_WITHDRAWALS_FACTORY = "0x8D74020d8EACCdFf0366dAAFfb96e6c98CDFc112"
SETTLE_GENERAL_DELAYED_PENALTY_FACTORY = "0x0B676AdEABcf4A696187cfAb90290Aa3ac51aFA2"
UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x5b0De22E65C068430f6e769754D51133775408cc"

# https://research.lido.fi/t/authorize-a-contingent-ldo-cex-liquidity-market-making-mandate/11839/39
LOL_LDO_REGISTRY = "0xf1e9c3bD021ED1419Dd3b37f9b6E49Eb662877Fe"
LOL_LDO_TOP_UP_FACTORY = "0xa3e98cb26F1277B623Edb95cee3bd33269b305F7"
LOL_TRUSTED_CALLER = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
LOL_LDO_LIMIT = 7_500_000 * 10**18
LOL_LDO_PERIOD_DURATION_MONTHS = 12
# Existing Finance ACL cap; the vote does not change it.
FINANCE_LDO_MAX_PER_CALL = 5_000_000 * 10**18
PAYMENT_CALLDATA_SIGNATURE = ["address[]", "uint256[]"]

# Expected deployment parameters are deliberately independent from the vote script.
CSM0X02_NAME = "Community Staking 0x02"
CSM0X02_TARGET_SHARE_BP = 1
CSM0X02_PRE_VOTE_TOP_UP_QUEUE_LIMIT = 16
CSM0X02_TOP_UP_QUEUE_LIMIT = 32
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 240
CSM0X02_MODULE_FEE_BP = 200
CSM0X02_TREASURY_FEE_BP = 800
CSM0X02_MAX_DEPOSITS_PER_BLOCK = 30
CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE = 0x02
CSM0X02_MODULE_ID = 5
CSM0X02_MODULE_STATUS_ACTIVE = 0
CSM0X02_ORACLE_PRE_VOTE_INITIAL_EPOCH = 48_038_396_021_100_853
CSM0X02_ORACLE_EPOCHS_PER_FRAME = 6_300

CURATED_V1_MODULE_ID = 1
CURATED_V2_MODULE_ID = 4
CONSENSYS_V1_NODE_OPERATOR_ID = 21
CONSENSYS_V2_NODE_OPERATOR_ID = 6
CURATED_V1_ADDRESS = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
CURATED_V2_ADDRESS = "0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1"
CURATED_V1_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 0
CURATED_V1_MODULE_FEE_BP = 350
CURATED_V1_TREASURY_FEE_BP = 650
CURATED_V1_MAX_DEPOSITS_PER_BLOCK = 150
CURATED_V1_MIN_DEPOSIT_BLOCK_DISTANCE = 25

# First report window: 2026-12-07 13:36:23 UTC; the preceding 28-day observation period
# starts on 2026-11-09 13:36:23 UTC, after the expected 2026-10-24 DG enactment.
CSM0X02_ORACLE_INITIAL_EPOCH = 494_340


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
# Fill the identifiers after the mainnet vote is created; fresh fork runs resolve
# the proposal ID from the vote execution receipt instead of assuming the latest proposal.
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 5
EXPECTED_DG_EVENTS_FROM_AGENT = 18
EXPECTED_DG_EVENTS_COUNT = 19
TIME_WINDOW_FROM = 14 * 3600
TIME_WINDOW_TO = 23 * 3600
IPFS_DESCRIPTION_HASH = "bafkreihqycnpry73szml3hvhuj6fgv4w4oif4adbcg7klpnmfa7fbjvzmi"
DG_PROPOSAL_METADATA = (
    "Connect CSM 0x02 to the protocol, set CMv1 stake share limit and priority exit share threshold to 0, "
    "set Consensys target limits to 0 in CMv1 and CMv2 (soft mode), and increase the CSM 0x02 top-up queue limit to 32"
)


# ============================================================================
# ============================= Helpers ======================================
# ============================================================================
def _selector(signature: str) -> str:
    return web3.keccak(text=signature).hex()[:10]


def _permission(contract_address: str, signature: str) -> str:
    return convert.to_address(contract_address).lower() + _selector(signature).removeprefix("0x")


def _assert_module_config(staking_router, module_id: int) -> None:
    module = staking_router.getStakingModuleStateConfig(module_id)
    registered_module = staking_router.getStakingModule(module_id)

    assert registered_module["name"] == CSM0X02_NAME
    assert registered_module["status"] == CSM0X02_MODULE_STATUS_ACTIVE
    assert module["moduleAddress"] == CSM0X02
    assert module["stakeShareLimit"] == CSM0X02_TARGET_SHARE_BP
    assert module["priorityExitShareThreshold"] == CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP
    assert module["moduleFee"] == CSM0X02_MODULE_FEE_BP
    assert module["treasuryFee"] == CSM0X02_TREASURY_FEE_BP
    assert module["withdrawalCredentialsType"] == CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE
    assert staking_router.getStakingModuleMaxDepositsPerBlock(module_id) == CSM0X02_MAX_DEPOSITS_PER_BLOCK
    assert staking_router.getStakingModuleMinDepositBlockDistance(module_id) == CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE


def _assert_easy_track_factories(easy_track, factories, factory_permissions) -> None:
    current_factories = easy_track.getEVMScriptFactories()
    for factory, permissions in zip(factories, factory_permissions):
        assert factory in current_factories
        assert bytes(easy_track.evmScriptFactoryPermissions(factory)) == bytes.fromhex(permissions.removeprefix("0x"))


def _assert_lol_ldo_setup() -> None:
    factory = interface.TopUpAllowedRecipientsSingleToken(LOL_LDO_TOP_UP_FACTORY)
    registry = interface.AllowedRecipientRegistry(LOL_LDO_REGISTRY)
    assert factory.trustedCaller() == LOL_TRUSTED_CALLER
    assert factory.token() == LDO_TOKEN
    assert factory.finance() == FINANCE
    assert factory.easyTrack() == EASY_TRACK
    assert factory.allowedRecipientsRegistry() == LOL_LDO_REGISTRY
    assert registry.getAllowedRecipients() == [LOL_TRUSTED_CALLER]
    assert registry.getLimitParameters() == (LOL_LDO_LIMIT, LOL_LDO_PERIOD_DURATION_MONTHS)
    assert registry.hasRole(registry.UPDATE_SPENT_AMOUNT_ROLE(), EVM_SCRIPT_EXECUTOR)


def _event(events, name: str, emitted_by: str):
    assert events.count(name) == 1
    event = events[name]
    assert convert.to_address(event["_emitted_by"]) == convert.to_address(emitted_by)
    return event


def _validate_module_added_event(events) -> None:
    validate_events_chain(
        [event.name for event in events],
        [
            "LogScriptCall",
            "StakingModuleAdded",
            "StakingModuleShareLimitSet",
            "StakingModuleFeesSet",
            "StakingModuleMaxDepositsPerBlockSet",
            "StakingModuleMinDepositBlockDistanceSet",
            "StakingRouterETHDeposited",
            "ScriptResult",
            "Executed",
        ],
    )
    added = _event(events, "StakingModuleAdded", STAKING_ROUTER)
    assert added["stakingModuleId"] == CSM0X02_MODULE_ID
    assert added["stakingModule"] == CSM0X02
    assert added["name"] == CSM0X02_NAME
    assert added["createdBy"] == AGENT

    shares = _event(events, "StakingModuleShareLimitSet", STAKING_ROUTER)
    assert shares["stakeShareLimit"] == CSM0X02_TARGET_SHARE_BP
    assert shares["priorityExitShareThreshold"] == CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP
    fees = _event(events, "StakingModuleFeesSet", STAKING_ROUTER)
    assert fees["stakingModuleFee"] == CSM0X02_MODULE_FEE_BP
    assert fees["treasuryFee"] == CSM0X02_TREASURY_FEE_BP
    max_deposits = _event(events, "StakingModuleMaxDepositsPerBlockSet", STAKING_ROUTER)
    assert max_deposits["maxDepositsPerBlock"] == CSM0X02_MAX_DEPOSITS_PER_BLOCK
    min_distance = _event(events, "StakingModuleMinDepositBlockDistanceSet", STAKING_ROUTER)
    assert min_distance["minDepositBlockDistance"] == CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE
    for event in (shares, fees, max_deposits, min_distance):
        assert event["stakingModuleId"] == CSM0X02_MODULE_ID
        assert event["setBy"] == AGENT

    deposited = _event(events, "StakingRouterETHDeposited", STAKING_ROUTER)
    assert deposited["stakingModuleId"] == CSM0X02_MODULE_ID
    assert deposited["amount"] == 0


def _validate_target_limit_event(events, module, operator_id: int, summary_before, nonce_before: int) -> None:
    is_curated_v1 = module.address == CURATED_V1_ADDRESS
    validate_events_chain(
        [event.name for event in events],
        [
            "LogScriptCall",
            "TargetValidatorsCountChanged",
            *(["KeysOpIndexSet"] if is_curated_v1 else ["DepositableSigningKeysCountChanged"]),
            "NonceChanged",
            "ScriptResult",
            "Executed",
        ],
    )
    changed = (summary_before["targetLimitMode"], summary_before["targetValidatorsCount"]) != (1, 0)
    if is_curated_v1 or changed:
        target = _event(events, "TargetValidatorsCountChanged", module.address)
        assert target["ARG0_VALUE"] == operator_id
        # NOR and CMv2 share the event topic, but encode mode/count in opposite order.
        assert target["ARG1_VALUE"] == (0 if is_curated_v1 else 1)
        assert target["ARG2_VALUE"] == (1 if is_curated_v1 else 0)
    else:
        assert events.count("TargetValidatorsCountChanged") == 0
    nonce = _event(events, "NonceChanged", module.address)
    assert nonce["nonce"] == nonce_before + 1
    if is_curated_v1:
        assert _event(events, "KeysOpIndexSet", module.address)["keysOpIndex"] == nonce_before + 1
    elif "DepositableSigningKeysCountChanged" in events:
        depositable = _event(events, "DepositableSigningKeysCountChanged", module.address)
        assert depositable["nodeOperatorId"] == operator_id
        assert depositable["depositableKeysCount"] == 0


# ============================================================================
# ============================== Fixtures ====================================
# ============================================================================
@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    return [{"target": target, "value": 0, "data": data} for target, data in get_dg_items()]


@pytest.fixture(scope="module")
def vote_applied(module_isolation, helpers, vote_ids_from_env, dg_proposal_ids_from_env):
    """Apply the vote for the motion tests, also supporting the post-enactment archive workflow.

    Function isolation rolls back test_vote's execution. Once the script is archived, a fresh
    mainnet fork already contains the registered factory, as in test_2026_08_05.py.
    """
    if not (
        vote_ids_from_env or dg_proposal_ids_from_env or is_there_any_vote_scripts() or is_there_any_upgrade_scripts()
    ):
        process_pending_proposals()
        return
    execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env)


# ============================================================================
# =============================== The test ===================================
# ============================================================================
def test_vote(
    helpers, accounts, ldo_holder, vote_ids_from_env, dg_proposal_ids_from_env, dual_governance_proposal_calls
):
    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    easy_track = interface.EasyTrack(EASY_TRACK)

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    burner = interface.Burner(BURNER)
    twg = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)
    csm = interface.CSModule(CSM0X02)
    hash_consensus = interface.HashConsensus(CSM0X02_HASH_CONSENSUS)
    curated_v1 = interface.NodeOperatorsRegistry(CURATED_V1_ADDRESS)
    curated_v2 = interface.CuratedModule(CURATED_V2_ADDRESS)

    assert curated_v1.getNodeOperator(CONSENSYS_V1_NODE_OPERATOR_ID, True)["name"] == "Consensys"
    assert curated_v2.getNodeOperator(CONSENSYS_V2_NODE_OPERATOR_ID)["managerAddress"] == (
        "0xF45C77EadD434612fCD93db978B3E36B0D58eC99"
    )

    factories = [
        REPORT_WITHDRAWALS_FACTORY,
        SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
        UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
        LOL_LDO_TOP_UP_FACTORY,
    ]
    factory_permissions = [
        _permission(CSM0X02, "reportSlashedWithdrawnValidators((uint256,uint256,uint256,uint256,bool)[])"),
        _permission(CSM0X02, "settleGeneralDelayedPenalty(uint256[],uint256[])"),
        (
            _permission(UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY, "validateParams((uint16,uint16,uint16,uint16))")
            + _permission(STAKING_ROUTER, "updateModuleShares(uint256,uint16,uint16)")[2:]
        ),
        (
            _permission(FINANCE, "newImmediatePayment(address,address,uint256,string)")
            + _permission(LOL_LDO_REGISTRY, "updateSpentAmount(uint256)")[2:]
        ),
    ]
    circuit_breaker_targets = [CSM0X02, CSM0X02_ACCOUNTING, CSM0X02_FEE_ORACLE, CSM0X02_VERIFIER, CSM0X02_EJECTOR]

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
    assert len(call_script_items) == EXPECTED_VOTE_EVENTS_COUNT
    assert len(dual_governance_proposal_calls) == EXPECTED_DG_EVENTS_COUNT
    assert str(voting.getVote(vote_id)["script"]).lower() == encode_call_script(call_script_items).lower()

    proposal_id = EXPECTED_DG_PROPOSAL_ID
    if dg_proposal_ids_from_env:
        assert len(dg_proposal_ids_from_env) == 1
        if proposal_id is not None:
            assert dg_proposal_ids_from_env[0] == proposal_id
        proposal_id = dg_proposal_ids_from_env[0]

    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    if not voting.getVote(vote_id)["executed"]:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================
        for factory in factories:
            assert factory not in easy_track.getEVMScriptFactories()
        _assert_lol_ldo_setup()
        lol_period_before = interface.AllowedRecipientRegistry(LOL_LDO_REGISTRY).getPeriodState()
        assert lol_period_before[0] == 0
        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        _assert_easy_track_factories(easy_track, factories, factory_permissions)
        assert interface.AllowedRecipientRegistry(LOL_LDO_REGISTRY).getPeriodState() == lol_period_before
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT
        submitted_id = vote_events[0]["ProposalSubmitted"][0]["id"]
        if proposal_id is not None:
            assert submitted_id == proposal_id
        proposal_id = submitted_id
        assert proposal_id == timelock.getProposalsCount()
        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=proposal_id,
            proposer=VOTING,
            executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            metadata=DG_PROPOSAL_METADATA,
            proposal_calls=dual_governance_proposal_calls,
        )
        for index, (factory, permissions) in enumerate(zip(factories, factory_permissions), start=1):
            validate_evmscript_factory_added_event(
                vote_events[index], EVMScriptFactoryAdded(factory, permissions), emitted_by=EASY_TRACK
            )

    assert proposal_id is not None, "Set EXPECTED_DG_PROPOSAL_ID or DG_PROPOSAL_IDS for the already-executed vote."

    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    curated_v1_config_before = None
    curated_v1_deposits_before = None
    if timelock.getProposalDetails(proposal_id)["status"] != PROPOSAL_STATUS["executed"]:
        # =========================================================================
        # ================== DG before proposal executed checks ===================
        # =========================================================================
        curated_v1_config_before = staking_router.getStakingModuleStateConfig(CURATED_V1_MODULE_ID).dict()
        curated_v1_deposits_before = staking_router.getStakingModuleStateDeposits(CURATED_V1_MODULE_ID).dict()
        target_summaries_before = [
            curated_v1.getNodeOperatorSummary(CONSENSYS_V1_NODE_OPERATOR_ID),
            curated_v2.getNodeOperatorSummary(CONSENSYS_V2_NODE_OPERATOR_ID),
        ]
        target_nonces_before = [curated_v1.getNonce(), curated_v2.getNonce()]
        assert staking_router.getStakingModulesCount() == CSM0X02_MODULE_ID - 1
        assert not staking_router.hasStakingModule(CSM0X02_MODULE_ID)
        assert not burner.hasRole(burner.REQUEST_BURN_MY_STETH_ROLE(), CSM0X02_ACCOUNTING)
        assert not twg.hasRole(twg.ADD_FULL_WITHDRAWAL_REQUEST_ROLE(), CSM0X02_EJECTOR)
        assert csm.isPaused()
        assert not csm.hasRole(csm.RESUME_ROLE(), AGENT)
        assert csm.getTopUpQueue()["enabled"]
        assert csm.getTopUpQueue()["limit"] == CSM0X02_PRE_VOTE_TOP_UP_QUEUE_LIMIT
        assert csm.getRoleMemberCount(csm.MANAGE_TOP_UP_QUEUE_ROLE()) == 0
        csm_nonce_before = csm.getNonce()
        frame_config_before = hash_consensus.getFrameConfig()
        assert frame_config_before["initialEpoch"] == CSM0X02_ORACLE_PRE_VOTE_INITIAL_EPOCH
        assert frame_config_before["epochsPerFrame"] == CSM0X02_ORACLE_EPOCHS_PER_FRAME
        for target in circuit_breaker_targets:
            assert circuit_breaker.getPauser(target) == ZERO_ADDRESS

        process_proposals([proposal_id])
        dg_tx: TransactionReceipt = history[-1]
        display_dg_events(dg_tx)
        dg_events = group_dg_events_from_receipt(
            dg_tx, timelock=EMERGENCY_PROTECTED_TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR
        )
        assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
        assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

        # 1.1. Check execution time window (14:00-23:00 UTC).
        validate_dg_time_constraints_executed_within_day_time_event(
            dg_events[0],
            TIME_WINDOW_FROM,
            TIME_WINDOW_TO,
            emitted_by=DUAL_GOVERNANCE_TIME_CONSTRAINTS,
        )
        # 1.2. Register CSM 0x02 and its independent router parameters.
        _validate_module_added_event(dg_events[1])
        # 1.3-1.5. Grant Burner, TWG and temporary module resume permissions.
        for index, role_name, account, emitter in (
            (2, "REQUEST_BURN_MY_STETH_ROLE", CSM0X02_ACCOUNTING, BURNER),
            (3, "ADD_FULL_WITHDRAWAL_REQUEST_ROLE", CSM0X02_EJECTOR, TRIGGERABLE_WITHDRAWALS_GATEWAY),
            (4, "RESUME_ROLE", AGENT, CSM0X02),
        ):
            validate_grant_role_event(
                dg_events[index],
                web3.keccak(text=role_name).hex(),
                account,
                sender=AGENT,
                emitted_by=emitter,
                event_chain=["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"],
            )
        # 1.6-1.7. Resume the module and remove the temporary permission.
        validate_events_chain(
            [event.name for event in dg_events[5]],
            ["LogScriptCall", "Resumed", "ScriptResult", "Executed"],
        )
        _event(dg_events[5], "Resumed", CSM0X02)
        validate_revoke_role_event(
            dg_events[6], web3.keccak(text="RESUME_ROLE").hex(), AGENT, sender=AGENT, emitted_by=CSM0X02
        )
        # 1.8. Set the initial oracle epoch without changing the 28-day frame.
        validate_events_chain(
            [event.name for event in dg_events[7]],
            ["LogScriptCall", "FrameConfigSet", "ScriptResult", "Executed"],
        )
        frame = _event(dg_events[7], "FrameConfigSet", CSM0X02_HASH_CONSENSUS)
        assert frame["newInitialEpoch"] == CSM0X02_ORACLE_INITIAL_EPOCH
        assert frame["newEpochsPerFrame"] == CSM0X02_ORACLE_EPOCHS_PER_FRAME
        # 1.9-1.13. Register each pausable with the CSM committee.
        for index, target in enumerate(circuit_breaker_targets, start=8):
            validate_events_chain(
                [event.name for event in dg_events[index]],
                ["LogScriptCall", "PauserSet", "HeartbeatUpdated", "ScriptResult", "Executed"],
            )
            validate_register_pauser_event(dg_events[index], target, CSM_COMMITTEE, emitted_by=CIRCUIT_BREAKER)
            _event(dg_events[index], "PauserSet", CIRCUIT_BREAKER)
            heartbeat = _event(dg_events[index], "HeartbeatUpdated", CIRCUIT_BREAKER)
            assert heartbeat["newHeartbeatExpiry"] == dg_tx.timestamp + circuit_breaker.heartbeatInterval()
        # 1.14. Set the CMv1 share limit and priority-exit threshold to zero.
        validate_staking_module_update_event(
            dg_events[13],
            StakingModuleItem(
                CURATED_V1_MODULE_ID,
                CURATED_V1_ADDRESS,
                "curated-onchain-v1",
                0,
                CURATED_V1_MODULE_FEE_BP,
                CURATED_V1_TREASURY_FEE_BP,
                CURATED_V1_PRIORITY_EXIT_SHARE_THRESHOLD_BP,
            ),
            emitted_by=STAKING_ROUTER,
        )
        for event_name in (
            "StakingModuleShareLimitSet",
            "StakingModuleFeesSet",
            "StakingModuleMaxDepositsPerBlockSet",
            "StakingModuleMinDepositBlockDistanceSet",
        ):
            event = _event(dg_events[13], event_name, STAKING_ROUTER)
            assert event["stakingModuleId"] == CURATED_V1_MODULE_ID
            assert event["setBy"] == AGENT
        assert dg_events[13]["StakingModuleMaxDepositsPerBlockSet"]["maxDepositsPerBlock"] == (
            CURATED_V1_MAX_DEPOSITS_PER_BLOCK
        )
        assert dg_events[13]["StakingModuleMinDepositBlockDistanceSet"]["minDepositBlockDistance"] == (
            CURATED_V1_MIN_DEPOSIT_BLOCK_DISTANCE
        )
        # 1.15-1.16. Stop deposits for Consensys in both curated modules.
        for index, module, operator_id, summary_before, nonce_before in zip(
            (14, 15),
            (curated_v1, curated_v2),
            (CONSENSYS_V1_NODE_OPERATOR_ID, CONSENSYS_V2_NODE_OPERATOR_ID),
            target_summaries_before,
            target_nonces_before,
        ):
            _validate_target_limit_event(dg_events[index], module, operator_id, summary_before, nonce_before)

        # 1.17-1.19. Increase the queue limit with temporary Agent permission,
        # then revoke it without granting the role to the CSM committee.
        validate_grant_role_event(
            dg_events[16],
            web3.keccak(text="MANAGE_TOP_UP_QUEUE_ROLE").hex(),
            AGENT,
            sender=AGENT,
            emitted_by=CSM0X02,
            event_chain=["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"],
        )
        validate_events_chain(
            [event.name for event in dg_events[17]],
            ["LogScriptCall", "TopUpQueueLimitSet", "NonceChanged", "ScriptResult", "Executed"],
        )
        assert _event(dg_events[17], "TopUpQueueLimitSet", CSM0X02)["limit"] == CSM0X02_TOP_UP_QUEUE_LIMIT
        assert _event(dg_events[17], "NonceChanged", CSM0X02)["nonce"] == csm_nonce_before + 1
        validate_revoke_role_event(
            dg_events[18],
            web3.keccak(text="MANAGE_TOP_UP_QUEUE_ROLE").hex(),
            AGENT,
            sender=AGENT,
            emitted_by=CSM0X02,
        )

    # =========================================================================
    # ==================== After DG proposal executed checks ==================
    # =========================================================================
    assert timelock.getProposalDetails(proposal_id)["status"] == PROPOSAL_STATUS["executed"]
    _assert_easy_track_factories(easy_track, factories, factory_permissions)

    assert staking_router.getStakingModulesCount() == CSM0X02_MODULE_ID
    assert staking_router.hasStakingModule(CSM0X02_MODULE_ID)
    _assert_module_config(staking_router, CSM0X02_MODULE_ID)

    curated_v1_config_after = staking_router.getStakingModuleStateConfig(CURATED_V1_MODULE_ID).dict()
    curated_v1_deposits_after = staking_router.getStakingModuleStateDeposits(CURATED_V1_MODULE_ID).dict()
    assert curated_v1_config_after["stakeShareLimit"] == 0
    assert curated_v1_config_after["priorityExitShareThreshold"] == CURATED_V1_PRIORITY_EXIT_SHARE_THRESHOLD_BP
    assert curated_v1_config_after["moduleFee"] == CURATED_V1_MODULE_FEE_BP
    assert curated_v1_config_after["treasuryFee"] == CURATED_V1_TREASURY_FEE_BP
    assert curated_v1_deposits_after["maxDepositsPerBlock"] == CURATED_V1_MAX_DEPOSITS_PER_BLOCK
    assert curated_v1_deposits_after["minDepositBlockDistance"] == CURATED_V1_MIN_DEPOSIT_BLOCK_DISTANCE
    if curated_v1_config_before is not None:
        assert curated_v1_config_after == {
            **curated_v1_config_before,
            "stakeShareLimit": 0,
            "priorityExitShareThreshold": 0,
        }
        assert curated_v1_deposits_after["maxDepositsPerBlock"] == curated_v1_deposits_before["maxDepositsPerBlock"]
        assert (
            curated_v1_deposits_after["minDepositBlockDistance"]
            == curated_v1_deposits_before["minDepositBlockDistance"]
        )
    for module, operator_id in (
        (curated_v1, CONSENSYS_V1_NODE_OPERATOR_ID),
        (curated_v2, CONSENSYS_V2_NODE_OPERATOR_ID),
    ):
        operator = module.getNodeOperatorSummary(operator_id)
        assert operator["targetLimitMode"] == 1
        assert operator["targetValidatorsCount"] == 0
        assert operator["depositableValidatorsCount"] == 0

    assert burner.hasRole(burner.REQUEST_BURN_MY_STETH_ROLE(), CSM0X02_ACCOUNTING)
    assert twg.hasRole(twg.ADD_FULL_WITHDRAWAL_REQUEST_ROLE(), CSM0X02_EJECTOR)
    assert not csm.isPaused()
    assert not csm.hasRole(csm.RESUME_ROLE(), AGENT)
    assert csm.getTopUpQueue()["enabled"]
    assert csm.getTopUpQueue()["limit"] == CSM0X02_TOP_UP_QUEUE_LIMIT
    assert csm.getRoleMemberCount(csm.MANAGE_TOP_UP_QUEUE_ROLE()) == 0
    assert not csm.hasRole(csm.MANAGE_TOP_UP_QUEUE_ROLE(), CSM_COMMITTEE)
    assert not csm.hasRole(csm.MANAGE_TOP_UP_QUEUE_ROLE(), AGENT)
    frame_config_after = hash_consensus.getFrameConfig()
    assert frame_config_after["initialEpoch"] == CSM0X02_ORACLE_INITIAL_EPOCH
    assert frame_config_after["epochsPerFrame"] == CSM0X02_ORACLE_EPOCHS_PER_FRAME
    for target in circuit_breaker_targets:
        assert circuit_breaker.getPauser(target) == CSM_COMMITTEE


# ============================================================================
# ======================== LOL LDO Easy Track motions ========================
# ============================================================================
# Keep these scenarios with the vote test so they are archived together, following
# archive/tests/test_2026_08_05.py (LOL stablecoins) and test_2023_02_21.py (TRP LDO).
def _start_fresh_lol_ldo_period(registry):
    _, _, _, period_end = registry.getPeriodState()
    chain.mine(1, max(chain.time(), period_end) + 1)
    return period_end


def test_lol_ldo_motion_guards(vote_applied, stranger):
    assert LOL_LDO_TOP_UP_FACTORY in contracts.easy_track.getEVMScriptFactories()
    factory = interface.TopUpAllowedRecipientsSingleToken(LOL_LDO_TOP_UP_FACTORY)
    for creator, recipients, amounts, reason in (
        (stranger, [LOL_TRUSTED_CALLER], [1], "CALLER_IS_FORBIDDEN"),
        (LOL_TRUSTED_CALLER, [stranger.address], [1], "RECIPIENT_NOT_ALLOWED"),
        (LOL_TRUSTED_CALLER, [LOL_TRUSTED_CALLER], [LOL_LDO_LIMIT + 1], "SUM_EXCEEDS_SPENDABLE_BALANCE"),
    ):
        assert_create_evm_script_reverts(
            factory, creator, _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [recipients, amounts]), reason
        )


def test_lol_ldo_payment(vote_applied, accounts, stranger):
    registry = interface.AllowedRecipientRegistry(LOL_LDO_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    amount = 1_000 * 10**18
    assert contracts.ldo_token.balanceOf(AGENT) >= amount
    _start_fresh_lol_ldo_period(registry)

    create_and_enact_payment_motion(
        contracts.easy_track, multisig, LOL_LDO_TOP_UP_FACTORY, contracts.ldo_token, [multisig], [amount], stranger
    )

    spent, spendable, _, _ = registry.getPeriodState()
    assert spent == amount
    assert spendable == LOL_LDO_LIMIT - amount
    assert registry.getAllowedRecipients() == [LOL_TRUSTED_CALLER]


def test_lol_ldo_single_payment_capped_by_acl(vote_applied, accounts, stranger):
    registry = interface.AllowedRecipientRegistry(LOL_LDO_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    amount = FINANCE_LDO_MAX_PER_CALL + 1
    assert amount < LOL_LDO_LIMIT
    assert contracts.ldo_token.balanceOf(AGENT) >= amount
    _start_fresh_lol_ldo_period(registry)
    period_before = registry.getPeriodState()
    balances_before = [contracts.ldo_token.balanceOf(address) for address in (AGENT, LOL_TRUSTED_CALLER)]

    with reverts("APP_AUTH_FAILED"):
        create_and_enact_payment_motion(
            contracts.easy_track, multisig, LOL_LDO_TOP_UP_FACTORY, contracts.ldo_token, [multisig], [amount], stranger
        )

    assert registry.getPeriodState() == period_before
    assert [contracts.ldo_token.balanceOf(address) for address in (AGENT, LOL_TRUSTED_CALLER)] == balances_before


def test_lol_ldo_period_limit(vote_applied, accounts, stranger):
    registry = interface.AllowedRecipientRegistry(LOL_LDO_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    assert contracts.ldo_token.balanceOf(AGENT) >= LOL_LDO_LIMIT
    period_end_before = _start_fresh_lol_ldo_period(registry)

    # The entire period budget in one motion, with each payment within the unchanged Finance ACL cap.
    create_and_enact_payment_motion(
        contracts.easy_track,
        multisig,
        LOL_LDO_TOP_UP_FACTORY,
        contracts.ldo_token,
        [multisig, multisig],
        [FINANCE_LDO_MAX_PER_CALL, LOL_LDO_LIMIT - FINANCE_LDO_MAX_PER_CALL],
        stranger,
    )

    spent, spendable, _, period_end_after = registry.getPeriodState()
    assert period_end_after > period_end_before
    assert spent == LOL_LDO_LIMIT
    assert spendable == 0

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            contracts.easy_track, multisig, LOL_LDO_TOP_UP_FACTORY, contracts.ldo_token, [multisig], [1], stranger
        )
