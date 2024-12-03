import csv, os
from datetime import datetime
from pathlib import Path

from brownie import *
from brownie import web3
from brownie import convert

from utils.comp_helpers import *
from utils.comp_print import *

def main():
    print('Script execution has been started.')
    print()

    # I. Set values for variables
    threshold_balance = "1 ether"  # the Ether threshold value that triggers a decision to charge the user
    target_balance = "1 ether"  # the Ether amount up to which the accrual will be made
    target_accrual = "1 ether"  # the Ether amount for which the accrual will be made

    accounting_oracle_hash_consensus_expected = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"

    accounting_oracle_proxy = Contract("0x852deD011285fe67063a08005c71a85690503Cee")
    accounting_oracle_hash_consensus = Contract(accounting_oracle_proxy.getConsensusContract())

    if accounting_oracle_hash_consensus!=accounting_oracle_hash_consensus_expected:
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

    # IV. Write info to file
    print('Write to file?')
    answer = input('Enter "yes" or "no": ').strip().lower()
    if answer == 'yes':
        write_to_file_accruals(members_info_filtered)
    elif answer == 'no':
        print()
    else:
        print('Incorrect input')

    print('Script execution has been completed.')
