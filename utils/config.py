import os
import sys
from brownie import network, accounts

try:
    if network.show_active() == "goerli":
        raise ImportError
    from utils.config_mainnet import *
except ImportError:
    from utils.config_goerli import *


def get_is_live():
    return network.show_active() != 'development'


def get_deployer_account():
    is_live = get_is_live()
    if is_live and 'DEPLOYER' not in os.environ:
        raise EnvironmentError(
            'Please set DEPLOYER env variable to the deployer account name')

    return accounts.load(os.environ['DEPLOYER']) if is_live else accounts.at(
        "0xAD4f7415407B83a081A0Bee22D05A8FDC18B42da", force=True)


def prompt_bool():
    choice = input().lower()
    if choice in {'yes', 'y'}:
        return True
    elif choice in {'no', 'n'}:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")
