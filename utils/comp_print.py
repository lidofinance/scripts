import csv, os
from pathlib import Path

from brownie import *
from brownie import web3
from brownie import convert

import utils.comp_helpers
from utils.comp_helpers import *

def print_members_info(members_info, header):
    column_names = ["#", "address", "balance_wei", "balance_eth", "accrual_flag", "accrual_wei", "accrual_eth"]
    column_widths = {col: len(col) for col in column_names}

    alignments = {
        "#": "ljust",
        "address": "ljust",
        "balance_wei": "rjust",
        "balance_eth": "rjust",
        "accrual_flag": "ljust",
        "accrual_wei": "rjust",
        "accrual_eth": "rjust",
    }

    for idx, item in enumerate(members_info, start=1):
        column_widths["#"] = max(column_widths["#"], len(str(idx)))
        for col in column_names[1:]:
            column_widths[col] = max(column_widths[col], len(str(item[col])))

    header_row = " | ".join(f"{col.ljust(column_widths[col])}" for col in column_names)
    separator_row = "-+-".join("-" * column_widths[col] for col in column_names)

    print(header + ":")
    print(header_row)
    print(separator_row)

    for idx, item in enumerate(members_info, start=1):
        row = (
            f"{str(idx).ljust(column_widths['#'])} | " + " | ".join(
            f"{str(item[col]).ljust(column_widths[col])}" if alignments[col] == "ljust"
            else f"{str(item[col]).rjust(column_widths[col])}"
            for col in column_names[1:]
        )
        )
        print(row)

    print()

def print_wallet_info(wallet_info):

    print('Wallet info:')
    print('- wallet address:', wallet_info['wallet_address'])
    print('- wallet balance in wei:', wallet_info['wallet_balance_wei'], type(wallet_info['wallet_balance_wei']))
    print('- wallet balance in ETH:', wallet_info['wallet_balance_eth'], type(wallet_info['wallet_balance_eth']))
    print()

def print_txns(txns):

    print('Transactions list:')
    for item in txns:
        print(
            'to:', item['to'],
            'value:', item['value'],
            'data:', item['data'],
            'gas:', item['gas']
        )
    print()

def print_total_accrual(total_accrual_wei, total_accrual_eth):

    print('Total accrual:')
    print('wei:', total_accrual_wei)
    print('eth:', total_accrual_eth)
    print()
