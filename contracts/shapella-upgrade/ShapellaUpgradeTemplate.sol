// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: MIT

pragma solidity 0.8.9;


interface IAccessControlEnumerable {
    function grantRole(bytes32 role, address account) external;
    function renounceRole(bytes32 role, address account) external;
    function getRoleMemberCount(bytes32 role) external view returns (uint256);
    function getRoleMember(bytes32 role, uint256 index) external view returns (address);
}

interface IVersioned {
    function getContractVersion() external view returns (uint256);
}

interface IPausableUntil {
    function isPaused() external view returns (bool);
    function getResumeSinceTimestamp() external view returns (uint256);
    function PAUSE_INFINITELY() external view returns (uint256);
}

interface IOssifiableProxy {
    function proxy__upgradeTo(address newImplementation) external;
    function proxy__changeAdmin(address newAdmin) external;
    function proxy__getAdmin() external view returns (address);
    function proxy__getImplementation() external view returns (address);
}

interface IBaseOracle is IAccessControlEnumerable, IVersioned {
    function getConsensusContract() external view returns (address);
}

interface IAccountingOracle is IBaseOracle, IOssifiableProxy {
    function initialize(address admin, address consensusContract, uint256 consensusVersion) external;
}

interface IBurner is IAccessControlEnumerable {
    function REQUEST_BURN_SHARES_ROLE() external view returns (bytes32);
}

interface IDepositSecurityModule {
    function getOwner() external view returns (address);
    function setOwner(address newValue) external;
    function getGuardianQuorum() external view returns (uint256);
    function getGuardians() external view returns (address[] memory);
    function addGuardians(address[] memory addresses, uint256 newQuorum) external;
    function getMaxDeposits() external view returns (uint256);
    function getPauseIntentValidityPeriodBlocks() external view returns (uint256);
    function getMinDepositBlockDistance() external view returns (uint256);
}

interface IGateSeal {
    function get_sealables() external view returns (address[] memory);
}

interface IHashConsensus is IAccessControlEnumerable {
    function MANAGE_MEMBERS_AND_QUORUM_ROLE() external view returns (bytes32);
    function addMember(address addr, uint256 quorum) external;
    function getFrameConfig() external view returns (uint256 initialEpoch, uint256 epochsPerFrame, uint256 fastLaneLengthSlots);
    function updateInitialEpoch(uint256 initialEpoch) external;
}

interface ILido is IVersioned {
    function finalizeUpgrade_v2(address lidoLocator, address eip712StETH) external;
}

interface ILidoLocator is IOssifiableProxy {
    function accountingOracle() external view returns(address);
    function depositSecurityModule() external view returns(address);
    function elRewardsVault() external view returns(address);
    function legacyOracle() external view returns(address);
    function lido() external view returns(address);
    function oracleReportSanityChecker() external view returns(address);
    function burner() external view returns(address);
    function stakingRouter() external view returns(address);
    function treasury() external view returns(address);
    function validatorsExitBusOracle() external view returns(address);
    function withdrawalQueue() external view returns(address);
    function withdrawalVault() external view returns(address);
    function postTokenRebaseReceiver() external view returns(address);
    function oracleDaemonConfig() external view returns(address);
}

interface ILegacyOracle is IVersioned {
    function finalizeUpgrade_v4(address accountingOracle) external;
}

interface ILidoOracle {
    function getVersion() external view returns (uint256);
    function getOracleMembers() external view returns (address[] memory);
    function getQuorum() external view returns (uint256);
    function getLastCompletedEpochId() external view returns (uint256);
}

interface INodeOperatorsRegistry is IVersioned {
    function finalizeUpgrade_v2(address locator, bytes32 stakingModuleType, uint256 stuckPenaltyDelay) external;
}

interface IOracleDaemonConfig is IAccessControlEnumerable {
    function CONFIG_MANAGER_ROLE() external view returns (bytes32);
    function get(string calldata _key) external view returns (bytes memory);
}

interface IOracleReportSanityChecker is IAccessControlEnumerable {
    function ALL_LIMITS_MANAGER_ROLE() external view returns (bytes32);
    function CHURN_VALIDATORS_PER_DAY_LIMIT_MANGER_ROLE() external view returns (bytes32);
    function ONE_OFF_CL_BALANCE_DECREASE_LIMIT_MANAGER_ROLE() external view returns (bytes32);
    function ANNUAL_BALANCE_INCREASE_LIMIT_MANAGER_ROLE() external view returns (bytes32);
    function SHARE_RATE_DEVIATION_LIMIT_MANAGER_ROLE() external view returns (bytes32);
    function MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_ROLE() external view returns (bytes32);
    function MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE() external view returns (bytes32);
    function MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE() external view returns (bytes32);
    function REQUEST_TIMESTAMP_MARGIN_MANAGER_ROLE() external view returns (bytes32);
    function MAX_POSITIVE_TOKEN_REBASE_MANAGER_ROLE() external view returns (bytes32);
    function getOracleReportLimits() external view returns (LimitsList memory);
}

