"""
Vote 2026_07_15

1. Submit a Dual Governance proposal to activate Staking Router v3 + Curated Module v2 + Community Staking Module v3

# ======================== Start Upgrade ========================
1.1. Call UpgradeTemplate.startUpgrade

# ======================== Core ========================
1.2. Upgrade LidoLocator implementation
1.3. Upgrade StakingRouter implementation and call finalizeUpgrade_v4
1.4. Upgrade AccountingOracle implementation and call finalizeUpgrade_v5
1.5. Upgrade ValidatorsExitBusOracle implementation and call finalizeUpgrade_v3
1.6. Upgrade Accounting implementation
1.7. Upgrade WithdrawalVault implementation and call finalizeUpgrade_v3
1.8. Grant Aragon APP_MANAGER_ROLE to the AGENT
1.9. Set Lido implementation in Kernel
1.10. Revoke Aragon APP_MANAGER_ROLE from the AGENT
1.11. Create Aragon BUFFER_RESERVE_MANAGER_ROLE and grant role manager to the AGENT
1.12. Call finalizeUpgrade_v4 on Lido
1.13. Grant Staking Router STAKING_MODULE_SHARE_MANAGE_ROLE to EasyTrack executor
1.14. Revoke Staking Router STAKING_MODULE_UNVETTING_ROLE from old DSM
1.15. Grant Staking Router STAKING_MODULE_UNVETTING_ROLE to new DSM
1.16. Grant TWG TW_EXIT_LIMIT_MANAGER_ROLE to AGENT
1.17. Set TWG exit request limits
1.18. Register CircuitBreaker pauser for ConsolidationGateway
1.19. Register CircuitBreaker pauser for TopUpGateway

# ======================== CSM ========================
1.20. Upgrade CSM to v3 and call finalizeUpgradeV3
1.21. Upgrade CSM ParametersRegistry to v3 and call finalizeUpgradeV3
1.22. Upgrade CSM FeeOracle to v3 and call finalizeUpgradeV3
1.23. Upgrade CSM VettedGate implementation
1.24. Upgrade CSM Accounting to v3 and call finalizeUpgradeV3
1.25. Upgrade CSM FeeDistributor to v3 and call finalizeUpgradeV3
1.26. Upgrade CSM ExitPenalties implementation
1.27. Upgrade CSM ValidatorStrikes implementation
1.28. Point CSM ValidatorStrikes to the New CSM Ejector
1.29. Revoke CSM REPORT_EL_REWARDS_STEALING_PENALTY_ROLE from CSM Committee
1.30. Grant CSM REPORT_GENERAL_DELAYED_PENALTY_ROLE to CSM Committee
1.31. Revoke CSM SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE from Easy Track executor
1.32. Grant CSM SETTLE_GENERAL_DELAYED_PENALTY_ROLE to Easy Track executor
1.33. Revoke CSM VERIFIER_ROLE from the Old CSM Verifier
1.34. Grant CSM VERIFIER_ROLE to the New CSM Verifier
1.35. Grant CSM REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE to the New CSM Verifier
1.36. Grant CSM REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE to Easy Track executor
1.37. Revoke CSM CREATE_NODE_OPERATOR_ROLE from the Old CSM PermissionlessGate
1.38. Grant CSM CREATE_NODE_OPERATOR_ROLE to the New CSM PermissionlessGate
1.39. Revoke VettedGate START_REFERRAL_SEASON_ROLE from AGENT
1.40. Revoke VettedGate END_REFERRAL_SEASON_ROLE from CSM Committee
1.41. Set name Identified Community Stakers for CSM VettedGate gate
1.42. Unregister CircuitBreaker pauser for Old CSM Verifier
1.43. Unregister CircuitBreaker pauser for Old CSM Ejector
1.44. Register CircuitBreaker pauser for New CSM Verifier
1.45. Register CircuitBreaker pauser for New CSM Ejector
1.46. Register CircuitBreaker pauser for CSM Identified DVT Cluster gate
1.47. Grant CSM CREATE_NODE_OPERATOR_ROLE to Identified DVT Cluster gate
1.48. Grant CSM Accounting SET_BOND_CURVE_ROLE to Identified DVT Cluster gate
1.49. Grant CSM Accounting MANAGE_BOND_CURVES_ROLE to Identified DVT Cluster curve setup
1.50. Grant CSM ParametersRegistry MANAGE_CURVE_PARAMETERS_ROLE to Identified DVT Cluster curve setup
1.51. Execute Identified DVT Cluster curve setup
1.52. Grant CSM ParametersRegistry MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE to CSM Committee
1.53. Revoke Burner REQUEST_BURN_SHARES_ROLE from CSM Accounting
1.54. Grant Burner REQUEST_BURN_MY_STETH_ROLE to CSM Accounting
1.55. Revoke TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE from the Old CSM Ejector
1.56. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the New CSM Ejector

# ======================== Curated Module ========================
1.57. Add Curated Module v2 to StakingRouter
1.58. Grant Burner REQUEST_BURN_MY_STETH_ROLE to Curated Accounting
1.59. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to Curated Ejector
1.60. Grant CM RESUME_ROLE to AGENT
1.61. Resume Curated Module v2
1.62. Revoke CM RESUME_ROLE from AGENT
1.63. Update Curated HashConsensus initial epoch
1.64. Register CircuitBreaker pauser for Curated Module v2
1.65. Register CircuitBreaker pauser for Curated Accounting
1.66. Register CircuitBreaker pauser for Curated FeeOracle
1.67. Register CircuitBreaker pauser for Curated Verifier
1.68. Register CircuitBreaker pauser for Curated Ejector
# ======================== Finish Upgrade ========================
1.69. Call UpgradeTemplate.finishUpgrade

# ======================== EasyTrack ========================
2. Remove CSMSettleElStealingPenalty factory from Easy Track
3. Remove CSMSetVettedGateTree factory from Easy Track
4. Add UpdateStakingModuleShareLimits (for CSM) factory to Easy Track
5. Add AllowConsolidationPair factory to Easy Track
6. Add SetMerkleGateTree CSM factory to Easy Track
7. Add ReportWithdrawalsForSlashedValidators CSM factory to Easy Track
8. Add SettleGeneralDelayedPenalty CSM factory to Easy Track
9. Add SetMerkleGateTree CM factory to Easy Track
10. Add ReportWithdrawalsForSlashedValidators CM factory to Easy Track
11. Add SettleGeneralDelayedPenalty CM factory to Easy Track
12. Add CreateOrUpdateOperatorGroup CM factory to Easy Track

Vote passed & executed on [TBA] +UTC, block [TBA]

"""

