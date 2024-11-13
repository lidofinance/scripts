import csv
from brownie import *
from brownie import web3
from brownie import convert
from brownie_safe import BrownieSafe


def get_members_list(address):
    members_list = address.getMembers()[0]
    return members_list


def print_members_list(members_list):
    print("Members list:")
    for item in members_list:
        print(item, type(item))
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
    members_info_filtered = list(filter(lambda x: x["accrual_flag"], members_info))
    return members_info_filtered


def print_members_info(members_info, header):
    print(header + ":")
    for item in members_info:
        print(
            "address",
            item["address"],
            "balance_wei",
            item["balance_wei"],
            "balance_eth",
            item["balance_eth"],
            "accrual_flag",
            item["accrual_flag"],
            "accrual_wei",
            item["accrual_wei"],
            "accrual_eth",
            item["accrual_eth"],
        )
    print()


def get_wallet_info(wallet_address):
    wallet_balance_wei = get_balance_in_wei(wallet_address)
    wallet_balance_eth = wei_to_eth(wallet_balance_wei)
    wallet_info = {
        "wallet_address": wallet_address,
        "wallet_balance_wei": wallet_balance_wei,
        "wallet_balance_eth": wallet_balance_eth,
    }
    return wallet_info


def print_wallet_info(wallet_info):
    print("Wallet info:")
    print("- wallet address:", wallet_info["wallet_address"])
    print("- wallet balance in wei:", wallet_info["wallet_balance_wei"], type(wallet_info["wallet_balance_wei"]))
    print("- wallet balance in ETH:", wallet_info["wallet_balance_eth"], type(wallet_info["wallet_balance_eth"]))
    print()


def get_total_accrual(members_info):
    total_accrual_wei = Wei(sum(item["accrual_wei"] for item in members_info))
    total_accrual_eth = wei_to_eth(total_accrual_wei)
    return total_accrual_wei, total_accrual_eth


def print_total_accrual(total_accrual_wei, total_accrual_eth):
    print("Total accrual:")
    print("wei:", total_accrual_wei)
    print("eth:", total_accrual_eth)
    print()


def create_transactions(members_info):
    txns = []
    for item in members_info:
        tx = {
            "to": item["address"],
            "value": item["accrual_wei"],
            "data": b"",  # пустые данные для простой отправки эфира
            "gas": 21000,  # стандартный лимит газа для перевода эфира
        }
        txns.append(tx)
    return txns


def print_txns(txns):
    print("Transactions list:")
    for item in txns:
        print("to:", item["to"], "value:", item["value"], "data:", item["data"], "gas:", item["gas"])
    print()


def send_transactions(txns):
    """
    safe_tx = safe.multicall(txns)  # отправляем multisend транзакцию
    safe.preview(safe_tx)  # просмотр предварительного результата и оценка газа
    estimated_gas = safe.estimate_gas(safe_tx)
    print(f"Estimated Gas: {estimated_gas}")
    safe.post_transaction(safe_tx)  # Подписание и отправка транзакции
    """
    pass


def wei_to_eth(amount_wei):
    amount_eth = amount_wei.to("ether")
    return amount_eth


def get_balance_in_wei(address):
    balance = Wei(web3.eth.get_balance(address))
    return balance


def write_transactions_to_file(filename, members_info):
    field_names = ["token_type", "token_address", "receiver", "amount"]
    data = []
    for item in members_info:
        row = {"token_type": "native", "token_address": "", "receiver": item["address"], "amount": item["accrual_eth"]}
        data.append(row)
    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(data)
    print(f"CSV файл '{filename}' успешно создан с данными.")


def main():
    print("Script execution started.")

    AccountingOracle_HashConsensus = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
    oracle = Contract(AccountingOracle_HashConsensus)

    wallet_address = "0xFf64362EBf794a22A23E12666C4f875A31581fCe"
    target_balance = "1 ether"

    filename = "accrual_data.csv"

    # network.connect('mainnet')  # Убедитесь, что подключены к нужной сети
    """
    safe = BrownieSafe('ychad.eth')  # Укажите ваш ENS адрес или адрес Safe
    """

    members_list = get_members_list(oracle)
    print_members_list(members_list)

    members_info = get_members_info(members_list, target_balance)
    print_members_info(members_info, "All members")

    members_info_filtered = filter_members_info(members_info)
    print_members_info(members_info_filtered, "Filtered members")
    write_transactions_to_file(filename, members_info_filtered)

    wallet_info = get_wallet_info(wallet_address)
    print_wallet_info(wallet_info)

    total_accrual_wei, total_accrual_eth = get_total_accrual(members_info_filtered)
    print_total_accrual(total_accrual_wei, total_accrual_eth)

    total_accrual_wei = 28910251107265401

    try:
        if total_accrual_wei > wallet_info["wallet_balance_wei"]:
            raise Exception(
                f"Insufficient funds for accrual, wallet balance - {wallet_info['wallet_balance_eth']}, needed - {total_accrual_eth}."
            )

    except Exception as e:
        print(f"Сообщение об ошибке: {e}")

    else:
        txns = create_transactions(members_info_filtered)
        print_txns(txns)

        attempts = 0
        print("Send transactions?")

        while attempts < 3:
            answer = input('Enter "yes" or "no": ').strip().lower()

            if answer == "yes":
                print("Sending transactions...")
                send_transactions(txns)
                print("Multicall transaction sent to fund accounts.")
                print("Script execution complete.")
                break
            elif answer == "no":
                print("Sending transactions has been canceled.")
                print("Script execution was interrupted .")
                break
            else:
                print("Incorrect input.")
                attempts += 1

            if attempts == 3:
                print("Exceeded the number of input attempts.")
                print("Script execution was interrupted .")


# to do:
# - проверять, есть ли вообще кому начислять
# - выводить адрес конракта, по которому собираются пользователи
# - перевести все на английский язык
