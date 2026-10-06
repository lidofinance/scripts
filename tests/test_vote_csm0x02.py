import json

import pytest
from avotes_parser.core import parse_script
from brownie import ZERO_ADDRESS, convert, interface, web3
from brownie.network.event import _decode_logs

from scripts.vote_csm0x02 import start_vote
from tests.vote_csm0x02_adi import (
    ADI_BNB_MESSAGE_ARTIFACT,
    ADI_BNB_MESSAGE_SESSION,
    BNB_BRIDGE_ADAPTERS_AFTER,
    BNB_BRIDGE_ADAPTERS_BEFORE,
    BNB_CHAIN_ID,
    BNB_CROSS_CHAIN_EXECUTOR,
    BNB_MESSAGE_GAS_LIMIT,
    ETHEREUM_CROSS_CHAIN_CONTROLLER,
    bnb_actions_set_message,
    encode_adi_envelope,
    encode_adi_transaction,
)
from utils.mainnet_fork import pass_and_exec_dao_vote


# Mainnet governance
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"

# Vote targets
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
BURNER = "0xE76c52750019b80B43E36DF30bf4060EB73F573a"
TRIGGERABLE_WITHDRAWALS_GATEWAY = "0xDC00116a0D3E064427dA2600449cfD2566B3037B"
CIRCUIT_BREAKER = "0x6019CB557978296BA3C08a7B73225C0975DFB2F7"
CSM_COMMITTEE = "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f"

TODO_ADDRESS = "TODO"

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

DEPLOYMENT_ADDRESSES = [
    CSM0X02,
    CSM0X02_ACCOUNTING,
    CSM0X02_FEE_ORACLE,
    CSM0X02_HASH_CONSENSUS,
    CSM0X02_VERIFIER,
    CSM0X02_EJECTOR,
    REPORT_WITHDRAWALS_FACTORY,
    SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
    UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
]

# Expected deployment parameters are deliberately independent from the vote script.
CSM0X02_NAME = "Community Staking 0x02"
CSM0X02_TARGET_SHARE_BP = 200
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 240
CSM0X02_MODULE_FEE_BP = 200
CSM0X02_TREASURY_FEE_BP = 800
CSM0X02_MAX_DEPOSITS_PER_BLOCK = 30
CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE = 0x02

CURATED_V1_MODULE_ID = 1
CURATED_V2_MODULE_ID = 4
CONSENSYS_V1_NODE_OPERATOR_ID = 21
CONSENSYS_V2_NODE_OPERATOR_ID = 6
CURATED_V1_ADDRESS = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
CURATED_V2_ADDRESS = "0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1"

# TODO: Calculate for the expected mainnet vote date after a complete oracle frame.
CSM0X02_ORACLE_INITIAL_EPOCH = 0


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

    assert staking_router.getStakingModule(module_id)["name"] == CSM0X02_NAME
    assert module["moduleAddress"] == CSM0X02
    assert module["stakeShareLimit"] == CSM0X02_TARGET_SHARE_BP
    assert module["priorityExitShareThreshold"] == CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP
    assert module["moduleFee"] == CSM0X02_MODULE_FEE_BP
    assert module["treasuryFee"] == CSM0X02_TREASURY_FEE_BP
    assert module["withdrawalCredentialsType"] == CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE
    assert staking_router.getStakingModuleMaxDepositsPerBlock(module_id) == CSM0X02_MAX_DEPOSITS_PER_BLOCK
    assert staking_router.getStakingModuleMinDepositBlockDistance(module_id) == CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE


