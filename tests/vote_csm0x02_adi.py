"""
a.DI expectations shared by tests/test_vote_csm0x02.py and tests/test_vote_csm0x02_bnb.py.

They are deliberately independent from the vote script.
"""

import uuid

from eth_abi import encode


AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"

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

# Forwarder bridge adapter configs as (destinationBridgeAdapter, currentChainBridgeAdapter).
BNB_BRIDGE_ADAPTERS_BEFORE = {
    (BNB_CCIP_ADAPTER, ETHEREUM_CCIP_ADAPTER),
    (BNB_LAYERZERO_ADAPTER, ETHEREUM_LAYERZERO_ADAPTER),
    (BNB_HYPERLANE_ADAPTER, ETHEREUM_HYPERLANE_ADAPTER),
    (BNB_WORMHOLE_ADAPTER, ETHEREUM_WORMHOLE_ADAPTER),
}
BNB_BRIDGE_ADAPTERS_AFTER = BNB_BRIDGE_ADAPTERS_BEFORE - {(BNB_WORMHOLE_ADAPTER, ETHEREUM_WORMHOLE_ADAPTER)}

# The forwarded a.DI transaction is saved here for tests/test_vote_csm0x02_bnb.py to replay on a BNB Chain fork.
ADI_BNB_MESSAGE_ARTIFACT = "build/adi_bnb_message.json"
# Written into the artifact, so the replay only accepts one produced in the same pytest session.
ADI_BNB_MESSAGE_SESSION = uuid.uuid4().hex

ENVELOPE_TYPE = "(uint256,address,address,uint256,uint256,bytes)"
ACTIONS_SET_TYPES = ["address[]", "uint256[]", "string[]", "bytes[]", "bool[]"]


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
    # Envelope(nonce, origin, destination, originChainId, destinationChainId, message), id = keccak256(abi.encode(envelope))
    envelope = (envelope_nonce, AGENT, BNB_CROSS_CHAIN_EXECUTOR, ETHEREUM_CHAIN_ID, BNB_CHAIN_ID, message)
    return encode([ENVELOPE_TYPE], [envelope])


def encode_adi_transaction(transaction_nonce: int, envelope_nonce: int, message: bytes) -> bytes:
    # Transaction(nonce, encodedEnvelope), id = keccak256(abi.encode(transaction))
    return encode(["(uint256,bytes)"], [(transaction_nonce, encode_adi_envelope(envelope_nonce, message))])
