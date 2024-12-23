from brownie import accounts, web3
from utils.test.helpers import ETH


def set_balance_in_wei(address, balance):
    account = accounts.at(address, force=True)
    providers = ["evm_setAccountBalance", "hardhat_setBalance", "anvil_setBalance"]

    for provider in providers:
        if account.balance() == balance:
            break

        try:
            web3.provider.make_request(provider, [address, hex(balance)])
        except ValueError as e:
            if e.args[0].get("message") != f"Method {provider} is not supported":
                raise e

    assert account.balance() == balance, f"FSB: EXP: {balance} ACT: {account.balance()} ADDR: {address}"
    return account


def set_balance(address, balanceInEth):
    balance = ETH(balanceInEth)

    return set_balance_in_wei(address, balance)
