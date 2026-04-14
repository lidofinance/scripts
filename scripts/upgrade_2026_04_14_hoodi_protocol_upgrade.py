"""
TODO Vote 2026_04_14

Uses deployed `UpgradeVoteScript` as the source of truth for both:
1. DG items returned by `getVoteItems()`
2. Immediate voting items returned by `getVotingVoteItems()`

Replace the TODO values below after the Hoodi deployment.
"""

from typing import Dict, List, Tuple

from brownie import interface

from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.dual_governance import submit_proposals
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.voting import bake_vote_items, confirm_vote_script, create_vote


# ============================== Addresses ===================================
UPGRADE_VOTE_SCRIPT = "0x0000000000000000000000000000000000000000"


# ============================= Description ==================================
DG_PROPOSAL_METADATA = "Upgrade Lido protocol contracts on Ethereum Hoodi testnet"
DG_SUBMISSION_DESCRIPTION = "1. Submit a Dual Governance proposal for the Lido protocol upgrade on Ethereum Hoodi testnet"
IPFS_DESCRIPTION = """
**Lido protocol upgrade on Ethereum Hoodi testnet**

**Dual Governance proposal**
1. Submit a Dual Governance proposal for the Lido protocol upgrade on Ethereum Hoodi testnet.
1.1. Call UpgradeTemplate.startUpgrade
1.2. Upgrade LidoLocator implementation
1.3. Grant Aragon APP_MANAGER_ROLE to the AGENT
1.4. Set Lido implementation in Kernel
1.5. Revoke Aragon APP_MANAGER_ROLE from the AGENT
1.6. Upgrade StakingRouter implementation and finalize v4 migration
1.7. Grant STAKING_MODULE_SHARE_MANAGE_ROLE to EasyTrack executor
1.8. Upgrade AccountingOracle implementation
1.9. Upgrade Accounting implementation
1.10. Upgrade WithdrawalVault implementation
1.11. Upgrade and finalize CSM v3
1.12. Upgrade and finalize ParametersRegistry v3
1.13. Upgrade and finalize FeeOracle v3
1.14. Upgrade VettedGate implementation
1.15. Upgrade and finalize Accounting v3
1.16. Upgrade and finalize FeeDistributor v3
1.17. Upgrade ExitPenalties implementation
1.18. Upgrade ValidatorStrikes implementation
1.19. Point ValidatorStrikes to the new Ejector
1.20. Grant REPORT_GENERAL_DELAYED_PENALTY_ROLE
1.21. Grant SETTLE_GENERAL_DELAYED_PENALTY_ROLE
1.22. Revoke REPORT_EL_REWARDS_STEALING_PENALTY_ROLE
1.23. Revoke SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE
1.24. Revoke VERIFIER_ROLE from old verifier
1.25. Grant VERIFIER_ROLE to VerifierV3
1.26. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE to VerifierV3
1.27. Grant REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE to Easy Track
1.28. Revoke CREATE_NODE_OPERATOR_ROLE from old PermissionlessGate
1.29. Grant CREATE_NODE_OPERATOR_ROLE to new PermissionlessGate
1.30. Revoke PAUSE_ROLE from old gate seal on CSModule
1.31. Revoke PAUSE_ROLE from old gate seal on Accounting
1.32. Revoke PAUSE_ROLE from old gate seal on FeeOracle
1.33. Revoke PAUSE_ROLE from old gate seal on VettedGate
1.34. Revoke PAUSE_ROLE from old gate seal on old Verifier
1.35. Revoke PAUSE_ROLE from old gate seal on old Ejector
1.36. Revoke PAUSE_ROLE from reseal manager on old Verifier
1.37. Revoke RESUME_ROLE from reseal manager on old Verifier
1.38. Revoke PAUSE_ROLE from reseal manager on old Ejector
1.39. Revoke RESUME_ROLE from reseal manager on old Ejector
1.40. Revoke START_REFERRAL_SEASON_ROLE
1.41. Revoke END_REFERRAL_SEASON_ROLE
1.42. Grant PAUSE_ROLE to GateSealV3 on CSModule
1.43. Grant PAUSE_ROLE to GateSealV3 on Accounting
1.44. Grant PAUSE_ROLE to GateSealV3 on FeeOracle
1.45. Grant PAUSE_ROLE to GateSealV3 on VettedGate
1.46. Grant MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE to penaltiesManager
1.47. Revoke REQUEST_BURN_SHARES_ROLE from CSM Accounting
1.48. Grant REQUEST_BURN_MY_STETH_ROLE to CSM Accounting
1.49. Revoke TWG full-withdrawal role from old Ejector
1.50. Grant TWG full-withdrawal role to new Ejector
1.51. Add Curated module to StakingRouter
1.52. Grant REQUEST_BURN_MY_STETH_ROLE to Curated Accounting
1.53. Grant TWG full-withdrawal role to Curated Ejector
1.54. Grant RESUME_ROLE to agent on Curated module
1.55. Resume Curated module
1.56. Revoke RESUME_ROLE from agent on Curated module
1.57. Update Curated HashConsensus initial epoch
1.58. Call UpgradeTemplate.finishUpgrade

**Immediate voting items**
2. Add UpdateStakingModuleShareLimits ET factory
3. Add AllowConsolidationPair ET factory
4. Add CreateOrUpdateOperatorGroup ET factory
"""


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    omnibus = interface.UpgradeVoteScript(UPGRADE_VOTE_SCRIPT)
    dg_items: List[Tuple[str, str]] = []

    for _, call_script in omnibus.getVoteItems():
        dg_items.append((call_script[0], call_script[1].hex()))

    return dg_items


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    omnibus = interface.UpgradeVoteScript(UPGRADE_VOTE_SCRIPT)

    vote_desc_items: List[str] = []
    call_script_items: List[Tuple[str, str]] = []

    dg_items = get_dg_items()

    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_METADATA)])
    vote_desc_items.append(DG_SUBMISSION_DESCRIPTION)
    call_script_items.append(dg_call_script[0])

    voting_items = omnibus.getVotingVoteItems()
    for desc, call_script in voting_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent
        else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    assert interface.UpgradeVoteScript(UPGRADE_VOTE_SCRIPT).isValidVoteScript(vote_id, DG_PROPOSAL_METADATA)

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
