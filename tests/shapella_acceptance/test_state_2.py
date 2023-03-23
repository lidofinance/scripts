from brownie import interface, web3, chain
from utils.config import (
    contracts,
    guardians,
    report_limits,
    beacon_spec,
    deposit_contract,
    dsm_pause_message_prefix,
    dsm_attest_message_prefix,
    lido_dao_accounting_oracle_implementation,
    lido_dao_hash_consensus_for_accounting_oracle,
    lido_dao_withdrawal_credentials,
)

from test_upgrade_shapella_goerli import oracle_app_id


def test_accounting_oracle_state():
    # address in locator
    assert contracts.lido_locator.accountingOracle() == contracts.accounting_oracle

    # AppProxyUpgradeable
    assert (
        interface.OssifiableProxy(contracts.accounting_oracle).proxy__getImplementation()
        == lido_dao_accounting_oracle_implementation
    )

    # Constants
    assert contracts.accounting_oracle.LIDO() == contracts.lido
    assert contracts.accounting_oracle.LOCATOR() == contracts.lido_locator
    assert contracts.accounting_oracle.LEGACY_ORACLE() == contracts.legacy_oracle
    assert contracts.accounting_oracle.EXTRA_DATA_FORMAT_EMPTY() == 0
    assert contracts.accounting_oracle.EXTRA_DATA_FORMAT_LIST() == 1
    assert contracts.accounting_oracle.EXTRA_DATA_TYPE_STUCK_VALIDATORS() == 1
    assert contracts.accounting_oracle.EXTRA_DATA_TYPE_EXITED_VALIDATORS() == 2
    assert contracts.accounting_oracle.SECONDS_PER_SLOT() == 12
    assert contracts.accounting_oracle.GENESIS_TIME() == 1616508000

    # consensus version
    assert contracts.accounting_oracle.getConsensusVersion() == 1

    # Versioned
    assert contracts.accounting_oracle.getContractVersion() == 1

    # Processing state
    state = contracts.accounting_oracle.getProcessingState()
    assert state["currentFrameRefSlot"] > 5254400
    assert state["processingDeadlineTime"] == 0
    assert state["mainDataHash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert state["mainDataSubmitted"] == False
    assert state["extraDataHash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert state["extraDataFormat"] == 0
    assert state["extraDataSubmitted"] == False
    assert state["extraDataItemsCount"] == 0
    assert state["extraDataItemsSubmitted"] == 0

    assert contracts.accounting_oracle.getLastProcessingRefSlot() == 5254400

    # Consensus
    assert contracts.accounting_oracle.getConsensusContract() == lido_dao_hash_consensus_for_accounting_oracle
    report = contracts.accounting_oracle.getConsensusReport()
    assert report["hash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert report["refSlot"] == 5254400
    assert report["processingDeadlineTime"] == 0
    assert report["processingStarted"] == False


def test_deposit_security_module_state():
    # address in locator
    assert contracts.lido_locator.depositSecurityModule() == contracts.deposit_security_module

    assert contracts.deposit_security_module.getOwner() == contracts.agent

    # Constants
    assert contracts.deposit_security_module.LIDO() == contracts.lido
    assert contracts.deposit_security_module.DEPOSIT_CONTRACT() == deposit_contract
    assert contracts.deposit_security_module.STAKING_ROUTER() == contracts.staking_router
    assert contracts.deposit_security_module.PAUSE_MESSAGE_PREFIX() == dsm_pause_message_prefix
    assert contracts.deposit_security_module.ATTEST_MESSAGE_PREFIX() == dsm_attest_message_prefix

    # state
    assert contracts.deposit_security_module.getMaxDeposits() == 0
    assert contracts.deposit_security_module.getMinDepositBlockDistance() == 1200

    assert contracts.deposit_security_module.getGuardians() == guardians
    assert contracts.deposit_security_module.getGuardianQuorum() == 1

    for guardian in guardians:
        assert contracts.deposit_security_module.getGuardianIndex(guardian) >= 0
        assert contracts.deposit_security_module.isGuardian(guardian) == True

    assert contracts.deposit_security_module.getPauseIntentValidityPeriodBlocks() == 10


def test_el_rewards_vault_state():
    # address in locator
    assert contracts.lido_locator.elRewardsVault() == contracts.execution_layer_rewards_vault

    # Constants
    assert contracts.execution_layer_rewards_vault.LIDO() == contracts.lido
    assert contracts.execution_layer_rewards_vault.TREASURY() == contracts.agent


def test_legacy_oracle_state():
    # address in locator
    assert contracts.lido_locator.legacyOracle() == contracts.legacy_oracle

    # Aragon app
    assert contracts.legacy_oracle.hasInitialized() == True
    assert contracts.legacy_oracle.getVersion() == 4
    assert contracts.legacy_oracle.appId() == oracle_app_id
    assert contracts.legacy_oracle.kernel() == contracts.kernel

    # AppProxyUpgradeable
    proxy = (
        interface.AppProxyUpgradeable(contracts.legacy_oracle).implementation()
        == "0x7D505d1CCd49C64C2dc0b15acbAE235C4651F50B"
    )

    # Versioned
    assert contracts.legacy_oracle.getContractVersion() == 4

    # State
    assert contracts.legacy_oracle.getLido() == contracts.lido
    assert contracts.legacy_oracle.getAccountingOracle() == contracts.accounting_oracle
    assert contracts.legacy_oracle.getRecoveryVault() == contracts.agent
    assert contracts.legacy_oracle.allowRecoverability(contracts.ldo_token) == True
    assert contracts.legacy_oracle.isPetrified() == False

    reported_delta = contracts.legacy_oracle.getLastCompletedReportDelta()
    assert reported_delta["postTotalPooledEther"] > 0
    assert reported_delta["preTotalPooledEther"] > 0
    assert reported_delta["timeElapsed"] > 0

    current_frame = contracts.legacy_oracle.getCurrentFrame()
    assert current_frame["frameEpochId"] > 0
    assert current_frame["frameStartTime"] > 0
    assert current_frame["frameEndTime"] > 0

    assert contracts.legacy_oracle.getLastCompletedEpochId() > 0

    assert contracts.legacy_oracle.getInitializationBlock() > 0
    assert contracts.legacy_oracle.getInitializationBlock() <= chain.height

    assert contracts.legacy_oracle.getEVMScriptRegistry() == "0xeC32ADA2a1E46Ff3F6206F47a6A2060200f24fDf"

    oracle_beacon_spec = contracts.legacy_oracle.getBeaconSpec()

    assert oracle_beacon_spec["epochsPerFrame"] == beacon_spec["epochsPerFrame"]
    assert oracle_beacon_spec["slotsPerEpoch"] == beacon_spec["slotsPerEpoch"]
    assert oracle_beacon_spec["secondsPerSlot"] == beacon_spec["secondsPerSlot"]
    assert oracle_beacon_spec["genesisTime"] == beacon_spec["genesisTime"]


def test_oracle_report_sanity_checker_state():
    # address in locator
    assert contracts.lido_locator.oracleReportSanityChecker() == contracts.oracle_report_sanity_checker

    # State
    assert contracts.oracle_report_sanity_checker.getLidoLocator() == contracts.lido_locator
    assert contracts.oracle_report_sanity_checker.getMaxPositiveTokenRebase() == report_limits["maxPositiveTokenRebase"]

    limits = contracts.oracle_report_sanity_checker.getOracleReportLimits()

    assert limits["churnValidatorsPerDayLimit"] == report_limits["churnValidatorsPerDayLimit"]
    assert limits["oneOffCLBalanceDecreaseBPLimit"] == report_limits["oneOffCLBalanceDecreaseBPLimit"]
    assert limits["annualBalanceIncreaseBPLimit"] == report_limits["annualBalanceIncreaseBPLimit"]
    assert limits["simulatedShareRateDeviationBPLimit"] == report_limits["simulatedShareRateDeviationBPLimit"]
    assert limits["maxValidatorExitRequestsPerReport"] == report_limits["maxValidatorExitRequestsPerReport"]
    assert limits["maxAccountingExtraDataListItemsCount"] == report_limits["maxAccountingExtraDataListItemsCount"]
    assert limits["maxNodeOperatorsPerExtraDataItemCount"] == report_limits["maxNodeOperatorsPerExtraDataItemCount"]
    assert limits["requestTimestampMargin"] == report_limits["requestTimestampMargin"]
    assert limits["maxPositiveTokenRebase"] == report_limits["maxPositiveTokenRebase"]


def test_burner_state():
    # address in locator
    assert contracts.lido_locator.burner() == contracts.burner

    # Constants
    assert contracts.burner.STETH() == contracts.lido
    assert contracts.burner.TREASURY() == contracts.agent

    shares_requested_to_burn = contracts.burner.getSharesRequestedToBurn()

    assert shares_requested_to_burn["coverShares"] == 0
    assert shares_requested_to_burn["nonCoverShares"] == 0

    assert contracts.burner.getCoverSharesBurnt() == 0
    assert contracts.burner.getExcessStETH() == 0
    assert contracts.burner.getNonCoverSharesBurnt() == 0


def test_staking_router_state():
    # address in locator
    assert contracts.lido_locator.stakingRouter() == contracts.staking_router

    # Versioned
    assert contracts.accounting_oracle.getContractVersion() == 1

    # Constants
    assert contracts.staking_router.DEPOSIT_CONTRACT() == deposit_contract
    assert contracts.staking_router.FEE_PRECISION_POINTS() == 100 * 10**18
    assert contracts.staking_router.MAX_STAKING_MODULES_COUNT() == 32
    assert contracts.staking_router.MAX_STAKING_MODULE_NAME_LENGTH() == 32
    assert contracts.staking_router.TOTAL_BASIS_POINTS() == 10000

    assert contracts.staking_router.getStakingModulesCount() == 1

    assert contracts.staking_router.getLido() == contracts.lido
    assert contracts.staking_router.getStakingModuleIds() == [1]
    assert contracts.staking_router.getStakingModuleIsActive(1) == True
    assert contracts.staking_router.getStakingModuleIsStopped(1) == False
    assert contracts.staking_router.getStakingModuleIsDepositsPaused(1) == False
    assert contracts.staking_router.getStakingModuleNonce(1) > 1740
    assert contracts.staking_router.getStakingModuleNonce(1) < 2000
    assert contracts.staking_router.getStakingModuleStatus(1) == 0

    curated_module = contracts.staking_router.getStakingModule(1)
    assert curated_module["id"] == 1
    assert curated_module["stakingModuleAddress"] == contracts.node_operators_registry
    assert curated_module["stakingModuleFee"] == 500
    assert curated_module["treasuryFee"] == 500
    assert curated_module["targetShare"] == 10000
    assert curated_module["status"] == 0
    assert curated_module["name"] == "curated-onchain-v1"
    assert curated_module["lastDepositAt"] >= 1679851100
    assert curated_module["lastDepositBlock"] >= 8705383
    assert curated_module["exitedValidatorsCount"] == 0

    fee_aggregate_distribution = contracts.staking_router.getStakingFeeAggregateDistribution()
    assert fee_aggregate_distribution["modulesFee"] == 5 * 10**18
    assert fee_aggregate_distribution["treasuryFee"] == 5 * 10**18
    assert fee_aggregate_distribution["basePrecision"] == 100 * 10**18

    fee_aggregate_distribution = contracts.staking_router.getStakingFeeAggregateDistribution()
    assert fee_aggregate_distribution["modulesFee"] == 5 * 10**18
    assert fee_aggregate_distribution["treasuryFee"] == 5 * 10**18
    assert fee_aggregate_distribution["basePrecision"] == 100 * 10**18

    fee_aggregate_distribution_e4 = contracts.staking_router.getStakingFeeAggregateDistributionE4Precision()
    assert fee_aggregate_distribution_e4["modulesFee"] == 500
    assert fee_aggregate_distribution_e4["treasuryFee"] == 500

    assert contracts.staking_router.getTotalFeeE4Precision() == 1000

    assert contracts.staking_router.getStakingModuleActiveValidatorsCount(1) >= 3521

    assert contracts.staking_router.getWithdrawalCredentials() == lido_dao_withdrawal_credentials
