// SPDX-License-Identifier: MIT

pragma solidity 0.8.9;


interface IAccessControlEnumerable {
    function DEFAULT_ADMIN_ROLE() external returns (bytes32);
    function grantRole(bytes32 role, address account) external;
    function renounceRole(bytes32 role, address account) external;
    function getRoleMemberCount(bytes32 role) external view returns (uint256);
    function getRoleMember(bytes32 role, uint256 index) external view returns (address);
}

interface IAccountingOracle {
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

interface IHashConsensus {
    function MANAGE_MEMBERS_AND_QUORUM_ROLE() external view returns (bytes32);
    function addMember(address addr, uint256 quorum) external;
    function getFrameConfig() external view returns (uint256 initialEpoch, uint256 epochsPerFrame, uint256 fastLaneLengthSlots);
    function updateInitialEpoch(uint256 initialEpoch) external;
}

interface ILido {
    function finalizeUpgrade_v2(address _lidoLocator, address _eip712StETH) external;
}

interface ILidoLocator {
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

interface ILegacyOracle {
    function finalizeUpgrade_v4(address _accountingOracle) external;
    function getContractVersion() external view returns (uint256);
}

interface ILidoOracle {
    function getVersion() external view returns (uint256);
    function getOracleMembers() external view returns (address[] memory);
    function getQuorum() external view returns (uint256);
    function getLastCompletedEpochId() external view returns (uint256);
}

interface INodeOperatorsRegistry {
    function finalizeUpgrade_v2(address _locator, bytes32 _type, uint256 _stuckPenaltyDelay) external;
}

interface IOssifiableProxy {
    function proxy__upgradeTo(address newImplementation_) external;
    function proxy__changeAdmin(address newAdmin_) external;
    function proxy__getAdmin() external view returns (address);
    function proxy__getImplementation() external view returns (address);
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

interface IStakingRouter is IAccessControlEnumerable {
    function MANAGE_WITHDRAWAL_CREDENTIALS_ROLE() external returns (bytes32);
    function STAKING_MODULE_PAUSE_ROLE() external returns (bytes32);
    function STAKING_MODULE_RESUME_ROLE() external returns (bytes32);
    function STAKING_MODULE_MANAGE_ROLE() external returns (bytes32);
    function REPORT_EXITED_VALIDATORS_ROLE() external returns (bytes32);
    function UNSAFE_SET_EXITED_VALIDATORS_ROLE() external returns (bytes32);
    function REPORT_REWARDS_MINTED_ROLE() external returns (bytes32);
    function initialize(address _admin, address _lido, bytes32 _withdrawalCredentials) external;
    function addStakingModule(
        string calldata _name,
        address _stakingModuleAddress,
        uint256 _targetShare,
        uint256 _stakingModuleFee,
        uint256 _treasuryFee
    ) external;
}

interface IValidatorsExitBusOracle is IAccessControlEnumerable, IPausableUntil {
    function initialize(address admin, address consensusContract, uint256 consensusVersion, uint256 lastProcessingRefSlot) external;
}

interface IVersioned {
    function getContractVersion() external view returns (uint256);
}

interface IWithdrawalQueue is IAccessControlEnumerable, IPausableUntil {
    function FINALIZE_ROLE() external returns (bytes32);
    function ORACLE_ROLE() external returns (bytes32);
    function initialize(address _admin) external;
    function pauseFor(uint256 _duration) external;
}


contract ShapellaUpgradeTemplate {

    // TODO mainnet: remove the structs
    struct Config {
        ILidoLocator locator;
        address eip712StETH;
        address voting;
        address nodeOperatorsRegistry;
        address hashConsensusForAccountingOracle;
        address hashConsensusForValidatorsExitBusOracle;
        address gateSeal;
        bytes32 withdrawalCredentials;
        uint256 nodeOperatorsRegistryStuckPenaltyDelay;
    }
    struct ConfigImplementations {
        address withdrawalQueueImplementation;
        address stakingRouterImplementation;
        address accountingOracleImplementation;
        address validatorsExitBusOracleImplementation;
        address dummyImplementation;
        address locatorImplementation;
    }

    uint256 public constant SECONDS_PER_BLOCK = 12;
    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    string public constant NOR_STAKING_MODULE_NAME = "curated-onchain-v1";
    bytes32 public constant NOR_STAKING_MODULE_NAME_BYTES = bytes32("curated-onchain-v1");

    // TODO mainnet: maybe make the immutables constants
    uint256 public immutable _accountingOracleConsensusVersion;
    uint256 public immutable _validatorsExitBusOracleConsensusVersion;
    bytes32 public immutable _nodeOperatorsRegistryStakingModuleType;
    ILidoLocator public immutable _locator;
    address public immutable _eip712StETH;
    address public immutable _voting;
    address public immutable _nodeOperatorsRegistry;
    address public immutable _hashConsensusForAccountingOracle;
    address public immutable _hashConsensusForValidatorsExitBusOracle;
    address public immutable _gateSeal;
    address public immutable _withdrawalQueueImplementation;
    address public immutable _stakingRouterImplementation;
    address public immutable _accountingOracleImplementation;
    address public immutable _validatorsExitBusOracleImplementation;
    bytes32 public immutable _withdrawalCredentials;
    uint256 public immutable _nodeOperatorsRegistryStuckPenaltyDelay;
    address public immutable _dummyImplementation;
    address public immutable _previousDepositSecurityModule;
    address public immutable _locatorImplementation;

    //
    // STRUCTURED STORAGE
    //
    bool public isUpgradeStarted;
    bool public isUpgradeFinished;

    constructor(Config memory _config, ConfigImplementations memory _configImpl) {
        // TODO mainnet/testnet: update the values
        _accountingOracleConsensusVersion = 1;
        _validatorsExitBusOracleConsensusVersion = 1;
        _nodeOperatorsRegistryStakingModuleType = NOR_STAKING_MODULE_NAME_BYTES;



        _locator = ILidoLocator(0x1eDf09b5023DC86737b59dE68a8130De878984f5);
        _eip712StETH = 0xB4300103FfD326f77FfB3CA54248099Fb29C3b9e;
        _voting = 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db;
        _nodeOperatorsRegistry = 0x9D4AF1Ee19Dad8857db3a45B0374c81c8A1C6320;
        _hashConsensusForAccountingOracle = 0x821688406B8000FE3bAa8B074F8e1CbCD72c0035;
        _hashConsensusForValidatorsExitBusOracle = 0xe47EA5f0406C1A976cE43f97cEdcB8f3dee5484A;
        _gateSeal = 0x75A77AE52d88999D0b12C6e5fABB1C1ef7E92638;

        _withdrawalCredentials = 0x010000000000000000000000AD9928A0863964a901f49e290a2AeAE68bE6EAFb;
        _nodeOperatorsRegistryStuckPenaltyDelay = 172800;

        _withdrawalQueueImplementation = 0x57d31c50dB78e4d95C49Ab83EC011B4D0b0acF59;
        _stakingRouterImplementation = 0x73dC7d1d5B3517141eA43fbFC6d092B6fEaFC20A;
        _accountingOracleImplementation = 0x0310fABFa308eFb71CFba9d86193710fFD763B71;
        _validatorsExitBusOracleImplementation = 0x3eb5f9aC4d71f76B5F6B4DE82f7aefFf414c5854;
        _dummyImplementation = 0x6A03b1BbB79460169a205eFBCBc77ebE1011bCf8;
        _previousDepositSecurityModule = 0x7DC1C1ff64078f73C98338e2f17D1996ffBb2eDe;
        _locatorImplementation = 0x4D2C33595e82d9eE44B653D6632BAd2b3fC9aF9c;

    }

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

    function _startUpgrade() internal {
        if (msg.sender != _voting) revert OnlyVotingCanUpgrade();
        if (isUpgradeStarted) revert CanOnlyStartOnce();
        isUpgradeStarted = true;

        // Need to check / set locator implementation first because the other initial state checks depend on correct locator
        if (IOssifiableProxy(address(_locator)).proxy__getImplementation() != _locatorImplementation) {
            IOssifiableProxy(address(_locator)).proxy__upgradeTo(_locatorImplementation);
        }

        _verifyInitialState();

        _prepareAccountingOracle();

        _prepareValidatorsExitBus();

        _migrateLidoOracleCommitteeMembers();

        _prepareWithdrawalQueue();

        _prepareStakingRouter();

        _migrateDSMGuardians();
    }

    function _verifyInitialState() internal view {
        if (ILidoOracle(_locator.legacyOracle()).getVersion() != 3) revert LidoOracleMustNotBeUpgradedToLegacyYet();

        _verifyProxyAdmins(address(this));

        // TODO: put back if enough gas
        _verifyInitialProxyImplementations();

        _verifyOZAdmins(address(this));

        if (IDepositSecurityModule(_locator.depositSecurityModule()).getOwner() != address(this)) revert WrongDsmOwner();
    }

    function _verifyProxyAdmins(address admin) internal view {
        if (IOssifiableProxy(address(_locator)).proxy__getAdmin() != admin) revert WrongLocatorAdmin();
        if (IOssifiableProxy(_locator.withdrawalQueue()).proxy__getAdmin() != admin) revert WrongWQAdmin();
        if (IOssifiableProxy(_locator.stakingRouter()).proxy__getAdmin() != admin) revert WrongSQAdmin();
        if (IOssifiableProxy(_locator.validatorsExitBusOracle()).proxy__getAdmin() != admin) revert WrongEBAdmin();
        if (IOssifiableProxy(_locator.accountingOracle()).proxy__getAdmin() != admin) revert WrongAOAdmin();
    }

    function _verifyInitialProxyImplementations() internal view {
        if (IOssifiableProxy(_locator.withdrawalQueue()).proxy__getImplementation() != _dummyImplementation) revert WrongWQInitialImpl();
        if (IOssifiableProxy(_locator.stakingRouter()).proxy__getImplementation() != _dummyImplementation) revert WrongSRInitialImpl();
        if (IOssifiableProxy(_locator.validatorsExitBusOracle()).proxy__getImplementation() != _dummyImplementation) revert WrongEBInitialImpl();
        if (IOssifiableProxy(_locator.accountingOracle()).proxy__getImplementation() != _dummyImplementation) revert WrongAOInitialImpl();
    }

    function _verifyOZAdmins(address admin) internal view {
        if (IAccessControlEnumerable(_hashConsensusForAccountingOracle).getRoleMemberCount(DEFAULT_ADMIN_ROLE) != 1) revert MultipleAdminsHCAO();
        if (IAccessControlEnumerable(_hashConsensusForAccountingOracle).getRoleMember(DEFAULT_ADMIN_ROLE, 0) != admin) revert WrongAdminHCAO();
        if (IAccessControlEnumerable(_hashConsensusForValidatorsExitBusOracle).getRoleMemberCount(DEFAULT_ADMIN_ROLE) != 1) revert MultipleAdminsHCEB();
        if (IAccessControlEnumerable(_hashConsensusForValidatorsExitBusOracle).getRoleMember(DEFAULT_ADMIN_ROLE, 0) != admin) revert WrongAdminHCEB();
        if (IAccessControlEnumerable(_locator.burner()).getRoleMemberCount(DEFAULT_ADMIN_ROLE) != 1) revert MultipleAdminsBU();
        if (IAccessControlEnumerable(_locator.burner()).getRoleMember(DEFAULT_ADMIN_ROLE, 0) != admin) revert WrongAdminBU();
    }

    function _prepareAccountingOracle() internal {
        (, uint256 epochsPerFrame, ) = IHashConsensus(_hashConsensusForAccountingOracle).getFrameConfig();
        uint256 lastLidoOracleCompletedEpochId = ILidoOracle(_locator.legacyOracle()).getLastCompletedEpochId();

        // NB: HashConsensus.updateInitialEpoch must be called after AccountingOracle implementation is bound to proxy
        IOssifiableProxy(_locator.accountingOracle()).proxy__upgradeTo(_accountingOracleImplementation);
        IHashConsensus(_hashConsensusForAccountingOracle).updateInitialEpoch(lastLidoOracleCompletedEpochId + epochsPerFrame);
        IAccountingOracle(_locator.accountingOracle()).initialize(
            address(this),
            _hashConsensusForAccountingOracle,
            _accountingOracleConsensusVersion
        );
    }

    function _prepareValidatorsExitBus() internal {
        IOssifiableProxy(_locator.validatorsExitBusOracle()).proxy__upgradeTo(_validatorsExitBusOracleImplementation);
        IValidatorsExitBusOracle(_locator.validatorsExitBusOracle()).initialize(
            address(this),
            _hashConsensusForValidatorsExitBusOracle,
            _validatorsExitBusOracleConsensusVersion,
            0 // lastProcessingRefSlot TODO when get sure about ExitBus frame duration
        );
    }

    function _migrateLidoOracleCommitteeMembers() internal {
        address[] memory members = ILidoOracle(_locator.legacyOracle()).getOracleMembers();
        uint256 quorum = ILidoOracle(_locator.legacyOracle()).getQuorum();
        IHashConsensus hcForAccounting = IHashConsensus(_hashConsensusForAccountingOracle);
        IHashConsensus hcForExitBus = IHashConsensus(_hashConsensusForValidatorsExitBusOracle);
        bytes32 manage_members_role = hcForAccounting.MANAGE_MEMBERS_AND_QUORUM_ROLE();
        bytes32 submit_data_role = IAccountingOracle(_locator.accountingOracle()).SUBMIT_DATA_ROLE();

        IAccessControlEnumerable(address(hcForAccounting)).grantRole(manage_members_role, address(this));
        IAccessControlEnumerable(address(hcForExitBus)).grantRole(manage_members_role, address(this));
        for (uint256 i; i < members.length; ++i) {
            hcForAccounting.addMember(members[i], quorum);
            IAccessControlEnumerable(_locator.accountingOracle()).grantRole(submit_data_role, members[i]);

            hcForExitBus.addMember(members[i], quorum);
            IAccessControlEnumerable(_locator.validatorsExitBusOracle()).grantRole(submit_data_role, members[i]);
        }
        IAccessControlEnumerable(address(hcForAccounting)).renounceRole(manage_members_role, address(this));
        IAccessControlEnumerable(address(hcForExitBus)).renounceRole(manage_members_role, address(this));
    }

    function _migrateDSMGuardians() internal {
        IDepositSecurityModule dsm = IDepositSecurityModule(_locator.depositSecurityModule());
        address[] memory guardians = dsm.getGuardians();
        uint256 quorum = dsm.getGuardianQuorum();
        dsm.addGuardians(guardians, quorum);
    }

    function _finishUpgrade() internal {
        if (msg.sender != _voting) revert OnlyVotingCanUpgrade();
        if (!isUpgradeStarted) revert StartMustBeCalledBeforeFinish();
        if (isUpgradeFinished) revert CanOnlyFinishOnce();
        /// Here we check that the contract got new ABI function getContractVersion(), although it is 0 yet
        /// because in the new contract version is stored in a different slot
        if (ILegacyOracle(_locator.legacyOracle()).getContractVersion() != 0) revert LidoOracleMustBeUpgradedToLegacy();
        isUpgradeFinished = true;

        ILegacyOracle(_locator.legacyOracle()).finalizeUpgrade_v4(_locator.accountingOracle());

        ILido(_locator.lido()).finalizeUpgrade_v2(address(_locator), _eip712StETH);

        INodeOperatorsRegistry(_nodeOperatorsRegistry).finalizeUpgrade_v2(
            address(_locator),
            _nodeOperatorsRegistryStakingModuleType,
            _nodeOperatorsRegistryStuckPenaltyDelay
        );

        _grantRoles();

        _passAdminRoleFromTemplateToVoting();

        _verifyFinishedUpgrade();
    }

    function _prepareWithdrawalQueue() internal {
        IOssifiableProxy(_locator.withdrawalQueue()).proxy__upgradeTo(_withdrawalQueueImplementation);
        IWithdrawalQueue(_locator.withdrawalQueue()).initialize(address(this));
        _resumePausableContract(_locator.withdrawalQueue());
        _resumePausableContract(_locator.validatorsExitBusOracle());
    }

    function _prepareStakingRouter() internal {
        IOssifiableProxy(_locator.stakingRouter()).proxy__upgradeTo(_stakingRouterImplementation);
        IStakingRouter(_locator.stakingRouter()).initialize(
            address(this),
            _locator.lido(),
            _withdrawalCredentials
        );
        _attachNORToStakingRouter();
        // TODO: maybe attach NOR as module to staking router
    }

    function _attachNORToStakingRouter() internal {
        bytes32 role = IStakingRouter(_locator.stakingRouter()).STAKING_MODULE_MANAGE_ROLE();
        IAccessControlEnumerable(_locator.stakingRouter()).grantRole(role, address(this));
        IStakingRouter(_locator.stakingRouter()).addStakingModule(
            NOR_STAKING_MODULE_NAME,
            _nodeOperatorsRegistry,
            10000, // 100% target share
            500, // 5% staking module fee
            500 // 5% treasury fee
        );
        IAccessControlEnumerable(_locator.stakingRouter()).renounceRole(role, address(this));
    }

    function _grantRoles() internal {
        IBurner burner = IBurner(_locator.burner());
        burner.grantRole(burner.REQUEST_BURN_SHARES_ROLE(), _nodeOperatorsRegistry);

        IStakingRouter router = IStakingRouter(_locator.stakingRouter());
        router.grantRole(router.STAKING_MODULE_PAUSE_ROLE(), _locator.depositSecurityModule());
        router.grantRole(router.STAKING_MODULE_RESUME_ROLE(), _locator.depositSecurityModule());
        router.grantRole(router.REPORT_EXITED_VALIDATORS_ROLE(), _locator.accountingOracle());
        router.grantRole(router.REPORT_REWARDS_MINTED_ROLE(), _locator.lido());

        IValidatorsExitBusOracle exitBusOracle = IValidatorsExitBusOracle(_locator.validatorsExitBusOracle());
        exitBusOracle.grantRole(exitBusOracle.PAUSE_ROLE(), _gateSeal);
        exitBusOracle.grantRole(exitBusOracle.RESUME_ROLE(), _voting);

        IWithdrawalQueue withdrawalQueue = IWithdrawalQueue(_locator.withdrawalQueue());
        withdrawalQueue.grantRole(withdrawalQueue.PAUSE_ROLE(), _gateSeal);
        withdrawalQueue.grantRole(withdrawalQueue.RESUME_ROLE(), _voting);
        withdrawalQueue.grantRole(withdrawalQueue.FINALIZE_ROLE(), _locator.lido());
        withdrawalQueue.grantRole(withdrawalQueue.ORACLE_ROLE(), _locator.accountingOracle());
    }

    function _passAdminRoleFromTemplateToVoting() internal {
        _transferOZAdminFromThisToVoting(_hashConsensusForValidatorsExitBusOracle);
        _transferOZAdminFromThisToVoting(_hashConsensusForAccountingOracle);
        _transferOZAdminFromThisToVoting(_locator.burner());
        _transferOZAdminFromThisToVoting(_locator.stakingRouter());
        _transferOZAdminFromThisToVoting(_locator.accountingOracle());
        _transferOZAdminFromThisToVoting(_locator.validatorsExitBusOracle());
        _transferOZAdminFromThisToVoting(_locator.withdrawalQueue());

        IOssifiableProxy(address(_locator)).proxy__changeAdmin(_voting);
        IOssifiableProxy(_locator.stakingRouter()).proxy__changeAdmin(_voting);
        IOssifiableProxy(_locator.accountingOracle()).proxy__changeAdmin(_voting);
        IOssifiableProxy(_locator.validatorsExitBusOracle()).proxy__changeAdmin(_voting);
        IOssifiableProxy(_locator.withdrawalQueue()).proxy__changeAdmin(_voting);

        IDepositSecurityModule(_locator.depositSecurityModule()).setOwner(_voting);
    }

    function _verifyFinishedUpgrade() internal view {
        // TODO: uncomment if enough gas
        // _checkContractVersions();

        _verifyProxyAdmins(_voting);

        _verifyOZAdmins(_voting);

        // TODO: maybe check non admin roles?

        if (IDepositSecurityModule(_locator.depositSecurityModule()).getOwner() != _voting) revert WrongDsmOwner();

        if (IPausableUntil(_locator.withdrawalQueue()).isPaused()) revert WQNotResumed();
        if (IPausableUntil(_locator.validatorsExitBusOracle()).isPaused()) revert EBNotResumed();
    }

    function _checkContractVersions() internal view {
        if (IVersioned(_locator.lido()).getContractVersion() != 2) revert InvalidLidoVersion();
        if (IVersioned(_locator.legacyOracle()).getContractVersion() != 4) revert InvalidLOVersion();
        if (IVersioned(_locator.accountingOracle()).getContractVersion() != 1) revert InvalidAOVersion();
        if (IVersioned(_locator.stakingRouter()).getContractVersion() != 1) revert InvalidSRVersion();
        if (IVersioned(_locator.validatorsExitBusOracle()).getContractVersion() != 1) revert InvalidEBVersion();
        if (IVersioned(_locator.withdrawalQueue()).getContractVersion() != 1) revert InvalidWQVersion();
    }

    function _transferOZAdminFromThisToVoting(address contractAddress) internal {
        IAccessControlEnumerable(contractAddress).grantRole(DEFAULT_ADMIN_ROLE, _voting);
        IAccessControlEnumerable(contractAddress).renounceRole(DEFAULT_ADMIN_ROLE, address(this));
    }

    function _resumePausableContract(address contractAddress) internal {
        IPausableUntil pausable = IPausableUntil(contractAddress);

        // Need to resume first, otherwise cannot pause
        IAccessControlEnumerable(address(pausable)).grantRole(pausable.RESUME_ROLE(), address(this));
        pausable.resume();
        IAccessControlEnumerable(address(pausable)).renounceRole(pausable.RESUME_ROLE(), address(this));
    }

    error OnlyVotingCanUpgrade();
    error CanOnlyStartOnce();
    error CanOnlyFinishOnce();
    error StartMustBeCalledBeforeFinish();
    error LidoOracleMustNotBeUpgradedToLegacyYet();
    error LidoOracleMustBeUpgradedToLegacy();
    error WrongDsmOwner();
    error WrongLocatorAdmin();
    error WrongWQAdmin();
    error WrongSQAdmin();
    error WrongEBAdmin();
    error WrongAOAdmin();
    error WrongWQInitialImpl();
    error WrongSRInitialImpl();
    error WrongEBInitialImpl();
    error WrongAOInitialImpl();
    error InvalidLidoVersion();
    error InvalidLOVersion();
    error InvalidAOVersion();
    error InvalidSRVersion();
    error InvalidEBVersion();
    error InvalidWQVersion();
    error MultipleAdminsHCAO();
    error WrongAdminHCAO();
    error MultipleAdminsHCEB();
    error WrongAdminHCEB();
    error MultipleAdminsBU();
    error WrongAdminBU();
    error WQNotResumed();
    error EBNotResumed();
}
