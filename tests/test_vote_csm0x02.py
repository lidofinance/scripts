"""Test the CSM 0x02 activation vote, following tests/_test_2026_MM_DD.py.

Check the initial state, each vote/DG item's events, and the resulting state.
Expected mainnet parameters are independent from the vote script.

The Ethereum vote test saves the forwarded a.DI transaction. The BNB Chain tests below replay
those bytes on a separate anvil fork, execute the action set, and check the resulting configuration.
Run the full file so the Ethereum test produces the artifact before the BNB tests consume it:
    BNB_RPC_URL=<rpc> poetry run brownie test tests/test_vote_csm0x02.py --network mfh-1

The BNB tests require anvil and BNB_RPC_URL and skip artifacts from another pytest session.
"""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import uuid

import pytest
from avotes_parser.core import parse_script
from brownie import ZERO_ADDRESS, convert, history, interface, web3
from brownie.network.event import _decode_logs
from brownie.network.transaction import TransactionReceipt

from eth_abi import decode, encode
from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.logs import DISCARD
from web3.middleware import geth_poa_middleware

from utils.dual_governance import PROPOSAL_STATUS, process_proposals
from utils.evm_script import encode_call_script
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.event_validators.circuit_breaker import validate_register_pauser_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.easy_track import EVMScriptFactoryAdded, validate_evmscript_factory_added_event
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.staking_router import StakingModuleItem, validate_staking_module_update_event
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
# ========================= Ethereum parameters ==============================
# ============================================================================
# Mainnet governance
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"

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

# Expected deployment parameters are deliberately independent from the vote script.
CSM0X02_NAME = "Community Staking 0x02"
CSM0X02_TARGET_SHARE_BP = 200
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
CURATED_V1_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 10_000
CURATED_V1_MODULE_FEE_BP = 350
CURATED_V1_TREASURY_FEE_BP = 650
CURATED_V1_MAX_DEPOSITS_PER_BLOCK = 150
CURATED_V1_MIN_DEPOSIT_BLOCK_DISTANCE = 25

# First report window: 2026-12-07 13:36:23 UTC; the preceding 28-day observation period
# starts on 2026-11-09 13:36:23 UTC, after the expected 2026-10-24 DG enactment.
CSM0X02_ORACLE_INITIAL_EPOCH = 494_340


# ============================================================================
# ============================= a.DI parameters ==============================
# ============================================================================
# a.DI governance forwarding to BNB Chain
# https://docs.lido.fi/deployed-contracts/#adi-governance-forwarding-eth
# https://docs.lido.fi/deployed-contracts/#adi-governance-forwarding-bsc
ETHEREUM_CROSS_CHAIN_CONTROLLER = "0x93559892D3C7F66DE4570132d68b69BD3c369A7C"
ETHEREUM_CCIP_ADAPTER = "0x29D4fA5FCC282ba2788A281860770c166F597d5d"
ETHEREUM_HYPERLANE_ADAPTER = "0x8d374DF3de08b971777Aa091fA68BCE109b3a7F3"
ETHEREUM_LAYERZERO_ADAPTER = "0x742650E0441Be8503682965d601AD0Ba1fB54411"
ETHEREUM_WORMHOLE_ADAPTER = "0xEDc0D2cb2289BBa1587424dd42bDD1ca7eAbDF17"
BNB_CROSS_CHAIN_CONTROLLER = "0x40C4464fCa8caCd550C33B39d674fC257966022F"
BNB_CROSS_CHAIN_EXECUTOR = "0x8E5175D17f74d1D512de59b2f5d5A5d8177A123d"
BNB_CCIP_ADAPTER = "0x15AD245133568c2498c7dA0cf2204A03b0e9b98A"
BNB_HYPERLANE_ADAPTER = "0xCd867B440c726461e5fAbe8d3a050b2f8701C230"
BNB_LAYERZERO_ADAPTER = "0xc934433f4c433Cf80DE6fB65fd70C7a650D8a408"
BNB_WORMHOLE_ADAPTER = "0xBb1E43408BbF2C767Ff3Bd5bBC34E183CC1Ef119"

ETHEREUM_CHAIN_ID = 1
BNB_CHAIN_ID = 56
BNB_REQUIRED_CONFIRMATIONS = 2
BNB_MESSAGE_GAS_LIMIT = 1_200_000

