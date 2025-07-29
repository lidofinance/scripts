import pytest
from brownie import ZERO_ADDRESS, interface  # type: ignore
from utils.config import network_name

if network_name() not in ["mainnet", "mainnet-fork", "hoodi", "hoodi-fork", "mfh-1", "mfh-2", "mfh-3"]:
    print(f"""\nSkip DG acceptance tests as it's not deployed on network "f{network_name()}" """)
    pytest.skip(allow_module_level=True)

from utils.config import (
    contracts,
    # addresses
    DUAL_GOVERNANCE,
    RESEAL_MANAGER,
    RESEAL_COMMITTEE,
    DUAL_GOVERNANCE_EXECUTORS,
    ESCROW_MASTER_COPY,
    ESCROW_VETO_SIGNALLING,
    WSTETH_TOKEN,
    LIDO,
    TIMELOCK,
    WITHDRAWAL_QUEUE,
    # contract values
    MAX_MIN_ASSETS_LOCK_DURATION,
    DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES,
    DUAL_GOVERNANCE_VALUES,
    EMERGENCY_PROTECTED_TIMELOCK_VALUES,
    TIEBREAKER_VALUES,
)

ESCROW_STATES = {
    "not_initialized": 0,
    "veto_signalling": 1,
    "rage_quit": 2,
}


def test_dual_governance_acceptance():
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

    assert dual_governance.getConfigProvider() == contracts.dual_governance_config_provider
    assert dual_governance.TIMELOCK() == contracts.emergency_protected_timelock

    assert dual_governance.getResealManager() == RESEAL_MANAGER
    assert dual_governance.getResealCommittee() == RESEAL_COMMITTEE

    proposer_data = dual_governance.getProposer(contracts.voting)
    assert proposer_data[0] == contracts.voting
    assert proposer_data[1] == DUAL_GOVERNANCE_EXECUTORS[0]

    assert (
        dual_governance.MAX_TIEBREAKER_ACTIVATION_TIMEOUT()
        == DUAL_GOVERNANCE_VALUES["MAX_TIEBREAKER_ACTIVATION_TIMEOUT"]
    )
    assert (
        dual_governance.MIN_TIEBREAKER_ACTIVATION_TIMEOUT()
        == DUAL_GOVERNANCE_VALUES["MIN_TIEBREAKER_ACTIVATION_TIMEOUT"]
    )

    assert (
        dual_governance.MAX_SEALABLE_WITHDRAWAL_BLOCKERS_COUNT()
        == DUAL_GOVERNANCE_VALUES["MAX_SEALABLE_WITHDRAWAL_BLOCKERS_COUNT"]
    )
    assert dual_governance.getProposalsCanceller() == contracts.voting

    tiebreaker_details = dual_governance.getTiebreakerDetails()
    assert tiebreaker_details[0] == False  # is tie
    assert tiebreaker_details[1] == DUAL_GOVERNANCE_VALUES["TIEBREAKER_DETAILS"]["TIEBREAKER_COMMITTEE"]
    assert tiebreaker_details[2] == DUAL_GOVERNANCE_VALUES["TIEBREAKER_DETAILS"]["TIEBREAKER_ACTIVATION_TIMEOUT"]
    assert tiebreaker_details[3] == DUAL_GOVERNANCE_VALUES["TIEBREAKER_DETAILS"]["WITHDRAWAL_BLOCKERS"]

    assert len(dual_governance.getProposers()) == DUAL_GOVERNANCE_VALUES["PROPOSERS_COUNT"]

    assert dual_governance.getVetoSignallingEscrow() == ESCROW_VETO_SIGNALLING


