from brownie import accounts, web3
from utils.test.helpers import ETH

def set_balance(address, balanceInEth):
    account = accounts.at(address, force=True)
    balance = ETH(balanceInEth)

    if account.balance() != balance:
        # try Ganache
        try:
            web3.provider.make_request("evm_setAccountBalance", [address, hex(balance)])
        except:
            pass
    if account.balance() != balance:
         # try Anvil
        try:
            web3.provider.make_request("anvil_setBalance", [address, hex(balance)])
        except:
            pass

    assert account.balance() == ETH(balanceInEth)
    return account