# Forwarder adapters of the Ethereum CrossChainController for BNB Chain as (destinationBridgeAdapter,
# currentChainBridgeAdapter) pairs.
BNB_BRIDGE_ADAPTERS_BEFORE = {
    (BNB_CCIP_ADAPTER, ETHEREUM_CCIP_ADAPTER),
    (BNB_LAYERZERO_ADAPTER, ETHEREUM_LAYERZERO_ADAPTER),
    (BNB_HYPERLANE_ADAPTER, ETHEREUM_HYPERLANE_ADAPTER),
    (BNB_WORMHOLE_ADAPTER, ETHEREUM_WORMHOLE_ADAPTER),
}
BNB_BRIDGE_ADAPTERS_AFTER = BNB_BRIDGE_ADAPTERS_BEFORE - {(BNB_WORMHOLE_ADAPTER, ETHEREUM_WORMHOLE_ADAPTER)}

# The Ethereum vote test saves the forwarded transaction here for the BNB replay tests below.
ADI_BNB_MESSAGE_ARTIFACT = "build/adi_bnb_message.json"
# Id of this pytest session. The vote test writes it into the artifact, and the replay accepts only a matching id.
ADI_BNB_MESSAGE_SESSION = uuid.uuid4().hex

ENVELOPE_TYPE = "(uint256,address,address,uint256,uint256,bytes)"
ACTIONS_SET_TYPES = ["address[]", "uint256[]", "string[]", "bytes[]", "bool[]"]


# ============================================================================
# =========================== BNB fork parameters ============================
# ============================================================================
BNB_RPC_URL_ENV = "BNB_RPC_URL"

BNB_STRANGER = "0x000000000000000000000000000000000000bEEF"
BNB_REQUIRED_CONFIRMATIONS_BEFORE = 3
BNB_EXECUTOR_GRACE_PERIOD = 86400

# Bridge entry points on BNB Chain that call the adapters, and the ids each bridge uses for Ethereum.
BNB_CCIP_ROUTER = "0x34B03Cb9086d7D758AC55af71584F81A598759FE"
BNB_LAYERZERO_ENDPOINT = "0x1a44076050125825900e736c501f859c50fE728c"
BNB_HYPERLANE_MAILBOX = "0x2971b9Aec44bE4eb673DF1B88cDB57b96eefe8a4"
CCIP_ETHEREUM_CHAIN_SELECTOR = 5009297550715157269
LAYERZERO_ETHEREUM_EID = 30101
HYPERLANE_ETHEREUM_DOMAIN = 1

# a.DI Errors.CALLER_NOT_APPROVED_BRIDGE
CALLER_NOT_APPROVED_BRIDGE = "5"

# BridgeExecutorBase.ActionsSetState
ACTIONS_SET_STATE_QUEUED = 0
ACTIONS_SET_STATE_EXECUTED = 1


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
# Fill the identifiers after the mainnet vote is created; fresh fork runs resolve
# the proposal ID from the vote execution receipt instead of assuming the latest proposal.
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 4
EXPECTED_DG_EVENTS_FROM_AGENT = 17
EXPECTED_DG_EVENTS_COUNT = 17
IPFS_DESCRIPTION_HASH = "bafkreibmx5eji72q4hecj6ups3542bbyvme4j63fyjljqr35vtvin5mezy"
DG_PROPOSAL_METADATA = (
    "Activate CSM 0x02, set CMv1 stake share limit to 0, set Consensys target limits to 0 in CMv1 and CMv2, "
    "remove the Wormhole adapter from a.DI forwarding to BNB Chain, and set the BNB Chain quorum to 2 of 3 bridges"
)


# ============================================================================
# ======================= Shared a.DI encoding helpers =======================
# ============================================================================
def bnb_actions_set_message() -> bytes:
    """The a.DI message payload the BNB Chain CrossChainExecutor decodes into an action set."""
    return encode(
        ACTIONS_SET_TYPES,
        [
            [BNB_CROSS_CHAIN_CONTROLLER, BNB_CROSS_CHAIN_CONTROLLER],
            [0, 0],
            ["disallowReceiverBridgeAdapters((address,uint256[])[])", "updateConfirmations((uint256,uint8)[])"],
            [
                encode(["(address,uint256[])[]"], [[(BNB_WORMHOLE_ADAPTER, [ETHEREUM_CHAIN_ID])]]),
                encode(["(uint256,uint8)[]"], [[(ETHEREUM_CHAIN_ID, BNB_REQUIRED_CONFIRMATIONS)]]),
            ],
            [False, False],
        ],
    )


def encode_adi_envelope(envelope_nonce: int, message: bytes) -> bytes:
    # Envelope(nonce, origin, destination, originChainId, destinationChainId, message),
    # id = keccak256(abi.encode(envelope))
    envelope = (envelope_nonce, AGENT, BNB_CROSS_CHAIN_EXECUTOR, ETHEREUM_CHAIN_ID, BNB_CHAIN_ID, message)
    return encode([ENVELOPE_TYPE], [envelope])


