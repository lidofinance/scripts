import csv, os
from pathlib import Path
from brownie import *
from brownie import web3
from brownie import convert
from brownie_safe import BrownieSafe


def get_members_list(address):
    members_list = address.getMembers()[0]
    return members_list

def print_members_list(members_list):
    print('Members list:')
    for item in members_list:
        print(item, type(item))
    print('Users count: ', len(members_list))
    print()

def get_members_info(members_list, target_balance):
    members_info = []
    for item in members_list:
        balance_wei = get_balance_in_wei(item)
        balance_eth = wei_to_eth(balance_wei)
        accrual_flag = balance_wei < target_balance
        accrual_wei = 0
        if accrual_flag:
            accrual_wei = Wei(target_balance) - balance_wei
        accrual_eth = wei_to_eth(Wei(accrual_wei))
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

def print_members_info(members_info, header):

    column_names = ["address", "balance_wei", "balance_eth", "accrual_flag", "accrual_wei", "accrual_eth"]
    column_widths = {col: len(col) for col in column_names}

    for item in members_info:
        for col in column_names:
            column_widths[col] = max(column_widths[col], len(str(item[col])))

    header_row = " | ".join(f"{col.ljust(column_widths[col])}" for col in column_names)
    separator_row = "-+-".join("-" * column_widths[col] for col in column_names)

    print(header + ":")
    print(header_row)
    print(separator_row)

    for item in members_info:
        row = " | ".join(f"{str(item[col]).ljust(column_widths[col])}" for col in column_names)
        print(row)

    print()

def get_wallet_info(wallet_address):
    wallet_balance_wei = get_balance_in_wei(wallet_address)
    wallet_balance_eth = wei_to_eth(wallet_balance_wei)
    wallet_info = {
        "wallet_address":wallet_address,
        "wallet_balance_wei": wallet_balance_wei,
        "wallet_balance_eth":wallet_balance_eth
    }
    return wallet_info

def print_wallet_info(wallet_info):
    print('Wallet info:')
    print('- wallet address:', wallet_info['wallet_address'])
    print('- wallet balance in wei:', wallet_info['wallet_balance_wei'], type(wallet_info['wallet_balance_wei']))
    print('- wallet balance in ETH:', wallet_info['wallet_balance_eth'], type(wallet_info['wallet_balance_eth']))
    print()

def get_total_accrual(members_info):
    total_accrual_wei = Wei(sum(item['accrual_wei'] for item in members_info))
    total_accrual_eth = wei_to_eth(total_accrual_wei)
    return total_accrual_wei, total_accrual_eth

def print_total_accrual(total_accrual_wei, total_accrual_eth):
    print('Total accrual:')
    print('wei:', total_accrual_wei)
    print('eth:', total_accrual_eth)
    print()

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

def write_to_file_accruals(filename, members_info):
    field_names = ["token_type", "token_address", "receiver", "amount"]
    data = []
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
    print(f"Absolute path: {file_path}")
    print(f"Clickable link: {file_link}")
    print()

def main():
    print('Script execution started...')
    print()

    AccountingOracle_HashConsensus = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
    oracle = Contract(AccountingOracle_HashConsensus)

    wallet_address = "0x12a43b049A7D330cB8aEAB5113032D18AE9a9030"
    target_balance = "1 ether"

    filename = 'accrual_data.csv'

    # network.connect('mainnet')
    # safe = BrownieSafe('ychad.eth')  # ENS or Safe address

    members_list = get_members_list(oracle)
    print_members_list(members_list)

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

    wallet_info = get_wallet_info(wallet_address)
    print_wallet_info(wallet_info)

    total_accrual_wei, total_accrual_eth = get_total_accrual(members_info_filtered)
    print_total_accrual(total_accrual_wei, total_accrual_eth)

    total_accrual_wei = 28910251107265401 # for tests

    try:
        if total_accrual_wei > wallet_info['wallet_balance_wei']:
            raise Exception(
                f"Insufficient funds for accrual, wallet balance - {wallet_info['wallet_balance_eth']}, needed - {total_accrual_eth}.")

    except Exception as e:
        print(f"Error massage: {e}")

    else:
        txns = create_transactions(members_info_filtered)
        print_txns(txns)

        attempts = 0
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
