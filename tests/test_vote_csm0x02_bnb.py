"""
Replays the a.DI transaction forwarded by the vote in scripts/vote_csm0x02.py on a BNB Chain fork.

tests/test_vote_csm0x02.py executes the vote on the Ethereum fork and saves the forwarded a.DI transaction to
ADI_BNB_MESSAGE_ARTIFACT. This module delivers exactly those bytes to the BNB Chain CrossChainController, executes
the queued action set, and checks the resulting configuration. Brownie forks Ethereum only, so the BNB Chain fork
is a separate anvil process driven through web3.

Requires anvil and BNB_RPC_URL. The replay skips an artifact saved in another pytest session, so run both stages
together:
    BNB_RPC_URL=<rpc> poetry run brownie test tests/test_vote_csm0x02.py tests/test_vote_csm0x02_bnb.py --network mfh-1
"""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time

import pytest
from eth_abi import decode, encode
from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.logs import DISCARD
from web3.middleware import geth_poa_middleware

from tests.vote_csm0x02_adi import (
    ACTIONS_SET_TYPES,
    ADI_BNB_MESSAGE_ARTIFACT,
    ADI_BNB_MESSAGE_SESSION,
    AGENT,
    BNB_CCIP_ADAPTER,
    BNB_CHAIN_ID,
    BNB_CROSS_CHAIN_CONTROLLER,
    BNB_CROSS_CHAIN_EXECUTOR,
    BNB_HYPERLANE_ADAPTER,
    BNB_LAYERZERO_ADAPTER,
    BNB_REQUIRED_CONFIRMATIONS,
    BNB_WORMHOLE_ADAPTER,
    ENVELOPE_TYPE,
    ETHEREUM_CHAIN_ID,
    ETHEREUM_CROSS_CHAIN_CONTROLLER,
    bnb_actions_set_message,
    encode_adi_transaction,
)


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


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


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
