"""
# Vote 2025_12_15

=== 1. DG PROPOSAL ===
1.1. Check execution time window (14:00–23:00 UTC)
1.2. Call V3Template.startUpgrade()
1.3. Upgrade LidoLocator implementation
1.4. Grant APP_MANAGER_ROLE to Agent
1.5. Set Lido implementation in Aragon Kernel
1.6. Revoke APP_MANAGER_ROLE from Agent
1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido on old Burner
1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated Module on old Burner
1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT on old Burner
1.10. Revoke REQUEST_BURN_SHARES_ROLE from CSM Accounting on old Burner
1.11. Upgrade AccountingOracle implementation
1.12. Revoke REPORT_REWARDS_MINTED_ROLE from Lido on StakingRouter
1.13. Grant REPORT_REWARDS_MINTED_ROLE to Accounting on StakingRouter
1.14. Grant CONFIG_MANAGER_ROLE to Agent on OracleDaemonConfig
1.15. Set SLASHING_RESERVE_WE_RIGHT_SHIFT in OracleDaemonConfig
1.16. Set SLASHING_RESERVE_WE_LEFT_SHIFT in OracleDaemonConfig
1.17. Revoke CONFIG_MANAGER_ROLE from Agent on OracleDaemonConfig
1.18. Grant PAUSE_ROLE to Agent
1.19. Pause PredepositGuarantee
1.20. Revoke PAUSE_ROLE from Agent
1.21. Call V3Template.finishUpgrade()

=== NON-DG ITEMS ===
2. Add AlterTiersInOperatorGrid factory to Easy Track (permissions: operatorGrid.alterTiers)
3. Add RegisterGroupsInOperatorGrid factory to Easy Track (permissions: operatorGrid.registerGroup, operatorGrid.registerTiers)
4. Add RegisterTiersInOperatorGrid factory to Easy Track (permissions: operatorGrid.registerTiers)
5. Add UpdateGroupsShareLimitInOperatorGrid factory to Easy Track (permissions: operatorGrid.updateGroupShareLimit)
6. Add SetJailStatusInOperatorGrid factory to Easy Track (permissions: vaultsAdapter.setVaultJailStatus)
7. Add UpdateVaultsFeesInOperatorGrid factory to Easy Track (permissions: vaultsAdapter.updateVaultFees)
8. Add ForceValidatorExitsInVaultHub factory to Easy Track (permissions: vaultsAdapter.forceValidatorExit)
9. Add SocializeBadDebtInVaultHub factory to Easy Track (permissions: vaultsAdapter.socializeBadDebt)

Vote #194 passed & executed on Dec-20-2025 02:01:35 PM UTC, block 24054276.
"""

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from brownie import interface


# ============================== Addresses ===================================
OMNIBUS_CONTRACT = "0xE1F4c16908fCE6935b5Ad38C6e3d58830fe86442"


# ============================= Description ==================================
IPFS_DESCRIPTION = """
**Activate Lido V3: Phase 1 (Soft Launch)** — a major upgrade to the Lido protocol introduces non-custodial, over-collateralized staking vaults (“stVaults”) that enable stakers to opt into specific operators or strategies while still minting stETH.  The Lido V3 design and implementation follow the DAO-approved [Snapshot](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x01cd474645cc7c3ddf68314d475d421ef833499297f508fee5f7411fafff3954). Phase 1 is intentionally [proposed in a constrained soft launch](https://research.lido.fi/t/lido-v3-design-implementation-proposal/10665/8) mode to enable early adopters and partners while maintaining a conservative security posture.

Deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20V3%20Security%20Audit%20Report%20-%2012-2025.pdf) | Formal verification: [Certora](https://github.com/lidofinance/audits/blob/main/Certora%20Lido%20V3%20Formal%20Verification%20Report%20-%2012-2025.pdf) | Audits: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20V3%20Security%20Audit%20Report%20-%2012-2025.pdf), [Certora](https://github.com/lidofinance/audits/blob/main/Certora%20Lido%20V3%20Audit%20Report%20-%2012-2025.pdf), [Consensys Diligence](https://github.com/lidofinance/audits/blob/main/Consensys%20Diligence%20Lido%20V3%20Security%20Audit%20-%2011-2025.pdf) | Offchain audits: [Certora](https://github.com/lidofinance/audits/blob/main/Certora%20Lido%20V3%20Oracle%20V7%20Audit%20Report%20-%2012-2025.pdf), [Composable Security](https://github.com/lidofinance/audits/blob/main/Composable%20Security%20Lido%20V3%20Oracle%20V7%20Audit%20Report%20-%2012-2025.pdf)

[Dual Governance Items](https://research.lido.fi/t/lido-v3-design-implementation-proposal/10665/5#p-23638-part-2-dual-governance-items-21-items-subject-to-dg-veto-period-27)
- Ensure DG proposal execution occurs during the monitored time window and aligns with oracle reports. Item 1.1.
- Lock upgrade window and validate network state. Item 1.2.
- Upgrade proxy implementations, reassign roles and permissions, configure oracle slashing parameters. Items 1.3-1.17.
- Disable Predeposit Guarantee guided deposit flows as a part of [Soft Launch](https://research.lido.fi/t/lido-v3-design-implementation-proposal/10665/9). Items 1.18-1.20.
- Finalize upgrade and validate Lido V3 activation state. Item 1.21.

[Voting Items](https://research.lido.fi/t/lido-v3-design-implementation-proposal/10665/5#p-23638-part-1-voting-items-8-items-execute-immediately-26)
- Add Easy Track factories enabling [stVault Committee](https://docs.lido.fi/multisigs/committees#216-stvaults-committee) to configure VaultHub and OperatorGrid contracts. Items 2–9."""
DG_PROPOSAL_DESCRIPTION = "Activate Lido V3: Phase 1 (Soft Launch)"
DG_SUBMISSION_DESCRIPTION = "1. Submit a Dual Governance proposal to activate Lido V3: Phase 1 (Soft Launch)"


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    vote_desc_items = []
    call_script_items = []

    # 1. receive DG vote items from omnibus contract
    contract_dg_items = interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).getVoteItems()

    dg_items = []
    for _, call_script in contract_dg_items:
        dg_items.append((call_script[0], call_script[1].hex()))

    dg_call_script = submit_proposals([
        (dg_items, DG_PROPOSAL_DESCRIPTION)
    ])

    vote_desc_items.append(DG_SUBMISSION_DESCRIPTION)
    call_script_items.append(dg_call_script[0])

    # 2. receive non-DG vote items from omnibus contract
    voting_items = interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).getVotingVoteItems()

    for desc, call_script in voting_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    assert interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).isValidVoteScript(vote_id, DG_PROPOSAL_DESCRIPTION)

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
