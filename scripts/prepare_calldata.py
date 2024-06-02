import csv
from brownie import Contract

def read_csv_data(filename):
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"', skipinitialspace=True)
        return list(reader)

def read_csv_purchasers(filename):
    data = [ {'operator':item[1], 'uri':item[2], 'description': item[3],'is_mandatory': bool(item[4]) } for item in read_csv_data(filename)]
    return data[2:]

def main():
    relay_list = read_csv_purchasers("RMC Onchain Tx #1 - Sheet1.csv")
    relay_list_contract = Contract.from_explorer('0xF95f069F9AD107938F6ba802a3da87892298610E')
    for relay in relay_list:
        print(relay_list_contract.add_relay.encode_input(relay['uri'], relay['operator'], relay['is_mandatory'], relay['description']))