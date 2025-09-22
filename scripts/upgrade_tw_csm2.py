"""
Upgrade to CSM v2, enable Triggerable Withdrawals, update the reward address and name for Node Operator ID 25 `Nethermind`, rotate Kiln Deposit Security Committee address

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

import time

from typing import Any, Dict
from typing import Tuple
from brownie import interface, web3, convert
from brownie.convert.main import to_uint  # type: ignore

from utils.agent import agent_forward
from utils.dsm import encode_remove_guardian, encode_add_guardian
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
)
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.dual_governance import submit_proposals
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.config import get_deployer_account, get_priority_fee, get_is_live
from utils.node_operators import encode_set_node_operator_name, encode_set_node_operator_reward_address

# ============================= Constants ===================================
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
ARAGON_KERNEL = "0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc"
NODE_OPERATORS_REGISTRY_ARAGON_APP_ID = "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d"
SIMPLE_DVT_ARAGON_APP_ID = "0xe1635b63b5f7b5e545f2a637558a4029dea7905361a2f0fc28c66e9136cf86a4"

CSM_COMMITTEE_MS = "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f"
CS_MODULE_ID = 3
CS_MODULE_MODULE_FEE_BP = 600
CS_MODULE_MAX_DEPOSITS_PER_BLOCK = 30
CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CS_MODULE_TREASURY_FEE_BP = 400
CS_GATE_SEAL_ADDRESS = "0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0"

UTC13 = 60 * 60 * 13
UTC19 = 60 * 60 * 19

# ============================== Addresses ===================================

LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
VALIDATORS_EXIT_BUS_ORACLE = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
WITHDRAWAL_VAULT = "0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f"
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
NODE_OPERATORS_REGISTRY = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
SIMPLE_DVT = "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433"
ORACLE_DAEMON_CONFIG = "0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09"
CSM_ADDRESS = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
DEPOSIT_SECURITY_MODULE = "0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD"
WITHDRAWAL_QUEUE = "0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1"
CS_ACCOUNTING_ADDRESS = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"
CS_FEE_ORACLE_ADDRESS = "0x4D4074628678Bd302921c20573EEa1ed38DdF7FB"
CS_FEE_DISTRIBUTOR_ADDRESS = "0xD99CC66fEC647E68294C6477B40fC7E0F6F618D0"

# New core contracts implementations
NEW_LIDO_LOCATOR_IMPL = "0x2C298963FB763f74765829722a1ebe0784f4F5Cf"
ACCOUNTING_ORACLE_IMPL = "0xE9906E543274cebcd335d2C560094089e9547e8d"
VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0x905A211eD6830Cfc95643f0bE2ff64E7f3bf9b94"
WITHDRAWAL_VAULT_IMPL = "0x7D2BAa6094E1C4B60Da4cbAF4A77C3f4694fD53D"
STAKING_ROUTER_IMPL = "0x226f9265CBC37231882b7409658C18bB7738173A"
NODE_OPERATORS_REGISTRY_IMPL = "0x6828b023e737f96B168aCd0b5c6351971a4F81aE"

TRIGGERABLE_WITHDRAWALS_GATEWAY = "0xDC00116a0D3E064427dA2600449cfD2566B3037B"
VALIDATOR_EXIT_VERIFIER = "0xbDb567672c867DB533119C2dcD4FB9d8b44EC82f"

# Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4
CSM_CONSENSUS_VERSION = 3

# Fixed constants
EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 14 * 7200  # 14 days in slots (assuming 12 seconds per slot)
NOR_EXIT_DEADLINE_IN_SEC = 345600  # 28800 slots

# VEB parameters
MAX_VALIDATORS_PER_REPORT = 600
MAX_EXIT_REQUESTS_LIMIT = 11200
EXITS_PER_FRAME = 1
FRAME_DURATION_IN_SEC = 48

# CSM
CS_MODULE_NEW_TARGET_SHARE_BP = 500  # 5%
CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 625  # 6.25%

CS_ACCOUNTING_IMPL_V2_ADDRESS = "0x6f09d2426c7405C5546413e6059F884D2D03f449"
CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS = "0x5DCF7cF7c6645E9E822a379dF046a8b0390251A1"
CS_FEE_ORACLE_IMPL_V2_ADDRESS = "0xe0B234f99E413E27D9Bc31aBba9A49A3e570Da97"
CSM_IMPL_V2_ADDRESS = "0x1eB6d4da13ca9566c17F526aE0715325d7a07665"

CS_GATE_SEAL_V2_ADDRESS = "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3"
CS_EJECTOR_ADDRESS = "0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C"
CS_PERMISSIONLESS_GATE_ADDRESS = "0xcF33a38111d0B1246A3F38a838fb41D626B454f0"
CS_VETTED_GATE_ADDRESS = "0xB314D4A76C457c93150d308787939063F4Cc67E0"
CS_VERIFIER_V2_ADDRESS = "0xdC5FE1782B6943f318E05230d688713a560063DC"

CS_VERIFIER_ADDRESS_OLD = "0xeC6Cc185f671F627fb9b6f06C8772755F587b05d"
CS_CURVES = [
    ([1, 2.4 * 10**18], [2, 1.3 * 10**18]),  # Default Curve
    ([1, 1.5 * 10**18], [2, 1.3 * 10**18]),  # Legacy EA Curve
]
CS_ICS_GATE_BOND_CURVE = ([1, 1.5 * 10**18], [2, 1.3 * 10**18])  # Identified Community Stakers Gate Bond Curve

# GateSeals config
OLD_GATE_SEAL_ADDRESS = "0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178"
NEW_WQ_GATE_SEAL = "0x8A854C4E750CDf24f138f34A9061b2f556066912"
NEW_TW_GATE_SEAL = "0xA6BC802fAa064414AA62117B4a53D27fFfF741F1"
RESEAL_MANAGER = "0x7914b5a1539b97Bd0bbd155757F25FD79A522d24"

# Add EasyTrack constants
EASYTRACK_EVMSCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x8aa34dAaF0fC263203A15Bcfa0Ed926D466e59F3"
EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0xB7668B5485d0f826B86a75b0115e088bB9ee03eE"
EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY = "0xBc5642bDD6F2a54b01A75605aAe9143525D97308"

# Vote enactment timeframe
DUAL_GOVERNANCE_TIME_CONSTRAINTS = "0x2a30F5aC03187674553024296bed35Aa49749DDa"

# NO changes
NETHERMIND_NO_ID = 25
NETHERMIND_NEW_REWARD_ADDRESS = "0x36201ed66DbC284132046ee8d99272F8eEeb24c8"
NETHERMIND_NEW_NO_NAME = "Twinstake"

# DSM council rotation
OLD_KILN_ADDRESS = "0x14D5d5B71E048d2D75a39FfC5B407e3a3AB6F314"
NEW_KILN_ADDRESS = "0x6d22aE126eB2c37F67a1391B37FF4f2863e61389"
DSM_QUORUM_SIZE = 4

# ============================= Description ==================================
IPFS_DESCRIPTION = "Triggerable withdrawals and CSM v2 upgrade voting"


def encode_staking_router_proxy_update(implementation: str) -> Tuple[str, str]:
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    proxy = interface.OssifiableProxy(staking_router)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_wv_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.WithdrawalContractProxy(proxy)

    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b"")


def encode_oracle_upgrade_consensus(proxy: Any, consensus_version: int) -> Tuple[str, str]:
    oracle = interface.BaseOracle(proxy)
    return oracle.address, oracle.setConsensusVersion.encode_input(consensus_version)


def encode_staking_router_update_csm_module_share() -> Tuple[str, str]:
    """Encode call to update CSM share limit"""
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    return (
        staking_router.address,
        staking_router.updateStakingModule.encode_input(
            CS_MODULE_ID,
            CS_MODULE_NEW_TARGET_SHARE_BP,
            CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
            CS_MODULE_MODULE_FEE_BP,
            CS_MODULE_TREASURY_FEE_BP,
            CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
            CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
        ),
    )


def to_percent(bp: int) -> float:
    """
    Convert basis points to percentage.
    """
    return bp / 10000 * 100


def get_vote_items():
    lido_locator = interface.LidoLocator(LIDO_LOCATOR)
    validator_exit_bus_oracle = interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE)
    agent = interface.Agent(AGENT)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    withdrawal_vault = interface.WithdrawalVault(WITHDRAWAL_VAULT)
    accounting_oracle = interface.AccountingOracle(ACCOUNTING_ORACLE)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    acl = interface.ACL(ACL)
    kernel = interface.Kernel(ARAGON_KERNEL)
    nor = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    simple_dvt = interface.SimpleDVT(SIMPLE_DVT)
    oracle_daemon_config = interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)
    csm = interface.CSModule(CSM_ADDRESS)
    dsm = interface.DepositSecurityModule(DEPOSIT_SECURITY_MODULE)
    withdrawal_queue = interface.WithdrawalQueueERC721(WITHDRAWAL_QUEUE)
    cs_accounting = interface.CSAccounting(CS_ACCOUNTING_ADDRESS)
    cs_fee_oracle = interface.CSFeeOracle(CS_FEE_ORACLE_ADDRESS)
    cs_fee_distributor = interface.CSFeeDistributor(CS_FEE_DISTRIBUTOR_ADDRESS)
    triggerable_withdrawal_gateway = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)

    dg_items = [
        # --- locator
        # "1.1. Update Lido Locator `0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb` implementation to `0x2C298963FB763f74765829722a1ebe0784f4F5Cf`",
        agent_forward([encode_proxy_upgrade_to(lido_locator, NEW_LIDO_LOCATOR_IMPL)]),
        # --- VEB
        # "1.2. Update Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e` implementation to `0x905A211eD6830Cfc95643f0bE2ff64E7f3bf9b94`",
        agent_forward([encode_proxy_upgrade_to(validator_exit_bus_oracle, VALIDATORS_EXIT_BUS_ORACLE_IMPL)]),
        # "1.3. Call `finalizeUpgrade_v2(maxValidatorsPerReport = 600, maxExitRequestsLimit = 11200, exitsPerFrame = 1, frameDurationInSec = 48)` on Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e`",
        agent_forward(
            [
                (
                    VALIDATORS_EXIT_BUS_ORACLE,
                    validator_exit_bus_oracle.finalizeUpgrade_v2.encode_input(
                        MAX_VALIDATORS_PER_REPORT, MAX_EXIT_REQUESTS_LIMIT, EXITS_PER_FRAME, FRAME_DURATION_IN_SEC
                    ),
                )
            ]
        ),
        # "1.4. Grant Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e` role `MANAGE_CONSENSUS_VERSION_ROLE` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=validator_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=AGENT,
                )
            ]
        ),
        # "1.5. Bump Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e` consensus version to `4`",
        agent_forward([encode_oracle_upgrade_consensus(validator_exit_bus_oracle, VEBO_CONSENSUS_VERSION)]),
        # "1.6. Revoke Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e` role `MANAGE_CONSENSUS_VERSION_ROLE` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=validator_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=AGENT,
                )
            ]
        ),
        # "1.7. Grant Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e` role `SUBMIT_REPORT_HASH_ROLE` to EasyTrack EVM Script Executor `0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=validator_exit_bus_oracle,
                    role_name="SUBMIT_REPORT_HASH_ROLE",
                    grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
                )
            ]
        ),
        # --- Triggerable Withdrawals Gateway (TWG)
        # "1.8. Grant Triggerable Withdrawals Gateway `0xDC00116a0D3E064427dA2600449cfD2566B3037B` role `ADD_FULL_WITHDRAWAL_REQUEST_ROLE` to CS Ejector `0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=CS_EJECTOR_ADDRESS,
                )
            ]
        ),
        # "1.9. Grant Triggerable Withdrawals Gateway `0xDC00116a0D3E064427dA2600449cfD2566B3037B` role `ADD_FULL_WITHDRAWAL_REQUEST_ROLE` to Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=VALIDATORS_EXIT_BUS_ORACLE,
                )
            ]
        ),
        # "Add Triggerable Withdrawals Gateway `0xDC00116a0D3E064427dA2600449cfD2566B3037B` as a sealable withdrawals blocker to Dual Governance `0xC1db28B3301331277e307FDCfF8DE28242A4486E`",
        (
            DUAL_GOVERNANCE,
            dual_governance.addTiebreakerSealableWithdrawalBlocker.encode_input(
                TRIGGERABLE_WITHDRAWALS_GATEWAY
            ),
        ),
        # --- WV
        # "1.11. Update Withdrawal Vault `0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f` implementation to `0x7D2BAa6094E1C4B60Da4cbAF4A77C3f4694fD53D`",
        agent_forward([encode_wv_proxy_upgrade_to(withdrawal_vault, WITHDRAWAL_VAULT_IMPL)]),
        # "1.12. Call `finalizeUpgrade_v2()` on Withdrawal Vault `0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f`",
        agent_forward(
            [
                (
                    WITHDRAWAL_VAULT,
                    withdrawal_vault.finalizeUpgrade_v2.encode_input(),
                )
            ]
        ),
        # --- AO
        # "1.13. Update Accounting Oracle `0x852deD011285fe67063a08005c71a85690503Cee` implementation to `0xE9906E543274cebcd335d2C560094089e9547e8d`",
        agent_forward([encode_proxy_upgrade_to(accounting_oracle, ACCOUNTING_ORACLE_IMPL)]),
        # "1.14. Grant Accounting Oracle `0x852deD011285fe67063a08005c71a85690503Cee` role `MANAGE_CONSENSUS_VERSION_ROLE` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=AGENT,
                )
            ]
        ),
        # "1.15. Bump Accounting Oracle `0x852deD011285fe67063a08005c71a85690503Cee` consensus version to `4`",
        agent_forward([encode_oracle_upgrade_consensus(accounting_oracle, AO_CONSENSUS_VERSION)]),
        # "1.16. Revoke Accounting Oracle `0x852deD011285fe67063a08005c71a85690503Cee` role `MANAGE_CONSENSUS_VERSION_ROLE` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=AGENT,
                )
            ]
        ),
        # "1.17. Call `finalizeUpgrade_v3()` on Accounting Oracle `0x852deD011285fe67063a08005c71a85690503Cee`",
        agent_forward(
            [
                (
                    ACCOUNTING_ORACLE,
                    accounting_oracle.finalizeUpgrade_v3.encode_input(),
                )
            ]
        ),
        # --- SR
        # "1.18. Update Staking Router `0xFdDf38947aFB03C621C71b06C9C70bce73f12999` implementation to `0x226f9265CBC37231882b7409658C18bB7738173A`",
        agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        # "1.19. Call `finalizeUpgrade_v3()` on Staking Router `0xFdDf38947aFB03C621C71b06C9C70bce73f12999`",
        agent_forward(
            [
                (
                    STAKING_ROUTER,
                    staking_router.finalizeUpgrade_v3.encode_input(),
                )
            ]
        ),
        # "1.20. Grant Staking Router `0xFdDf38947aFB03C621C71b06C9C70bce73f12999` role `REPORT_VALIDATOR_EXITING_STATUS_ROLE` to Validator Exit Delay Verifier `0xbDb567672c867DB533119C2dcD4FB9d8b44EC82f`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=staking_router,
                    role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                    grant_to=VALIDATOR_EXIT_VERIFIER,
                )
            ]
        ),
        # "1.21. Grant Staking Router `0xFdDf38947aFB03C621C71b06C9C70bce73f12999` role `REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE` to Triggerable Withdrawals Gateway `0xDC00116a0D3E064427dA2600449cfD2566B3037B`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=staking_router,
                    role_name="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE",
                    grant_to=TRIGGERABLE_WITHDRAWALS_GATEWAY,
                )
            ]
        ),
        # --- Curated Staking Module and sDVT
        # "1.22. Grant `APP_MANAGER_ROLE` role to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` on Lido DAO Kernel `0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc` via Aragon ACL `0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb`",
        agent_forward(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(
                        AGENT,
                        ARAGON_KERNEL,
                        convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE")),
                    ),
                )
            ]
        ),
        # "1.23. Update Node Operators Registry (Aragon APP ID = `0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d`) implementation to `0x6828b023e737f96B168aCd0b5c6351971a4F81aE` via Lido DAO Kernel `0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc`",
        agent_forward(
            [
                (
                    kernel.address,
                    kernel.setApp.encode_input(
                        kernel.APP_BASES_NAMESPACE(),
                        NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
                        NODE_OPERATORS_REGISTRY_IMPL,
                    ),
                )
            ]
        ),
        # "1.24. Call `finalizeUpgrade_v4(norExitDeadlineInSec = 345600)` on Curated Staking Module Node Operators Registry `0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5`",
        agent_forward(
            [
                (
                    interface.NodeOperatorsRegistry(nor).address,
                    interface.NodeOperatorsRegistry(nor).finalizeUpgrade_v4.encode_input(
                        NOR_EXIT_DEADLINE_IN_SEC
                    ),
                )
            ]
        ),
        # "1.25. Update Simple DVT (Aragon APP ID = `0xe1635b63b5f7b5e545f2a637558a4029dea7905361a2f0fc28c66e9136cf86a4`) implementation to `0x6828b023e737f96B168aCd0b5c6351971a4F81aE` via Lido DAO Kernel `0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc`",
        agent_forward(
            [
                (
                    kernel.address,
                    kernel.setApp.encode_input(
                        kernel.APP_BASES_NAMESPACE(),
                        SIMPLE_DVT_ARAGON_APP_ID,
                        NODE_OPERATORS_REGISTRY_IMPL,
                    ),
                )
            ]
        ),
        # "1.26. Call `finalizeUpgrade_v4(norExitDeadlineInSec = 345600) on Simple DVT Staking Module Node Operators Registry `0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433`",
        agent_forward(
            [
                (
                    interface.NodeOperatorsRegistry(simple_dvt).address,
                    interface.NodeOperatorsRegistry(simple_dvt).finalizeUpgrade_v4.encode_input(
                        NOR_EXIT_DEADLINE_IN_SEC
                    ),
                )
            ]
        ),
        # "1.27. Revoke `APP_MANAGER_ROLE` role from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` on Lido DAO Kernel `0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc` via Aragon ACL `0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb`",
        agent_forward(
            [
                (
                    acl.address,
                    acl.revokePermission.encode_input(
                        AGENT,
                        ARAGON_KERNEL,
                        convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE")),
                    ),
                )
            ]
        ),
        # --- Oracle configs
        # "1.28. Grant Oracle Daemon Config `0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09` role `CONFIG_MANAGER_ROLE` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    grant_to=AGENT,
                )
            ]
        ),
        # "1.29. Remove `NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP` variable from Oracle Daemon Config `0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09`",
        agent_forward(
            [
                (
                    oracle_daemon_config.address,
                    oracle_daemon_config.unset.encode_input("NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP"),
                )
            ]
        ),
        # "1.30. Remove `VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS` variable from Oracle Daemon Config `0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09`",
        agent_forward(
            [
                (
                    oracle_daemon_config.address,
                    oracle_daemon_config.unset.encode_input("VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS"),
                )
            ]
        ),
        # "1.31. Remove `VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS` variable from Oracle Daemon Config `0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09`",
        agent_forward(
            [
                (
                    oracle_daemon_config.address,
                    oracle_daemon_config.unset.encode_input("VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS"),
                )
            ]
        ),
        # "1.32. Add `EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS=14 * 7200` variable to Oracle Daemon Config `0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09`",
        agent_forward(
            [
                (
                    oracle_daemon_config.address,
                    oracle_daemon_config.set.encode_input(
                        "EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS", EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS
                    ),
                )
            ]
        ),
        # "1.33. Revoke Oracle Daemon Config `0xbf05A929c3D7885a6aeAd833a992dA6E5ac23b09` role `CONFIG_MANAGER_ROLE` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    revoke_from=AGENT,
                )
            ]
        ),
        # --- CSM
        # "1.34. Update CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` implementation to `0x1eB6d4da13ca9566c17F526aE0715325d7a07665`",
        agent_forward(
            [
                encode_proxy_upgrade_to(csm, CSM_IMPL_V2_ADDRESS)
            ]
        ),
        # "1.35. Call `finalizeUpgradeV2()` on CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F`",
        agent_forward(
            [
                (
                    csm.address,
                    csm.finalizeUpgradeV2.encode_input(),
                )
            ]
        ),
        # "1.36. Update CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` implementation to `0x6f09d2426c7405C5546413e6059F884D2D03f449`",
        agent_forward(
            [
                encode_proxy_upgrade_to(
                    cs_accounting,
                    CS_ACCOUNTING_IMPL_V2_ADDRESS,
                )
            ]
        ),
        # "1.37. Call `finalizeUpgradeV2(bondCurves=[ ([1, 2.4 * 10**18], [2, 1.3 * 10**18]), ([1, 1.5 * 10**18], [2, 1.3 * 10**18]) ])` on CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da`",
        agent_forward(
            [
                (
                    cs_accounting.address,
                    cs_accounting.finalizeUpgradeV2.encode_input(CS_CURVES),
                )
            ]
        ),
        # "1.38. Update CSFeeOracle `0x4D4074628678Bd302921c20573EEa1ed38DdF7FB` implementation to `0xe0B234f99E413E27D9Bc31aBba9A49A3e570Da97`",
        agent_forward(
            [
                encode_proxy_upgrade_to(
                    cs_fee_oracle,
                    CS_FEE_ORACLE_IMPL_V2_ADDRESS,
                )
            ]
        ),
        # "1.39. Call `finalizeUpgradeV2(consensusVersion=3)` on CSFeeOracle `0x4D4074628678Bd302921c20573EEa1ed38DdF7FB`",
        agent_forward(
            [
                (
                    cs_fee_oracle.address,
                    cs_fee_oracle.finalizeUpgradeV2.encode_input(CSM_CONSENSUS_VERSION),
                )
            ]
        ),
        # "1.40. Update CSFeeDistributor `0xD99CC66fEC647E68294C6477B40fC7E0F6F618D0` implementation to `0x5DCF7cF7c6645E9E822a379dF046a8b0390251A1`",
        agent_forward(
            [
                encode_proxy_upgrade_to(
                    cs_fee_distributor,
                    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
                )
            ]
        ),
        # "1.41. Call `finalizeUpgradeV2(_rebateRecipient=0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c)` on CSFeeDistributor `0xD99CC66fEC647E68294C6477B40fC7E0F6F618D0`",
        agent_forward(
            [
                (
                    cs_fee_distributor.address,
                    cs_fee_distributor.finalizeUpgradeV2.encode_input(agent),
                )
            ]
        ),
        # "1.42. Revoke CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` role `SET_BOND_CURVE_ROLE` from CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    revoke_from=csm,
                )
            ]
        ),
        # "1.43. Revoke CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` role `RESET_BOND_CURVE_ROLE` from CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=csm,
                )
            ]
        ),
        # "1.44. Revoke CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` role `RESET_BOND_CURVE_ROLE` from CSM Committee `0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=CSM_COMMITTEE_MS,
                )
            ]
        ),
        # "1.45. Grant CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` role `CREATE_NODE_OPERATOR_ROLE` for CS Permissionless Gate `0xcF33a38111d0B1246A3F38a838fb41D626B454f0`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=CS_PERMISSIONLESS_GATE_ADDRESS,
                )
            ]
        ),
        # "1.46. Grant CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` role `CREATE_NODE_OPERATOR_ROLE` for CS Vetted Gate `0xB314D4A76C457c93150d308787939063F4Cc67E0`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=CS_VETTED_GATE_ADDRESS,
                )
            ]
        ),
        # "1.47. Grant CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` role `SET_BOND_CURVE_ROLE` for CS Vetted Gate `0xB314D4A76C457c93150d308787939063F4Cc67E0`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    grant_to=CS_VETTED_GATE_ADDRESS,
                )
            ]
        ),
        # "1.48. Revoke CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` role `VERIFIER_ROLE` from the previous instance of CS Verifier `0xeC6Cc185f671F627fb9b6f06C8772755F587b05d`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=csm,
                    role_name="VERIFIER_ROLE",
                    revoke_from=CS_VERIFIER_ADDRESS_OLD,
                )
            ]
        ),
        # "1.49. Grant CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` role `VERIFIER_ROLE` to the new instance of CS Verifier `0xdC5FE1782B6943f318E05230d688713a560063DC`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=csm,
                    role_name="VERIFIER_ROLE",
                    grant_to=CS_VERIFIER_V2_ADDRESS,
                )
            ]
        ),
        # "1.50. Revoke CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` role `PAUSE_ROLE` from the previous GateSeal instance `0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=csm,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "1.51. Revoke CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` role `PAUSE_ROLE` from the previous GateSeal instance `0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=cs_accounting,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "1.52. Revoke CSFeeOracle `0x4D4074628678Bd302921c20573EEa1ed38DdF7FB` role `PAUSE_ROLE` from the previous GateSeal instance `0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=cs_fee_oracle,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "1.53. Grant CSM `0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F` role `PAUSE_ROLE` for the new GateSeal instance `0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=csm,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ]
        ),
        # "1.54. Grant CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` role `PAUSE_ROLE` for the new GateSeal instance `0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=cs_accounting,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ]
        ),
        # "1.55. Grant CSFeeOracle `0x4D4074628678Bd302921c20573EEa1ed38DdF7FB` role `PAUSE_ROLE` for the new GateSeal instance `0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=cs_fee_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ]
        ),
        # "1.56. Grant CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` role `MANAGE_BOND_CURVES_ROLE` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=cs_accounting,
                    role_name="MANAGE_BOND_CURVES_ROLE",
                    grant_to=agent,
                )
            ]
        ),
        # "1.57. Add Identified Community Stakers Gate Bond Curve `([1, 1.5 * 10**18], [2, 1.3 * 10**18])` to CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da`",
        agent_forward(
            [
                (
                    cs_accounting.address,
                    cs_accounting.addBondCurve.encode_input(CS_ICS_GATE_BOND_CURVE),
                )
            ]
        ),
        # "1.58. Revoke CSAccounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` role `MANAGE_BOND_CURVES_ROLE` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=cs_accounting,
                    role_name="MANAGE_BOND_CURVES_ROLE",
                    revoke_from=agent,
                )
            ]
        ),
        # "1.59. Increase CSM (`MODULE_ID = 3`) share limit from `3%` to `5%` and priority exit threshold from `3.75%` to `6.25%` in Staking Router `0xFdDf38947aFB03C621C71b06C9C70bce73f12999`",
        agent_forward([encode_staking_router_update_csm_module_share()]),
        # --- Gate Seals
        # "1.60. Revoke Withdrawal Queue `0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1` role `PAUSE_ROLE` from the old GateSeal `0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=withdrawal_queue,
                    role_name="PAUSE_ROLE",
                    revoke_from=OLD_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "1.61. Revoke Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e` role `PAUSE_ROLE` from the old GateSeal `0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178`",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=validator_exit_bus_oracle,
                    role_name="PAUSE_ROLE",
                    revoke_from=OLD_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "1.62. Grant Withdrawal Queue `0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1` role `PAUSE_ROLE` to the new Withdrawal Queue GateSeal `0x8A854C4E750CDf24f138f34A9061b2f556066912`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=withdrawal_queue,
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_WQ_GATE_SEAL,
                )
            ]
        ),
        # "1.63. Grant Validators Exit Bus Oracle `0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e` role `PAUSE_ROLE` to the new Triggerable Withdrawals GateSeal `0xA6BC802fAa064414AA62117B4a53D27fFfF741F1`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=validator_exit_bus_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_TW_GATE_SEAL,
                )
            ]
        ),
        # "1.64. Grant Triggerable Withdrawals Gateway `0xDC00116a0D3E064427dA2600449cfD2566B3037B` role `PAUSE_ROLE` to the new Triggerable Withdrawals GateSeal `0xA6BC802fAa064414AA62117B4a53D27fFfF741F1`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_TW_GATE_SEAL,
                )
            ]
        ),
        # "1.65. Grant Triggerable Withdrawals Gateway `0xDC00116a0D3E064427dA2600449cfD2566B3037B` role `PAUSE_ROLE` to Reseal Manager `0x7914b5a1539b97Bd0bbd155757F25FD79A522d24`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=triggerable_withdrawal_gateway,
                    role_name="PAUSE_ROLE",
                    grant_to=RESEAL_MANAGER,
                )
            ]
        ),
        # "1.66. Grant Triggerable Withdrawals Gateway `0xDC00116a0D3E064427dA2600449cfD2566B3037B` role `RESUME_ROLE` to Reseal Manager `0x7914b5a1539b97Bd0bbd155757F25FD79A522d24`",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=triggerable_withdrawal_gateway,
                    role_name="RESUME_ROLE",
                    grant_to=RESEAL_MANAGER,
                )
            ]
        ),
        # "1.67. Rename Node Operator `ID 25` from `Nethermind` to `Twinstake`"
        agent_forward(
            [
                encode_set_node_operator_name(id=NETHERMIND_NO_ID, name=NETHERMIND_NEW_NO_NAME, registry=nor),
            ]
        ),
        # "1.68. Change Node Operator `ID 25` reward address from `0x237DeE529A47750bEcdFa8A59a1D766e3e7B5F91` to `0x36201ed66DbC284132046ee8d99272F8eEeb24c8`"
        agent_forward(
            [
                encode_set_node_operator_reward_address(id=NETHERMIND_NO_ID, rewardAddress=NETHERMIND_NEW_REWARD_ADDRESS, registry=nor),
            ]
        ),
        # "1.69. Remove old `Kiln` address `0x14D5d5B71E048d2D75a39FfC5B407e3a3AB6F314` from Deposit Security Module `0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD` and keep quorum size as `4`"
        agent_forward(
            [
                encode_remove_guardian(dsm=dsm, guardian_address=OLD_KILN_ADDRESS, quorum_size=DSM_QUORUM_SIZE),
            ]
        ),
        # "1.70. Add new `Kiln` address `0x6d22aE126eB2c37F67a1391B37FF4f2863e61389` to Deposit Security Module `0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD` and keep quorum size as `4`"
        agent_forward(
            [
                encode_add_guardian(dsm=dsm, guardian_address=NEW_KILN_ADDRESS, quorum_size=DSM_QUORUM_SIZE),
            ]
        ),
        # "1.71. Set time constraints for Dual Governance Proposal execution (13:00 to 19:00 UTC) on Dual Governance Time Constraints `0x2a30F5aC03187674553024296bed35Aa49749DDa`"
        (
            DUAL_GOVERNANCE_TIME_CONSTRAINTS,
            interface.TimeConstraints(DUAL_GOVERNANCE_TIME_CONSTRAINTS).checkTimeWithinDayTimeAndEmit.encode_input(
                UTC13,  # 13:00 UTC
                UTC19,  # 19:00 UTC
            ),
        ),
    ]
    dg_call_script = submit_proposals(
        [
            (
                dg_items,
                "Upgrade to CSM v2, enable Triggerable Withdrawals, update the reward address and name for Node Operator ID 25 `Nethermind`, rotate Kiln Deposit Security Committee address",
            )
        ]
    )

    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to upgrade to CSM v2, enable Triggerable Withdrawals, update the reward address and name for Node Operator ID 25 `Nethermind`, rotate Kiln Deposit Security Committee address",
            dg_call_script[0],
        ),
        (
            "2. Add CSSetVettedGateTree factory `0xBc5642bDD6F2a54b01A75605aAe9143525D97308` to EasyTrack `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` with permissions `setTreeParams`",
            add_evmscript_factory(
                factory=EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY,
                permissions=(create_permissions(interface.CSVettedGate(CS_VETTED_GATE_ADDRESS), "setTreeParams")),
            ),
        ),
        (
            "3. Add SubmitValidatorsExitRequestHashes (Simple DVT) EVM script factory `0xAa3D6A8B52447F272c1E8FAaA06EA06658bd95E2` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` with permissions `submitExitRequestsHash`",
            add_evmscript_factory(
                factory=EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                permissions=(create_permissions(validator_exit_bus_oracle, "submitExitRequestsHash")),
            ),
        ),
        (
            "4. Add SubmitValidatorsExitRequestHashes (Curated Module) EVM script factory `0x397206ecdbdcb1A55A75e60Fc4D054feC72E5f63` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` with permissions `submitExitRequestsHash`",
            add_evmscript_factory(
                factory=EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                permissions=(create_permissions(validator_exit_bus_oracle, "submitExitRequestsHash")),
            ),
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    assert confirm_vote_script(vote_items, silent, desc_ipfs)

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
