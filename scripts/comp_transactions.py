import csv, os
from pathlib import Path

from brownie import *
from brownie import web3
from brownie import convert

from brownie_safe import BrownieSafe

from utils.comp_helpers import *
from utils.comp_print import *

def main():

    print('Script execution started...')
    print()

    AccountingOracle_HashConsensus = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
    # получать адрес из метода getConsensusContract
    # https: // etherscan.io / address / 0x852deD011285fe67063a08005c71a85690503Cee  # readProxyContract#F14
    oracle = Contract(AccountingOracle_HashConsensus)

    target_balance = "1 ether"
    filename = 'accrual_data.csv'

    members_list = get_members_list(oracle)
    members_info = get_members_info(members_list, target_balance)
    print_members_info(members_info, 'All members')

    members_info_filtered = filter_members_info(members_info)

    # network.connect('mainnet')
    # safe = BrownieSafe('ychad.eth')  # ENS or Safe address

    wallet_address = "0x12a43b049A7D330cB8aEAB5113032D18AE9a9030"
    wallet_acc = accounts.at(wallet_address, force=True) # из тестов

    wallet_info = get_wallet_info(wallet_address)
    print_wallet_info(wallet_info)

    total_accrual_wei, total_accrual_eth = get_total_accrual(members_info_filtered)
    print_total_accrual(total_accrual_wei, total_accrual_eth)

    total_accrual_wei = 28910251107265401  # for tests

    try:
        if total_accrual_wei > wallet_info['wallet_balance_wei']:
            raise Exception(
                f"Insufficient funds for accrual, wallet balance - {wallet_info['wallet_balance_eth']}, needed - {total_accrual_eth}.")

    except Exception as e:
        print(f"Error massage: {e}")

    else:
        txns = create_transactions(members_info_filtered)
        print_txns(txns)

        print('Send transactions?')
        answer = input('Enter "yes" or "no": ').strip().lower()

        if answer == "yes":
            print("Sending transactions...")
            send_transactions(txns)
            print("Multicall transaction sent to fund accounts.")
            print('Script execution complete.')
        elif answer == "no":
            print("Sending transactions has been canceled.")
            print('Script execution was interrupted .')
        else:
            print("Incorrect input.")
