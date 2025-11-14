import os
import sys

from typing import Any, Union, Optional, Dict, Tuple

from utils.brownie_prelude import *
from brownie import network, accounts
from brownie.utils import color
from brownie.network.account import Account, LocalAccount

from brownie import Contract, web3


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
elif network_name() in ("holesky", "holesky-fork"):
    print(f'Using {color("cyan")}config_holesky.py{color} addresses')
    from configs.config_holesky import *
elif network_name() in ("sepolia", "sepolia-fork"):
    print(f'Using {color("yellow")}config_sepolia.py{color} addresses')
    from configs.config_sepolia import *
elif network_name() in ("hoodi", "hoodi-fork"):
    print(f'Using {color("cyan")}config_hoodi.py{color} addresses')
    from configs.config_hoodi import *
else:
    print(f'Using {color("magenta")}config_mainnet.py{color} addresses')
    from configs.config_mainnet import *


def get_vote_duration() -> int:
    """
    Get the vote duration in seconds.
    """
    voting = interface.Voting(VOTING)
    return voting.voteTime()


def get_is_live() -> bool:
    dev_networks = [
        "development",
        "hardhat",
        "hardhat-fork",
        "goerli-fork",
        "local-fork",
        "mainnet-fork",
        "mfh-1",
        "mfh-2",
        "mfh-3",
        "holesky-fork",
        "sepolia-fork",
        "hoodi-fork",
    ]
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


def local_deployer() -> LocalAccount:
    """
    Local deployer can ONLY be used for the local run.
    """
    deployer = accounts[4]
    agent = accounts.at(AGENT, force=True)

    if web3.eth.get_balance(agent.address) < 10 * 10**18:
        from utils.balance import set_balance

        set_balance(agent.address, 10)

    interface.MiniMeToken(LDO_TOKEN).transfer(deployer, 10**18, {"from": agent})
    return deployer


def get_deployer_account() -> Union[LocalAccount, Account]:
    is_live = get_is_live()

    if is_live:
        deployer = os.environ.get("DEPLOYER")
        if deployer is None:
            raise EnvironmentError("For live deployment please set DEPLOYER env variable to the deployer account name")
        return accounts.load(deployer)

    return local_deployer()


def get_web3_storage_token(silent=False) -> str:
    is_live = get_is_live()
    if is_live and not silent and "WEB3_STORAGE_TOKEN" not in os.environ:
        raise EnvironmentError(
            "Please set WEB3_STORAGE_TOKEN env variable to the web3.storage API token to be able to "
            "upload the vote description to IPFS by calling upload_vote_ipfs_description. Alternatively, "
            "you can only calculate cid without uploading to IPFS by calling calculate_vote_ipfs_description"
        )

    return os.environ["WEB3_STORAGE_TOKEN"] if (is_live or "WEB3_STORAGE_TOKEN" in os.environ) else ""


def get_pinata_cloud_token(silent=False) -> str:
    is_live = get_is_live()
    if is_live and not silent and "PINATA_CLOUD_TOKEN" not in os.environ:
        raise EnvironmentError(
            "Please set PINATA_CLOUD_TOKEN env variable to the pinata.cloud API token to be able to "
            "upload the vote description to IPFS by calling upload_vote_ipfs_description. Alternatively, "
            "you can only calculate cid without uploading to IPFS by calling calculate_vote_ipfs_description"
        )

    return os.environ["PINATA_CLOUD_TOKEN"] if (is_live or "PINATA_CLOUD_TOKEN" in os.environ) else ""


def get_infura_io_keys(silent=False) -> Tuple[str, str]:
    is_live = get_is_live()
    if (
        is_live
        and not silent
        and ("WEB3_INFURA_IPFS_PROJECT_ID" not in os.environ or "WEB3_INFURA_IPFS_PROJECT_SECRET" not in os.environ)
    ):
        raise EnvironmentError(
            "Please set WEB3_INFURA_IPFS_PROJECT_ID and WEB3_INFURA_IPFS_PROJECT_SECRET env variable "
            "to the web3.storage api token"
        )
    project_id = (
        os.environ["WEB3_INFURA_IPFS_PROJECT_ID"] if (is_live or "WEB3_INFURA_IPFS_PROJECT_ID" in os.environ) else ""
    )
    project_secret = (
        os.environ["WEB3_INFURA_IPFS_PROJECT_SECRET"]
        if (is_live or "WEB3_INFURA_IPFS_PROJECT_SECRET" in os.environ)
        else ""
    )
    return project_id, project_secret


