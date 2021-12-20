import os
import sys

from typing import Any, Union, Optional

from utils.brownie_prelude import *

from brownie import network, accounts
from brownie.utils import color
from brownie.network.account import Account, LocalAccount

if network.show_active() == "goerli":
    print(f'Using {color("cyan")}config_goerli.py{color} addresses')
    from utils.config_goerli import *
else:
    print(f'Using {color("magenta")}config_mainnet.py{color} addresses')
    from utils.config_mainnet import *


def get_is_live() -> bool:
    return network.show_active() != 'development'


def get_deployer_account() -> Union[LocalAccount, Account]:
    is_live = get_is_live()
    if is_live and 'DEPLOYER' not in os.environ:
        raise EnvironmentError(
            'Please set DEPLOYER env variable to the deployer account name')

    return accounts.load(os.environ['DEPLOYER']) if is_live else accounts.at(
        "0x3e40d73eb977dc6a537af587d48316fee66e9c8c", force=True)


def prompt_bool() -> Optional[bool]:
    choice = input().lower()
    if choice in {'yes', 'y'}:
        return True
    elif choice in {'no', 'n'}:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")


class ContractsLazyLoader:
    @property
    def lido(self) -> interface.Lido:
        return interface.Lido(lido_dao_steth_address)

    @property
    def voting(self) -> interface.Voting:
        return interface.Voting(lido_dao_voting_address)

    @property
    def token_manager(self) -> interface.TokenManager:
        return interface.TokenManager(lido_dao_token_manager_address)

    @property
    def finance(self) -> interface.Finance:
        return interface.Finance(lido_dao_finance_address)

    @property
    def acl(self) -> interface.ACL:
        return interface.ACL(lido_dao_acl_address)

    @property
    def agent(self) -> interface.Agent:
        return interface.Agent(lido_dao_agent_address)

    @property
    def note_operators_registry(self) -> interface.NodeOperatorsRegistry:
        return interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    @property
    def kernel(self) -> interface.Kernel:
        return interface.Kernel(lido_dao_kernel)


def __getattr__(name: str) -> Any:
    if name == "contracts":
        return ContractsLazyLoader()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")