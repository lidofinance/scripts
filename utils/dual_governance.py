from brownie import accounts, chain, web3
from typing import Tuple, Sequence

from eth_abi.abi import encode

from utils.config import contracts
from tests.conftest import get_active_proposals_from_env

MAX_ITERATIONS = 1000

# https://github.com/lidofinance/dual-governance/blob/main/contracts/libraries/ExecutableProposals.sol#L27
PROPOSAL_STATUS = {
    "not_exist": 0,
    "submitted": 1,
    "scheduled": 2,
    "executed": 3,
    "cancelled": 4,
}

# https://github.com/lidofinance/dual-governance/blob/main/contracts/libraries/DualGovernanceStateMachine.sol#L35
DUAL_GOVERNANCE_STATE = {
    "normal": 1,
    "veto_signalling": 2,
    "veto_signalling_deactivation": 3,
    "veto_cooldown": 4,
    "rage_quit": 5,
}


def is_there_any_proposals_from_env() -> bool:
    return len(get_active_proposals_from_env()) > 0


def submit_proposals(items: Sequence[Tuple[Sequence[Tuple[str, str]], str]]) -> Sequence[Tuple[str, str]]:
    proposal_list = []

    for call_script, description in items:
        proposal_calldata = []

        for address, calldata in call_script:
            proposal_calldata.append((address, 0, calldata))

        proposal_list.append(
            (
                contracts.dual_governance.address,
                contracts.dual_governance.submitProposal.encode_input(proposal_calldata, description),
            )
        )
    return proposal_list


def process_proposals(proposal_ids: Sequence[int]):
    proposals_to_be_processed = list(proposal_ids)
    stranger = accounts[0]

    after_submit_delay = contracts.emergency_protected_timelock.getAfterSubmitDelay()
    after_schedule_delay = contracts.emergency_protected_timelock.getAfterScheduleDelay()

    submitted_proposals = []
    scheduled_proposals = []

    copy_proposals_to_be_processed = proposals_to_be_processed.copy()
    for proposal_id in copy_proposals_to_be_processed:
        (_, _, _, _, proposal_status) = contracts.emergency_protected_timelock.getProposalDetails(proposal_id)
        if proposal_status == PROPOSAL_STATUS["submitted"]:
            submitted_proposals.append(proposal_id)
            proposals_to_be_processed.remove(proposal_id)
        elif proposal_status == PROPOSAL_STATUS["scheduled"]:
            scheduled_proposals.append(proposal_id)
            proposals_to_be_processed.remove(proposal_id)
        elif proposal_status in [PROPOSAL_STATUS["cancelled"], PROPOSAL_STATUS["executed"]]:
            proposals_to_be_processed.remove(proposal_id)

    if len(submitted_proposals):
        chain.sleep(after_submit_delay + 1)

        first_proposal_id = submitted_proposals[0]
        iterations = 0
        while not contracts.dual_governance.canScheduleProposal(first_proposal_id):
            wait_for_normal_state(stranger)
            iterations += 1
            if iterations > MAX_ITERATIONS:
                raise Exception(f"Unable to schedule the proposal. ({first_proposal_id})")

        for proposal_id in submitted_proposals:
            contracts.dual_governance.scheduleProposal(proposal_id, {"from": stranger})
            scheduled_proposals.append(proposal_id)

    if len(scheduled_proposals):
        chain.sleep(after_schedule_delay + 1)
        wait_for_target_time_to_satisfy_time_constrains()

        # The SRv3/CMv2 upgrade calls Lido.finalizeUpgrade_v4, which reverts with "NO_REPORT"
        # unless the current AccountingOracle frame already has a submitted main report.
        # The DG submit/schedule delays above advance time by ~4 days, rolling the oracle frame
        # over and invalidating any prior report. On real mainnet a fresh daily report naturally
        # exists by execution time; on a fork we reproduce that by pushing one right before execute.
        # The report goes through the OLD (pre-upgrade, v4) oracle, so it is built in the legacy
        # v4 format, self-contained below. Once the AO is at v5+ (the upgrade is already enacted
        # on the forked chain / future votes), no report is needed at all.
        # Test/fork-only scaffolding for this specific vote: delete together with archiving
        # scripts/upgrade_2026_04_30_srv3_cmv2.py.
        if contracts.accounting_oracle.getContractVersion() < 5:
            # Mine a block first so the latest block timestamp absorbs the accumulated
            # chain.sleep offset from the DG delays above; otherwise the frame math (which
            # mixes a pending-state getCurrentFrame() with the latest mined block time)
            # overshoots the frame.
            chain.mine(1)
            _push_legacy_v4_oracle_report()

        for proposal_id in scheduled_proposals:
            contracts.emergency_protected_timelock.execute(proposal_id, {"from": stranger})
            (_, _, _, _, proposal_status) = contracts.emergency_protected_timelock.getProposalDetails(proposal_id)
            assert proposal_status == PROPOSAL_STATUS["executed"], f"Proposal {proposal_id} execution failed"

    if len(proposals_to_be_processed):
        raise Exception(
            f"Unable to process proposals: {proposals_to_be_processed}. Proposals are already processed or cancelled."
        )


