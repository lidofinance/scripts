"""
Dual Governance Launch on Mainnet

1. Revoke STAKING_CONTROL_ROLE permission from Voting on Lido
2. Set STAKING_CONTROL_ROLE manager to Agent on Lido
3. Revoke RESUME_ROLE permission from Voting on Lido
4. Set RESUME_ROLE manager to Agent on Lido
5. Revoke PAUSE_ROLE permission from Voting on Lido
6. Set PAUSE_ROLE manager to Agent on Lido
7. Revoke STAKING_PAUSE_ROLE permission from Voting on Lido
8. Set STAKING_PAUSE_ROLE manager to Agent on Lido
9. Revoke APP_MANAGER_ROLE permission from Voting on DAOKernel
10. Set APP_MANAGER_ROLE manager to Agent on DAOKernel
11. Create MINT_ROLE permission on TokenManager with manager Voting and grant it to Voting
12. Create REVOKE_VESTINGS_ROLE permission on TokenManager with manager Voting and grant it to Voting
13. Create CHANGE_PERIOD_ROLE permission on Finance with manager Voting and grant it to Voting
14. Create CHANGE_BUDGETS_ROLE permission on Finance with manager Voting and grant it to Voting
15. Revoke REGISTRY_ADD_EXECUTOR_ROLE permission from Voting on EVMScriptRegistry
16. Set REGISTRY_ADD_EXECUTOR_ROLE manager to Agent on EVMScriptRegistry
17. Revoke REGISTRY_MANAGER_ROLE permission from Voting on EVMScriptRegistry
18. Set REGISTRY_MANAGER_ROLE manager to Agent on EVMScriptRegistry
19. Set STAKING_ROUTER_ROLE manager to Agent on CuratedModule
20. Set MANAGE_NODE_OPERATOR_ROLE manager to Agent on CuratedModule
21. Revoke SET_NODE_OPERATOR_LIMIT_ROLE permission from Voting on CuratedModule
22. Set SET_NODE_OPERATOR_LIMIT_ROLE manager to Agent on CuratedModule
23. Revoke MANAGE_SIGNING_KEYS permission from Voting on CuratedModule
24. Set MANAGE_SIGNING_KEYS manager to Agent on CuratedModule
25. Set STAKING_ROUTER_ROLE manager to Agent on SimpleDVT
26. Set MANAGE_NODE_OPERATOR_ROLE manager to Agent on SimpleDVT
27. Set SET_NODE_OPERATOR_LIMIT_ROLE manager to Agent on SimpleDVT
28. Grant CREATE_PERMISSIONS_ROLE permission to Agent on ACL
29. Revoke CREATE_PERMISSIONS_ROLE permission from Voting on ACL
30. Set CREATE_PERMISSIONS_ROLE manager to Agent on ACL
31. Grant RUN_SCRIPT_ROLE permission to DGAdminExecutor on Agent
32. Set RUN_SCRIPT_ROLE manager to Agent on Agent
33. Grant EXECUTE_ROLE permission to DGAdminExecutor on Agent
34. Set EXECUTE_ROLE manager to Agent on Agent
35. Grant PAUSE_ROLE to ResealManager on WithdrawalQueueERC721
36. Grant RESUME_ROLE to ResealManager on WithdrawalQueueERC721
37. Grant PAUSE_ROLE to ResealManager on ValidatorsExitBusOracle
38. Grant RESUME_ROLE to ResealManager on ValidatorsExitBusOracle
39. Grant PAUSE_ROLE to ResealManager on CSModule
40. Grant RESUME_ROLE to ResealManager on CSModule
41. Grant PAUSE_ROLE to ResealManager on CSAccounting
42. Grant RESUME_ROLE to ResealManager on CSAccounting
43. Grant PAUSE_ROLE to ResealManager on CSFeeOracle
44. Grant RESUME_ROLE to ResealManager on CSFeeOracle
45. Grant DEFAULT_ADMIN_ROLE to Voting on AllowedTokensRegistry
46. Revoke DEFAULT_ADMIN_ROLE from Agent on AllowedTokensRegistry
47. Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Agent on AllowedTokensRegistry
48. Revoke REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE from Agent on AllowedTokensRegistry
49. Set admin to Agent on WithdrawalVault
50. Set owner to Voting on InsuranceFund
51. Validate transferred roles
52. Submit a proposal to the Dual Governance to:
    1. Add the "expiration date" to the Dual Governance proposal
    2. Add the "execution time window" to the Dual Governance proposal
    3. Revoke RUN_SCRIPT_ROLE from Aragon Voting
    4. Revoke EXECUTE_ROLE from Aragon Voting
    5. Validate roles were updated correctly
53. Verify Dual Governance launch state
54. Set an "expiration deadline" after which the omnibus can no longer be enacted
"""

import time
from typing import Dict
from brownie import interface
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.mainnet_fork import pass_and_exec_dao_vote


voting_contract = "0xcD7d0c2f0aEFF8cBD17702bfa9505421253edE54"
description = "Dual Governance Launch on Mainnet" # TODO: change description

def get_vote_items():
    voting_items = interface.DGLaunchOmnibus(voting_contract).getVoteItems()

    vote_desc_items = []
    call_script_items = []

    for desc, call_script in voting_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id))


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
