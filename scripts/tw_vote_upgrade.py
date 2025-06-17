from itertools import count
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from utils.config import (
    CS_ACCOUNTING_IMPL_V2_ADDRESS,
    CS_CURVES,
    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
    CS_FEE_ORACLE_IMPL_V2_ADDRESS,
    CS_GATE_SEAL_ADDRESS,
    CS_GATE_SEAL_V2_ADDRESS,
    CSM_COMMITTEE_MS,
    CSM_IMPL_V2_ADDRESS,
    NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
    NODE_OPERATORS_REGISTRY_IMPL,
    ACCOUNTING_ORACLE_IMPL,
    SIMPLE_DVT_ARAGON_APP_ID,
    STAKING_ROUTER_IMPL,
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    WITHDRAWAL_VAULT_IMPL,
    LIDO_LOCATOR_IMPL,
    contracts,
    get_deployer_account,
    get_priority_fee,
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, get_priority_fee
from utils.agent import agent_forward
from utils.kernel import update_app_implementation

try:
    from brownie import interface
except ImportError as e:
    print(f"ImportError: {e}")
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")
    if TYPE_CHECKING:
        interface: Any = ...


TW_DESCRIPTION = "Proposal to use TW in Lido protocol"

# TWG
TWG_MAX_EXIT_REQUESTS_LIMIT = 13000
TWG_EXIT_REQUESTS_PER_FRAME = 1
TWG_FRAME_DURATION = 48  # in hours

## Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4

EXIT_DAILY_LIMIT = 20
TW_DAILY_LIMIT = 10

EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 7200

NOR_EXIT_DEADLINE_IN_SEC = 30 * 60

DEVNET_01_ADDRESS = '0x308eaCED5a0c5C4e717b29eD49300158ddeE8D54'

NOR_VERSION = ["3", "0", "0"]
SDVT_VERSION = ["2", "0", "0"]

def _add_implementation_to_repo(repo, version, address, content_uri):
    return (repo.address, repo.newVersion.encode_input(version, address, content_uri))

def add_implementation_to_nor_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.nor_app_repo, version, address, content_uri)

def add_implementation_to_sdvt_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.simple_dvt_app_repo, version, address, content_uri)

def encode_staking_router_proxy_update(implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(contracts.staking_router)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)

def get_repo_uri(repo_address: str) -> str:
    print("repo_address", repo_address)
    contract = interface.Repo(repo_address).getLatest()
    print("contract", contract)
    return contract["contentURI"]

def encode_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)

def encode_wv_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.WithdrawalContractProxy(proxy)
    if (proxy.proxy_getAdmin() != contracts.voting.address):
        raise Exception('withdrawal_contract is not in a valid state')

    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b'')


def encode_oracle_upgrade_consensus(proxy: Any, consensus_version: int) -> Tuple[str, str]:
    oracle = interface.BaseOracle(proxy)
    return oracle.address, oracle.setConsensusVersion.encode_input(consensus_version)