# Legacy (pre-SRv3) AccountingOracle ReportData tuple — 17 fields, v4 layout with
# numValidators/clBalanceGwei. Hardcoded on purpose: interfaces/AccountingOracle.json
# holds the v5 ABI, while this report targets the OLD implementation before the vote
# is executed. Self-contained so the main oracle helpers can stay v5-only.
# Delete together with archiving scripts/upgrade_2026_04_30_srv3_cmv2.py.
_LEGACY_V4_REPORT_ABI = (
    "(uint256,uint256,uint256,uint256,uint256[],uint256[],uint256,uint256,uint256,"
    "uint256[],uint256,bool,bytes32,string,uint256,bytes32,uint256)"
)


def _push_legacy_v4_oracle_report():
    """Push a minimal v4-format accounting report so the current frame has
    mainDataSubmitted == true (required by Lido.finalizeUpgrade_v4). No withdrawal
    finalization, no extra data — just enough for the NO_REPORT check to pass."""
    from utils.test.helpers import eth_balance
    from utils.test.oracle_report_helpers import (
        ZERO_BYTES32,
        MOCK_VAULTS_DATA_TREE_ROOT,
        MOCK_VAULTS_DATA_TREE_CID,
        reach_consensus,
        wait_to_next_available_report_time,
    )

    consensus = contracts.hash_consensus_for_accounting_oracle
    oracle = contracts.accounting_oracle

    wait_to_next_available_report_time(consensus)
    (ref_slot, _) = consensus.getCurrentFrame()

    # version getters are identical in the v4 and v5 ABIs — safe via the interface
    contract_version = oracle.getContractVersion()
    consensus_version = oracle.getConsensusVersion()
    (_, beacon_validators, beacon_balance) = contracts.lido.getBeaconStat()
    (cover_shares, non_cover_shares) = contracts.burner.getSharesRequestedToBurn()

    report = (
        int(consensus_version),
        int(ref_slot),
        int(beacon_validators),
        int(beacon_balance) // 10**9,  # clBalanceGwei
        [],  # stakingModuleIdsWithNewlyExitedValidators
        [],  # numExitedValidatorsByStakingModule
        int(eth_balance(contracts.withdrawal_vault.address)),
        int(eth_balance(contracts.execution_layer_rewards_vault.address)),
        int(cover_shares + non_cover_shares),
        [],  # withdrawalFinalizationBatches (skip withdrawals)
        0,  # simulatedShareRate (unchecked when batches are empty)
        False,  # isBunkerMode
        bytes(MOCK_VAULTS_DATA_TREE_ROOT),
        MOCK_VAULTS_DATA_TREE_CID,
        0,  # extraDataFormat: EXTRA_DATA_FORMAT_EMPTY
        bytes(ZERO_BYTES32),
        0,  # extraDataItemsCount
    )

    encoded_report = encode([_LEGACY_V4_REPORT_ABI], [report])
    report_hash = web3.keccak(encoded_report)

    submitter = reach_consensus(ref_slot, report_hash, consensus_version, consensus, silent=True)
    accounts[0].transfer(submitter, 10**19)

    # raw calls: the loaded interface carries the v5 ABI, the old impl needs v4 encoding
    submit_calldata = web3.keccak(text=f"submitReportData({_LEGACY_V4_REPORT_ABI},uint256)")[:4] + encode(
        [_LEGACY_V4_REPORT_ABI, "uint256"], [report, int(contract_version)]
    )
    accounts.at(submitter, force=True).transfer(to=oracle.address, data=submit_calldata)

    extra_data_calldata = web3.keccak(text="submitReportExtraDataEmpty()")[:4]
    accounts.at(submitter, force=True).transfer(to=oracle.address, data=extra_data_calldata)