def test_emergency_protected_timelock_acceptance():
    ept = contracts.emergency_protected_timelock

    assert ept.MAX_AFTER_SCHEDULE_DELAY() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["MAX_AFTER_SCHEDULE_DELAY"]
    assert ept.MAX_AFTER_SUBMIT_DELAY() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["MAX_AFTER_SUBMIT_DELAY"]
    assert ept.MAX_EMERGENCY_MODE_DURATION() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["MAX_EMERGENCY_MODE_DURATION"]
    assert (
        ept.MAX_EMERGENCY_PROTECTION_DURATION()
        == EMERGENCY_PROTECTED_TIMELOCK_VALUES["MAX_EMERGENCY_PROTECTION_DURATION"]
    )
    assert ept.MIN_EXECUTION_DELAY() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["MIN_EXECUTION_DELAY"]

    assert ept.getAfterScheduleDelay() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["AFTER_SCHEDULE_DELAY"]
    assert ept.getAfterSubmitDelay() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["AFTER_SUBMIT_DELAY"]

    assert ept.getAdminExecutor() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["ADMIN_EXECUTOR"]
    assert ept.getGovernance() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["GOVERNANCE"]

    assert ept.isEmergencyModeActive() == False
    assert ept.isEmergencyProtectionEnabled() == True

    assert (
        ept.getEmergencyActivationCommittee() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["EMERGENCY_ACTIVATION_COMMITTEE"]
    )
    assert ept.getEmergencyExecutionCommittee() == EMERGENCY_PROTECTED_TIMELOCK_VALUES["EMERGENCY_EXECUTION_COMMITTEE"]

    assert ept.getEmergencyGovernance() == contracts.emergency_governance

    emergency_protection_details = ept.getEmergencyProtectionDetails()

    # https://github.com/lidofinance/dual-governance/blob/main/contracts/interfaces/IEmergencyProtectedTimelock.sol#L10
    assert (
        emergency_protection_details[0] == EMERGENCY_PROTECTED_TIMELOCK_VALUES["EMERGENCY_PROTECTION_DETAILS"][0]
    )  # Emergency mode duration
    assert (
        emergency_protection_details[1] == EMERGENCY_PROTECTED_TIMELOCK_VALUES["EMERGENCY_PROTECTION_DETAILS"][1]
    )  # Emergency mode ends after
    assert (
        emergency_protection_details[2] == EMERGENCY_PROTECTED_TIMELOCK_VALUES["EMERGENCY_PROTECTION_DETAILS"][2]
    )  # Emergency protection ends after


def test_emergency_governance():
    eg = contracts.emergency_governance

    assert eg.GOVERNANCE() == contracts.voting
    assert eg.TIMELOCK() == contracts.emergency_protected_timelock


def test_dual_governance_executor():
    for executor_address in DUAL_GOVERNANCE_EXECUTORS:
        executor = interface.DualGovernanceExecutor(executor_address)

        assert executor.owner() == contracts.emergency_protected_timelock


def test_dual_governance_config_provider_acceptance():
    dgcp = contracts.dual_governance_config_provider

    assert dgcp.FIRST_SEAL_RAGE_QUIT_SUPPORT() == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["FIRST_SEAL_RAGE_QUIT_SUPPORT"]
    assert (
        dgcp.SECOND_SEAL_RAGE_QUIT_SUPPORT() == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["SECOND_SEAL_RAGE_QUIT_SUPPORT"]
    )
    assert dgcp.MIN_ASSETS_LOCK_DURATION() == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["MIN_ASSETS_LOCK_DURATION"]
    assert (
        dgcp.RAGE_QUIT_ETH_WITHDRAWALS_DELAY_GROWTH()
        == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["RAGE_QUIT_ETH_WITHDRAWALS_DELAY_GROWTH"]
    )
    assert (
        dgcp.RAGE_QUIT_ETH_WITHDRAWALS_MIN_DELAY()
        == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["RAGE_QUIT_ETH_WITHDRAWALS_MIN_DELAY"]
    )
    assert (
        dgcp.RAGE_QUIT_ETH_WITHDRAWALS_MAX_DELAY()
        == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["RAGE_QUIT_ETH_WITHDRAWALS_MAX_DELAY"]
    )
    assert (
        dgcp.RAGE_QUIT_EXTENSION_PERIOD_DURATION()
        == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["RAGE_QUIT_EXTENSION_PERIOD_DURATION"]
    )
    assert dgcp.VETO_COOLDOWN_DURATION() == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_COOLDOWN_DURATION"]
    assert (
        dgcp.VETO_SIGNALLING_DEACTIVATION_MAX_DURATION()
        == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_DEACTIVATION_MAX_DURATION"]
    )
    assert (
        dgcp.VETO_SIGNALLING_MIN_ACTIVE_DURATION()
        == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_MIN_ACTIVE_DURATION"]
    )
    assert dgcp.VETO_SIGNALLING_MAX_DURATION() == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_MAX_DURATION"]
    assert dgcp.VETO_SIGNALLING_MIN_DURATION() == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_MIN_DURATION"]

    config = dgcp.getDualGovernanceConfig()

    assert config[0] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["FIRST_SEAL_RAGE_QUIT_SUPPORT"]
    assert config[1] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["SECOND_SEAL_RAGE_QUIT_SUPPORT"]
    assert config[2] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["MIN_ASSETS_LOCK_DURATION"]
    assert config[3] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_MIN_DURATION"]
    assert config[4] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_MAX_DURATION"]
    assert config[5] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_MIN_ACTIVE_DURATION"]
    assert config[6] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_SIGNALLING_DEACTIVATION_MAX_DURATION"]
    assert config[7] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["VETO_COOLDOWN_DURATION"]
    assert config[8] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["RAGE_QUIT_EXTENSION_PERIOD_DURATION"]
    assert config[9] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["RAGE_QUIT_ETH_WITHDRAWALS_MIN_DELAY"]
    assert config[10] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["RAGE_QUIT_ETH_WITHDRAWALS_MAX_DELAY"]
    assert config[11] == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["RAGE_QUIT_ETH_WITHDRAWALS_DELAY_GROWTH"]


