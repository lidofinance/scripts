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

    // The following methods actually belong to the oracle but are identical
    function PAUSE_ROLE() external returns (bytes32);
    function RESUME_ROLE() external returns (bytes32);
    function resume() external;
}

interface IOssifiableProxy {
    function proxy__upgradeTo(address newImplementation) external;
    function proxy__changeAdmin(address newAdmin) external;
    function proxy__getAdmin() external view returns (address);
    function proxy__getImplementation() external view returns (address);
}

interface IAccountingOracle is IAccessControlEnumerable, IVersioned, IOssifiableProxy {
    function SUBMIT_DATA_ROLE() external view returns (bytes32);
    function initialize(address admin, address consensusContract, uint256 consensusVersion) external;
}

interface IBaseOracle {
    function getConsensusContract() external view returns (address);
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

interface INodeOperatorsRegistry {
    function finalizeUpgrade_v2(address locator, bytes32 stakingModuleType, uint256 stuckPenaltyDelay) external;
}


interface IStakingRouter is IVersioned, IAccessControlEnumerable, IOssifiableProxy {
    function MANAGE_WITHDRAWAL_CREDENTIALS_ROLE() external returns (bytes32);
    function STAKING_MODULE_PAUSE_ROLE() external returns (bytes32);
    function STAKING_MODULE_RESUME_ROLE() external returns (bytes32);
    function STAKING_MODULE_MANAGE_ROLE() external returns (bytes32);
    function REPORT_EXITED_VALIDATORS_ROLE() external returns (bytes32);
    function UNSAFE_SET_EXITED_VALIDATORS_ROLE() external returns (bytes32);
    function REPORT_REWARDS_MINTED_ROLE() external returns (bytes32);
    function initialize(address admin, address lido, bytes32 withdrawalCredentials) external;
    function addStakingModule(
        string calldata name,
        address stakingModuleAddress,
        uint256 targetShare,
        uint256 stakingModuleFee,
        uint256 treasuryFee
    ) external;
}

interface IValidatorsExitBusOracle is IAccessControlEnumerable, IPausableUntil, IVersioned, IOssifiableProxy {
    function initialize(address admin, address consensusContract, uint256 consensusVersion, uint256 lastProcessingRefSlot) external;
}


interface IWithdrawalQueue is IAccessControlEnumerable, IPausableUntil, IVersioned, IOssifiableProxy {
    function FINALIZE_ROLE() external returns (bytes32);
    function ORACLE_ROLE() external returns (bytes32);
    function initialize(address _admin) external;
    function pauseFor(uint256 _duration) external;
}

interface IWithdrawalVault is IVersioned, IOssifiableProxy {
    function initialize() external;
}


contract ShapellaUpgradeTemplate {
    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;

    // TODO mainnet: maybe make the immutables constants
    uint256 public constant _accountingOracleConsensusVersion = 1;
    uint256 public constant _validatorsExitBusOracleConsensusVersion = 1;
    string public constant NOR_STAKING_MODULE_NAME = "curated-onchain-v1";
    bytes32 public constant _nodeOperatorsRegistryStakingModuleType = bytes32("curated-onchain-v1");
    uint256 public constant _nodeOperatorsRegistryStuckPenaltyDelay = 172800;
    bytes32 public constant _withdrawalCredentials = 0x010000000000000000000000AD9928A0863964a901f49e290a2AeAE68bE6EAFb;
    uint256 public constant NOR_STAKING_MODULE_TARGET_SHARE_BP = 10000; // 100%
    uint256 public constant NOR_STAKING_MODULE_MODULE_FEE_BP = 500; // 5%
    uint256 public constant NOR_STAKING_MODULE_TREASURY_FEE_BP = 500; // 5%
    uint256 public constant VEBO_LAST_PROCESSING_REF_SLOT = 0;

    ILidoLocator public constant _locator = ILidoLocator(0x1eDf09b5023DC86737b59dE68a8130De878984f5);
    IHashConsensus public constant _hashConsensusForAccountingOracle = IHashConsensus(0x821688406B8000FE3bAa8B074F8e1CbCD72c0035);
    IHashConsensus public constant _hashConsensusForValidatorsExitBusOracle = IHashConsensus(0xe47EA5f0406C1A976cE43f97cEdcB8f3dee5484A);
    address public constant _eip712StETH = 0xB4300103FfD326f77FfB3CA54248099Fb29C3b9e;
    address public constant _voting = 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db;
    address public constant _nodeOperatorsRegistry = 0x9D4AF1Ee19Dad8857db3a45B0374c81c8A1C6320;
    address public constant _gateSeal = 0x75A77AE52d88999D0b12C6e5fABB1C1ef7E92638;
    address public constant _withdrawalQueueImplementation = 0x57d31c50dB78e4d95C49Ab83EC011B4D0b0acF59;
    address public constant _stakingRouterImplementation = 0x73dC7d1d5B3517141eA43fbFC6d092B6fEaFC20A;
    address public constant _accountingOracleImplementation = 0x0310fABFa308eFb71CFba9d86193710fFD763B71;
    address public constant _validatorsExitBusOracleImplementation = 0x3eb5f9aC4d71f76B5F6B4DE82f7aefFf414c5854;
    address public constant _dummyImplementation = 0x6A03b1BbB79460169a205eFBCBc77ebE1011bCf8;
    address public constant _locatorImplementation = 0xf47F64a3B2AA52A77dC080D50927Af378d7dA7B8;
    address public constant _withdrawalVaultImplementation = 0x26852993A6420dDa2692b033b5AF3b0846c15d5B;
    address public constant _previousDepositSecurityModule = 0x7DC1C1ff64078f73C98338e2f17D1996ffBb2eDe;

    uint256 public constant EXPECTED_FINAL_LIDO_VERSION = 2;
    uint256 public constant EXPECTED_FINAL_LEGACY_ORACLE_VERSION = 4;
    uint256 public constant EXPECTED_FINAL_ACCOUNTING_ORACLE_VERSION = 1;
    uint256 public constant EXPECTED_FINAL_STAKING_ROUTER_VERSION = 1;
    uint256 public constant EXPECTED_FINAL_VALIDATORS_EXIT_BUS_ORACLE_VERSION = 1;
    uint256 public constant EXPECTED_FINAL_WITHDRAWAL_QUEUE_VERSION = 1;
    uint256 public constant EXPECTED_FINAL_WITHDRAWAL_VAULT_VERSION = 1;
    uint256 public constant NOT_INITIALIZED_CONTRACT_VERSION = 0;

    //
    // STRUCTURED STORAGE
    //
    bool public isUpgradeStarted;
    bool public isUpgradeFinished;

    function verifyInitialState() external view {
        _verifyInitialState();
    }

    /// Need to be called before LidoOracle implementation is upgraded to LegacyOracle
    function startUpgrade() external {
        _startUpgrade();
    }

    function finishUpgrade() external {
        _finishUpgrade();
    }

    /// Perform basic checks to revert the entire upgrade if something gone wrong
    function verifyFinishedUpgrade() external view {
        _verifyFinishedUpgrade();
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

        // Need to check / set locator implementation first because the other initial state checks depend on correct locator
        if (_locator.proxy__getImplementation() != _locatorImplementation) {
            _locator.proxy__upgradeTo(_locatorImplementation);
        }

        _verifyInitialState();

        _prepareWithdrawalVault();

        _prepareAccountingOracle();

        _prepareValidatorsExitBus();

        _migrateLidoOracleCommitteeMembers();

        _prepareWithdrawalQueue();

        _prepareStakingRouter();

        _migrateDSMGuardians();
    }

    function _verifyInitialState() internal view {
        if (ILidoOracle(address(_legacyOracle())).getVersion() != 3) revert LidoOracleMustNotBeUpgradedToLegacyYet();

        _verifyAdminsOfProxies(address(this));

        _verifyInitialProxyImplementations();

        _verifyOZAccessControlAdmins(address(this));

        if (_depositSecurityModule().getOwner() != address(this)) revert WrongDsmOwner();
    }

    function _verifyAdminsOfProxies(address admin) internal view {
        _verifyProxyAdmin(_accountingOracle(), admin);
        _verifyProxyAdmin(_locator, admin);
        _verifyProxyAdmin(_stakingRouter(), admin);
        _verifyProxyAdmin(_validatorsExitBusOracle(), admin);
        _verifyProxyAdmin(_withdrawalQueue(), admin);
        _verifyProxyAdmin(_withdrawalVault(), admin);
    }

    function _verifyProxyAdmin(IOssifiableProxy proxy, address admin) internal view {
        if (proxy.proxy__getAdmin() != admin) revert WrongProxyAdmin(address(proxy));
    }

    function _verifyInitialProxyImplementations() internal view {
        _verifyInitialImplementation(_accountingOracle());
        _verifyInitialImplementation(_stakingRouter());
        _verifyInitialImplementation(_validatorsExitBusOracle());
        _verifyInitialImplementation(_withdrawalQueue());
        _verifyInitialImplementation(_withdrawalVault());
    }

    function _verifyInitialImplementation(IOssifiableProxy proxy) internal view {
        if (proxy.proxy__getImplementation() != _dummyImplementation) revert WrongInitialImplementation(address(proxy));
    }

    function _verifyOZAccessControlAdmins(address admin) internal view {
        _verifySingleOZAdmin(_hashConsensusForAccountingOracle, admin);
        _verifySingleOZAdmin(_hashConsensusForValidatorsExitBusOracle, admin);
        _verifySingleOZAdmin(_burner(), admin);
    }

    function _verifySingleOZAdmin(IAccessControlEnumerable accessControlled, address admin) internal view {
        if (accessControlled.getRoleMemberCount(DEFAULT_ADMIN_ROLE) != 1
         || accessControlled.getRoleMember(DEFAULT_ADMIN_ROLE, 0) != admin
        ) {
            revert WrongOZAccessControlAdmin(address(accessControlled));
        }
    }

    function _prepareWithdrawalVault() internal {
        _withdrawalVault().proxy__upgradeTo(_withdrawalVaultImplementation);
        _withdrawalVault().initialize();
    }

    function _prepareAccountingOracle() internal {
        (, uint256 epochsPerFrame, ) = _hashConsensusForAccountingOracle.getFrameConfig();
        uint256 lastLidoOracleCompletedEpochId = _lidoOracle().getLastCompletedEpochId();

        // NB: HashConsensus.updateInitialEpoch must be called after AccountingOracle implementation is bound to proxy
        _accountingOracle().proxy__upgradeTo(_accountingOracleImplementation);
        _hashConsensusForAccountingOracle.updateInitialEpoch(lastLidoOracleCompletedEpochId + epochsPerFrame);
        _accountingOracle().initialize(
            address(this),
            address(_hashConsensusForAccountingOracle),
            _accountingOracleConsensusVersion
        );
    }

    function _prepareValidatorsExitBus() internal {
        _validatorsExitBusOracle().proxy__upgradeTo(_validatorsExitBusOracleImplementation);
        _validatorsExitBusOracle().initialize(
            address(this),
            address(_hashConsensusForValidatorsExitBusOracle),
            _validatorsExitBusOracleConsensusVersion,
            VEBO_LAST_PROCESSING_REF_SLOT
        );
    }

    function _migrateLidoOracleCommitteeMembers() internal {
        address[] memory members = _lidoOracle().getOracleMembers();
        uint256 quorum = _lidoOracle().getQuorum();
        bytes32 manage_members_role = _hashConsensusForAccountingOracle.MANAGE_MEMBERS_AND_QUORUM_ROLE();
        bytes32 submit_data_role = _accountingOracle().SUBMIT_DATA_ROLE();

        _hashConsensusForAccountingOracle.grantRole(manage_members_role, address(this));
        _hashConsensusForValidatorsExitBusOracle.grantRole(manage_members_role, address(this));
        for (uint256 i; i < members.length; ++i) {
            _hashConsensusForAccountingOracle.addMember(members[i], quorum);
            _accountingOracle().grantRole(submit_data_role, members[i]);

            _hashConsensusForValidatorsExitBusOracle.addMember(members[i], quorum);
            _validatorsExitBusOracle().grantRole(submit_data_role, members[i]);
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

        INodeOperatorsRegistry(_nodeOperatorsRegistry).finalizeUpgrade_v2(
            address(_locator),
            _nodeOperatorsRegistryStakingModuleType,
            _nodeOperatorsRegistryStuckPenaltyDelay
        );

        _attachNORToStakingRouter();

        _grantRoles();

        _passAdminRoleFromTemplateToVoting();

        _verifyFinishedUpgrade();
    }

    function _prepareWithdrawalQueue() internal {
        _withdrawalQueue().proxy__upgradeTo(_withdrawalQueueImplementation);
        _withdrawalQueue().initialize(address(this));
        _resumePausableContract(address(_withdrawalQueue()));
        _resumePausableContract(address(_validatorsExitBusOracle()));
    }

    function _prepareStakingRouter() internal {
        _stakingRouter().proxy__upgradeTo(_stakingRouterImplementation);
        _stakingRouter().initialize(address(this), address(_lido()), _withdrawalCredentials);
    }

    function _attachNORToStakingRouter() internal {
        bytes32 sm_manage_role = _stakingRouter().STAKING_MODULE_MANAGE_ROLE();
        _stakingRouter().grantRole(sm_manage_role, address(this));
        _stakingRouter().addStakingModule(
            NOR_STAKING_MODULE_NAME,
            _nodeOperatorsRegistry,
            NOR_STAKING_MODULE_TARGET_SHARE_BP,
            NOR_STAKING_MODULE_MODULE_FEE_BP,
            NOR_STAKING_MODULE_TREASURY_FEE_BP
        );
        _stakingRouter().renounceRole(sm_manage_role, address(this));
    }

    function _grantRoles() internal {
        IBurner burner = _burner();
        burner.grantRole(burner.REQUEST_BURN_SHARES_ROLE(), _nodeOperatorsRegistry);

        IStakingRouter router = _stakingRouter();
        router.grantRole(router.STAKING_MODULE_PAUSE_ROLE(), address(_depositSecurityModule()));
        router.grantRole(router.STAKING_MODULE_RESUME_ROLE(), address(_depositSecurityModule()));
        router.grantRole(router.REPORT_EXITED_VALIDATORS_ROLE(), address(_accountingOracle()));
        router.grantRole(router.REPORT_REWARDS_MINTED_ROLE(), address(_lido()));

        IValidatorsExitBusOracle exitBusOracle = _validatorsExitBusOracle();
        exitBusOracle.grantRole(exitBusOracle.PAUSE_ROLE(), _gateSeal);

        IWithdrawalQueue withdrawalQueue = _withdrawalQueue();
        withdrawalQueue.grantRole(withdrawalQueue.PAUSE_ROLE(), _gateSeal);
        withdrawalQueue.grantRole(withdrawalQueue.FINALIZE_ROLE(), address(_lido()));
        withdrawalQueue.grantRole(withdrawalQueue.ORACLE_ROLE(), address(_accountingOracle()));
    }

    function _passAdminRoleFromTemplateToVoting() internal {
        _transferOZAdminFromThisToVoting(_hashConsensusForValidatorsExitBusOracle);
        _transferOZAdminFromThisToVoting(_hashConsensusForAccountingOracle);
        _transferOZAdminFromThisToVoting(_burner());
        _transferOZAdminFromThisToVoting(_stakingRouter());
        _transferOZAdminFromThisToVoting(_accountingOracle());
        _transferOZAdminFromThisToVoting(_validatorsExitBusOracle());
        _transferOZAdminFromThisToVoting(_withdrawalQueue());

        _locator.proxy__changeAdmin(_voting);
        _stakingRouter().proxy__changeAdmin(_voting);
        _accountingOracle().proxy__changeAdmin(_voting);
        _validatorsExitBusOracle().proxy__changeAdmin(_voting);
        _withdrawalQueue().proxy__changeAdmin(_voting);
        _withdrawalVault().proxy__changeAdmin(_voting);

        _depositSecurityModule().setOwner(_voting);
    }

    function _verifyFinishedUpgrade() internal view {
        _checkContractVersions();

        _verifyAdminsOfProxies(_voting);

        _verifyOZAccessControlAdmins(_voting);

        // TODO: maybe check non admin roles if enough contract bytecode size?

        if (_depositSecurityModule().getOwner() != _voting) revert WrongDsmOwner();

        if (_withdrawalQueue().isPaused()) revert WQNotResumed();
        if (_validatorsExitBusOracle().isPaused()) revert EBNotResumed();
    }

    function _checkContractVersions() internal view {
        _verifyContractVersion(_lido(), EXPECTED_FINAL_LIDO_VERSION);
        _verifyContractVersion(_legacyOracle(), EXPECTED_FINAL_LEGACY_ORACLE_VERSION);
        _verifyContractVersion(_accountingOracle(), EXPECTED_FINAL_ACCOUNTING_ORACLE_VERSION);
        _verifyContractVersion(_stakingRouter(), EXPECTED_FINAL_STAKING_ROUTER_VERSION);
        _verifyContractVersion(_validatorsExitBusOracle(), EXPECTED_FINAL_VALIDATORS_EXIT_BUS_ORACLE_VERSION);
        _verifyContractVersion(_withdrawalQueue(), EXPECTED_FINAL_WITHDRAWAL_QUEUE_VERSION);
        _verifyContractVersion(_withdrawalVault(), EXPECTED_FINAL_WITHDRAWAL_VAULT_VERSION);
    }

    function _verifyContractVersion(IVersioned versioned, uint256 expectedVersion) internal view {
        if (versioned.getContractVersion() != expectedVersion) {
            revert InvalidContractVersion(address(versioned), expectedVersion);
        }
    }

    function _transferOZAdminFromThisToVoting(IAccessControlEnumerable accessControlled) internal {
        accessControlled.grantRole(DEFAULT_ADMIN_ROLE, _voting);
        accessControlled.renounceRole(DEFAULT_ADMIN_ROLE, address(this));
    }

    function _resumePausableContract(address contractAddress) internal {
        bytes32 resume_role = IPausableUntil(contractAddress).RESUME_ROLE();

        IAccessControlEnumerable(contractAddress).grantRole(resume_role, address(this));
        IPausableUntil(contractAddress).resume();
        IAccessControlEnumerable(contractAddress).renounceRole(resume_role, address(this));
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

    // Returns the same address as _legacyOracle()
    function _lidoOracle() internal view returns (ILidoOracle) {
        return ILidoOracle(_locator.legacyOracle());
    }

    // Returns the same address as _lidoOracle()
    function _legacyOracle() internal view returns (ILegacyOracle) {
        return ILegacyOracle(_locator.legacyOracle());
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
    error WQNotResumed();
    error EBNotResumed();
}
