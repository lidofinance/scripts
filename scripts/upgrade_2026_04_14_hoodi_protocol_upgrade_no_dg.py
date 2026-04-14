"""
TODO Vote 2026_04_14 (no DG)

Uses deployed `UpgradeVoteScript` as the source of truth for both:
1. Former DG items returned by `getVoteItems()`
2. Immediate voting items returned by `getVotingVoteItems()`

Unlike the DG-enabled version, this script flattens both sets of items into a
single Aragon vote and executes them directly.

Replace the TODO values below after the Hoodi deployment.
"""

from typing import Dict, List, Tuple

from brownie import interface

from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.voting import bake_vote_items, confirm_vote_script, create_vote


# ============================== Addresses ===================================
UPGRADE_VOTE_SCRIPT = "0x0000000000000000000000000000000000000000"


# ============================= Description ==================================
IPFS_DESCRIPTION = """
**Lido protocol upgrade on Ethereum Hoodi testnet (direct vote, no Dual Governance)**

This variant executes all upgrade items returned by the deployed `UpgradeVoteScript`
directly as part of the Aragon vote, without wrapping the former DG items into
`DualGovernance.submitProposal`.

**Directly executed upgrade items**
1. Call UpgradeTemplate.startUpgrade
2. Upgrade LidoLocator implementation
3. Grant Aragon APP_MANAGER_ROLE to the AGENT
4. Set Lido implementation in Kernel
5. Revoke Aragon APP_MANAGER_ROLE from the AGENT
6. Upgrade StakingRouter implementation and finalize v4 migration
7. Grant STAKING_MODULE_SHARE_MANAGE_ROLE to EasyTrack executor
8. Upgrade AccountingOracle implementation
9. Upgrade Accounting implementation
10. Upgrade WithdrawalVault implementation
11. Upgrade and finalize CSM v3
12. Upgrade and finalize ParametersRegistry v3
13. Upgrade and finalize FeeOracle v3
14. Upgrade VettedGate implementation
15. Upgrade and finalize Accounting v3
16. Upgrade and finalize FeeDistributor v3
17. Upgrade ExitPenalties implementation
18. Upgrade ValidatorStrikes implementation
19. Point ValidatorStrikes to the new Ejector
20. Grant REPORT_GENERAL_DELAYED_PENALTY_ROLE
21. Grant SETTLE_GENERAL_DELAYED_PENALTY_ROLE
22. Revoke REPORT_EL_REWARDS_STEALING_PENALTY_ROLE
23. Revoke SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE
24. Revoke VERIFIER_ROLE from old verifier
25. Grant VERIFIER_ROLE to VerifierV3
26. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE to VerifierV3
27. Grant REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE to Easy Track
28. Revoke CREATE_NODE_OPERATOR_ROLE from old PermissionlessGate
29. Grant CREATE_NODE_OPERATOR_ROLE to new PermissionlessGate
30. Revoke PAUSE_ROLE from old gate seal on CSModule
31. Revoke PAUSE_ROLE from old gate seal on Accounting
32. Revoke PAUSE_ROLE from old gate seal on FeeOracle
33. Revoke PAUSE_ROLE from old gate seal on VettedGate
34. Revoke PAUSE_ROLE from old gate seal on old Verifier
35. Revoke PAUSE_ROLE from old gate seal on old Ejector
36. Revoke PAUSE_ROLE from reseal manager on old Verifier
37. Revoke RESUME_ROLE from reseal manager on old Verifier
38. Revoke PAUSE_ROLE from reseal manager on old Ejector
39. Revoke RESUME_ROLE from reseal manager on old Ejector
40. Revoke START_REFERRAL_SEASON_ROLE
41. Revoke END_REFERRAL_SEASON_ROLE
42. Grant PAUSE_ROLE to GateSealV3 on CSModule
43. Grant PAUSE_ROLE to GateSealV3 on Accounting
44. Grant PAUSE_ROLE to GateSealV3 on FeeOracle
45. Grant PAUSE_ROLE to GateSealV3 on VettedGate
46. Grant MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE to penaltiesManager
47. Revoke REQUEST_BURN_SHARES_ROLE from CSM Accounting
48. Grant REQUEST_BURN_MY_STETH_ROLE to CSM Accounting
49. Revoke TWG full-withdrawal role from old Ejector
50. Grant TWG full-withdrawal role to new Ejector
51. Add Curated module to StakingRouter
52. Grant REQUEST_BURN_MY_STETH_ROLE to Curated Accounting
53. Grant TWG full-withdrawal role to Curated Ejector
54. Grant RESUME_ROLE to agent on Curated module
55. Resume Curated module
56. Revoke RESUME_ROLE from agent on Curated module
57. Update Curated HashConsensus initial epoch
58. Call UpgradeTemplate.finishUpgrade

**Immediate voting items**
59. Add UpdateStakingModuleShareLimits ET factory
60. Add AllowConsolidationPair ET factory
61. Add CreateOrUpdateOperatorGroup ET factory
"""


def _extract_vote_items(vote_items) -> Tuple[List[str], List[Tuple[str, str]]]:
    vote_desc_items: List[str] = []
    call_script_items: List[Tuple[str, str]] = []

    for desc, call_script in vote_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def get_direct_upgrade_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    omnibus = interface.UpgradeVoteScript(UPGRADE_VOTE_SCRIPT)
    direct_items = omnibus.getVoteItems()

    assert len(direct_items) == omnibus.DG_ITEMS_COUNT(), "Unexpected number of former DG items"

    return _extract_vote_items(direct_items)


def get_immediate_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    omnibus = interface.UpgradeVoteScript(UPGRADE_VOTE_SCRIPT)
    voting_items = omnibus.getVotingVoteItems()

    assert len(voting_items) == omnibus.VOTING_ITEMS_COUNT(), "Unexpected number of immediate voting items"

    return _extract_vote_items(voting_items)


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    direct_vote_desc_items, direct_call_script_items = get_direct_upgrade_items()
    voting_vote_desc_items, voting_call_script_items = get_immediate_vote_items()

    return (
        direct_vote_desc_items + voting_vote_desc_items,
        direct_call_script_items + voting_call_script_items,
    )


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
