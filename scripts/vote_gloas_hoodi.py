"""
Hoodi vote for the on-chain part of LIP-43 (Glamsterdam/Gloas compatibility).

1. Submit the Gloas upgrade to Dual Governance as a single Aragon Agent forward call
1.1. Upgrade LidoLocator implementation
1.2. Upgrade PredepositGuarantee implementation
1.3. Upgrade TopUpGateway implementation
1.4. Upgrade ConsolidationBus implementation
1.5. Upgrade WithdrawalVault implementation
1.6. Grant REPORT_VALIDATOR_EXITING_STATUS_ROLE on StakingRouter to the new ValidatorExitDelayVerifier
1.7. Revoke REPORT_VALIDATOR_EXITING_STATUS_ROLE on StakingRouter from the old ValidatorExitDelayVerifier
1.8. Register the new ConsolidationGateway on CircuitBreaker
1.9. Unregister the old ConsolidationGateway from CircuitBreaker
1.10. Revoke PAUSE_ROLE on the old ConsolidationGateway from CircuitBreaker
1.11. Revoke PAUSE_ROLE on the old ConsolidationGateway from ResealManager
1.12. Revoke RESUME_ROLE on the old ConsolidationGateway from ResealManager
1.13. Revoke ADD_CONSOLIDATION_REQUEST_ROLE on the old ConsolidationGateway from ConsolidationBus
1.14. Grant VERIFIER_ROLE on CSM to the new CSM Verifier
1.15. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on CSM to the new CSM Verifier
1.16. Register the new CSM Verifier on CircuitBreaker
1.17. Revoke VERIFIER_ROLE on CSM from the old CSM Verifier
1.18. Revoke REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on CSM from the old CSM Verifier
1.19. Unregister the old CSM Verifier from CircuitBreaker
1.20. Grant VERIFIER_ROLE on CSM 0x02 to the new CSM 0x02 Verifier
1.21. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on CSM 0x02 to the new CSM 0x02 Verifier
1.22. Register the new CSM 0x02 Verifier on CircuitBreaker
1.23. Revoke VERIFIER_ROLE on CSM 0x02 from the old CSM 0x02 Verifier
1.24. Revoke REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on CSM 0x02 from the old CSM 0x02 Verifier
1.25. Unregister the old CSM 0x02 Verifier from CircuitBreaker
1.26. Grant VERIFIER_ROLE on Curated Module v2 to the new Curated Module v2 Verifier
1.27. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on Curated Module v2 to the new Curated Module v2 Verifier
1.28. Register the new Curated Module v2 Verifier on CircuitBreaker
1.29. Revoke VERIFIER_ROLE on Curated Module v2 from the old Curated Module v2 Verifier
1.30. Revoke REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on Curated Module v2 from the old Curated Module v2 Verifier
1.31. Unregister the old Curated Module v2 Verifier from CircuitBreaker
1.32. Grant CONFIG_MANAGER_ROLE on OracleDaemonConfig to Aragon Agent
1.33. Set MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT on OracleDaemonConfig to 500
1.34. Revoke CONFIG_MANAGER_ROLE on OracleDaemonConfig from Aragon Agent
1.35. Grant ALL_LIMITS_MANAGER_ROLE on OracleReportSanityChecker to Aragon Agent
1.36. Update OracleReportSanityChecker limits: exited 411975, consolidation 205875, max exit requested 11520
1.37. Revoke ALL_LIMITS_MANAGER_ROLE on OracleReportSanityChecker from Aragon Agent
1.38. Grant MANAGE_CONSENSUS_VERSION_ROLE on AccountingOracle to Aragon Agent
1.39. Set the AccountingOracle consensus version to 7
1.40. Revoke MANAGE_CONSENSUS_VERSION_ROLE on AccountingOracle from Aragon Agent
1.41. Grant MANAGE_CONSENSUS_VERSION_ROLE on ValidatorsExitBusOracle to Aragon Agent
1.42. Set the ValidatorsExitBusOracle consensus version to 6
1.43. Revoke MANAGE_CONSENSUS_VERSION_ROLE on ValidatorsExitBusOracle from Aragon Agent
1.44. Grant MANAGE_CONSENSUS_VERSION_ROLE on CSM FeeOracle to Aragon Agent
1.45. Set the CSM FeeOracle consensus version to 5
1.46. Revoke MANAGE_CONSENSUS_VERSION_ROLE on CSM FeeOracle from Aragon Agent
1.47. Grant MANAGE_CONSENSUS_VERSION_ROLE on CSM 0x02 FeeOracle to Aragon Agent
1.48. Set the CSM 0x02 FeeOracle consensus version to 5
1.49. Revoke MANAGE_CONSENSUS_VERSION_ROLE on CSM 0x02 FeeOracle from Aragon Agent
1.50. Grant MANAGE_CONSENSUS_VERSION_ROLE on Curated Module v2 FeeOracle to Aragon Agent
1.51. Set the Curated Module v2 FeeOracle consensus version to 5
1.52. Revoke MANAGE_CONSENSUS_VERSION_ROLE on Curated Module v2 FeeOracle from Aragon Agent

TODO (after vote) Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from typing import Dict, List, Tuple

from brownie import ZERO_ADDRESS, convert, interface

from utils.agent import agent_forward
from utils.config import (
    ACCOUNTING_ORACLE,
    AGENT,
    CS_FEE_ORACLE_ADDRESS,
    CSM_ADDRESS,
    CSM_COMMITTEE_MS,
    LIDO_LOCATOR,
    ORACLE_DAEMON_CONFIG,
    RESEAL_MANAGER,
    STAKING_ROUTER,
    VALIDATORS_EXIT_BUS_ORACLE,
    WITHDRAWAL_VAULT,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.dual_governance import submit_proposals
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.voting import bake_vote_items, confirm_vote_script, create_vote


# ============================== Constants ===================================
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L753
NEW_LIDO_LOCATOR_IMPLEMENTATION = "0x101430e537EFfA1385CC74838EbD43a91D58a722"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L906
NEW_PREDEPOSIT_GUARANTEE_IMPLEMENTATION = "0x972A2a03011D629cded15b5b7e70e60b3E17a142"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L1012
NEW_TOP_UP_GATEWAY_IMPLEMENTATION = "0x18Ed6Ba7EBaecEd415b71dbB3795362070b227C5"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L368
NEW_CONSOLIDATION_BUS_IMPLEMENTATION = "0x95a435Bbae97685d4a9B77d77E23e2a827a717a5"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L1403
NEW_WITHDRAWAL_VAULT_IMPLEMENTATION = "0xdfC1E89ceb393C15e2d864F453c7991230367708"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L1312
NEW_VALIDATOR_EXIT_DELAY_VERIFIER = "0x34eFB78e7e4241269D6fe96042Eaa0c5715C7Ba4"
# https://github.com/lidofinance/core/blob/f4c5782c5b0930c59c6e2d99c92fdb24c1f9eefa/deployed-hoodi.json#L374
NEW_CONSOLIDATION_GATEWAY = "0x0718B7DE68ee5A82ebb17a86cF99371881154E51"
# https://github.com/lidofinance/staking-modules/blob/844b05f64370a06e6daceccb156238c8aad5a06b/artifacts/hoodi/csm/upgrade-v3-hoodi.json#L206
NEW_CSM_VERIFIER = "0xb70fA371989d7C1FCb88d6Be10A83F286E8e3508"
# https://github.com/lidofinance/staking-modules/blob/844b05f64370a06e6daceccb156238c8aad5a06b/artifacts/hoodi/csm0x02/deploy-hoodi.json#L114
NEW_CSM0X02_VERIFIER = "0x3B30b0F9b4dEc685F79192fAa407898B20E5688c"
# https://github.com/lidofinance/staking-modules/blob/844b05f64370a06e6daceccb156238c8aad5a06b/artifacts/hoodi/curated/deploy-hoodi.json#L636
NEW_CM_V2_VERIFIER = "0xda4e4a7F600bF6974e4837fBB0Caced8E9C8056D"

# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/deployed-hoodi.json#L345
CIRCUIT_BREAKER = "0x44a5789dFeDa59cD176Ab5709ec2F4829dE4d555"
# Pauser of the old ConsolidationGateway, the gateSeal sealing committee,
# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/deployed-hoodi.json#L650
CIRCUIT_BREAKER_COMMITTEE = "0x83BCE68B4e8b7071b2a664a26e6D3Bc17eEe3102"

# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/deployed-hoodi.json#L899
PREDEPOSIT_GUARANTEE = "0xa5F55f3402beA2B14AE15Dae1b6811457D43581d"
# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/deployed-hoodi.json#L1010
TOP_UP_GATEWAY = "0x10DBEb3367876826d00D21718D1d893e0fbD2956"
# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/deployed-hoodi.json#L359
CONSOLIDATION_BUS = "0xe09fBcE63826468867eE66Eda491E444829E022A"
# Old ValidatorExitDelayVerifier, the LidoLocator entry replaced by the vote,
# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/deployed-hoodi.json#L1325
OLD_VALIDATOR_EXIT_DELAY_VERIFIER = "0xa5F5A9360275390fF9728262a29384399f38d2f0"
# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/deployed-hoodi.json#L374
OLD_CONSOLIDATION_GATEWAY = "0xC9991Bb865d025364BCbBd99f36e85889Fb68e69"
# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/deployed-hoodi.json#L866
ORACLE_REPORT_SANITY_CHECKER = "0xD0261b0032A00a7449ee7fbE14d3f98702996441"

# CSM, its FeeOracle and its committee are CSM_ADDRESS, CS_FEE_ORACLE_ADDRESS and CSM_COMMITTEE_MS from utils.config
# https://github.com/lidofinance/staking-modules/blob/1289e46b41e6b591e0c34fad59cefa38a7c0da54/artifacts/hoodi/csm/upgrade-v3-hoodi.json#L27
OLD_CSM_VERIFIER = "0xC96406b0eADdAC5708aFCa04DcCA67BAdC9642Fd"

# https://github.com/lidofinance/staking-modules/blob/1289e46b41e6b591e0c34fad59cefa38a7c0da54/artifacts/hoodi/csm0x02/deploy-hoodi.json#L4
CSM0X02 = "0xbb7dd81FAC80f3Effa10eA8b973c15AE65a4CAf9"
# https://github.com/lidofinance/staking-modules/blob/1289e46b41e6b591e0c34fad59cefa38a7c0da54/artifacts/hoodi/csm0x02/deploy-hoodi.json#L14
CSM0X02_FEE_ORACLE = "0x9B8bBA11bbE1a351CC8dD1CFCa6719FF7274A208"
# https://github.com/lidofinance/staking-modules/blob/1289e46b41e6b591e0c34fad59cefa38a7c0da54/artifacts/hoodi/csm0x02/deploy-hoodi.json#L23
OLD_CSM0X02_VERIFIER = "0xFdE0FD9aDa4E898D3b34Dd4EA3433b75f0B6dd30"

# https://github.com/lidofinance/staking-modules/blob/1289e46b41e6b591e0c34fad59cefa38a7c0da54/artifacts/hoodi/curated/deploy-hoodi.json#L18
CM_V2 = "0x87EB69Ae51317405FD285efD2326a4a11f6173b9"
# https://github.com/lidofinance/staking-modules/blob/1289e46b41e6b591e0c34fad59cefa38a7c0da54/artifacts/hoodi/curated/deploy-hoodi.json#L25
CM_V2_FEE_ORACLE = "0x5D2F27000C80f6f7A03015Fd49dB7FEba3fBfa83"
# https://github.com/lidofinance/staking-modules/blob/1289e46b41e6b591e0c34fad59cefa38a7c0da54/artifacts/hoodi/curated/deploy-hoodi.json#L35
OLD_CM_V2_VERIFIER = "0x209190Ebc2Be80367a15d05e626784Eb94d6A880"
# Curated Module committee, pauser of the old CM v2 Verifier,
# https://github.com/lidofinance/core/blob/ab9a169759f28ffad0f618c7714e3bd24fa89782/scripts/upgrade/upgrade-params-hoodi.toml#L146
CM_COMMITTEE = "0x84DffcfB232594975C608DE92544Ff239a24c9E9"

ACCOUNTING_ORACLE_CONSENSUS_VERSION = 7
VALIDATORS_EXIT_BUS_ORACLE_CONSENSUS_VERSION = 6
FEE_ORACLE_CONSENSUS_VERSION = 5

MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT = 500

EXITED_ETH_AMOUNT_PER_DAY_LIMIT = 411_975
CONSOLIDATION_ETH_AMOUNT_PER_DAY_LIMIT = 205_875
MAX_BALANCE_EXIT_REQUESTED_PER_REPORT_IN_ETH = 11_520

# LimitsList of OracleReportSanityChecker.setOracleReportLimits, the unchanged fields are the current Hoodi values
ORACLE_REPORT_LIMITS = (
    EXITED_ETH_AMOUNT_PER_DAY_LIMIT,  # exitedEthAmountPerDayLimit
    57_600,  # appearedEthAmountPerDayLimit
    1_000,  # annualBalanceIncreaseBPLimit
    50,  # simulatedShareRateDeviationBPLimit
    MAX_BALANCE_EXIT_REQUESTED_PER_REPORT_IN_ETH,  # maxBalanceExitRequestedPerReportInEth
    32,  # maxEffectiveBalanceWeightWCType01
    2_048,  # maxEffectiveBalanceWeightWCType02
    8,  # maxItemsPerExtraDataTransaction
    24,  # maxNodeOperatorsPerExtraDataItem
    128,  # requestTimestampMargin
    750_000,  # maxPositiveTokenRebase
    360,  # maxCLBalanceDecreaseBP
    50,  # clBalanceOraclesErrorUpperBPLimit
    CONSOLIDATION_ETH_AMOUNT_PER_DAY_LIMIT,  # consolidationEthAmountPerDayLimit
    32,  # exitedValidatorEthAmountLimit
    300,  # externalPendingBalanceCapEth
)
SECOND_OPINION_ORACLE = ZERO_ADDRESS


# ============================= IPFS Description ==================================
DG_PROPOSAL_METADATA = "Upgrade the protocol on Hoodi for the Gloas hard fork (LIP-43): fork-aware verifiers, oracle consensus versions and sanity limits"
DG_SUBMISSION_DESCRIPTION = "1. Submit the Gloas upgrade to Dual Governance"
IPFS_DESCRIPTION = """
1. **Submit the Gloas upgrade (LIP-43) to Dual Governance on Hoodi**: upgrade the LidoLocator, PredepositGuarantee, TopUpGateway, ConsolidationBus and WithdrawalVault implementations, switch the protocol to the fork-aware ValidatorExitDelayVerifier and ConsolidationGateway, replace the CSM, CSM 0x02 and Curated Module v2 Verifiers, bump the consensus versions of the AccountingOracle, ValidatorsExitBusOracle and the three FeeOracles, set the MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT value on OracleDaemonConfig and update the OracleReportSanityChecker limits. Items 1.1-1.52.
"""


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    predeposit_guarantee_proxy = interface.OssifiableProxy(PREDEPOSIT_GUARANTEE)
    top_up_gateway_proxy = interface.OssifiableProxy(TOP_UP_GATEWAY)
    consolidation_bus_proxy = interface.OssifiableProxy(CONSOLIDATION_BUS)
    withdrawal_vault_proxy = interface.WithdrawalsManagerProxy(WITHDRAWAL_VAULT)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    old_consolidation_gateway = interface.ConsolidationGateway(OLD_CONSOLIDATION_GATEWAY)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)
    csm = interface.CSModule(CSM_ADDRESS)
    csm0x02 = interface.CSModule(CSM0X02)
    cm_v2 = interface.CuratedModule(CM_V2)
    accounting_oracle = interface.AccountingOracle(ACCOUNTING_ORACLE)
    validators_exit_bus_oracle = interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE)
    csm_fee_oracle = interface.FeeOracle(CS_FEE_ORACLE_ADDRESS)
    csm0x02_fee_oracle = interface.FeeOracle(CSM0X02_FEE_ORACLE)
    cm_v2_fee_oracle = interface.FeeOracle(CM_V2_FEE_ORACLE)
    oracle_daemon_config = interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)
    sanity_checker = interface.OracleReportSanityChecker(ORACLE_REPORT_SANITY_CHECKER)

    return [
        agent_forward(
            [
                # 1.1. Upgrade LidoLocator implementation
                (
                    locator_proxy.address,
                    locator_proxy.proxy__upgradeTo.encode_input(NEW_LIDO_LOCATOR_IMPLEMENTATION),
                ),
                # 1.2. Upgrade PredepositGuarantee implementation
                (
                    predeposit_guarantee_proxy.address,
                    predeposit_guarantee_proxy.proxy__upgradeTo.encode_input(NEW_PREDEPOSIT_GUARANTEE_IMPLEMENTATION),
                ),
                # 1.3. Upgrade TopUpGateway implementation
                (
                    top_up_gateway_proxy.address,
                    top_up_gateway_proxy.proxy__upgradeTo.encode_input(NEW_TOP_UP_GATEWAY_IMPLEMENTATION),
                ),
                # 1.4. Upgrade ConsolidationBus implementation
                (
                    consolidation_bus_proxy.address,
                    consolidation_bus_proxy.proxy__upgradeTo.encode_input(NEW_CONSOLIDATION_BUS_IMPLEMENTATION),
                ),
                # 1.5. Upgrade WithdrawalVault implementation
                (
                    withdrawal_vault_proxy.address,
                    withdrawal_vault_proxy.proxy_upgradeTo.encode_input(NEW_WITHDRAWAL_VAULT_IMPLEMENTATION, b""),
                ),
                # 1.6. Grant REPORT_VALIDATOR_EXITING_STATUS_ROLE on StakingRouter to the new ValidatorExitDelayVerifier
                encode_oz_grant_role(
                    contract=staking_router,
                    role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                    grant_to=NEW_VALIDATOR_EXIT_DELAY_VERIFIER,
                ),
                # 1.7. Revoke REPORT_VALIDATOR_EXITING_STATUS_ROLE on StakingRouter from the old ValidatorExitDelayVerifier
                encode_oz_revoke_role(
                    contract=staking_router,
                    role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                    revoke_from=OLD_VALIDATOR_EXIT_DELAY_VERIFIER,
                ),
                # 1.8. Register the new ConsolidationGateway on CircuitBreaker
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(NEW_CONSOLIDATION_GATEWAY, CIRCUIT_BREAKER_COMMITTEE),
                ),
                # 1.9. Unregister the old ConsolidationGateway from CircuitBreaker
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(OLD_CONSOLIDATION_GATEWAY, ZERO_ADDRESS),
                ),
                # 1.10. Revoke PAUSE_ROLE on the old ConsolidationGateway from CircuitBreaker
                encode_oz_revoke_role(
                    contract=old_consolidation_gateway,
                    role_name="PAUSE_ROLE",
                    revoke_from=CIRCUIT_BREAKER,
                ),
                # 1.11. Revoke PAUSE_ROLE on the old ConsolidationGateway from ResealManager
                encode_oz_revoke_role(
                    contract=old_consolidation_gateway,
                    role_name="PAUSE_ROLE",
                    revoke_from=RESEAL_MANAGER,
                ),
                # 1.12. Revoke RESUME_ROLE on the old ConsolidationGateway from ResealManager
                encode_oz_revoke_role(
                    contract=old_consolidation_gateway,
                    role_name="RESUME_ROLE",
                    revoke_from=RESEAL_MANAGER,
                ),
                # 1.13. Revoke ADD_CONSOLIDATION_REQUEST_ROLE on the old ConsolidationGateway from ConsolidationBus
                encode_oz_revoke_role(
                    contract=old_consolidation_gateway,
                    role_name="ADD_CONSOLIDATION_REQUEST_ROLE",
                    revoke_from=CONSOLIDATION_BUS,
                ),
                # 1.14. Grant VERIFIER_ROLE on CSM to the new CSM Verifier
                encode_oz_grant_role(
                    contract=csm,
                    role_name="VERIFIER_ROLE",
                    grant_to=NEW_CSM_VERIFIER,
                ),
                # 1.15. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on CSM to the new CSM Verifier
                encode_oz_grant_role(
                    contract=csm,
                    role_name="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                    grant_to=NEW_CSM_VERIFIER,
                ),
                # 1.16. Register the new CSM Verifier on CircuitBreaker
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(NEW_CSM_VERIFIER, CSM_COMMITTEE_MS),
                ),
                # 1.17. Revoke VERIFIER_ROLE on CSM from the old CSM Verifier
                encode_oz_revoke_role(
                    contract=csm,
                    role_name="VERIFIER_ROLE",
                    revoke_from=OLD_CSM_VERIFIER,
                ),
                # 1.18. Revoke REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on CSM from the old CSM Verifier
                encode_oz_revoke_role(
                    contract=csm,
                    role_name="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                    revoke_from=OLD_CSM_VERIFIER,
                ),
                # 1.19. Unregister the old CSM Verifier from CircuitBreaker
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(OLD_CSM_VERIFIER, ZERO_ADDRESS),
                ),
                # 1.20. Grant VERIFIER_ROLE on CSM 0x02 to the new CSM 0x02 Verifier
                encode_oz_grant_role(
                    contract=csm0x02,
                    role_name="VERIFIER_ROLE",
                    grant_to=NEW_CSM0X02_VERIFIER,
                ),
                # 1.21. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on CSM 0x02 to the new CSM 0x02 Verifier
                encode_oz_grant_role(
                    contract=csm0x02,
                    role_name="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                    grant_to=NEW_CSM0X02_VERIFIER,
                ),
                # 1.22. Register the new CSM 0x02 Verifier on CircuitBreaker
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(NEW_CSM0X02_VERIFIER, CSM_COMMITTEE_MS),
                ),
                # 1.23. Revoke VERIFIER_ROLE on CSM 0x02 from the old CSM 0x02 Verifier
                encode_oz_revoke_role(
                    contract=csm0x02,
                    role_name="VERIFIER_ROLE",
                    revoke_from=OLD_CSM0X02_VERIFIER,
                ),
                # 1.24. Revoke REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on CSM 0x02 from the old CSM 0x02 Verifier
                encode_oz_revoke_role(
                    contract=csm0x02,
                    role_name="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                    revoke_from=OLD_CSM0X02_VERIFIER,
                ),
                # 1.25. Unregister the old CSM 0x02 Verifier from CircuitBreaker
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(OLD_CSM0X02_VERIFIER, ZERO_ADDRESS),
                ),
                # 1.26. Grant VERIFIER_ROLE on Curated Module v2 to the new Curated Module v2 Verifier
                encode_oz_grant_role(
                    contract=cm_v2,
                    role_name="VERIFIER_ROLE",
                    grant_to=NEW_CM_V2_VERIFIER,
                ),
                # 1.27. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on Curated Module v2 to the new Curated Module v2 Verifier
                encode_oz_grant_role(
                    contract=cm_v2,
                    role_name="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                    grant_to=NEW_CM_V2_VERIFIER,
                ),
                # 1.28. Register the new Curated Module v2 Verifier on CircuitBreaker
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(NEW_CM_V2_VERIFIER, CM_COMMITTEE),
                ),
                # 1.29. Revoke VERIFIER_ROLE on Curated Module v2 from the old Curated Module v2 Verifier
                encode_oz_revoke_role(
                    contract=cm_v2,
                    role_name="VERIFIER_ROLE",
                    revoke_from=OLD_CM_V2_VERIFIER,
                ),
                # 1.30. Revoke REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE on Curated Module v2 from the old Curated Module v2 Verifier
                encode_oz_revoke_role(
                    contract=cm_v2,
                    role_name="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                    revoke_from=OLD_CM_V2_VERIFIER,
                ),
                # 1.31. Unregister the old Curated Module v2 Verifier from CircuitBreaker
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(OLD_CM_V2_VERIFIER, ZERO_ADDRESS),
                ),
                # 1.32. Grant CONFIG_MANAGER_ROLE on OracleDaemonConfig to Aragon Agent
                encode_oz_grant_role(
                    contract=oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    grant_to=AGENT,
                ),
                # 1.33. Set MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT on OracleDaemonConfig to 500
                (
                    oracle_daemon_config.address,
                    oracle_daemon_config.set.encode_input(
                        "MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT",
                        convert.to_bytes(MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT, "bytes"),
                    ),
                ),
                # 1.34. Revoke CONFIG_MANAGER_ROLE on OracleDaemonConfig from Aragon Agent
                encode_oz_revoke_role(
                    contract=oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    revoke_from=AGENT,
                ),
                # 1.35. Grant ALL_LIMITS_MANAGER_ROLE on OracleReportSanityChecker to Aragon Agent
                encode_oz_grant_role(
                    contract=sanity_checker,
                    role_name="ALL_LIMITS_MANAGER_ROLE",
                    grant_to=AGENT,
                ),
                # 1.36. Update OracleReportSanityChecker limits: exited 411975, consolidation 205875, max exit requested 11520
                (
                    sanity_checker.address,
                    sanity_checker.setOracleReportLimits.encode_input(ORACLE_REPORT_LIMITS, SECOND_OPINION_ORACLE),
                ),
                # 1.37. Revoke ALL_LIMITS_MANAGER_ROLE on OracleReportSanityChecker from Aragon Agent
                encode_oz_revoke_role(
                    contract=sanity_checker,
                    role_name="ALL_LIMITS_MANAGER_ROLE",
                    revoke_from=AGENT,
                ),
                # 1.38. Grant MANAGE_CONSENSUS_VERSION_ROLE on AccountingOracle to Aragon Agent
                encode_oz_grant_role(
                    contract=accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=AGENT,
                ),
                # 1.39. Set the AccountingOracle consensus version to 7
                (
                    accounting_oracle.address,
                    accounting_oracle.setConsensusVersion.encode_input(ACCOUNTING_ORACLE_CONSENSUS_VERSION),
                ),
                # 1.40. Revoke MANAGE_CONSENSUS_VERSION_ROLE on AccountingOracle from Aragon Agent
                encode_oz_revoke_role(
                    contract=accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=AGENT,
                ),
                # 1.41. Grant MANAGE_CONSENSUS_VERSION_ROLE on ValidatorsExitBusOracle to Aragon Agent
                encode_oz_grant_role(
                    contract=validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=AGENT,
                ),
                # 1.42. Set the ValidatorsExitBusOracle consensus version to 6
                (
                    validators_exit_bus_oracle.address,
                    validators_exit_bus_oracle.setConsensusVersion.encode_input(
                        VALIDATORS_EXIT_BUS_ORACLE_CONSENSUS_VERSION
                    ),
                ),
                # 1.43. Revoke MANAGE_CONSENSUS_VERSION_ROLE on ValidatorsExitBusOracle from Aragon Agent
                encode_oz_revoke_role(
                    contract=validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=AGENT,
                ),
                # 1.44. Grant MANAGE_CONSENSUS_VERSION_ROLE on CSM FeeOracle to Aragon Agent
                encode_oz_grant_role(
                    contract=csm_fee_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=AGENT,
                ),
                # 1.45. Set the CSM FeeOracle consensus version to 5
                (
                    csm_fee_oracle.address,
                    csm_fee_oracle.setConsensusVersion.encode_input(FEE_ORACLE_CONSENSUS_VERSION),
                ),
                # 1.46. Revoke MANAGE_CONSENSUS_VERSION_ROLE on CSM FeeOracle from Aragon Agent
                encode_oz_revoke_role(
                    contract=csm_fee_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=AGENT,
                ),
                # 1.47. Grant MANAGE_CONSENSUS_VERSION_ROLE on CSM 0x02 FeeOracle to Aragon Agent
                encode_oz_grant_role(
                    contract=csm0x02_fee_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=AGENT,
                ),
                # 1.48. Set the CSM 0x02 FeeOracle consensus version to 5
                (
                    csm0x02_fee_oracle.address,
                    csm0x02_fee_oracle.setConsensusVersion.encode_input(FEE_ORACLE_CONSENSUS_VERSION),
                ),
                # 1.49. Revoke MANAGE_CONSENSUS_VERSION_ROLE on CSM 0x02 FeeOracle from Aragon Agent
                encode_oz_revoke_role(
                    contract=csm0x02_fee_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=AGENT,
                ),
                # 1.50. Grant MANAGE_CONSENSUS_VERSION_ROLE on Curated Module v2 FeeOracle to Aragon Agent
                encode_oz_grant_role(
                    contract=cm_v2_fee_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=AGENT,
                ),
                # 1.51. Set the Curated Module v2 FeeOracle consensus version to 5
                (
                    cm_v2_fee_oracle.address,
                    cm_v2_fee_oracle.setConsensusVersion.encode_input(FEE_ORACLE_CONSENSUS_VERSION),
                ),
                # 1.52. Revoke MANAGE_CONSENSUS_VERSION_ROLE on Curated Module v2 FeeOracle from Aragon Agent
                encode_oz_revoke_role(
                    contract=cm_v2_fee_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=AGENT,
                ),
            ]
        ),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    dg_items = get_dg_items()

    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_METADATA)])

    vote_desc_items, call_script_items = zip(
        (
            DG_SUBMISSION_DESCRIPTION,
            dg_call_script[0],
        ),
    )

    return list(vote_desc_items), list(call_script_items)


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