from typing import Dict, List, Optional, Tuple

from brownie import interface

from utils.config import (
    UPGRADE_VOTE_SCRIPT,
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.dual_governance import submit_proposals
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

# SRv3/CMv2 upgrade omnibus (UpgradeVoteScript) — the vote script reads its items
# from this contract. Synced from core/deployed-mainnet.json.
UPGRADE_VOTE_SCRIPT = "0xE6530830A2cf90773cB232748b2c674c27b6E0CA"

# ============================= Description ==================================
DG_PROPOSAL_METADATA = "Activate Staking Router v3 + Curated Module v2 + Community Staking Module v3"
DG_SUBMISSION_DESCRIPTION = "1. Submit a Dual Governance proposal to activate Staking Router v3 + Curated Module v2 + Community Staking Module v3"
IPFS_DESCRIPTION = """
1. **Activate Staking Router v3**, including protocol contract upgrades and Dual Governance execution setup. Items 1.1-1.19.
2. **Upgrade Community Staking Module to v3**, including CSM contract upgrades, role updates and identified DVT cluster setup. Items 1.20-1.56.
3. **Add and configure Curated Module v2**. Items 1.57-1.68.
4. **Finalize the protocol upgrade**. Item 1.69.
5. **Update Easy Track factories for CSM v3 and Curated Module v2 operations**. Items 2-12.
"""


def is_placeholder_vote_script_address(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in (
        "",
        "0x0000000000000000000000000000000000000000",
    ) or normalized.startswith("todo")


def get_dg_items(upgrade_vote_script: Optional[str] = None) -> List[Tuple[str, str]]:
    vote_script_address = (upgrade_vote_script or UPGRADE_VOTE_SCRIPT).strip()
    if is_placeholder_vote_script_address(vote_script_address):
        raise ValueError(
            "UpgradeVoteScript address is not configured. "
            "Pass upgrade_vote_script explicitly or set UPGRADE_VOTE_SCRIPT at the top of this file."
        )

    omnibus = interface.UpgradeVoteScript(vote_script_address)
    dg_items: List[Tuple[str, str]] = []

    for _, call_script in omnibus.getVoteItems():
        dg_items.append((call_script[0], call_script[1].hex()))

    return dg_items


def get_vote_items(
    upgrade_vote_script: Optional[str] = None,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    vote_script_address = (upgrade_vote_script or UPGRADE_VOTE_SCRIPT).strip()
    if is_placeholder_vote_script_address(vote_script_address):
        raise ValueError(
            "UpgradeVoteScript address is not configured. "
            "Pass upgrade_vote_script explicitly or set UPGRADE_VOTE_SCRIPT at the top of this file."
        )

    omnibus = interface.UpgradeVoteScript(vote_script_address)

    vote_desc_items: List[str] = []
    call_script_items: List[Tuple[str, str]] = []

    dg_items = get_dg_items(upgrade_vote_script)

    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_METADATA)])
    vote_desc_items.append(DG_SUBMISSION_DESCRIPTION)
    call_script_items.append(dg_call_script[0])

    voting_items = omnibus.getVotingVoteItems()
    for desc, call_script in voting_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
    upgrade_vote_script: Optional[str] = None,
):
    vote_desc_items, call_script_items = get_vote_items(
        upgrade_vote_script=upgrade_vote_script,
    )
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))
    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    vote_script_address = (upgrade_vote_script or UPGRADE_VOTE_SCRIPT).strip()
    assert interface.UpgradeVoteScript(vote_script_address).isValidVoteScript(
        vote_id,
        DG_PROPOSAL_METADATA,
    )

    return vote_id, tx


def main(upgrade_vote_script: Optional[str] = None):
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(
        tx_params=tx_params,
        silent=False,
        upgrade_vote_script=upgrade_vote_script,
    )
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def post_vote_on_fork():
    if get_is_live():
        raise Exception("This hook is for local testing only.")

    print("Rebuilding CSM total withdrawn validators after vote...")
    contracts.csm.rebuildTotalWithdrawnValidators({"from": get_deployer_account(), "silent": True})
    print("[ok] CSM total withdrawn validators rebuilt")


def start_and_execute_vote_on_fork_manual(upgrade_vote_script: Optional[str] = None):
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(
        tx_params=tx_params,
        silent=True,
        upgrade_vote_script=upgrade_vote_script,
    )
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(
        int(vote_id),
        step_by_step=True,
    )
    post_vote_on_fork()
