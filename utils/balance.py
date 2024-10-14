from brownie import accounts, web3
from utils.test.helpers import ETH


def set_balance_in_wei(address, balance):
    account = accounts.at(address, force=True)

    if account.balance() != balance:
        # set balance for Ganache node
        web3.provider.make_request("evm_setAccountBalance", [address, hex(balance)])
        # set balance for Anvil and Hardhat nodes (https://book.getfoundry.sh/reference/anvil/#custom-methods)
        web3.provider.make_request("hardhat_setBalance", [address, hex(balance)])

    assert account.balance() == balance
    return account


def set_balance(address, balanceInEth):
    balance = ETH(balanceInEth)

    return set_balance_in_wei(address, balance)
