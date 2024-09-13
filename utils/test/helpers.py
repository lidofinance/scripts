import math

from hexbytes import HexBytes
from brownie import web3, accounts
from web3.types import BlockIdentifier  # type: ignore

from utils.config import contracts

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

# Required to top up contracts to be able to make transactions on london hardfork.
def topped_up_contract(address):
    contract = accounts.at(address, force=True)
    web3.provider.make_request("evm_setAccountBalance", [contract.address, "0x152D02C7E14AF6800000"])
    web3.provider.make_request("hardhat_setBalance", [contract.address, "0x152D02C7E14AF6800000"])
    assert contract.balance() == ETH(100000)
    return contract
