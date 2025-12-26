from brownie import accounts, web3
from utils.test.helpers import ETH


def set_balance_in_wei(address, balance):
    # Accept both a plain address string and a Brownie Account object
    address_str = address.address if hasattr(address, "address") else address

    account = accounts.at(address_str, force=True)
    providers = ["evm_setAccountBalance", "hardhat_setBalance", "anvil_setBalance"]

    for provider in providers:
        if account.balance() == balance:
            break

        try:
            web3.provider.make_request(provider, [address_str, hex(balance)])
        except ValueError as e:
            if e.args[0].get("message") != f"Method {provider} is not supported":
                raise e

    assert account.balance() == balance, f"Failed to set balance {balance} for account: {address_str}"
    return account


def set_balance(address, balanceInEth):
    balance = ETH(balanceInEth)

    return set_balance_in_wei(address, balance)