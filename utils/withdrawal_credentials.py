import os


ETH1_ADDRESS_WITHDRAWAL_PREFIX = '01'


def strip_byte_prefix(hexstr):
    return hexstr[2:] if hexstr[0:2] == '0x' else hexstr


def get_eth1_withdrawal_credentials(withdrawal_contract_address):
    return '0x' + ETH1_ADDRESS_WITHDRAWAL_PREFIX + '00' * 11 + strip_byte_prefix(withdrawal_contract_address)


def encode_set_withdrawal_credentials(withdrawal_credentials, lido):
    return (
        lido.address,
        lido.setWithdrawalCredentials.encode_input(withdrawal_credentials)
    )
