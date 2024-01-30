import os
import sys

from typing import Any, Union, Optional, Dict, Tuple

from utils.brownie_prelude import *

from brownie import network, accounts
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
        return "300 gwei"


def get_deployer_account() -> Union[LocalAccount, Account]:
    is_live = get_is_live()
    if is_live and "DEPLOYER" not in os.environ:
        raise EnvironmentError("Please set DEPLOYER env variable to the deployer account name")

    return accounts.load(os.environ["DEPLOYER"]) if (is_live or "DEPLOYER" in os.environ) else accounts[4]


def get_web3_storage_token() -> str:
    is_live = get_is_live()
    if is_live and "WEB3_STORAGE_TOKEN" not in os.environ:
        raise EnvironmentError(
            "Please set WEB3_STORAGE_TOKEN env variable to the web3.storage API token to be able to "
            "upload the vote description to IPFS by calling upload_vote_ipfs_description. Alternatively, "
            "you can only calculate cid without uploading to IPFS by calling calculate_vote_ipfs_description"
        )

    return os.environ["WEB3_STORAGE_TOKEN"] if (is_live or "WEB3_STORAGE_TOKEN" in os.environ) else ""


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
        import configs.config_goerli

        ret = {x: globals()[x] for x in dir(configs.config_goerli) if not x.startswith("__")}
    else:
        import configs.config_mainnet

        ret = {x: globals()[x] for x in dir(configs.config_mainnet) if not x.startswith("__")}
    return ret


class ContractsLazyLoader:
    @property
    def lido_v1(self) -> interface.LidoV1:
        return interface.LidoV1(LIDO)

    @property
    def lido(self) -> interface.Lido:
        return interface.Lido(LIDO)

    @property
    def ldo_token(self) -> interface.MiniMeToken:
        return interface.MiniMeToken(LDO_TOKEN)

    @property
    def voting(self) -> interface.Voting:
        return interface.Voting(VOTING)

    @property
    def token_manager(self) -> interface.TokenManager:
        return interface.TokenManager(TOKEN_MANAGER)

    @property
    def finance(self) -> interface.Finance:
        return interface.Finance(FINANCE)

    @property
    def acl(self) -> interface.ACL:
        return interface.ACL(ACL)

    @property
    def agent(self) -> interface.Agent:
        return interface.Agent(AGENT)

    @property
    def node_operators_registry(self) -> interface.NodeOperatorsRegistry:
        return interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)

    @property
    def simple_dvt(self) -> interface.NodeOperatorsRegistry:
        return interface.NodeOperatorsRegistry(SIMPLE_DVT)

    @property
    def legacy_oracle(self) -> interface.LegacyOracle:
        return interface.LegacyOracle(LEGACY_ORACLE)

    @property
    def deposit_security_module_v1(self) -> interface.DepositSecurityModule:
        return interface.DepositSecurityModuleV1(DEPOSIT_SECURITY_MODULE_V1)

    @property
    def deposit_security_module(self) -> interface.DepositSecurityModule:
        return interface.DepositSecurityModule(DEPOSIT_SECURITY_MODULE)

    @property
    def burner(self) -> interface.Burner:
        return interface.Burner(BURNER)

    @property
    def execution_layer_rewards_vault(self) -> interface.LidoExecutionLayerRewardsVault:
        return interface.LidoExecutionLayerRewardsVault(EXECUTION_LAYER_REWARDS_VAULT)

    @property
    def hash_consensus_for_accounting_oracle(self) -> interface.HashConsensus:
        return interface.HashConsensus(HASH_CONSENSUS_FOR_AO)

    @property
    def accounting_oracle(self) -> interface.AccountingOracle:
        return interface.AccountingOracle(ACCOUNTING_ORACLE)

    @property
    def hash_consensus_for_validators_exit_bus_oracle(self) -> interface.HashConsensus:
        return interface.HashConsensus(HASH_CONSENSUS_FOR_VEBO)

    @property
    def validators_exit_bus_oracle(self) -> interface.ValidatorsExitBusOracle:
        return interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE)

    @property
    def oracle_report_sanity_checker(self) -> interface.OracleReportSanityChecker:
        return interface.OracleReportSanityChecker(ORACLE_REPORT_SANITY_CHECKER)

    @property
    def withdrawal_queue(self) -> interface.WithdrawalQueueERC721:
        return interface.WithdrawalQueueERC721(WITHDRAWAL_QUEUE)

    @property
    def lido_locator(self) -> interface.LidoLocator:
        return interface.LidoLocator(LIDO_LOCATOR)

    @property
    def eip712_steth(self) -> interface.EIP712StETH:
        return interface.EIP712StETH(EIP712_STETH)

    @property
    def withdrawal_vault(self) -> interface.WithdrawalVault:
        return interface.WithdrawalVault(WITHDRAWAL_VAULT)

    @property
    def staking_router(self) -> interface.StakingRouter:
        return interface.StakingRouter(STAKING_ROUTER)

    @property
    def kernel(self) -> interface.Kernel:
        return interface.Kernel(ARAGON_KERNEL)

    @property
    def lido_app_repo(self) -> interface.Repo:
        return interface.Repo(LIDO_REPO)

    @property
    def nor_app_repo(self) -> interface.Repo:
        return interface.Repo(NODE_OPERATORS_REGISTRY_REPO)

    @property
    def voting_app_repo(self) -> interface.Repo:
        return interface.Repo(VOTING_REPO)

    @property
    def oracle_app_repo(self) -> interface.Repo:
        return interface.Repo(LEGACY_ORACLE_REPO)

    @property
    def easy_track(self) -> interface.EasyTrack:
        return interface.EasyTrack(EASYTRACK)

    @property
    def relay_allowed_list(self) -> interface.MEVBoostRelayAllowedList:
        return interface.MEVBoostRelayAllowedList(RELAY_ALLOWED_LIST)

    @property
    def dai_token(self) -> interface.ERC20:
        return interface.ERC20(DAI_TOKEN)

    @property
    def usdt_token(self) -> interface.ERC20:
        return interface.ERC20(USDT_TOKEN)

    @property
    def usdc_token(self) -> interface.ERC20:
        return interface.ERC20(USDC_TOKEN)

    @property
    def weth_token(self) -> interface.WethToken:
        return interface.WethToken(WETH_TOKEN)

    @property
    def oracle_daemon_config(self) -> interface.OracleDaemonConfig:
        return interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)

    @property
    def wsteth(self) -> interface.WstETH:
        return interface.WstETH(WSTETH_TOKEN)

    @property
    def gate_seal(self) -> interface.GateSeal:
        return interface.GateSeal(GATE_SEAL)

    @property
    def evm_script_registry(self) -> interface.EVMScriptRegistry:
        return interface.EVMScriptRegistry(ARAGON_EVMSCRIPT_REGISTRY)

    @property
    def insurance_fund(self) -> interface.InsuranceFund:
        return interface.InsuranceFund(INSURANCE_FUND)

    @property
    def anchor_vault(self) -> interface.InsuranceFund:
        return interface.AnchorVault(ANCHOR_VAULT_PROXY)

    @property
    def anchor_vault_proxy(self) -> interface.InsuranceFund:
        return interface.AnchorVaultProxy(ANCHOR_VAULT_PROXY)


def __getattr__(name: str) -> Any:
    if name == "contracts":
        return ContractsLazyLoader()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
