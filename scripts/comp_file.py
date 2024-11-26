import csv, os
from pathlib import Path

from brownie import *
from brownie import web3
from brownie import convert

from utils.comp_helpers import *
from utils.comp_print import *

def main():
    print('Script execution started...')
    print()

    AccountingOracle_HashConsensus = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
    oracle = Contract(AccountingOracle_HashConsensus)

    target_balance = "1 ether"
    filename = 'accrual_data.csv' # + тек дата время

    members_list = get_members_list(oracle)
    members_info = get_members_info(members_list, target_balance)
    print_members_info(members_info, 'All members')

    members_info_filtered = filter_members_info(members_info)

    if len(members_info_filtered) != 0:
        print_members_info(members_info_filtered, 'Filtered members')
        print('Write to file?')
        answer = input('Enter "yes" or "no": ').strip().lower()
        if answer == 'yes':
            write_to_file_accruals(filename, members_info_filtered)
        elif answer == 'no':
            print()
        else:
            print('Incorrect input')
    else:
        print('There are no users requiring fund accrual.')

    print('Script execution completed...')

# todo - посмотреть есть ли адрес hash consensus в proxy accounting oracle, поменять, если можно получить
# сделать выравнивание баланса по правому краю или точке (для эфиров)
# начислять по одному эфиру