def process_pending_proposals():
    last_proposal_id = contracts.emergency_protected_timelock.getProposalsCount()

    if is_proposal_executed(last_proposal_id):
        return

    current_proposal_id = last_proposal_id
    while not is_proposal_executed(current_proposal_id):
        current_proposal_id -= 1
        if current_proposal_id == 1:
            break

    current_proposal_id += 1

    process_proposals(list(range(current_proposal_id, last_proposal_id + 1)))


def wait_for_normal_state(stranger):
    # https://github.com/lidofinance/dual-governance/blob/main/contracts/interfaces/IDualGovernance.sol#L15
    state_details = contracts.dual_governance.getStateDetails()

    effective_state = state_details[0]
    persisted_state_entered_at = state_details[2]
    veto_signalling_activated_at = state_details[3]
    veto_signalling_duration = state_details[7]

    if effective_state == DUAL_GOVERNANCE_STATE["rage_quit"]:
        raise Exception("Dual Governance is in Rage Quit state. Unable to process proposals.")

    if effective_state == DUAL_GOVERNANCE_STATE["veto_signalling"]:
        remaining_time = veto_signalling_activated_at + veto_signalling_duration - chain.time()
        if remaining_time > 0:
            chain.sleep(remaining_time + 1)

    if effective_state == DUAL_GOVERNANCE_STATE["veto_signalling_deactivation"]:
        # https://github.com/lidofinance/dual-governance/blob/main/contracts/ImmutableDualGovernanceConfigProvider.sol#L98
        config = contracts.dual_governance_config_provider.getDualGovernanceConfig()
        veto_signalling_deactivation_max_duration = config[4]

        remaining_time = persisted_state_entered_at + veto_signalling_deactivation_max_duration - chain.time()

        if remaining_time > 0:
            chain.sleep(remaining_time + 1)

    contracts.dual_governance.activateNextState({"from": stranger})


def wait_for_time_window(from_hour_utc: int, to_hour_utc: int):
    """Wait until current time is within specified UTC hour window"""
    current_time = chain.time()
    seconds_per_day = 24 * 60 * 60

    # Get current UTC hour
    current_utc_seconds = current_time % seconds_per_day
    current_utc_hour = current_utc_seconds // 3600

    # Check if we're already in the window
    if from_hour_utc <= current_utc_hour < to_hour_utc:
        print(f"Already in time window ({from_hour_utc}:00-{to_hour_utc}:00 UTC)")
        return

    # Calculate when to sleep until
    day_start = current_time - current_utc_seconds
    window_start = day_start + from_hour_utc * 60 * 60
    window_end = day_start + to_hour_utc * 60 * 60

    # If we're past today's window, wait for tomorrow's window
    if current_time >= window_end:
        target_time = window_start + seconds_per_day
    else:
        # Wait for today's window
        target_time = window_start

    sleep_time = target_time - current_time + 1
    print(f"Sleeping {sleep_time} seconds to reach time window ({from_hour_utc}:00-{to_hour_utc}:00 UTC)")
    chain.sleep(sleep_time)


def wait_for_target_time_to_satisfy_time_constrains():
    current_time = chain.time()
    target_time = 16 * 60 * 60  # 16:00 UTC
    seconds_per_day = 24 * 60 * 60

    day_start = current_time - (current_time % seconds_per_day)
    today_target_time = day_start + target_time

    if current_time >= today_target_time:
        target_time = today_target_time + seconds_per_day
    else:
        target_time = today_target_time

    chain.sleep(target_time - current_time)


def is_proposal_executed(proposal_id: int) -> bool:
    (_, _, _, _, proposal_status) = contracts.emergency_protected_timelock.getProposalDetails(proposal_id)
    return proposal_status == PROPOSAL_STATUS["executed"]
