"""
# Vote 2025_12_10

=== 1. DG PROPOPSAL ===
1.1. Check DG voting enactment is within daily time window (14:00 UTC - 23:00 UTC)
1.2. Call UpgradeTemplateV3.startUpgrade
1.3. Upgrade LidoLocator implementation
1.4. Grant Aragon APP_MANAGER_ROLE to the AGENT
1.5. Set Lido implementation in Kernel
1.6. Revoke Aragon APP_MANAGER_ROLE from the AGENT
1.7. Revoke REQUEST_BURN_SHARES_ROLE from Lido
1.8. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking module
1.9. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
1.10. Revoke REQUEST_BURN_SHARES_ROLE from Community Staking Accounting
1.11. Upgrade AccountingOracle implementation
1.12. Revoke REPORT_REWARDS_MINTED_ROLE from Lido
1.13. Grant REPORT_REWARDS_MINTED_ROLE to Accounting
1.14. Grant OracleDaemonConfig's CONFIG_MANAGER_ROLE to Agent
1.15. Set SLASHING_RESERVE_WE_RIGHT_SHIFT to 0x2000 at OracleDaemonConfig
1.16. Set SLASHING_RESERVE_WE_LEFT_SHIFT to 0x2000 at OracleDaemonConfig
1.17. Revoke OracleDaemonConfig's CONFIG_MANAGER_ROLE from Agent
1.18. Call UpgradeTemplateV3.finishUpgrade

=== NON-DG ITEMS ===
2. Add AlterTiersInOperatorGrid factory to EasyTrack (permissions: operatorGrid, alterTiers);
3. Add RegisterGroupsInOperatorGrid factory to EasyTrack (permissions: operatorGrid, registerGroup + registerTiers);
4. Add RegisterTiersInOperatorGrid factory to EasyTrack (permissions: operatorGrid, registerTiers);
5. Add UpdateGroupsShareLimitInOperatorGrid factory to EasyTrack (permissions: operatorGrid, updateGroupShareLimit);
6. Add SetJailStatusInOperatorGrid factory to EasyTrack (permissions: vaultsAdapter, setVaultJailStatus);
7. Add UpdateVaultsFeesInOperatorGrid factory to EasyTrack (permissions: vaultsAdapter, updateVaultFees);
8. Add ForceValidatorExitsInVaultHub factory to EasyTrack (permissions: vaultsAdapter, forceValidatorExit);
9. Add SetLiabilitySharesTargetInVaultHub factory to EasyTrack (permissions: vaultsAdapter, setLiabilitySharesTarget);
10. Add SocializeBadDebtInVaultHub factory to EasyTrack (permissions: vaultsAdapter, socializeBadDebt).

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from brownie import interface


# ============================== Addresses ===================================
OMNIBUS_CONTRACT = "0x7e2ef38FeDFEc1e768E55D63cb0273a726d0a318" # TODO replace with the actual omnibus contract address


# ============================= Description ==================================
# TODO <a description for IPFS (will appear in the voting description on vote.lido.fi)>
IPFS_DESCRIPTION = "omni dec 2025"
DG_PROPOSAL_DESCRIPTION = "TODO DG proposal description"
DG_SUBMISSION_DESCRIPTION = "1. TODO DG submission description"


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
