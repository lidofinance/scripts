"""
Vote 2025_11_24 - Mainnet V3 Upgrade

=== 1. DG PROPOSAL ===
I. Lido V3 Upgrade
1.1. Call UpgradeTemplateV3.startUpgrade
1.2. Upgrade LidoLocator implementation
1.3. Grant APP_MANAGER_ROLE to the AGENT
1.4. Set Lido implementation in Kernel
1.5. Revoke APP_MANAGER_ROLE from the AGENT on Kernel
1.6. Revoke REQUEST_BURN_SHARES_ROLE from Lido
1.7. Revoke REQUEST_BURN_SHARES_ROLE from Curated staking modules (NodeOperatorsRegistry)
1.8. Revoke REQUEST_BURN_SHARES_ROLE from SimpleDVT
1.9. Revoke REQUEST_BURN_SHARES_ROLE from CS Accounting
1.10. Upgrade AccountingOracle implementation
1.11. Revoke REPORT_REWARDS_MINTED_ROLE from Lido
1.12. Grant REPORT_REWARDS_MINTED_ROLE to Accounting
1.13. Call UpgradeTemplateV3.finishUpgrade
1.14. Revoke REQUEST_BURN_SHARES_ROLE from Hoodi Sandbox module (only on Hoodi)

=== NON-DG ITEMS ===
II. Easy Track factories for Lido V3
2. Add Lido V3 factories to Easy Track registry

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
omnibus_contract = "0x67988077f29FbA661911d9567E05cc52C51ca1B0" # TODO replace with the actual omnibus contract address


# ============================= Description ==================================
# TODO <a description for IPFS (will appear in the voting description on vote.lido.fi)>
IPFS_DESCRIPTION = "TODO description for IPFS"


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    vote_desc_items = []
    call_script_items = []

    # receive DG vote items from omnibus contract
    dg_items = interface.V3LaunchOmnibus(omnibus_contract).getVoteItems()

    dg_call_script = submit_proposals([
        (dg_items, "TODO DG proposal description")
    ])

    vote_desc_items.append("TODO DG submission description")
    call_script_items.append(dg_call_script)

    # receive non-DG vote items from omnibus contract
    voting_items = interface.V3LaunchOmnibus(omnibus_contract).getVotingVoteItems()

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

    assert interface.V3LaunchOmnibus(omnibus_contract).isValidVoteScript(vote_id)

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