def encode_adi_transaction(transaction_nonce: int, envelope_nonce: int, message: bytes) -> bytes:
    # Transaction(nonce, encodedEnvelope), id = keccak256(abi.encode(transaction))
    return encode(["(uint256,bytes)"], [(transaction_nonce, encode_adi_envelope(envelope_nonce, message))])


# ============================================================================
# ============================= Ethereum helpers =============================
# ============================================================================
def _selector(signature: str) -> str:
    return web3.keccak(text=signature).hex()[:10]


def _permission(contract_address: str, signature: str) -> str:
    return convert.to_address(contract_address).lower() + _selector(signature).removeprefix("0x")


def _forwarder_bridge_adapters(ccc, chain_id: int) -> set:
    return {
        (convert.to_address(destination_adapter), convert.to_address(current_chain_adapter))
        for destination_adapter, current_chain_adapter in ccc.getForwarderBridgeAdaptersByChain(chain_id)
    }


def _forward_message_args(proposal_calls) -> list:
    """Decode the single forwardMessage call packed into the Agent.forward call scripts of a DG proposal."""
    agent = interface.Agent(AGENT)
    ethereum_ccc = interface.CrossChainController(ETHEREUM_CROSS_CHAIN_CONTROLLER)
    forward_message_calls = [
        call
        for target, _, payload in proposal_calls
        if target == AGENT
        for call in parse_script("0x" + bytes(agent.forward.decode_input(payload)[0]).hex()).calls
        if convert.to_address(call.address) == ETHEREUM_CROSS_CHAIN_CONTROLLER
        and call.method_id == _selector("forwardMessage(uint256,address,uint256,bytes)")
    ]
    assert len(forward_message_calls) == 1

    call = forward_message_calls[0]
    return ethereum_ccc.forwardMessage.decode_input(call.method_id + call.encoded_call_data.removeprefix("0x"))


def _forwarding_attempts(from_block: int, envelope_id: bytes) -> list:
    logs = web3.eth.get_logs(
        {
            "address": ETHEREUM_CROSS_CHAIN_CONTROLLER,
            "fromBlock": from_block,
            "topics": [
                web3.keccak(
                    text="TransactionForwardingAttempted(bytes32,bytes32,bytes,uint256,address,address,bool,bytes)"
                ).hex(),
                envelope_id.hex(),
            ],
        }
    )
    assert logs, "No TransactionForwardingAttempted events for the a.DI envelope"
    return _decode_logs(logs)["TransactionForwardingAttempted"]._ordered


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
# ========================== Ethereum fixtures ===============================
# ============================================================================
@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    return [{"target": target, "value": 0, "data": data} for target, data in get_dg_items()]