def create_tw_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[Any]]:
    """
        Triggerable withdrawals voting baking and sending.

        Contains next steps:
            --- Locator
            1. Update locator implementation
            --- VEB
            2. Update VEBO implementation
            3. Call finalizeUpgrade_v2(maxValidatorsPerReport, maxExitRequestsLimit, exitsPerFrame, frameDurationInSec) on VEBO
            4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            5. Bump VEBO consensus version to `4`
            6. Grant VEB role SUBMIT_REPORT_HASH_ROLE to the ET (TBD)
            --- Triggerable Withdrawals Gateway (TWG)
            7. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector
            8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB
            --- WV
            9. Update WithdrawalVault implementation
            10. Call finalizeUpgrade_v2() on WithdrawalVault
            --- AO
            11. Update Accounting Oracle implementation
            12. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            13. Bump AO consensus version to `4`
            --- SR
            14. Update SR implementation
            15. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
            16. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
            --- NOR
            17. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo
            18. Update `NodeOperatorsRegistry` implementation
            19. Call finalizeUpgrade_v4 on NOR
            --- sDVT
            20. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo
            21. Update `SimpleDVT` implementation
            22. Call finalizeUpgrade_v4 on sDVT
            --- Oracle configs ---
            23. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
            24. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            25. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            26. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig
            --- Temp ---
            27. Add PAUSE_ROLE for TWG to the TEMP-DEVNET-01
            28. Add RESUME_ROLE for TWG to the TEMP-DEVNET-01
            29. Add PAUSE_ROLE for VEB to the TEMP-DEVNET-01
            30. Add RESUME_ROLE for VEB to the TEMP-DEVNET-01
            --- CSM ---
            31. Upgrade CSM implementation on proxy
            32. Upgrade CSAccounting implementation on proxy
            33. Upgrade CSFeeOracle implementation on proxy
            34. Upgrade CSFeeDistributor implementation on proxy
            35. Call `finalizeUpgradeV2(exitPenalties)` on CSM contract
            36. Call `finalizeUpgradeV2(defaultBondCurve,vettedBondCurve)` on CSAccounting contract
            37. Call `finalizeUpgradeV2(consensusVersion,strikesContract)` on CSFeeOracle contract
            38. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract
            39. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract
            40. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract
            41. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee
            42. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate
            43. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate
            44. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate
            45. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract
            46. Grant role VERIFIER_ROLE to the new instance of the Verifier contract
            47. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance
            48. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance
            49. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance
            50. Grant CSM role PAUSE_ROLE for the new GateSeal instance
            51. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance
            52. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance
            53. Revoke Burner role REQUEST_BURN_SHARES_ROLE from the CSAccounting contract
            54. Grant Burner role REQUEST_BURN_MY_STETH_ROLE to the CSAccounting contract
    """

    item_idx = count(1)

    nor_repo = contracts.nor_app_repo.address
    # simple_dvt_repo = contracts.simple_dvt_app_repo.address

    nor_uri = get_repo_uri(nor_repo)
    # simple_dvt_uri = get_repo_uri(simple_dvt_repo)
    print(f"LIDO_LOCATOR_IMPL repo URI: {LIDO_LOCATOR_IMPL}")
    vote_descriptions, call_script_items = zip(
         (
            f"{next(item_idx)}. Update locator implementation",
            agent_forward([encode_proxy_upgrade_to(contracts.lido_locator, LIDO_LOCATOR_IMPL)]),
        ),
         (
            f"{next(item_idx)}. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo",
            add_implementation_to_nor_app_repo(NOR_VERSION, NODE_OPERATORS_REGISTRY_IMPL, nor_uri),
        ),
        (
            f"{next(item_idx)}. Update `NodeOperatorsRegistry` implementation",
            update_app_implementation(NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        (
            f"{next(item_idx)}. Update SR implementation",
            agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        ),

        (
            f"{next(item_idx)}. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.triggerable_withdrawals_gateway,
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.cs_ejector,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Add PAUSE_ROLE for TWG to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.triggerable_withdrawals_gateway,
                    role_name="PAUSE_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Add RESUME_ROLE for TWG to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.triggerable_withdrawals_gateway,
                    role_name="RESUME_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE",
                    grant_to=contracts.triggerable_withdrawals_gateway,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.triggerable_withdrawals_gateway,
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.validators_exit_bus_oracle,
                )
            ])
        ),

        (
            f"{next(item_idx)}. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitDelayVerifier",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                    grant_to=contracts.validator_exit_verifier,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitDelayVerifier",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                    grant_to=contracts.validator_exit_verifier,
                )
            ])
        ),
    )

    vote_items = bake_vote_items(list(vote_descriptions), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(TW_DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(TW_DESCRIPTION)

    assert confirm_vote_script(vote_items, silent, desc_ipfs), 'Vote not confirmed.'

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)


def main():
    print('Start baking vote.')
    print("DEPLOYER ACCOUNT:", get_deployer_account())
    tx_params = {
        "from": get_deployer_account(),
        "priority_fee": get_priority_fee(),
    }


    vote_id, _ = create_tw_vote(tx_params=tx_params, silent=True)

    if vote_id:
        print(f'Vote [{vote_id}] created.')
