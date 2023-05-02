import os
import sys

from typing import Any, Union, Optional, Dict

from utils.brownie_prelude import *

from brownie import network, accounts, ShapellaUpgradeTemplate
from brownie.utils import color
from brownie.network.account import Account, LocalAccount


MAINNET_VOTE_DURATION = 3 * 24 * 60 * 60


def network_name() -> Optional[str]:
    if network.show_active() is not None:
        return network.show_active()
    cli_args = sys.argv[1:]
    net_ind = next((cli_args.index(arg) for arg in cli_args if arg == "--network"), len(cli_args))

    net_name = None
    if net_ind != len(cli_args):
        net_name = cli_args[net_ind + 1]

    return net_name


if network_name() in ("goerli", "goerli-fork"):
    print(f'Using {color("cyan")}config_goerli.py{color} addresses')
    from configs.config_goerli import *
else:
    print(f'Using {color("magenta")}config_mainnet.py{color} addresses')
    from configs.config_mainnet import *

    print(f'Using {color("magenta")}config_shapella_addresses_mainnet.py{color} addresses')
    from configs.config_shapella_addresses_mainnet import *

    print(f'Using {color("magenta")}config_shapella_other_mainnet.py{color} values')
    from configs.config_shapella_other_mainnet import *


def get_is_live() -> bool:
    dev_networks = ["development", "hardhat", "hardhat-fork", "goerli-fork", "local-fork", "mainnet-fork"]
    return network.show_active() not in dev_networks


def get_priority_fee() -> str:
    if "OMNIBUS_PRIORITY_FEE" in os.environ:
        return os.environ["OMNIBUS_PRIORITY_FEE"]
    else:
        return "2 gwei"


def get_max_fee() -> str:
    if "OMNIBUS_MAX_FEE" in os.environ:
        return os.environ["OMNIBUS_MAX_FEE"]
    else:
        return "100 gwei"


def get_deployer_account() -> Union[LocalAccount, Account]:
    is_live = get_is_live()
    if is_live and "DEPLOYER" not in os.environ:
        raise EnvironmentError("Please set DEPLOYER env variable to the deployer account name")

    return (
        accounts.load(os.environ["DEPLOYER"]) if os.environ["DEPLOYER"] else accounts.at(ldo_vote_executors_for_tests[0], force=True)
    )


def prompt_bool() -> Optional[bool]:
    choice = input().lower()
    if choice in {"yes", "y"}:
        return True
    elif choice in {"no", "n"}:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")


def get_config_params() -> Dict[str, str]:
    if network_name() in ("goerli", "goerli-fork"):
        import utils.config_goerli

        ret = {x: globals()[x] for x in dir(utils.config_goerli) if not x.startswith("__")}
    else:
        import utils.config_mainnet

        ret = {x: globals()[x] for x in dir(utils.config_mainnet) if not x.startswith("__")}
    return ret


class ContractsLazyLoader:
    @property
    def lido_v1(self) -> interface.LidoV1:
        return interface.LidoV1(lido_dao_steth_address)

    @property
    def node_operators_registry_v1(self) -> interface.NodeOperatorsRegistryV1:
        return interface.NodeOperatorsRegistryV1(lido_dao_node_operators_registry)

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
    def legacy_oracle(self) -> interface.LegacyOracle:
        return interface.LegacyOracle(lido_dao_legacy_oracle)

    @property
    def deposit_security_module_v1(self) -> interface.DepositSecurityModule:
        return interface.DepositSecurityModuleV1(lido_dao_deposit_security_module_address_v1)

    @property
    def deposit_security_module(self) -> interface.DepositSecurityModule:
        return interface.DepositSecurityModule(lido_dao_deposit_security_module_address)

    @property
    def burner(self) -> interface.Burner:
        return interface.Burner(lido_dao_burner)

    @property
    def execution_layer_rewards_vault(self) -> interface.LidoExecutionLayerRewardsVault:
        return interface.LidoExecutionLayerRewardsVault(lido_dao_execution_layer_rewards_vault)

    @property
    def hash_consensus_for_accounting_oracle(self) -> interface.HashConsensus:
        return interface.HashConsensus(lido_dao_hash_consensus_for_accounting_oracle)

    @property
    def accounting_oracle(self) -> interface.AccountingOracle:
        return interface.AccountingOracle(lido_dao_accounting_oracle)

    @property
    def hash_consensus_for_validators_exit_bus_oracle(self) -> interface.HashConsensus:
        return interface.HashConsensus(lido_dao_hash_consensus_for_validators_exit_bus_oracle)

    @property
    def validators_exit_bus_oracle(self) -> interface.ValidatorsExitBusOracle:
        return interface.ValidatorsExitBusOracle(lido_dao_validators_exit_bus_oracle)

    @property
    def oracle_report_sanity_checker(self) -> interface.OracleReportSanityChecker:
        return interface.OracleReportSanityChecker(lido_dao_oracle_report_sanity_checker)

    @property
    def withdrawal_queue(self) -> interface.WithdrawalQueueERC721:
        return interface.WithdrawalQueueERC721(lido_dao_withdrawal_queue)

    @property
    def lido_locator(self) -> interface.LidoLocator:
        return interface.LidoLocator(lido_dao_lido_locator)

    @property
    def eip712_steth(self) -> interface.EIP712StETH:
        return interface.EIP712StETH(lido_dao_eip712_steth)

    @property
    def withdrawal_vault(self) -> interface.WithdrawalVault:
        return interface.WithdrawalVault(lido_dao_withdrawal_vault)

    @property
    def staking_router(self) -> interface.StakingRouter:
        return interface.StakingRouter(lido_dao_staking_router)

    @property
    def kernel(self) -> interface.Kernel:
        return interface.Kernel(lido_dao_kernel)

    @property
    def lido_app_repo(self) -> interface.Repo:
        return interface.Repo(lido_dao_lido_repo)

    @property
    def nor_app_repo(self) -> interface.Repo:
        return interface.Repo(lido_dao_node_operators_registry_repo)

    @property
    def voting_app_repo(self) -> interface.Repo:
        return interface.Repo(lido_dao_voting_repo)

    @property
    def oracle_app_repo(self) -> interface.Repo:
        return interface.Repo(lido_dao_legacy_oracle_repo)

    @property
    def easy_track(self) -> interface.EasyTrack:
        return interface.EasyTrack(lido_easytrack)

    @property
    def relay_allowed_list(self) -> interface.MEVBoostRelayAllowedList:
        return interface.MEVBoostRelayAllowedList(lido_relay_allowed_list)

    @property
    def dai_token(self) -> interface.ERC20:
        return interface.ERC20(dai_token_address)

    @property
    def weth_token(self) -> interface.WethToken:
        return interface.WethToken(weth_token_address)

    @property
    def oracle_daemon_config(self) -> interface.OracleDaemonConfig:
        return interface.OracleDaemonConfig(oracle_daemon_config)

    @property
    def wsteth(self) -> interface.WstETH:
        return interface.WstETH(wsteth_token_address)

    @property
    def gate_seal(self) -> interface.GateSeal:
        return interface.GateSeal(gate_seal_address)

    @property
    def shapella_upgrade_template(self) -> ShapellaUpgradeTemplate:
        return ShapellaUpgradeTemplate.at(lido_dao_template_address)


def __getattr__(name: str) -> Any:
    if name == "contracts":
        return ContractsLazyLoader()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