interface IStakingRouter is IVersioned, IAccessControlEnumerable, IOssifiableProxy {
    function MANAGE_WITHDRAWAL_CREDENTIALS_ROLE() external view returns (bytes32);
    function STAKING_MODULE_PAUSE_ROLE() external view returns (bytes32);
    function STAKING_MODULE_RESUME_ROLE() external view returns (bytes32);
    function STAKING_MODULE_MANAGE_ROLE() external view returns (bytes32);
    function REPORT_EXITED_VALIDATORS_ROLE() external view returns (bytes32);
    function UNSAFE_SET_EXITED_VALIDATORS_ROLE() external view returns (bytes32);
    function REPORT_REWARDS_MINTED_ROLE() external view returns (bytes32);
    function initialize(address admin, address lido, bytes32 withdrawalCredentials) external;
    function addStakingModule(
        string calldata name,
        address stakingModuleAddress,
        uint256 targetShare,
        uint256 stakingModuleFee,
        uint256 treasuryFee
    ) external;
    function hasStakingModule(uint256 _stakingModuleId) external view returns (bool);
}

interface IValidatorsExitBusOracle is IBaseOracle, IPausableUntil, IOssifiableProxy {
    function initialize(address admin, address consensusContract, uint256 consensusVersion, uint256 lastProcessingRefSlot) external;
    function PAUSE_ROLE() external view returns (bytes32);
    function RESUME_ROLE() external view returns (bytes32);
    function resume() external;
}


interface IWithdrawalQueue is IAccessControlEnumerable, IPausableUntil, IVersioned, IOssifiableProxy {
    function FINALIZE_ROLE() external view returns (bytes32);
    function ORACLE_ROLE() external view returns (bytes32);
    function initialize(address _admin) external;
    function PAUSE_ROLE() external view returns (bytes32);
    function RESUME_ROLE() external view returns (bytes32);
    function resume() external;
}

interface IWithdrawalsManagerProxy {
    function proxy_getAdmin() external view returns (address);
    function implementation() external view returns (address);
}

interface IWithdrawalVault is IVersioned, IWithdrawalsManagerProxy {
    function initialize() external;
}

struct LimitsList {
    /// @notice The max possible number of validators that might appear or exit on the Consensus
    ///     Layer during one day
    /// @dev Must fit into uint16 (<= 65_535)
    uint256 churnValidatorsPerDayLimit;

    /// @notice The max decrease of the total validators' balances on the Consensus Layer since
    ///     the previous oracle report
    /// @dev Represented in the Basis Points (100% == 10_000)
    uint256 oneOffCLBalanceDecreaseBPLimit;

    /// @notice The max annual increase of the total validators' balances on the Consensus Layer
    ///     since the previous oracle report
    /// @dev Represented in the Basis Points (100% == 10_000)
    uint256 annualBalanceIncreaseBPLimit;

    /// @notice The max deviation of the provided `simulatedShareRate`
    ///     and the actual one within the currently processing oracle report
    /// @dev Represented in the Basis Points (100% == 10_000)
    uint256 simulatedShareRateDeviationBPLimit;

    /// @notice The max number of exit requests allowed in report to ValidatorsExitBusOracle
    uint256 maxValidatorExitRequestsPerReport;

    /// @notice The max number of data list items reported to accounting oracle in extra data
    /// @dev Must fit into uint16 (<= 65_535)
    uint256 maxAccountingExtraDataListItemsCount;

    /// @notice The max number of node operators reported per extra data list item
    /// @dev Must fit into uint16 (<= 65_535)
    uint256 maxNodeOperatorsPerExtraDataItemCount;

    /// @notice The min time required to be passed from the creation of the request to be
    ///     finalized till the time of the oracle report
    uint256 requestTimestampMargin;

    /// @notice The positive token rebase allowed per single LidoOracle report
    /// @dev uses 1e9 precision, e.g.: 1e6 - 0.1%; 1e9 - 100%, see `setMaxPositiveTokenRebase()`
    uint256 maxPositiveTokenRebase;
}

