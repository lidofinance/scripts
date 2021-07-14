import os


ETH1_ADDRESS_WITHDRAWAL_PREFIX = '01'


def strip_byte_prefix(hexstr):
    return hexstr[2:] if hexstr[0:2] == '0x' else hexstr


def get_eth1_withdrawal_credentials(withdrawal_contract_address):
    wc = '0x' + ETH1_ADDRESS_WITHDRAWAL_PREFIX + '00' * 11 + strip_byte_prefix(withdrawal_contract_address)
    return wc.lower()


def encode_set_withdrawal_credentials(withdrawal_credentials, lido):
    return (
        lido.address,
        lido.setWithdrawalCredentials.encode_input(withdrawal_credentials)
    )


def extract_address_from_eth1_wc(withdrawal_credentials):
    striped_wc = strip_byte_prefix(withdrawal_credentials)

    if len(striped_wc) != 64:
        raise Exception('withdrawal_contract has a not valid length')

    prefix = striped_wc[0:2]
    zero_pad = striped_wc[2:24]
    address = striped_wc[24:]

    if prefix != '01':
        raise Exception('withdrawal_contract has not valid eth1 prefix')

    if zero_pad != '0000000000000000000000':
        raise Exception('withdrawal_contract has not valid zero_pad')

    return '0x' + address


def colorize_withdrawal_credentials(withdrawal_credentials):
    byte_prefix = withdrawal_credentials[:2]
    prefix = withdrawal_credentials[2:4]
    zero_pad = withdrawal_credentials[4:26]
    address = withdrawal_credentials[26:]

    hl_color = '\x1b[38;5;141m'
    yellow_color = '\x1b[0;33m'
    gray_color = '\x1b[0;m'
    end_of_color = '\033[0m'

    return f'{hl_color}{byte_prefix}{yellow_color}{prefix}{gray_color}{zero_pad}{hl_color}{address}{end_of_color}'

