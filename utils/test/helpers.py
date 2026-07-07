import math

from hexbytes import HexBytes
from brownie import web3
from web3.types import BlockIdentifier  # type: ignore

from utils.config import contracts
from utils.evm_script import encode_error

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
GWEI = 10**9
ONE_ETH = 10**18
ZERO_HASH = bytes([0] * 32)
ZERO_BYTES32 = HexBytes(ZERO_HASH)


def ETH(amount):
    return math.floor(amount * 10**18)


def SHARES(amount):
    return ETH(amount)


def steth_balance(account):
    return contracts.lido.balanceOf(account)


def eth_balance(account: str, block_identifier: BlockIdentifier = "latest"):
    return web3.eth.get_balance(account, block_identifier=block_identifier)


def almostEqEth(b1, b2):
    return abs(b1 - b2) <= 10


def shares_balance(account):
    return contracts.lido.sharesOf(account)


def almostEqWithDiff(b1, b2, diff):
    return abs(b1 - b2) <= diff


def round_to_gwei(amount: int) -> int:
    """Round amount to gwei"""
    return amount // GWEI * GWEI


def access_control_unauthorized(account, role_name: str) -> str:
    """OZ v5 AccessControl revert: AccessControlUnauthorizedAccount(account, neededRole).
    To match the brownie decoder output the address must be lowercase (the decoder does
    not checksum it) and the role must be passed to encode_error as bytes."""
    address = str(getattr(account, "address", account)).lower()
    return encode_error(
        "AccessControlUnauthorizedAccount(address,bytes32)",
        [address, bytes(web3.keccak(text=role_name))],
    )
