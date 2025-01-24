from brownie import accounts, web3
import time
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

    if account.balance() != balance:
        time.sleep(2)

    if account.balance() != balance:
        web3.provider.make_request("evm_mine", [{blocks: 5}])

    if account.balance() != balance:
        time.sleep(2)

    if account.balance() < balance:
        eth_whale = accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)
        eth_whale.transfer(account, balance - account.balance())

    if account.balance() != balance:
        time.sleep(2)

    assert account.balance() == balance, f"Failed to set balance {balance} for account: {address}"
    return account


def set_balance(address, balanceInEth):
    balance = ETH(balanceInEth)

    return set_balance_in_wei(address, balance)