# ============================================================================
# =========================== Ethereum vote ==================================
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
    ethereum_ccc = interface.CrossChainController(ETHEREUM_CROSS_CHAIN_CONTROLLER)

    assert curated_v1.getNodeOperator(CONSENSYS_V1_NODE_OPERATOR_ID, True)["name"] == "Consensys"
    assert curated_v2.getNodeOperator(CONSENSYS_V2_NODE_OPERATOR_ID)["managerAddress"] == (
        "0xF45C77EadD434612fCD93db978B3E36B0D58eC99"
    )

    factories = [
        REPORT_WITHDRAWALS_FACTORY,
        SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
        UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
    ]
    factory_permissions = [
        _permission(CSM0X02, "reportSlashedWithdrawnValidators((uint256,uint256,uint256,uint256,bool)[])"),
        _permission(CSM0X02, "settleGeneralDelayedPenalty(uint256[],uint256[])"),
        (
            _permission(UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY, "validateParams((uint16,uint16,uint16,uint16))")
            + _permission(STAKING_ROUTER, "updateModuleShares(uint256,uint16,uint16)")[2:]
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
        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        dg_proposals_count_before = timelock.getProposalsCount()
        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        _assert_easy_track_factories(easy_track, factories, factory_permissions)
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT
        submitted_id = vote_events[0]["ProposalSubmitted"][0]["id"]
        if proposal_id is not None:
            assert submitted_id == proposal_id
        proposal_id = submitted_id
        assert proposal_id == timelock.getProposalsCount() == dg_proposals_count_before + 1
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
    bnb_message = bnb_actions_set_message()
    # a.DI: the DG proposal contains the expected forwardMessage call, with the gas limit for the BNB Chain delivery.
    destination_chain_id, destination, gas_limit, message = _forward_message_args(
        timelock.getProposalCalls(proposal_id)
    )
    assert destination_chain_id == BNB_CHAIN_ID
    assert destination == BNB_CROSS_CHAIN_EXECUTOR
    assert gas_limit == BNB_MESSAGE_GAS_LIMIT
    assert bytes(message) == bnb_message

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
        frame_config_before = hash_consensus.getFrameConfig()
        assert frame_config_before["initialEpoch"] == CSM0X02_ORACLE_PRE_VOTE_INITIAL_EPOCH
        assert frame_config_before["epochsPerFrame"] == CSM0X02_ORACLE_EPOCHS_PER_FRAME
        for target in circuit_breaker_targets:
            assert circuit_breaker.getPauser(target) == ZERO_ADDRESS

        # a.DI: all four bridges forward to BNB Chain, the Agent is an approved sender, and the message is not sent yet.
        assert ethereum_ccc.isSenderApproved(AGENT)
        assert _forwarder_bridge_adapters(ethereum_ccc, BNB_CHAIN_ID) == BNB_BRIDGE_ADAPTERS_BEFORE
        envelope_nonce_before = ethereum_ccc.getCurrentEnvelopeNonce()
        transaction_nonce_before = ethereum_ccc.getCurrentTransactionNonce()
        envelope_id = web3.keccak(encode_adi_envelope(envelope_nonce_before, bnb_message))
        transaction_id = web3.keccak(
            encode_adi_transaction(transaction_nonce_before, envelope_nonce_before, bnb_message)
        )
        assert not ethereum_ccc.isEnvelopeRegistered["bytes32"](envelope_id)
        assert not ethereum_ccc.isTransactionForwarded["bytes32"](transaction_id)
        ethereum_ccc_eth_balance_before = web3.eth.get_balance(ETHEREUM_CROSS_CHAIN_CONTROLLER)
        adi_from_block = web3.eth.block_number

        process_proposals([proposal_id])
        dg_tx: TransactionReceipt = history[-1]
        display_dg_events(dg_tx)
        dg_events = group_dg_events_from_receipt(
            dg_tx, timelock=EMERGENCY_PROTECTED_TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR
        )
        assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
        assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

        # 1.1. Register CSM 0x02 and its independent router parameters.
        _validate_module_added_event(dg_events[0])
        # 1.2-1.4. Grant Burner, TWG and temporary module resume permissions.
        for index, role_name, account, emitter in (
            (1, "REQUEST_BURN_MY_STETH_ROLE", CSM0X02_ACCOUNTING, BURNER),
            (2, "ADD_FULL_WITHDRAWAL_REQUEST_ROLE", CSM0X02_EJECTOR, TRIGGERABLE_WITHDRAWALS_GATEWAY),
            (3, "RESUME_ROLE", AGENT, CSM0X02),
        ):
            validate_grant_role_event(
                dg_events[index],
                web3.keccak(text=role_name).hex(),
                account,
                sender=AGENT,
                emitted_by=emitter,
                event_chain=["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"],
            )
        # 1.5-1.6. Resume the module and remove the temporary permission.
        validate_events_chain(
            [event.name for event in dg_events[4]],
            ["LogScriptCall", "Resumed", "ScriptResult", "Executed"],
        )
        _event(dg_events[4], "Resumed", CSM0X02)
        validate_revoke_role_event(
            dg_events[5], web3.keccak(text="RESUME_ROLE").hex(), AGENT, sender=AGENT, emitted_by=CSM0X02
        )
        # 1.7. Set the initial oracle epoch without changing the 28-day frame.
        validate_events_chain(
            [event.name for event in dg_events[6]],
            ["LogScriptCall", "FrameConfigSet", "ScriptResult", "Executed"],
        )
        frame = _event(dg_events[6], "FrameConfigSet", CSM0X02_HASH_CONSENSUS)
        assert frame["newInitialEpoch"] == CSM0X02_ORACLE_INITIAL_EPOCH
        assert frame["newEpochsPerFrame"] == CSM0X02_ORACLE_EPOCHS_PER_FRAME
        # 1.8-1.12. Register each pausable with the CSM committee.
        for index, target in enumerate(circuit_breaker_targets, start=7):
            validate_events_chain(
                [event.name for event in dg_events[index]],
                ["LogScriptCall", "PauserSet", "HeartbeatUpdated", "ScriptResult", "Executed"],
            )
            validate_register_pauser_event(dg_events[index], target, CSM_COMMITTEE, emitted_by=CIRCUIT_BREAKER)
            _event(dg_events[index], "PauserSet", CIRCUIT_BREAKER)
            heartbeat = _event(dg_events[index], "HeartbeatUpdated", CIRCUIT_BREAKER)
            assert heartbeat["newHeartbeatExpiry"] == dg_tx.timestamp + circuit_breaker.heartbeatInterval()
        # 1.13. Set only the CMv1 share limit to zero.
        validate_staking_module_update_event(
            dg_events[12],
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
            event = _event(dg_events[12], event_name, STAKING_ROUTER)
            assert event["stakingModuleId"] == CURATED_V1_MODULE_ID
            assert event["setBy"] == AGENT
        assert dg_events[12]["StakingModuleMaxDepositsPerBlockSet"]["maxDepositsPerBlock"] == (
            CURATED_V1_MAX_DEPOSITS_PER_BLOCK
        )
        assert dg_events[12]["StakingModuleMinDepositBlockDistanceSet"]["minDepositBlockDistance"] == (
            CURATED_V1_MIN_DEPOSIT_BLOCK_DISTANCE
        )
        # 1.14-1.15. Stop deposits for Consensys in both curated modules.
        for index, module, operator_id, summary_before, nonce_before in zip(
            (13, 14),
            (curated_v1, curated_v2),
            (CONSENSYS_V1_NODE_OPERATOR_ID, CONSENSYS_V2_NODE_OPERATOR_ID),
            target_summaries_before,
            target_nonces_before,
        ):
            _validate_target_limit_event(dg_events[index], module, operator_id, summary_before, nonce_before)

        # a.DI: exactly one envelope with the expected BNB Chain action set was registered and forwarded, and the bridge
        # fees were paid from the CrossChainController balance. The BNB replay tests below check the BNB Chain
        # changes on a separate fork.
        assert ethereum_ccc.getCurrentEnvelopeNonce() == envelope_nonce_before + 1
        assert ethereum_ccc.getCurrentTransactionNonce() == transaction_nonce_before + 1
        assert ethereum_ccc.isEnvelopeRegistered["bytes32"](envelope_id)
        assert ethereum_ccc.isTransactionForwarded["bytes32"](transaction_id)
        assert web3.eth.get_balance(ETHEREUM_CROSS_CHAIN_CONTROLLER) < ethereum_ccc_eth_balance_before

        # a.DI: all four bridges got the same encoded transaction. forwardMessage does not revert when a bridge fails,
        # and since Wormhole no longer delivers, the 3-of-4 quorum needs CCIP, LayerZero, and Hyperlane to accept it.
        attempts = _forwarding_attempts(adi_from_block, envelope_id)
        assert len(attempts) == len(BNB_BRIDGE_ADAPTERS_BEFORE)
        assert {(a["destinationBridgeAdapter"], a["bridgeAdapter"]) for a in attempts} == BNB_BRIDGE_ADAPTERS_BEFORE
        assert all(
            a["adapterSuccessful"]
            for a in attempts
            if (a["destinationBridgeAdapter"], a["bridgeAdapter"]) in BNB_BRIDGE_ADAPTERS_AFTER
        )
        encoded_transactions = {bytes(a["encodedTransaction"]) for a in attempts}
        assert len(encoded_transactions) == 1
        encoded_transaction = encoded_transactions.pop()
        assert web3.keccak(encoded_transaction) == transaction_id

        with open(ADI_BNB_MESSAGE_ARTIFACT, "w") as f:
            json.dump(
                {
                    "encodedTransaction": "0x" + encoded_transaction.hex(),
                    "transactionId": transaction_id.hex(),
                    "gasLimit": gas_limit,
                    "session": ADI_BNB_MESSAGE_SESSION,
                },
                f,
                indent=2,
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
        assert curated_v1_config_after == {**curated_v1_config_before, "stakeShareLimit": 0}
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
    frame_config_after = hash_consensus.getFrameConfig()
    assert frame_config_after["initialEpoch"] == CSM0X02_ORACLE_INITIAL_EPOCH
    assert frame_config_after["epochsPerFrame"] == CSM0X02_ORACLE_EPOCHS_PER_FRAME
    for target in circuit_breaker_targets:
        assert circuit_breaker.getPauser(target) == CSM_COMMITTEE

    assert _forwarder_bridge_adapters(ethereum_ccc, BNB_CHAIN_ID) == BNB_BRIDGE_ADAPTERS_AFTER
    assert ethereum_ccc.isSenderApproved(AGENT)


# ============================================================================
# ============================ BNB replay helpers ============================
# ============================================================================
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _contract(w3, address: str, interface_name: str):
    with open(f"interfaces/{interface_name}.json") as f:
        return w3.eth.contract(address=address, abi=json.load(f))


def _send(w3, sender: str, to: str, data, gas: int = None) -> dict:
    w3.provider.make_request("anvil_setBalance", [sender, hex(10**18)])
    tx = {"from": sender, "to": to, "data": data}
    if gas is not None:
        tx["gas"] = gas
    receipt = w3.eth.wait_for_transaction_receipt(w3.eth.send_transaction(tx))
    assert receipt.status == 1
    return receipt


def _events(contract, receipt) -> list:
    """Decode the events the contract emitted in the receipt, in emission order."""
    events = []
    for log in receipt.logs:
        if log.address != contract.address:
            continue
        for event_abi in contract.events:
            decoded = event_abi().process_receipt({"logs": [log]}, errors=DISCARD)
            if decoded:
                events.append(decoded[0])
                break
    return events


def _receive_from_adapter(w3, ccc, adapter: str, encoded_transaction: bytes) -> dict:
    """Call the CrossChainController as the BNB Chain adapter of a bridge that has delivered the transaction."""
    data = ccc.encodeABI(fn_name="receiveCrossChainMessage", args=[encoded_transaction, ETHEREUM_CHAIN_ID])
    return _send(w3, adapter, ccc.address, data)


def _bridge_delivery(bridge: str, encoded_transaction: bytes) -> tuple:
    """The bridge's BNB Chain entry point, its adapter, and the calldata the entry point sends to the adapter."""
    ethereum_ccc_as_bytes32 = bytes(12) + bytes.fromhex(ETHEREUM_CROSS_CHAIN_CONTROLLER.removeprefix("0x"))
    if bridge == "ccip":
        signature = "ccipReceive((bytes32,uint64,bytes,bytes,(address,uint256)[]))"
        args = encode(
            ["(bytes32,uint64,bytes,bytes,(address,uint256)[])"],
            [(bytes(32), CCIP_ETHEREUM_CHAIN_SELECTOR, ethereum_ccc_as_bytes32, encoded_transaction, [])],
        )
        return BNB_CCIP_ROUTER, BNB_CCIP_ADAPTER, Web3.keccak(text=signature)[:4] + args
    if bridge == "layerzero":
        signature = "lzReceive((uint32,bytes32,uint64),bytes32,bytes,address,bytes)"
        args = encode(
            ["(uint32,bytes32,uint64)", "bytes32", "bytes", "address", "bytes"],
            [(LAYERZERO_ETHEREUM_EID, ethereum_ccc_as_bytes32, 1), bytes(32), encoded_transaction, BNB_STRANGER, b""],
        )
        return BNB_LAYERZERO_ENDPOINT, BNB_LAYERZERO_ADAPTER, Web3.keccak(text=signature)[:4] + args
    if bridge == "hyperlane":
        signature = "handle(uint32,bytes32,bytes)"
        args = encode(
            ["uint32", "bytes32", "bytes"],
            [HYPERLANE_ETHEREUM_DOMAIN, ethereum_ccc_as_bytes32, encoded_transaction],
        )
        return BNB_HYPERLANE_MAILBOX, BNB_HYPERLANE_ADAPTER, Web3.keccak(text=signature)[:4] + args
    raise ValueError(f"Unknown bridge {bridge}")


def _intrinsic_gas(data: bytes) -> int:
    return 21_000 + sum(16 if byte else 4 for byte in data)


# ============================================================================
# =========================== BNB replay fixtures ============================
# ============================================================================
@pytest.fixture(scope="module")
def bnb_fork():
    rpc_url = os.getenv(BNB_RPC_URL_ENV)
    if not rpc_url:
        pytest.skip(f"Set {BNB_RPC_URL_ENV} to replay the a.DI message on a BNB Chain fork")
    if shutil.which("anvil") is None:
        pytest.skip("anvil is required to fork BNB Chain")

    port = _free_port()
    anvil_log = tempfile.TemporaryFile()
    anvil = subprocess.Popen(
        ["anvil", "--fork-url", rpc_url, "--port", str(port), "--auto-impersonate", "--silent"],
        stdout=anvil_log,
        stderr=subprocess.STDOUT,
    )
    w3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{port}", request_kwargs={"timeout": 300}))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # BNB Chain block headers carry long extraData.
    try:
        for _ in range(60):
            if w3.is_connected() or anvil.poll() is not None:
                break
            time.sleep(1)
        if not w3.is_connected():
            anvil_log.seek(0)
            output = anvil_log.read().decode(errors="replace").replace(rpc_url, f"${BNB_RPC_URL_ENV}")
            pytest.fail(f"anvil failed to fork BNB Chain:\n{output}")
        assert w3.eth.chain_id == BNB_CHAIN_ID
        yield w3
    finally:
        anvil.terminate()
        anvil.wait()
        anvil_log.close()


@pytest.fixture
def bnb(bnb_fork):
    snapshot_id = bnb_fork.provider.make_request("evm_snapshot", [])["result"]
    yield bnb_fork
    bnb_fork.provider.make_request("evm_revert", [snapshot_id])


@pytest.fixture(scope="module")
def forwarded_transaction():
    artifact = {}
    if os.path.exists(ADI_BNB_MESSAGE_ARTIFACT):
        with open(ADI_BNB_MESSAGE_ARTIFACT) as f:
            artifact = json.load(f)
    if artifact.get("session") != ADI_BNB_MESSAGE_SESSION:
        pytest.skip(f"Run tests/test_vote_csm0x02.py in the same session, it saves {ADI_BNB_MESSAGE_ARTIFACT}")

    encoded_transaction = bytes.fromhex(artifact["encodedTransaction"].removeprefix("0x"))
    assert Web3.keccak(encoded_transaction).hex() == artifact["transactionId"]

    # Unpack the transaction the way the BNB Chain CrossChainController does and check the envelope.
    ((_, encoded_envelope),) = decode(["(uint256,bytes)"], encoded_transaction)
    ((_, origin, destination, origin_chain_id, destination_chain_id, message),) = decode(
        [ENVELOPE_TYPE], encoded_envelope
    )
    assert Web3.to_checksum_address(origin) == AGENT
    assert Web3.to_checksum_address(destination) == BNB_CROSS_CHAIN_EXECUTOR
    assert origin_chain_id == ETHEREUM_CHAIN_ID
    assert destination_chain_id == BNB_CHAIN_ID
    assert message == bnb_actions_set_message()

    return encoded_transaction, artifact["gasLimit"]


# ============================================================================
# ============================= BNB replay tests =============================
# ============================================================================
@pytest.mark.parametrize("last_bridge", ["ccip", "layerzero", "hyperlane"])
def test_vote_bnb_actions_set(bnb, forwarded_transaction, last_bridge):
    encoded_transaction, gas_limit = forwarded_transaction
    ccc = _contract(bnb, BNB_CROSS_CHAIN_CONTROLLER, "CrossChainController")
    executor = _contract(bnb, BNB_CROSS_CHAIN_EXECUTOR, "CrossChainExecutor")
    bridge_adapters = {"ccip": BNB_CCIP_ADAPTER, "layerzero": BNB_LAYERZERO_ADAPTER, "hyperlane": BNB_HYPERLANE_ADAPTER}

    # Before the action set: BNB Chain requires 3 of 4 bridges, and queued action sets can be executed immediately.
    assert set(ccc.functions.getReceiverBridgeAdaptersByChain(ETHEREUM_CHAIN_ID).call()) == {
        *bridge_adapters.values(),
        BNB_WORMHOLE_ADAPTER,
    }
    required_confirmations, validity_timestamp = ccc.functions.getConfigurationByChain(ETHEREUM_CHAIN_ID).call()
    assert required_confirmations == BNB_REQUIRED_CONFIRMATIONS_BEFORE
    assert ccc.functions.owner().call() == BNB_CROSS_CHAIN_EXECUTOR
    assert executor.functions.getEthereumGovernanceExecutor().call() == AGENT
    assert executor.functions.getDelay().call() == 0
    assert executor.functions.getGracePeriod().call() == BNB_EXECUTOR_GRACE_PERIOD
    actions_sets_count_before = executor.functions.getActionsSetCount().call()

    # Two bridges deliver: below the 3-of-4 quorum, nothing is queued.
    for bridge, adapter in bridge_adapters.items():
        if bridge != last_bridge:
            _receive_from_adapter(bnb, ccc, adapter, encoded_transaction)
    assert executor.functions.getActionsSetCount().call() == actions_sets_count_before

    # The last bridge delivers through its BNB Chain entry point with the gas limit paid on Ethereum on top of the
    # intrinsic cost (adapters add no base gas). CCIP passes exactly this gas to the adapter. LayerZero spends part of
    # it in the endpoint first, so the test is slightly optimistic there; Hyperlane relayers choose the gas themselves.
    # The ~880k used leaves enough margin within 1.2M.
    entry_point, adapter, data = _bridge_delivery(last_bridge, encoded_transaction)
    receipt = _send(bnb, entry_point, adapter, data, gas=_intrinsic_gas(data) + gas_limit)

    (delivery,) = ccc.events.EnvelopeDeliveryAttempted().process_receipt(receipt, errors=DISCARD)
    assert delivery.args.isDelivered

    # The executor unpacked the message into exactly the expected action set.
    (message_received,) = executor.events.MessageReceived().process_receipt(receipt, errors=DISCARD)
    assert message_received.args.originSender == AGENT
    assert message_received.args.originChainId == ETHEREUM_CHAIN_ID
    assert message_received.args.message == bnb_actions_set_message()

    targets, values, signatures, calldatas, with_delegatecalls = decode(ACTIONS_SET_TYPES, bnb_actions_set_message())
    (queued,) = executor.events.ActionsSetQueued().process_receipt(receipt, errors=DISCARD)
    assert queued.args.id == actions_sets_count_before
    assert queued.args.targets == [Web3.to_checksum_address(target) for target in targets]
    assert queued.args["values"] == list(values)
    assert queued.args.signatures == list(signatures)
    assert queued.args.calldatas == list(calldatas)
    assert queued.args.withDelegatecalls == list(with_delegatecalls)
    assert executor.functions.getCurrentState(queued.args.id).call() == ACTIONS_SET_STATE_QUEUED

    # Anyone can execute the action set. It makes exactly the two configuration changes on the CrossChainController.
    receipt = _send(bnb, BNB_STRANGER, executor.address, executor.encodeABI(fn_name="execute", args=[queued.args.id]))
    assert executor.functions.getCurrentState(queued.args.id).call() == ACTIONS_SET_STATE_EXECUTED
    assert [(event.event, dict(event.args)) for event in _events(ccc, receipt)] == [
        (
            "ReceiverBridgeAdaptersUpdated",
            {"bridgeAdapter": BNB_WORMHOLE_ADAPTER, "allowed": False, "chainId": ETHEREUM_CHAIN_ID},
        ),
        ("ConfirmationsUpdated", {"newConfirmations": BNB_REQUIRED_CONFIRMATIONS, "chainId": ETHEREUM_CHAIN_ID}),
    ]

    assert set(ccc.functions.getReceiverBridgeAdaptersByChain(ETHEREUM_CHAIN_ID).call()) == set(
        bridge_adapters.values()
    )
    assert not ccc.functions.isReceiverBridgeAdapterAllowed(BNB_WORMHOLE_ADAPTER, ETHEREUM_CHAIN_ID).call()
    assert tuple(ccc.functions.getConfigurationByChain(ETHEREUM_CHAIN_ID).call()) == (
        BNB_REQUIRED_CONFIRMATIONS,
        validity_timestamp,
    )
    assert ccc.functions.getSupportedChains().call() == [ETHEREUM_CHAIN_ID]
    assert ccc.functions.owner().call() == BNB_CROSS_CHAIN_EXECUTOR


def test_vote_bnb_two_of_three(bnb, forwarded_transaction):
    encoded_transaction, _ = forwarded_transaction
    ccc = _contract(bnb, BNB_CROSS_CHAIN_CONTROLLER, "CrossChainController")
    executor = _contract(bnb, BNB_CROSS_CHAIN_EXECUTOR, "CrossChainExecutor")

    # Apply the vote's action set.
    for adapter in [BNB_CCIP_ADAPTER, BNB_LAYERZERO_ADAPTER, BNB_HYPERLANE_ADAPTER]:
        _receive_from_adapter(bnb, ccc, adapter, encoded_transaction)
    vote_actions_set_id = executor.functions.getActionsSetCount().call() - 1
    _send(bnb, BNB_STRANGER, executor.address, executor.encodeABI(fn_name="execute", args=[vote_actions_set_id]))

    # The next Lido DAO message, with a harmless action set: a view call on the CrossChainController.
    ((transaction_nonce, encoded_envelope),) = decode(["(uint256,bytes)"], encoded_transaction)
    ((envelope_nonce, *_),) = decode([ENVELOPE_TYPE], encoded_envelope)
    next_message = encode(
        ACTIONS_SET_TYPES, [[BNB_CROSS_CHAIN_CONTROLLER], [0], ["getSupportedChains()"], [b""], [False]]
    )
    next_transaction = encode_adi_transaction(transaction_nonce + 1, envelope_nonce + 1, next_message)
    receive_call = {
        "to": ccc.address,
        "data": ccc.encodeABI(fn_name="receiveCrossChainMessage", args=[next_transaction, ETHEREUM_CHAIN_ID]),
    }

    # Wormhole deliveries are rejected.
    with pytest.raises(ContractLogicError, match=f"execution reverted: {CALLER_NOT_APPROVED_BRIDGE}$"):
        bnb.eth.call({"from": BNB_WORMHOLE_ADAPTER, **receive_call})

    # One confirmation is not enough, two of the three remaining bridges are.
    actions_sets_count = executor.functions.getActionsSetCount().call()
    _receive_from_adapter(bnb, ccc, BNB_CCIP_ADAPTER, next_transaction)
    assert executor.functions.getActionsSetCount().call() == actions_sets_count
    _receive_from_adapter(bnb, ccc, BNB_LAYERZERO_ADAPTER, next_transaction)
    assert executor.functions.getActionsSetCount().call() == actions_sets_count + 1