@pytest.mark.skipif(
    TODO_ADDRESS in DEPLOYMENT_ADDRESSES or CSM0X02_ORACLE_INITIAL_EPOCH <= 0,
    reason="Set mainnet CSM 0x02 deployment addresses and initial oracle epoch",
)
def test_vote(ldo_holder):
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

    curated_v1_config_before = staking_router.getStakingModuleStateConfig(CURATED_V1_MODULE_ID).dict()
    curated_v1_deposits_before = staking_router.getStakingModuleStateDeposits(CURATED_V1_MODULE_ID).dict()
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

    modules_count_before = staking_router.getStakingModulesCount()
    module_id = modules_count_before + 1

    # The deployment contracts exist, but none of the activation effects is applied yet.
    assert not staking_router.hasStakingModule(module_id)
    assert not burner.hasRole(burner.REQUEST_BURN_MY_STETH_ROLE(), CSM0X02_ACCOUNTING)
    assert not twg.hasRole(twg.ADD_FULL_WITHDRAWAL_REQUEST_ROLE(), CSM0X02_EJECTOR)
    assert csm.isPaused()
    assert not csm.hasRole(csm.RESUME_ROLE(), AGENT)
    assert hash_consensus.getFrameConfig()[0] != CSM0X02_ORACLE_INITIAL_EPOCH
    for target in circuit_breaker_targets:
        assert circuit_breaker.getPauser(target) == ZERO_ADDRESS
    for factory in factories:
        assert factory not in easy_track.getEVMScriptFactories()

    # a.DI: all four bridges forward to BNB Chain, the Agent is an approved sender, and the message is not sent yet.
    assert ethereum_ccc.isSenderApproved(AGENT)
    assert _forwarder_bridge_adapters(ethereum_ccc, BNB_CHAIN_ID) == BNB_BRIDGE_ADAPTERS_BEFORE
    bnb_message = bnb_actions_set_message()
    envelope_nonce_before = ethereum_ccc.getCurrentEnvelopeNonce()
    transaction_nonce_before = ethereum_ccc.getCurrentTransactionNonce()
    envelope_id = web3.keccak(encode_adi_envelope(envelope_nonce_before, bnb_message))
    transaction_id = web3.keccak(encode_adi_transaction(transaction_nonce_before, envelope_nonce_before, bnb_message))
    assert not ethereum_ccc.isEnvelopeRegistered["bytes32"](envelope_id)
    assert not ethereum_ccc.isTransactionForwarded["bytes32"](transaction_id)
    ethereum_ccc_eth_balance_before = web3.eth.get_balance(ETHEREUM_CROSS_CHAIN_CONTROLLER)
    adi_from_block = web3.eth.block_number
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dg_proposals_count_before = timelock.getProposalsCount()

    vote_id, _ = start_vote({"from": ldo_holder}, silent=True)
    pass_and_exec_dao_vote(vote_id)

    for factory, permissions in zip(factories, factory_permissions):
        assert factory in easy_track.getEVMScriptFactories()
        assert bytes(easy_track.evmScriptFactoryPermissions(factory)) == bytes.fromhex(permissions.removeprefix("0x"))

    assert staking_router.getStakingModulesCount() == module_id
    assert staking_router.hasStakingModule(module_id)
    _assert_module_config(staking_router, module_id)

    curated_v1_config_after = staking_router.getStakingModuleStateConfig(CURATED_V1_MODULE_ID).dict()
    assert curated_v1_config_after == {**curated_v1_config_before, "stakeShareLimit": 0}
    curated_v1_deposits_after = staking_router.getStakingModuleStateDeposits(CURATED_V1_MODULE_ID).dict()
    assert curated_v1_deposits_after["maxDepositsPerBlock"] == curated_v1_deposits_before["maxDepositsPerBlock"]
    assert curated_v1_deposits_after["minDepositBlockDistance"] == curated_v1_deposits_before["minDepositBlockDistance"]
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
    assert hash_consensus.getFrameConfig()[0] == CSM0X02_ORACLE_INITIAL_EPOCH
    for target in circuit_breaker_targets:
        assert circuit_breaker.getPauser(target) == CSM_COMMITTEE

    # a.DI: exactly one envelope with the expected BNB Chain action set was registered and forwarded,
    # bridge fees were paid from the CrossChainController balance, and Wormhole no longer forwards to BNB Chain.
    # The BNB Chain side (disallowing the Wormhole adapter, 2-of-3 confirmations) is checked on a BNB Chain fork
    # in tests/test_vote_csm0x02_bnb.py.
    assert ethereum_ccc.getCurrentEnvelopeNonce() == envelope_nonce_before + 1
    assert ethereum_ccc.getCurrentTransactionNonce() == transaction_nonce_before + 1
    assert ethereum_ccc.isEnvelopeRegistered["bytes32"](envelope_id)
    assert ethereum_ccc.isTransactionForwarded["bytes32"](transaction_id)
    assert web3.eth.get_balance(ETHEREUM_CROSS_CHAIN_CONTROLLER) < ethereum_ccc_eth_balance_before
    assert _forwarder_bridge_adapters(ethereum_ccc, BNB_CHAIN_ID) == BNB_BRIDGE_ADAPTERS_AFTER
    assert ethereum_ccc.isSenderApproved(AGENT)

    # a.DI: the vote's DG proposal packs the expected forwardMessage call, including the gas limit for BNB Chain delivery.
    assert timelock.getProposalsCount() == dg_proposals_count_before + 1
    destination_chain_id, destination, gas_limit, message = _forward_message_args(
        timelock.getProposalCalls(dg_proposals_count_before + 1)
    )
    assert destination_chain_id == BNB_CHAIN_ID
    assert destination == BNB_CROSS_CHAIN_EXECUTOR
    assert gas_limit == BNB_MESSAGE_GAS_LIMIT
    assert bytes(message) == bnb_message

    # a.DI: all four bridges got the same encoded transaction. A failed bridge does not revert forwardMessage, and
    # without Wormhole the message reaches the 3-of-4 quorum only if the three remaining bridges all accepted it.
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
