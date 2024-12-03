import csv, os
from datetime import datetime
from pathlib import Path

from brownie import *
from brownie import web3
from brownie import convert

from utils.comp_print import *

def get_oracle_members_list(address):
    members_list = address.getMembers()[0]
    return members_list

def get_oracle_members_info(members_list, threshold_balance, target_balance=None, target_accrual=None):

    if target_balance is None and target_accrual is None:
        raise ValueError("You must provide either 'target_balance' or 'target_accrual'.")

    members_info = []
    for item in members_list:

        balance_wei = get_balance_in_wei(item)
        balance_eth = wei_to_eth(balance_wei)

        accrual_flag = balance_wei < Wei(threshold_balance)

        accrual_wei = (
            Wei(target_balance)-balance_wei if accrual_flag and target_balance is not None and balance_wei < target_balance
            else Wei(target_accrual) if accrual_flag and target_accrual is not None
            else 0
        )
        accrual_eth = (
            wei_to_eth(Wei(accrual_wei)) if accrual_wei
            else 0
        )

        members_info.append(
            {
                "address": item,
                "balance_wei": balance_wei,
                "balance_eth": balance_eth,
                "accrual_flag": accrual_flag,
                "accrual_wei": accrual_wei,
                "accrual_eth": accrual_eth,
            }
        )

    return members_info

def filter_members_info(members_info):
    members_info_filtered = list(filter(lambda x: x['accrual_flag'], members_info))
    return members_info_filtered

def get_wallet_info(wallet_address):
    wallet_balance_wei = get_balance_in_wei(wallet_address)
    wallet_balance_eth = wei_to_eth(wallet_balance_wei)
    wallet_info = {
        "wallet_address":wallet_address,
        "wallet_balance_wei": wallet_balance_wei,
        "wallet_balance_eth":wallet_balance_eth
    }
    return wallet_info

def get_total_accrual(members_info):
    total_accrual_wei = Wei(sum(item['accrual_wei'] for item in members_info))
    total_accrual_eth = wei_to_eth(total_accrual_wei)
    return total_accrual_wei, total_accrual_eth

def create_transactions(members_info):
    txns = []
    for item in members_info:
        tx = {
            'to': item['address'],
            'value': item['accrual_wei'],
            'data': b'',
            'gas': 21000
        }
        txns.append(tx)
    return txns

def send_transactions(txns):
    '''
    safe_tx = safe.multicall(txns)  # send multisend transaction
    safe.preview(safe_tx)  # preview and gas esteem
    estimated_gas = safe.estimate_gas(safe_tx)
    print(f"Estimated Gas: {estimated_gas}")
    safe.post_transaction(safe_tx)  # signing and sending transaction
    '''
    pass

def wei_to_eth(amount_wei):
    amount_eth = amount_wei.to("ether")
    return amount_eth

def get_balance_in_wei(address):
    balance = Wei(web3.eth.get_balance(address))
    return balance

def write_to_file_accruals(members_info):

    current_date_iso_format = datetime.now().isoformat()
    filename = "oracle_members_accrual_data_" + str(current_date_iso_format) + ".csv"

    data = []

    field_names = ["token_type",
                   "token_address",
                   "receiver",
                   "amount"
                   ]

    for item in members_info:
        row = {
            "token_type": "native",
            "token_address": "",
            "receiver": item['address'],
            "amount": item['accrual_eth']
        }
        data.append(row)

    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(data)

    print(f"A CSV-file has been created: '{filename}'")
    file_path = Path(filename).resolve()
    if not file_path.is_file():
        print(f"File '{filename}' does not exist.")
        return
    file_link = f"file://{file_path}"
    print(f"Path: {file_path}")
    print(f"Link: {file_link}")
    print()
