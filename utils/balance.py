from brownie import accounts, web3
from utils.test.helpers import ETH


def set_balance_in_wei(address, balance):
    account = accounts.at(address, force=True)
    providers = ["evm_setAccountBalance", "hardhat_setBalance", "anvil_setBalance"]

    log_string = ""

    for provider in providers:
        if account.balance() == balance:
            break

        try:
            resp = web3.provider.make_request(provider, [address, hex(balance)])
            log_string += f"ERR1: {provider}: {resp}; "
        except ValueError as e:
            log_string += f"ERR12 {provider}: {e.args[0].get('message')}; "
            if e.args[0].get("message") != f"Method {provider} is not supported":
                raise e

    assert account.balance() == balance, f"FSB: EXP: {balance} ACT: {account.balance()} ADDR: {address}, ERR: {log_string}"
    return account


def set_balance(address, balanceInEth):
    balance = ETH(balanceInEth)

    return set_balance_in_wei(address, balance)
