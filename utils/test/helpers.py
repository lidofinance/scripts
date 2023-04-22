import math
from brownie import web3  # type: ignore
from utils.config import (
    contracts,
)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def ETH(amount):
    return math.floor(amount * 10**18)


def SHARES(amount):
    return ETH(amount)


def steth_balance(account):
    return contracts.lido.balanceOf(account)


def eth_balance(account):
    return web3.eth.get_balance(account)


def almostEqEth(b1, b2):
    return abs(b1 - b2) <= 10


def shares_balance(account):
    return contracts.lido.sharesOf(account)


def almostEq(b1, b2, diff):
    return abs(b1 - b2) <= diff