def prompt_bool() -> Optional[bool]:
    choice = input().lower()
    if choice in {"yes", "y"}:
        return True
    elif choice in {"no", "n"}:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")


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
    def simple_dvt(self) -> interface.SimpleDVT:
        return interface.SimpleDVT(SIMPLE_DVT)

    @property
    def csm(self) -> interface.CSModule:
        return interface.CSModule(CSM_ADDRESS)

    @property
    def cs_permissionless_gate(self) -> interface.CSPermissionlessGate:
        return interface.CSPermissionlessGate(CS_PERMISSIONLESS_GATE_ADDRESS)

    @property
    def cs_vetted_gate(self) -> interface.CSVettedGate:
        return interface.CSVettedGate(CS_VETTED_GATE_ADDRESS)

    @property
    def cs_accounting(self) -> interface.CSAccounting:
        return interface.CSAccounting(CS_ACCOUNTING_ADDRESS)

    @property
    def cs_parameters_registry(self) -> interface.CSParametersRegistry:
        return interface.CSParametersRegistry(CS_PARAMS_REGISTRY_ADDRESS)

    @property
    def cs_fee_distributor(self) -> interface.CSFeeDistributor:
        return interface.CSFeeDistributor(CS_FEE_DISTRIBUTOR_ADDRESS)

    @property
    def cs_fee_oracle(self) -> interface.CSFeeOracle:
        return interface.CSFeeOracle(CS_FEE_ORACLE_ADDRESS)

    @property
    def csm_hash_consensus(self) -> interface.CSHashConsensus:
        return interface.CSHashConsensus(CS_ORACLE_HASH_CONSENSUS_ADDRESS)

    @property
    def cs_verifier(self) -> interface.CSVerifierV2:
        return interface.CSVerifierV2(CS_VERIFIER_V2_ADDRESS)

    @property
    def cs_exit_penalties(self) -> interface.CSExitPenalties:
        return interface.CSExitPenalties(CS_EXIT_PENALTIES_ADDRESS)

    @property
    def cs_ejector(self) -> interface.CSEjector:
        return interface.CSEjector(CS_EJECTOR_ADDRESS)

    @property
    def cs_strikes(self) -> interface.CSStrikes:
        return interface.CSStrikes(CS_STRIKES_ADDRESS)

    @property
    def sandbox(self) -> interface.SimpleDVT:
        return interface.Sandbox(SANDBOX)

    @property
    def deposit_security_module_v1(self) -> interface.DepositSecurityModule:
        return interface.DepositSecurityModuleV1(DEPOSIT_SECURITY_MODULE_V1)

    @property
    def deposit_security_module_v2(self) -> interface.DepositSecurityModule:
        return interface.DepositSecurityModule(DEPOSIT_SECURITY_MODULE_V2)

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
    def triggerable_withdrawals_gateway(self):
        return interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)

    @property
    def withdrawal_queue(self) -> interface.WithdrawalQueueERC721:
        return interface.WithdrawalQueueERC721(WITHDRAWAL_QUEUE)

    @property
    def vault_hub(self) -> interface.VaultHub:
        return interface.VaultHub(VAULT_HUB)

    @property
    def accounting(self) -> interface.Accounting:
        return interface.Accounting(ACCOUNTING)

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
    def apm_registry(self) -> interface.APMRegistry:
        return interface.APMRegistry(APM_REGISTRY)

    @property
    def lido_app_repo(self) -> interface.Repo:
        return interface.Repo(LIDO_REPO)

    @property
    def nor_app_repo(self) -> interface.Repo:
        return interface.Repo(NODE_OPERATORS_REGISTRY_REPO)

    @property
    def simple_dvt_app_repo(self) -> interface.Repo:
        return interface.Repo(SIMPLE_DVT_REPO)

    @property
    def sandbox_repo(self) -> interface.Repo:
        return interface.Repo(SANDBOX_REPO)

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
    def veb_twg_gate_seal(self) -> interface.GateSeal:
        return interface.GateSeal(VEB_TWG_GATE_SEAL)

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

    @property
    def obol_lido_split_factory(self) -> interface.ObolLidoSplitFactory:
        return interface.ObolLidoSplitFactory(OBOL_LIDO_SPLIT_FACTORY)

    @property
    def split_main(self) -> interface.SplitMain:
        return interface.SplitMain(SPLIT_MAIN)

    @property
    def trp_escrow_factory(self) -> interface.VestingEscrowFactory:
        return interface.VestingEscrowFactory(TRP_VESTING_ESCROW_FACTORY)

    @property
    def token_rate_notifier(self) -> interface.TokenRateNotifier:
        return interface.TokenRateNotifier(L1_TOKEN_RATE_NOTIFIER)

    @property
    def validator_exit_verifier(self) -> interface.ValidatorsExitBusOracle:
        return interface.ValidatorExitVerifier(VALIDATOR_EXIT_VERIFIER)

    @property
    def dual_governance(self) -> interface.DualGovernance:
        return interface.DualGovernance(DUAL_GOVERNANCE)

    @property
    def dual_governance_config_provider(self) -> interface.DualGovernanceConfigProvider:
        return interface.DualGovernanceConfigProvider(DUAL_GOVERNANCE_CONFIG_PROVIDER)

    @property
    def emergency_protected_timelock(self) -> interface.EmergencyProtectedTimelock:
        return interface.EmergencyProtectedTimelock(TIMELOCK)

    @property
    def emergency_governance(self) -> interface.EmergencyGovernance:
        return interface.EmergencyGovernance(DAO_EMERGENCY_GOVERNANCE)

    @property
    def triggerable_withdrawals_gateway(self) -> interface.TriggerableWithdrawalsGateway:
        return interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)


def __getattr__(name: str) -> Any:
    if name == "contracts":
        return ContractsLazyLoader()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