def test_tiebreaker_committees():
    tiebreaker_core_committee = interface.TiebreakerCommittee(TIEBREAKER_VALUES["CORE_COMMITTEE"]["ADDRESS"])

    assert tiebreaker_core_committee.owner() == TIEBREAKER_VALUES["CORE_COMMITTEE"]["OWNER"]
    assert tiebreaker_core_committee.getMembers() == TIEBREAKER_VALUES["CORE_COMMITTEE"]["MEMBERS"]
    assert tiebreaker_core_committee.getQuorum() == TIEBREAKER_VALUES["CORE_COMMITTEE"]["QUORUM"]
    assert tiebreaker_core_committee.getTimelockDuration() == TIEBREAKER_VALUES["CORE_COMMITTEE"]["TIMELOCK_DURATION"]
    assert tiebreaker_core_committee.DUAL_GOVERNANCE() == DUAL_GOVERNANCE

    for i, sub_committee in enumerate(TIEBREAKER_VALUES["SUB_COMMITTEES"]):
        tiebreaker_sub_committee = interface.TiebreakerCommittee(sub_committee["ADDRESS"])

        assert tiebreaker_sub_committee.owner() == sub_committee["OWNER"]
        assert tiebreaker_sub_committee.getMembers() == sub_committee["MEMBERS"]
        assert tiebreaker_sub_committee.getQuorum() == sub_committee["QUORUM"]
        assert tiebreaker_sub_committee.TIEBREAKER_CORE_COMMITTEE() == TIEBREAKER_VALUES["CORE_COMMITTEE"]["ADDRESS"]

        assert sub_committee["ADDRESS"] == TIEBREAKER_VALUES["CORE_COMMITTEE"]["MEMBERS"][i]


def test_escrow():
    escrow_proxy = interface.DualGovernanceEscrow(ESCROW_VETO_SIGNALLING)
    escrow_master_copy = interface.DualGovernanceEscrow(ESCROW_MASTER_COPY)

    for escrow in [escrow_master_copy, escrow_proxy]:
        assert escrow.ESCROW_MASTER_COPY() == ESCROW_MASTER_COPY
        assert escrow.DUAL_GOVERNANCE() == DUAL_GOVERNANCE
        assert escrow.ST_ETH() == LIDO
        assert escrow.WST_ETH() == WSTETH_TOKEN
        assert escrow.WITHDRAWAL_QUEUE() == WITHDRAWAL_QUEUE
        assert escrow.MAX_MIN_ASSETS_LOCK_DURATION() == MAX_MIN_ASSETS_LOCK_DURATION
        assert escrow.MIN_TRANSFERRABLE_ST_ETH_AMOUNT() == 100
        assert escrow.MIN_WITHDRAWALS_BATCH_SIZE() == 4

    assert escrow_proxy.getMinAssetsLockDuration() == DUAL_GOVERNANCE_CONFIG_PROVIDER_VALUES["MIN_ASSETS_LOCK_DURATION"]
    assert escrow_proxy.getEscrowState() == ESCROW_STATES["veto_signalling"]
    assert contracts.dual_governance.getRageQuitEscrow() == ZERO_ADDRESS


def test_reseal_manager():
    reseal_manager = interface.ResealManager(RESEAL_MANAGER)

    assert reseal_manager.EMERGENCY_PROTECTED_TIMELOCK() == TIMELOCK
