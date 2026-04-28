"""
TODO Vote 2026_04_14

Uses deployed `UpgradeVoteScript` as the source of truth for both:
1. DG items returned by `getVoteItems()`
2. Immediate voting items returned by `getVotingVoteItems()`

Replace the TODO values below after the Hoodi deployment.
"""

import os

from typing import Dict, List, Optional, Tuple

from brownie import interface

from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.dual_governance import submit_proposals
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.voting import bake_vote_items, confirm_vote_script, create_vote


# ============================== Addresses ===================================
UPGRADE_VOTE_SCRIPT = "TODO: set deployed UpgradeVoteScript address"
HOODI_DG_ONLY_ENV = "HOODI_DG_ONLY"


# ============================= Description ==================================
DG_PROPOSAL_METADATA = "Upgrade Lido protocol contracts on Ethereum Hoodi testnet"
DG_SUBMISSION_DESCRIPTION = "1. Submit a Dual Governance proposal for the Lido protocol upgrade on Ethereum Hoodi testnet"
DG_IPFS_DESCRIPTION = """
**Lido protocol upgrade on Ethereum Hoodi testnet**

**Dual Governance proposal**
1. Submit a Dual Governance proposal for the Lido protocol upgrade on Ethereum Hoodi testnet.
1.1. Call UpgradeTemplate.startUpgrade
1.2. Upgrade LidoLocator implementation
1.3. Upgrade StakingRouter implementation
1.4. Upgrade AccountingOracle implementation
1.5. Upgrade ValidatorsExitBusOracle implementation
1.6. Upgrade Accounting implementation
1.7. Upgrade WithdrawalVault implementation
1.8. Grant Aragon APP_MANAGER_ROLE to the AGENT
1.9. Set Lido implementation in Kernel
1.10. Revoke Aragon APP_MANAGER_ROLE from the AGENT
1.11. Create and grant Aragon BUFFER_RESERVE_MANAGER_ROLE to the AGENT
1.12. Call finalizeUpgrade_v4 on Lido
1.13. Grant STAKING_MODULE_SHARE_MANAGE_ROLE to EasyTrack executor
1.14. Revoke STAKING_MODULE_UNVETTING_ROLE from old DSM
1.15. Grant STAKING_MODULE_UNVETTING_ROLE to new DSM
1.16. Grant TW_EXIT_LIMIT_MANAGER_ROLE to Agent on TWGateway
1.17. Set TWGateway exit request limits
1.18. Register CircuitBreaker pauser for ConsolidationGateway
1.19. Upgrade and finalize CSM v3
1.20. Upgrade and finalize ParametersRegistry v3
1.21. Upgrade and finalize FeeOracle v3
1.22. Upgrade VettedGate implementation
1.23. Upgrade and finalize Accounting v3
1.24. Upgrade and finalize FeeDistributor v3
1.25. Upgrade ExitPenalties implementation
1.26. Upgrade ValidatorStrikes implementation
1.27. Point ValidatorStrikes to the new Ejector
1.28. Revoke REPORT_EL_REWARDS_STEALING_PENALTY_ROLE
1.29. Grant REPORT_GENERAL_DELAYED_PENALTY_ROLE
1.30. Revoke SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE
1.31. Grant SETTLE_GENERAL_DELAYED_PENALTY_ROLE
1.32. Revoke VERIFIER_ROLE from old verifier
1.33. Grant VERIFIER_ROLE to new verifier
1.34. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE to VerifierV3
1.35. Grant REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE to Easy Track
1.36. Revoke CREATE_NODE_OPERATOR_ROLE from old PermissionlessGate
1.37. Grant CREATE_NODE_OPERATOR_ROLE to new PermissionlessGate
1.38. Revoke START_REFERRAL_SEASON_ROLE
1.39. Revoke END_REFERRAL_SEASON_ROLE
1.40. Register CircuitBreaker pauser for CSM new verifier
1.41. Register CircuitBreaker pauser for CSM Ejector
1.42. Register CircuitBreaker pauser for CSM identified DVT cluster gate
1.43. Grant CREATE_NODE_OPERATOR_ROLE to identified DVT cluster gate
1.44. Grant SET_BOND_CURVE_ROLE to identified DVT cluster gate
1.45. Grant MANAGE_BOND_CURVES_ROLE to identified DVT cluster curve setup
1.46. Grant MANAGE_CURVE_PARAMETERS_ROLE to identified DVT cluster curve setup
1.47. Execute identified DVT cluster curve setup
1.48. Grant MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE to CSM Committee
1.49. Revoke REQUEST_BURN_SHARES_ROLE from CSM Accounting
1.50. Grant REQUEST_BURN_MY_STETH_ROLE to CSM Accounting
1.51. Revoke TWG full-withdrawal role from old Ejector
1.52. Grant TWG full-withdrawal role to new Ejector
1.53. Add Curated module to StakingRouter
1.54. Grant REQUEST_BURN_MY_STETH_ROLE to Curated Accounting
1.55. Grant TWG full-withdrawal role to Curated Ejector
1.56. Grant RESUME_ROLE to agent on Curated module
1.57. Resume Curated module
1.58. Revoke RESUME_ROLE from agent on Curated module
1.59. Update Curated HashConsensus initial epoch
1.60. Register CircuitBreaker pauser for CuratedModule
1.61. Register CircuitBreaker pauser for Curated Accounting
1.62. Register CircuitBreaker pauser for Curated FeeOracle
1.63. Register CircuitBreaker pauser for Curated Verifier
1.64. Register CircuitBreaker pauser for Curated Ejector
1.65. Call UpgradeTemplate.finishUpgrade
"""

