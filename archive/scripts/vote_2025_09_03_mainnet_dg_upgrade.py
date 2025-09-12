"""
Vote 2025_09_03

I. Dual Governance Upgrade
1. Set Tiebreaker activation timeout to 31536000 seconds (1 year) on the new Dual Governance instance 0xC1db28B3301331277e307FDCfF8DE28242A4486E
2. Set Tiebreaker committee to 0xf65614d73952Be91ce0aE7Dd9cFf25Ba15bEE2f5 on the new Dual Governance instance 0xC1db28B3301331277e307FDCfF8DE28242A4486E
3. Add Withdrawal Queue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 as Tiebreaker Sealable Withdrawal Blocker on the new Dual Governance instance 0xC1db28B3301331277e307FDCfF8DE28242A4486E
4. Add Validators Exit Bus Oracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e as Tiebreaker Sealable Withdrawal Blocker on the new Dual Governance instance 0xC1db28B3301331277e307FDCfF8DE28242A4486E
5. Register Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e as Proposer on the new Dual Governance instance 0xC1db28B3301331277e307FDCfF8DE28242A4486E
6. Set Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e as Proposals Canceller on the new Dual Governance instance 0xC1db28B3301331277e307FDCfF8DE28242A4486E
7. Set Reseal committee to 0xFFe21561251c49AdccFad065C94Fb4931dF49081 on the new Dual Governance instance 0xC1db28B3301331277e307FDCfF8DE28242A4486E
8. Set Governance address to the new Dual Governance contract 0xC1db28B3301331277e307FDCfF8DE28242A4486E on Emergency Protected Timelock 0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316
9. Set new Config Provider 0xc934E90E76449F09f2369BB85DCEa056567A327a for the old Dual Governance contract 0xcdF49b058D606AD34c5789FD8c3BF8B3E54bA2db
10. Verify the Dual Governance state using Dual Governance Upgrade State Verifier 0x487b764a2085ffd595D9141BAec0A766B7904786

Vote 191 passed & executed on 3 days ago (Sep-08-2025 06:16:59 PM UTC), block 23320106.
"""

import time

from typing import Dict, Tuple, List
from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.mainnet_fork import pass_and_exec_dao_vote

# ============================== Addresses ===================================
omnibus_contract = "0x67988077f29FbA661911d9567E05cc52C51ca1B0"

# ============================= Description ==================================
IPFS_DESCRIPTION = """
**Fix for the Dual Governance RageQuit mechanism**. Full context [on the forum](https://research.lido.fi/t/dual-governance-security-upgrade-plan-ragequit-eth-withdrawal-delay-fix/10543). Audited by [Certora](https://github.com/lidofinance/audits/blob/main/Certora%20Dual%20Governance%20v1.0.1%20Hotfix%20Review%20Report%2008-2025.pdf) and [Statemind](https://github.com/lidofinance/audits/blob/main/Statemind%20Dual%20Governance%20Escrow%20Fix%20Review%20Report%2008-2025.pdf).

1. Finalize the configuration of the new Dual Governance (items 1-7).
2. Set the Governance address in the EmergencyProtectedTimelock to the new Dual Governance (item 8).
3. Replace the config provider in the old Dual Governance with the new ImmutableDualGovernanceConfigProvider to prevent re-entering the vulnerable state and enable free withdrawals from the old Escrow (item 9).
4. Verify the resulting state of the new Dual Governance on-chain (item 10).
"""


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    voting_items = interface.DGLaunchOmnibus(omnibus_contract).getVoteItems()

    vote_desc_items = []
    call_script_items = []

    for desc, call_script in voting_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, TransactionReceipt]:
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(IPFS_DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(IPFS_DESCRIPTION)

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    assert interface.DGLaunchOmnibus(omnibus_contract).isValidVoteScript(vote_id)

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
