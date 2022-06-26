import os
import sys

from typing import Any, Union, Optional, Dict

from utils.brownie_prelude import *

from brownie import network, accounts
from brownie.utils import color
from brownie.network.account import Account, LocalAccount


def network_name() -> Optional[str]:
    if network.show_active() is not None:
        return network.show_active()
    cli_args = sys.argv[1:]
    net_ind = next((cli_args.index(arg) for arg in cli_args if arg == '--network'), len(cli_args))

    net_name = None
    if net_ind != len(cli_args):
        net_name = cli_args[net_ind + 1]

    return net_name


if network_name() in ("goerli", "goerli-fork"):
    print(f'Using {color("cyan")}config_goerli.py{color} addresses')
    from utils.config_goerli import *
else:
    print(f'Using {color("magenta")}config_mainnet.py{color} addresses')
    from utils.config_mainnet import *


def get_is_live() -> bool:
    dev_networks = [
        "development",
        "hardhat",
        "hardhat-fork",
        "mainnet-fork",
        "goerli-fork"
    ]
    return network.show_active() not in dev_networks


def get_deployer_account() -> Union[LocalAccount, Account]:
    is_live = get_is_live()
    if is_live and 'DEPLOYER' not in os.environ:
        raise EnvironmentError(
            'Please set DEPLOYER env variable to the deployer account name')

    return accounts.load(os.environ['DEPLOYER']) if is_live else accounts.at(
        ldo_vote_executors_for_tests[0], force=True)


def prompt_bool() -> Optional[bool]:
    choice = input().lower()
    if choice in {'yes', 'y'}:
        return True
    elif choice in {'no', 'n'}:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")


def get_config_params() -> Dict[str, str]:
    if network_name in ("goerli", "goerli-fork"):
        import utils.config_goerli
        ret = {x: globals()[x] for x in dir(utils.config_goerli) if not x.startswith("__")}
    else:
        import utils.config_mainnet
        ret = {x: globals()[x] for x in dir(utils.config_mainnet) if not x.startswith("__")}
    return ret


class ContractsLazyLoader:
    @property
    def lido(self) -> interface.Lido:
        return interface.Lido(lido_dao_steth_address)

    @property
    def ldo_token(self) -> interface.MiniMeToken:
        return interface.MiniMeToken(ldo_token_address)

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
    def node_operators_registry(self) -> interface.NodeOperatorsRegistry:
        return interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    @property
    def lido_oracle(self) -> interface.LidoOracle:
        return interface.LidoOracle(lido_dao_oracle)

    @property
    def deposit_security_module(self) -> interface.DepositSecurityModule:
        return interface.DepositSecurityModule(lido_dao_deposit_security_module_address)

    @property
    def composite_post_rebase_beacon_receiver(self) -> interface.CompositePostRebaseBeaconReceiver:
        return interface.CompositePostRebaseBeaconReceiver(lido_dao_composite_post_rebase_beacon_receiver)

    @property
    def self_owned_steth_burner(self) -> interface.SelfOwnedStETHBurner:
        return interface.SelfOwnedStETHBurner(lido_dao_self_owned_steth_burner)

    @property
    def kernel(self) -> interface.Kernel:
        return interface.Kernel(lido_dao_kernel)

    @property
    def lido_app_repo(self) -> interface.Repo:
        return interface.Repo(lido_dao_lido_repo)

    @property
    def nos_app_repo(self) -> interface.Repo:
        return interface.Repo(lido_dao_node_operators_registry_repo)

    @property
    def voting_app_repo(self) -> interface.Repo:
        return interface.Repo(lido_dao_voting_repo)

    @property
    def oracle_app_repo(self) -> interface.Repo:
        return interface.Repo(lido_dao_oracle_repo)

    @property
    def easy_track(self) -> interface.EasyTrack:
        return interface.EasyTrack(lido_easytrack)


def __getattr__(name: str) -> Any:
    if name == "contracts":
        return ContractsLazyLoader()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