IMMEDIATE_VOTING_IPFS_DESCRIPTION = """**Immediate voting items**
2. Remove CSMSettleElStealingPenalty ET factory
3. Remove CSMSetVettedGateTree ET factory
4. Add UpdateStakingModuleShareLimits ET factory
5. Add AllowConsolidationPair ET factory
6. Add SetMerkleGateTree CSM ET factory
7. Add ReportWithdrawalsForSlashedValidators CSM ET factory
8. Add SettleGeneralDelayedPenalty CSM ET factory
9. Add SetMerkleGateTree CM ET factory
10. Add ReportWithdrawalsForSlashedValidators CM ET factory
11. Add SettleGeneralDelayedPenalty CM ET factory
12. Add CreateOrUpdateOperatorGroup CM ET factory
"""

IPFS_DESCRIPTION = DG_IPFS_DESCRIPTION + "\n" + IMMEDIATE_VOTING_IPFS_DESCRIPTION


# ================================ Main ======================================


def is_dg_only_mode() -> bool:
    return os.getenv(HOODI_DG_ONLY_ENV, "").lower() in ("1", "true", "yes", "on")


def is_placeholder_vote_script_address(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in ("", "0x0000000000000000000000000000000000000000") or normalized.startswith("todo")


def get_ipfs_description(dg_only: Optional[bool] = None) -> str:
    dg_only = is_dg_only_mode() if dg_only is None else dg_only
    return DG_IPFS_DESCRIPTION if dg_only else IPFS_DESCRIPTION


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
    dg_only: Optional[bool] = None,
    upgrade_vote_script: Optional[str] = None,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    dg_only = is_dg_only_mode() if dg_only is None else dg_only
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

    if not dg_only:
        voting_items = omnibus.getVotingVoteItems()
        for desc, call_script in voting_items:
            vote_desc_items.append(desc)
            call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
    dg_only: Optional[bool] = None,
    upgrade_vote_script: Optional[str] = None,
):
    dg_only = is_dg_only_mode() if dg_only is None else dg_only
    vote_desc_items, call_script_items = get_vote_items(
        dg_only=dg_only,
        upgrade_vote_script=upgrade_vote_script,
    )
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))
    ipfs_description = get_ipfs_description(dg_only=dg_only)

    desc_ipfs = (
        calculate_vote_ipfs_description(ipfs_description)
        if silent
        else upload_vote_ipfs_description(ipfs_description)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    if not dg_only:
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
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
