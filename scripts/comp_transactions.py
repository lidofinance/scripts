import csv, os
from pathlib import Path

from brownie import *
from brownie import web3
from brownie import convert

from brownie_safe import BrownieSafe

from utils.comp_helpers import *
from utils.comp_print import *

def main():
    print('Script execution has been started.')
    print()

    # I. Set values for variables
    wallet_address = "0x12a43b049A7D330cB8aEAB5113032D18AE9a9030"
    wallet_safe = BrownieSafe('0x12a43b049A7D330cB8aEAB5113032D18AE9a9030')

    threshold_balance = "1 ether"  # the Ether threshold value that triggers a decision to charge the user
    target_balance = "1 ether"  # the Ether amount up to which the accrual will be made
    target_accrual = "1 ether"  # the Ether amount for which the accrual will be made

    accounting_oracle_hash_consensus_expected = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"

    accounting_oracle_proxy = Contract("0x852deD011285fe67063a08005c71a85690503Cee")
    accounting_oracle_hash_consensus = Contract(accounting_oracle_proxy.getConsensusContract())

    if accounting_oracle_hash_consensus != accounting_oracle_hash_consensus_expected:
        print('AccountingOracle HashConsensus address has changed since the last script execution.')
        print('Please, make sure that the correct addresses are used.')

    # II. Collect members info
    print('Members info will be collected using')
    print('accounting_oracle_proxy:', accounting_oracle_proxy)
    print('accounting_oracle_hash_consensus:', accounting_oracle_hash_consensus)

    members_list = get_oracle_members_list(accounting_oracle_hash_consensus)
    members_info = get_oracle_members_info(members_list, threshold_balance=threshold_balance, target_accrual=target_accrual)
    print_members_info(members_info, 'All members')

    members_info_filtered = filter_members_info(members_info)

    # III. Сheck the need for a transfer
    if len(members_info_filtered) != 0:
        print_members_info(members_info_filtered, 'Filtered members')
    else:
        print('There are no users requiring fund accrual.')
        print('Script execution has been completed.')
        return 0

    # IV. Collect wallet info
    wallet_info = get_wallet_info(wallet_address)
    print_wallet_info(wallet_info)
    # wallet_account = accounts.at(wallet_address, force=True)

    total_accrual_wei, total_accrual_eth = get_total_accrual(members_info_filtered)
    print_total_accrual(total_accrual_wei, total_accrual_eth)

    total_accrual_wei = 28910251107265401  # for tests

    # V. Check wallet balance
    try:
        if total_accrual_wei > wallet_info['wallet_balance_wei']:
            raise Exception(
                f"Insufficient funds for accrual, wallet balance - {wallet_info['wallet_balance_eth']}, needed - {total_accrual_eth}.")
    except Exception as e:
        print(f"Error massage: {e}")

    # VI. Create and send transactions
    txns = create_transactions(members_info_filtered)
    print_txns(txns)

    print('Send transactions?')
    answer = input('Enter "yes" or "no": ').strip().lower()
    if answer == 'yes':
        print("Sending transactions...")
        send_transactions(txns)
        print("Multicall transaction sent to fund accounts.")
    elif answer == 'no':
        print("Sending transactions has been canceled.")
        print('Script execution was interrupted .')
        return 0
    else:
        print('Incorrect input')
        return 0

    print('Script execution has been completed.')
