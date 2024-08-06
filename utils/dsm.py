from typing import Any, Dict
from eth_account import Account
from eth_account.datastructures import (
    SignedMessage,
)
from web3 import Web3
from dataclasses import dataclass

@dataclass
class UnvetArgs:
    block_number: int = None
    block_hash: str = None
    staking_module_id: int = None
    nonce: int = None
    node_operator_ids: bytes = None
    vetted_signing_keys_counts: bytes = None

class DSMMessage:
    MESSAGE_PREFIX: str = ""

    @classmethod
    def set_message_prefix(cls, new_message_prefix: str):
        cls.MESSAGE_PREFIX = new_message_prefix

    @property
    def message_prefix(self) -> str:
        if not self.MESSAGE_PREFIX:
            raise ValueError("MESSAGE_PREFIX isn't set")
        return self.MESSAGE_PREFIX

    @property
    def hash(self) -> str:
        raise NotImplementedError("Unimplemented")

    def sign(self, signer_private_key: str) -> Dict[str, Any]:
        signedMessage = Account.signHash(self.hash, signer_private_key)
        return to_eip2098(signedMessage)


class DSMUnvetMessage(DSMMessage):
    def __init__(self, block_number: int, block_hash: str, staking_module: int, nonce: int,
                 node_operator_ids: str, vetted_signing_keys_counts: str):
        super().__init__()
        self.block_number = block_number
        self.block_hash = block_hash
        self.staking_module = staking_module
        self.nonce = nonce
        self.node_operator_ids = node_operator_ids
        self.vetted_signing_keys_counts = vetted_signing_keys_counts

    @property
    def hash(self) -> str:
        return Web3.solidity_keccak(
            ["bytes32", "uint256", "bytes32", "uint256", "uint256", "bytes", "bytes"],
            [
                self.message_prefix,
                self.block_number,
                self.block_hash,
                self.staking_module,
                self.nonce,
                self.node_operator_ids,
                self.vetted_signing_keys_counts
            ]
        ).hex()

def to_eip2098(signedMessage: SignedMessage) -> Dict[str, Any]:
    r = signedMessage.r
    s = signedMessage.s
    v = signedMessage.v

    assert (r.bit_length() + 7) // 8 == 32
    assert (s.bit_length() + 7) // 8 == 32

    if v not in (27, 28):
        raise ValueError("Invalid v value. Must be 27 or 28.")

    r_bytes = r.to_bytes(32, byteorder='big')
    s_bytes = s.to_bytes(32, byteorder='big')

    vs = bytearray(s_bytes)
    if vs[0] >> 7 == 1:
        raise ValueError("invalid signature 's' value")
    vs[0] |= (v % 27) << 7  # set the first bit of vs to the v parity bit
    return (r_bytes, bytes(vs))
