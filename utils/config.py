import os
import sys

from brownie import network, accounts
from brownie.utils import color

if network.show_active() == "goerli":
    print(f'Using {color("cyan")}config_goerli.py{color} addresses')
    from utils.config_goerli import *
else:
    print(f'Using {color("magenta")}config_mainnet.py{color} addresses')
    from utils.config_mainnet import *


def get_is_live():
    return network.show_active() != 'development'


def get_deployer_account():
    is_live = get_is_live()
    if is_live and 'DEPLOYER' not in os.environ:
        raise EnvironmentError(
            'Please set DEPLOYER env variable to the deployer account name')

    return accounts.load(os.environ['DEPLOYER']) if is_live else accounts.at(
        "0x3e40d73eb977dc6a537af587d48316fee66e9c8c", force=True)


def prompt_bool():
    choice = input().lower()
    if choice in {'yes', 'y'}:
        return True
    elif choice in {'no', 'n'}:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")