/**
* @title Shapella Lido Upgrade Template
*
* @dev Auxiliary contracts which performs binding of already deployed Shapella upgrade contracts.
* Must be used by means of two calls:
*   - `startUpgrade()` before updating implementation of Aragon apps
*   - `finishUpgrade()` after updating implementation of Aragon apps
* The required initial on-chain state is checked in `assertCorrectInitialState()`
*/
contract ShapellaUpgradeTemplate {

    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    uint256 public constant NOT_INITIALIZED_CONTRACT_VERSION = 0;

    uint256 public constant _accountingOracleConsensusVersion = 1;
    uint256 public constant _validatorsExitBusOracleConsensusVersion = 1;
    string public constant NOR_STAKING_MODULE_NAME = "curated-onchain-v1";
    bytes32 public constant _nodeOperatorsRegistryStakingModuleType = bytes32("curated-onchain-v1");
    uint256 public constant _nodeOperatorsRegistryStuckPenaltyDelay = 172800;
    bytes32 public constant _withdrawalCredentials = 0x010000000000000000000000dc62f9e8c34be08501cdef4ebde0a280f576d762;
    uint256 public constant NOR_STAKING_MODULE_TARGET_SHARE_BP = 10000; // 100%
    uint256 public constant NOR_STAKING_MODULE_MODULE_FEE_BP = 500; // 5%
    uint256 public constant NOR_STAKING_MODULE_TREASURY_FEE_BP = 500; // 5%
    uint256 public constant VEBO_LAST_PROCESSING_REF_SLOT = 0;

    ILidoLocator public constant _locator = ILidoLocator(0x1eDf09b5023DC86737b59dE68a8130De878984f5);
    IHashConsensus public constant _hashConsensusForAccountingOracle = IHashConsensus(0x8d87A8BCF8d4e542fd396D1c50223301c164417b);
    IHashConsensus public constant _hashConsensusForValidatorsExitBusOracle = IHashConsensus(0x8374B4aC337D7e367Ea1eF54bB29880C3f036A51);
    address public constant _eip712StETH = 0xB4300103FfD326f77FfB3CA54248099Fb29C3b9e;
    address public constant _voting = 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db;
    address public constant _agent = 0x4333218072D5d7008546737786663c38B4D561A4;
    INodeOperatorsRegistry public constant _nodeOperatorsRegistry = INodeOperatorsRegistry(0x9D4AF1Ee19Dad8857db3a45B0374c81c8A1C6320);
    address public constant _gateSeal = 0x75A77AE52d88999D0b12C6e5fABB1C1ef7E92638;
    address public constant _withdrawalQueueImplementation = 0xF7a378BB9E911550baA5e729f5Ab1592aDD905A5;
    address public constant _stakingRouterImplementation = 0xb02791097DE4B7B83265C9516640C8223830a351;
    address public constant _accountingOracleImplementation = 0x49cc40EE660BfD5f46423f04891502410d32E965;
    address public constant _validatorsExitBusOracleImplementation = 0xBE378f865Ab69f51d8874aeB9508cbbC42B3FBDE;
    address public constant _dummyImplementation = 0x6A03b1BbB79460169a205eFBCBc77ebE1011bCf8;
    address public constant _locatorImplementation = 0x6D5b7439c166A1BDc5c8DB547c1a871c082CE22C;
    address public constant _withdrawalVaultImplementation = 0x297Eb629655C8c488Eb26442cF4dfC8A7Cc32fFb;
    address public constant _previousDepositSecurityModule = 0x7DC1C1ff64078f73C98338e2f17D1996ffBb2eDe;

    uint256 public constant EXPECTED_FINAL_LIDO_VERSION = 2;
    uint256 public constant EXPECTED_FINAL_NODE_OPERATORS_REGISTRY_VERSION = 2;
    uint256 public constant EXPECTED_FINAL_LEGACY_ORACLE_VERSION = 4;
    uint256 public constant EXPECTED_FINAL_ACCOUNTING_ORACLE_VERSION = 1;
    uint256 public constant EXPECTED_FINAL_STAKING_ROUTER_VERSION = 1;
    uint256 public constant EXPECTED_FINAL_VALIDATORS_EXIT_BUS_ORACLE_VERSION = 1;
    uint256 public constant EXPECTED_FINAL_WITHDRAWAL_QUEUE_VERSION = 1;
    uint256 public constant EXPECTED_FINAL_WITHDRAWAL_VAULT_VERSION = 1;

    uint256 public constant EXPECTED_DSM_MAX_DEPOSITS_PER_BLOCK = 0;
    uint256 public constant EXPECTED_DSM_MIN_DEPOSIT_BLOCK_DISTANCE = 1200;
    uint256 public constant EXPECTED_DSM_PAUSE_INTENT_VALIDITY_PERIOD_BLOCKS = 10;

    uint256 public constant sanityLimit_churnValidatorsPerDayLimit = 1500;
    uint256 public constant sanityLimit_oneOffCLBalanceDecreaseBPLimit = 500;
    uint256 public constant sanityLimit_annualBalanceIncreaseBPLimit = 1000;
    uint256 public constant sanityLimit_simulatedShareRateDeviationBPLimit = 10;
    uint256 public constant sanityLimit_maxValidatorExitRequestsPerReport = 500;
    uint256 public constant sanityLimit_maxAccountingExtraDataListItemsCount = 500;
    uint256 public constant sanityLimit_maxNodeOperatorsPerExtraDataItemCount = 100;
    uint256 public constant sanityLimit_requestTimestampMargin = 384;
    uint256 public constant sanityLimit_maxPositiveTokenRebase = 750000;

    //
    // STRUCTURED STORAGE
    //
    bool public isUpgradeStarted;
    bool public isUpgradeFinished;

    /// Check chain is in the correct state to start the upgrade
    function assertCorrectInitialState() external view {
        _assertCorrectInitialState();
    }

    /// Need to be called before LidoOracle implementation is upgraded to LegacyOracle
    function startUpgrade() external {
        _startUpgrade();
    }

    function finishUpgrade() external {
        _finishUpgrade();
    }

    /// Perform basic checks to revert the entire upgrade if something gone wrong
    function assertUpgradeIsFinishedCorrectly() external view {
        _assertUpgradeIsFinishedCorrectly();
    }

    function revertIfUpgradeNotFinished() external view {
        if (!isUpgradeFinished) {
            revert UpgradeIsNotFinished();
        }
    }

    function _startUpgrade() internal {
        if (msg.sender != _voting) revert OnlyVotingCanUpgrade();
        if (isUpgradeStarted) revert CanOnlyStartOnce();
        isUpgradeStarted = true;

        _locator.proxy__upgradeTo(_locatorImplementation);

        // Locator must be upgraded at this point
        _assertCorrectInitialState();

        // Upgrade proxy implementation
        _upgradeProxyImplementations();

        // Need to have the implementations already attached at this point
        _assertCorrectInitialRoleHolders();

        _withdrawalVault().initialize();

        _initializeWithdrawalQueue();

        _initializeAccountingOracle();

        _initializeValidatorsExitBus();

        _migrateLidoOracleCommitteeMembers();

        _initializeStakingRouter();

        _migrateDSMGuardians();

        // Need to have the implementations and proxy contracts initialize at this point
        _assertProxyOZAccessControlContractsAdmin(address(this));
    }

    function _assertCorrectInitialState() internal view {
        if (ILidoOracle(address(_legacyOracle())).getVersion() != EXPECTED_FINAL_LEGACY_ORACLE_VERSION - 1) {
            revert LidoOracleMustNotBeUpgradedToLegacyYet();
        }

        _assertAdminsOfProxies(address(this));
        if (_withdrawalVault().proxy_getAdmin() != _voting) revert WrongProxyAdmin(address(_withdrawalVault()));

        _assertInitialProxyImplementations();

        // Check roles of non-proxy contracts (can do without binding implementations)
        _assertNonProxyOZAccessControlContractsAdmin(address(this));

        if (_depositSecurityModule().getOwner() != address(this)) revert WrongDsmOwner();

        _assertOracleDaemonConfigRoles();
        _assertOracleReportSanityCheckerRoles();

        _assertCorrectDSMParameters();
    }

    function _assertCorrectDSMParameters() internal view {
        IDepositSecurityModule dsm = _depositSecurityModule();
        if (
            dsm.getMaxDeposits() != EXPECTED_DSM_MAX_DEPOSITS_PER_BLOCK
         || dsm.getPauseIntentValidityPeriodBlocks() != EXPECTED_DSM_PAUSE_INTENT_VALIDITY_PERIOD_BLOCKS
         || dsm.getMinDepositBlockDistance() != EXPECTED_DSM_MIN_DEPOSIT_BLOCK_DISTANCE
        ) {
            revert IncorrectDepositSecurityModuleParameters(address(dsm));
        }
    }

    function _upgradeProxyImplementations() internal {
        _accountingOracle().proxy__upgradeTo(_accountingOracleImplementation);
        _validatorsExitBusOracle().proxy__upgradeTo(_validatorsExitBusOracleImplementation);
        _stakingRouter().proxy__upgradeTo(_stakingRouterImplementation);
        _withdrawalQueue().proxy__upgradeTo(_withdrawalQueueImplementation);
    }

    function _assertNonProxyOZAccessControlContractsAdmin(address admin) internal view {
        _assertSingleOZRoleHolder(_hashConsensusForAccountingOracle, DEFAULT_ADMIN_ROLE, admin);
        _assertSingleOZRoleHolder(_hashConsensusForValidatorsExitBusOracle, DEFAULT_ADMIN_ROLE, admin);
        _assertSingleOZRoleHolder(_burner(), DEFAULT_ADMIN_ROLE, admin);
    }

    function _assertProxyOZAccessControlContractsAdmin(address admin) internal view {
        _assertSingleOZRoleHolder(_accountingOracle(), DEFAULT_ADMIN_ROLE, admin);
        _assertSingleOZRoleHolder(_stakingRouter(), DEFAULT_ADMIN_ROLE, admin);
        _assertSingleOZRoleHolder(_validatorsExitBusOracle(), DEFAULT_ADMIN_ROLE, admin);
        _assertSingleOZRoleHolder(_withdrawalQueue(), DEFAULT_ADMIN_ROLE, admin);
    }

    function _assertAdminsOfProxies(address admin) internal view {
        _assertProxyAdmin(_locator, admin);
        _assertProxyAdmin(_accountingOracle(), admin);
        _assertProxyAdmin(_stakingRouter(), admin);
        _assertProxyAdmin(_validatorsExitBusOracle(), admin);
        _assertProxyAdmin(_withdrawalQueue(), admin);
    }

    function _assertProxyAdmin(IOssifiableProxy proxy, address admin) internal view {
        if (proxy.proxy__getAdmin() != admin) revert WrongProxyAdmin(address(proxy));
    }

    function _assertOracleReportSanityCheckerRoles() internal view {
        IOracleReportSanityChecker checker = _oracleReportSanityChecker();
        _assertSingleOZRoleHolder(checker, DEFAULT_ADMIN_ROLE, _agent);
        _assertZeroOZRoleHolders(checker, checker.ALL_LIMITS_MANAGER_ROLE());
        _assertZeroOZRoleHolders(checker, checker.CHURN_VALIDATORS_PER_DAY_LIMIT_MANGER_ROLE());
        _assertZeroOZRoleHolders(checker, checker.ONE_OFF_CL_BALANCE_DECREASE_LIMIT_MANAGER_ROLE());
        _assertZeroOZRoleHolders(checker, checker.ANNUAL_BALANCE_INCREASE_LIMIT_MANAGER_ROLE());
        _assertZeroOZRoleHolders(checker, checker.SHARE_RATE_DEVIATION_LIMIT_MANAGER_ROLE());
        _assertZeroOZRoleHolders(checker, checker.MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT_ROLE());
        _assertZeroOZRoleHolders(checker, checker.MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE());
        _assertZeroOZRoleHolders(checker, checker.MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE());
        _assertZeroOZRoleHolders(checker, checker.REQUEST_TIMESTAMP_MARGIN_MANAGER_ROLE());
        _assertZeroOZRoleHolders(checker, checker.MAX_POSITIVE_TOKEN_REBASE_MANAGER_ROLE());

        LimitsList memory limitsList = checker.getOracleReportLimits();
        if (
            limitsList.churnValidatorsPerDayLimit != sanityLimit_churnValidatorsPerDayLimit
         || limitsList.oneOffCLBalanceDecreaseBPLimit != sanityLimit_oneOffCLBalanceDecreaseBPLimit
         || limitsList.annualBalanceIncreaseBPLimit != sanityLimit_annualBalanceIncreaseBPLimit
         || limitsList.simulatedShareRateDeviationBPLimit != sanityLimit_simulatedShareRateDeviationBPLimit
         || limitsList.maxValidatorExitRequestsPerReport != sanityLimit_maxValidatorExitRequestsPerReport
         || limitsList.maxAccountingExtraDataListItemsCount != sanityLimit_maxAccountingExtraDataListItemsCount
         || limitsList.maxNodeOperatorsPerExtraDataItemCount != sanityLimit_maxNodeOperatorsPerExtraDataItemCount
         || limitsList.requestTimestampMargin != sanityLimit_requestTimestampMargin
         || limitsList.maxPositiveTokenRebase != sanityLimit_maxPositiveTokenRebase
         ) {
            revert InvalidOracleReportSanityCheckerConfig();
         }
    }

    function _assertOracleDaemonConfigRoles() internal view {
        IOracleDaemonConfig config = _oracleDaemonConfig();
        _assertSingleOZRoleHolder(config, DEFAULT_ADMIN_ROLE, _agent);
        _assertZeroOZRoleHolders(config, config.CONFIG_MANAGER_ROLE());

    }

    function _assertInitialProxyImplementations() internal view {
        if (_withdrawalVault().implementation() != _withdrawalVaultImplementation) revert WrongInitialImplementation(address(_withdrawalVault()));
        _assertInitialDummyImplementation(_accountingOracle());
        _assertInitialDummyImplementation(_stakingRouter());
        _assertInitialDummyImplementation(_validatorsExitBusOracle());
        _assertInitialDummyImplementation(_withdrawalQueue());
    }

    function _assertInitialDummyImplementation(IOssifiableProxy proxy) internal view {
        if (proxy.proxy__getImplementation() != _dummyImplementation) revert WrongInitialImplementation(address(proxy));
    }

    function _assertSingleOZRoleHolder(IAccessControlEnumerable accessControlled, bytes32 role, address holder) internal view {
        if (accessControlled.getRoleMemberCount(role) != 1
         || accessControlled.getRoleMember(role, 0) != holder
        ) {
            revert WrongOZAccessControlRoleHolders(address(accessControlled), role);
        }
    }

    function _assertTwoOZRoleHolders(IAccessControlEnumerable accessControlled, bytes32 role, address holder1, address holder2) internal view {
        if (accessControlled.getRoleMemberCount(role) != 2
         || accessControlled.getRoleMember(role, 0) != holder1
         || accessControlled.getRoleMember(role, 1) != holder2
        ) {
            revert WrongOZAccessControlRoleHolders(address(accessControlled), role);
        }
    }

    function _assertCorrectInitialRoleHolders() internal view {
        _assertSingleOZRoleHolder(_burner(), _burner().REQUEST_BURN_SHARES_ROLE(), address(_lido()));

        _assertZeroOZRoleHolders(_accountingOracle(), DEFAULT_ADMIN_ROLE);

        _assertZeroOZRoleHolders(_stakingRouter(), DEFAULT_ADMIN_ROLE);
        _assertZeroOZRoleHolders(_stakingRouter(), _stakingRouter().STAKING_MODULE_PAUSE_ROLE());
        _assertZeroOZRoleHolders(_stakingRouter(), _stakingRouter().STAKING_MODULE_RESUME_ROLE());
        _assertZeroOZRoleHolders(_stakingRouter(), _stakingRouter().REPORT_EXITED_VALIDATORS_ROLE());
        _assertZeroOZRoleHolders(_stakingRouter(), _stakingRouter().REPORT_REWARDS_MINTED_ROLE());

        _assertZeroOZRoleHolders(_validatorsExitBusOracle(), DEFAULT_ADMIN_ROLE);
        _assertZeroOZRoleHolders(_validatorsExitBusOracle(), _validatorsExitBusOracle().PAUSE_ROLE());

        _assertZeroOZRoleHolders(_withdrawalQueue(), DEFAULT_ADMIN_ROLE);
        _assertZeroOZRoleHolders(_withdrawalQueue(), _withdrawalQueue().PAUSE_ROLE());
        _assertZeroOZRoleHolders(_withdrawalQueue(), _withdrawalQueue().FINALIZE_ROLE());
        _assertZeroOZRoleHolders(_withdrawalQueue(), _withdrawalQueue().ORACLE_ROLE());
    }

    function _assertZeroOZRoleHolders(IAccessControlEnumerable accessControlled, bytes32 role) internal view {
        if (accessControlled.getRoleMemberCount(role) != 0) {
            revert NonZeroRoleHolders(address(accessControlled), role);
        }
    }

    function _initializeAccountingOracle() internal {
        (, uint256 epochsPerFrame, ) = _hashConsensusForAccountingOracle.getFrameConfig();
        uint256 lastLidoOracleCompletedEpochId = _lidoOracle().getLastCompletedEpochId();

        // NB: HashConsensus.updateInitialEpoch must be called after AccountingOracle implementation is bound to proxy
        _hashConsensusForAccountingOracle.updateInitialEpoch(lastLidoOracleCompletedEpochId + epochsPerFrame);

        _accountingOracle().initialize(
            address(this),
            address(_hashConsensusForAccountingOracle),
            _accountingOracleConsensusVersion
        );
    }

    function _initializeWithdrawalQueue() internal {
        IWithdrawalQueue wq = _withdrawalQueue();
        wq.initialize(address(this));
        wq.grantRole(wq.PAUSE_ROLE(), _gateSeal);
        wq.grantRole(wq.FINALIZE_ROLE(), address(_lido()));
        wq.grantRole(wq.ORACLE_ROLE(), address(_accountingOracle()));
        _resumeWithdrawalQueue();
    }

    function _initializeStakingRouter() internal {
        IStakingRouter sr = _stakingRouter();
        sr.initialize(address(this), address(_lido()), _withdrawalCredentials);
        sr.grantRole(sr.STAKING_MODULE_PAUSE_ROLE(), address(_depositSecurityModule()));
        sr.grantRole(sr.REPORT_EXITED_VALIDATORS_ROLE(), address(_accountingOracle()));
        sr.grantRole(sr.REPORT_REWARDS_MINTED_ROLE(), address(_lido()));
    }

    function _initializeValidatorsExitBus() internal {
        IValidatorsExitBusOracle vebo = _validatorsExitBusOracle();
        vebo.initialize(
            address(this),
            address(_hashConsensusForValidatorsExitBusOracle),
            _validatorsExitBusOracleConsensusVersion,
            VEBO_LAST_PROCESSING_REF_SLOT
        );
        vebo.grantRole(vebo.PAUSE_ROLE(), _gateSeal);
        _resumeValidatorsExitBusOracle();
    }

    function _migrateLidoOracleCommitteeMembers() internal {
        address[] memory members = _lidoOracle().getOracleMembers();
        uint256 quorum = _lidoOracle().getQuorum();
        bytes32 manage_members_role = _hashConsensusForAccountingOracle.MANAGE_MEMBERS_AND_QUORUM_ROLE();

        _hashConsensusForAccountingOracle.grantRole(manage_members_role, address(this));
        _hashConsensusForValidatorsExitBusOracle.grantRole(manage_members_role, address(this));
        for (uint256 i; i < members.length; ++i) {
            _hashConsensusForAccountingOracle.addMember(members[i], quorum);
            _hashConsensusForValidatorsExitBusOracle.addMember(members[i], quorum);
        }
        _hashConsensusForAccountingOracle.renounceRole(manage_members_role, address(this));
        _hashConsensusForValidatorsExitBusOracle.renounceRole(manage_members_role, address(this));
    }

    function _migrateDSMGuardians() internal {
        IDepositSecurityModule previousDSM = IDepositSecurityModule(_previousDepositSecurityModule);
        address[] memory guardians = previousDSM.getGuardians();
        uint256 quorum = previousDSM.getGuardianQuorum();
        _depositSecurityModule().addGuardians(guardians, quorum);
    }

    function _finishUpgrade() internal {
        if (msg.sender != _voting) revert OnlyVotingCanUpgrade();
        if (!isUpgradeStarted) revert StartMustBeCalledBeforeFinish();
        if (isUpgradeFinished) revert CanOnlyFinishOnce();
        /// Here we check that the contract got new ABI function getContractVersion(), although it is 0 yet
        /// because in the new contract version is stored in a different slot
        if (_legacyOracle().getContractVersion() != NOT_INITIALIZED_CONTRACT_VERSION) {
            revert LidoOracleMustBeUpgradedToLegacy();
        }
        isUpgradeFinished = true;

        _legacyOracle().finalizeUpgrade_v4(address(_accountingOracle()));

        _lido().finalizeUpgrade_v2(address(_locator), _eip712StETH);

        _nodeOperatorsRegistry.finalizeUpgrade_v2(
            address(_locator),
            _nodeOperatorsRegistryStakingModuleType,
            _nodeOperatorsRegistryStuckPenaltyDelay
        );

        _attachNORToStakingRouter();

        _burner().grantRole(_burner().REQUEST_BURN_SHARES_ROLE(), address(_nodeOperatorsRegistry));

        _passAdminRoleFromTemplateToAgent();

        _assertUpgradeIsFinishedCorrectly();
    }

    function _attachNORToStakingRouter() internal {
        bytes32 sm_manage_role = _stakingRouter().STAKING_MODULE_MANAGE_ROLE();
        _stakingRouter().grantRole(sm_manage_role, address(this));
        _stakingRouter().addStakingModule(
            NOR_STAKING_MODULE_NAME,
            address(_nodeOperatorsRegistry),
            NOR_STAKING_MODULE_TARGET_SHARE_BP,
            NOR_STAKING_MODULE_MODULE_FEE_BP,
            NOR_STAKING_MODULE_TREASURY_FEE_BP
        );
        _stakingRouter().renounceRole(sm_manage_role, address(this));
    }

    function _passAdminRoleFromTemplateToAgent() internal {
        // NB: No need to pass OracleDaemonConfig and OracleReportSanityChecker admin roles
        // because they were Agent at the beginning and are needed by the template
        _transferOZAdminFromThisToAgent(_hashConsensusForValidatorsExitBusOracle);
        _transferOZAdminFromThisToAgent(_hashConsensusForAccountingOracle);
        _transferOZAdminFromThisToAgent(_burner());
        _transferOZAdminFromThisToAgent(_stakingRouter());
        _transferOZAdminFromThisToAgent(_accountingOracle());
        _transferOZAdminFromThisToAgent(_validatorsExitBusOracle());
        _transferOZAdminFromThisToAgent(_withdrawalQueue());

        _locator.proxy__changeAdmin(_agent);
        _stakingRouter().proxy__changeAdmin(_agent);
        _accountingOracle().proxy__changeAdmin(_agent);
        _validatorsExitBusOracle().proxy__changeAdmin(_agent);
        _withdrawalQueue().proxy__changeAdmin(_agent);

        _depositSecurityModule().setOwner(_agent);
    }

    function _assertUpgradeIsFinishedCorrectly() internal view {
        _checkContractVersions();

        _assertAdminsOfProxies(_agent);
        _assertProxyOZAccessControlContractsAdmin(_agent);
        _assertNonProxyOZAccessControlContractsAdmin(_agent);
        _assertOracleDaemonConfigRoles();
        _assertOracleReportSanityCheckerRoles();

        _assertGateSealSealables();

        _assertZeroOZRoleHolders(_withdrawalQueue(), _withdrawalQueue().RESUME_ROLE());
        _assertSingleOZRoleHolder(_withdrawalQueue(), _withdrawalQueue().PAUSE_ROLE(), _gateSeal);
        _assertSingleOZRoleHolder(_withdrawalQueue(), _withdrawalQueue().FINALIZE_ROLE(), address(_lido()));
        _assertSingleOZRoleHolder(_withdrawalQueue(), _withdrawalQueue().ORACLE_ROLE(), address(_accountingOracle()));
        _assertZeroOZRoleHolders(_stakingRouter(), _stakingRouter().STAKING_MODULE_RESUME_ROLE());
        _assertSingleOZRoleHolder(_stakingRouter(), _stakingRouter().STAKING_MODULE_PAUSE_ROLE(), address(_depositSecurityModule()));
        _assertSingleOZRoleHolder(_stakingRouter(), _stakingRouter().REPORT_EXITED_VALIDATORS_ROLE(), address(_accountingOracle()));
        _assertSingleOZRoleHolder(_stakingRouter(), _stakingRouter().REPORT_REWARDS_MINTED_ROLE(), address(_lido()));
        _assertTwoOZRoleHolders(_burner(), _burner().REQUEST_BURN_SHARES_ROLE(), address(_lido()), address(_nodeOperatorsRegistry));
        _assertZeroOZRoleHolders(_validatorsExitBusOracle(), _validatorsExitBusOracle().RESUME_ROLE());
        _assertSingleOZRoleHolder(_validatorsExitBusOracle(), _validatorsExitBusOracle().PAUSE_ROLE(), _gateSeal);

        if (_depositSecurityModule().getOwner() != _agent) revert WrongDsmOwner();

        _assertCorrectOracleAndConsensusContractsBinding(_accountingOracle(), _hashConsensusForAccountingOracle);
        _assertCorrectOracleAndConsensusContractsBinding(_validatorsExitBusOracle(), _hashConsensusForValidatorsExitBusOracle);

        if (_withdrawalQueue().isPaused()) revert WQNotResumed();
        if (_validatorsExitBusOracle().isPaused()) revert VEBONotResumed();

        if (!_stakingRouter().hasStakingModule(1) || _stakingRouter().hasStakingModule(2)) {
            revert WrongStakingModulesCount();
        }
    }

    function _assertGateSealSealables() internal view {
        // TODO: sync VEBO proxy and its sealable at re-deploy
        address[] memory sealables = IGateSeal(_gateSeal).get_sealables();
        if (
            sealables[0] != address(_withdrawalQueue())
        //  || sealables[1] != address(_validatorsExitBusOracle())
         ) {
            revert WrongSealGateSealables();
        }
    }

    function _assertCorrectOracleAndConsensusContractsBinding(IBaseOracle oracle, IHashConsensus hashConsensus) internal view {
        if (oracle.getConsensusContract() != address(hashConsensus)) {
            revert IncorrectOracleAndHashConsensusBinding(address(oracle), address(hashConsensus));
        }
        // TODO: check the binding in opposite direction when the view is added to HashConsensus
    }

    function _checkContractVersions() internal view {
        _assertContractVersion(_lido(), EXPECTED_FINAL_LIDO_VERSION);
        _assertContractVersion(_nodeOperatorsRegistry, EXPECTED_FINAL_NODE_OPERATORS_REGISTRY_VERSION);
        _assertContractVersion(_legacyOracle(), EXPECTED_FINAL_LEGACY_ORACLE_VERSION);
        _assertContractVersion(_accountingOracle(), EXPECTED_FINAL_ACCOUNTING_ORACLE_VERSION);
        _assertContractVersion(_stakingRouter(), EXPECTED_FINAL_STAKING_ROUTER_VERSION);
        _assertContractVersion(_validatorsExitBusOracle(), EXPECTED_FINAL_VALIDATORS_EXIT_BUS_ORACLE_VERSION);
        _assertContractVersion(_withdrawalQueue(), EXPECTED_FINAL_WITHDRAWAL_QUEUE_VERSION);
        _assertContractVersion(_withdrawalVault(), EXPECTED_FINAL_WITHDRAWAL_VAULT_VERSION);
    }

    function _assertContractVersion(IVersioned versioned, uint256 expectedVersion) internal view {
        if (versioned.getContractVersion() != expectedVersion) {
            revert InvalidContractVersion(address(versioned), expectedVersion);
        }
    }

    function _transferOZAdminFromThisToAgent(IAccessControlEnumerable accessControlled) internal {
        accessControlled.grantRole(DEFAULT_ADMIN_ROLE, _agent);
        accessControlled.renounceRole(DEFAULT_ADMIN_ROLE, address(this));
    }

    function _resumeWithdrawalQueue() internal {
        IWithdrawalQueue wq = _withdrawalQueue();
        bytes32 resume_role = wq.RESUME_ROLE();
        wq.grantRole(resume_role, address(this));
        wq.resume();
        wq.renounceRole(resume_role, address(this));
    }

    // To be strict need two almost identical _resume... function because RESUME_ROLE and resume()
    // do not actually belong to PausableUntil contract
    function _resumeValidatorsExitBusOracle() internal {
        IValidatorsExitBusOracle vebo = _validatorsExitBusOracle();
        bytes32 resume_role = vebo.RESUME_ROLE();
        vebo.grantRole(resume_role, address(this));
        vebo.resume();
        vebo.renounceRole(resume_role, address(this));
    }

    function _accountingOracle() internal view returns (IAccountingOracle) {
        return IAccountingOracle(_locator.accountingOracle());
    }

    function _burner() internal view returns (IBurner) {
        return IBurner(_locator.burner());
    }

    function _depositSecurityModule() internal view returns (IDepositSecurityModule) {
        return IDepositSecurityModule(_locator.depositSecurityModule());
    }

    function _lido() internal view returns (ILido) {
        return ILido(_locator.lido());
    }

    // Returns the same address as _legacyOracle(): we're renaming the contract, but it's on the same address
    function _lidoOracle() internal view returns (ILidoOracle) {
        return ILidoOracle(_locator.legacyOracle());
    }

    // Returns the same address as _lidoOracle(): we're renaming the contract, but it's on the same address
    function _legacyOracle() internal view returns (ILegacyOracle) {
        return ILegacyOracle(_locator.legacyOracle());
    }

    function _oracleDaemonConfig() internal view returns (IOracleDaemonConfig) {
        return IOracleDaemonConfig(_locator.oracleDaemonConfig());
    }

    function _oracleReportSanityChecker() internal view returns (IOracleReportSanityChecker) {
        return IOracleReportSanityChecker(_locator.oracleReportSanityChecker());
    }

    function _stakingRouter() internal view returns (IStakingRouter) {
        return IStakingRouter(_locator.stakingRouter());
    }

    function _validatorsExitBusOracle() internal view returns (IValidatorsExitBusOracle) {
        return IValidatorsExitBusOracle(_locator.validatorsExitBusOracle());
    }

    function _withdrawalQueue() internal view returns (IWithdrawalQueue) {
        return IWithdrawalQueue(_locator.withdrawalQueue());
    }

    function _withdrawalVault() internal view returns (IWithdrawalVault) {
        return IWithdrawalVault(_locator.withdrawalVault());
    }

    error OnlyVotingCanUpgrade();
    error CanOnlyStartOnce();
    error CanOnlyFinishOnce();
    error StartMustBeCalledBeforeFinish();
    error UpgradeIsNotFinished();
    error LidoOracleMustNotBeUpgradedToLegacyYet();
    error LidoOracleMustBeUpgradedToLegacy();
    error WrongDsmOwner();
    error WrongProxyAdmin(address proxy);
    error WrongInitialImplementation(address proxy);
    error InvalidContractVersion(address contractAddress, uint256 actualVersion);
    error WrongOZAccessControlAdmin(address contractAddress);
    error WrongOZAccessControlRoleHolders(address contractAddress, bytes32 role);
    error NonZeroRoleHolders(address contractAddress, bytes32 role);
    error WQNotResumed();
    error VEBONotResumed();
    error IncorrectOracleAndHashConsensusBinding(address oracle, address hashConsensus);
    error IncorrectDepositSecurityModuleParameters(address _depositSecurityModule);
    error WrongStakingModulesCount();
    error InvalidOracleReportSanityCheckerConfig();
    error WrongSealGateSealables();
}
