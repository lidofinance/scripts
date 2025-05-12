"""
Dual Governance Launch on Hoodi testnet

1. Revoke STAKING_CONTROL_ROLE permission from Voting on Lido
2. Set STAKING_CONTROL_ROLE manager to Agent on Lido
3. Revoke RESUME_ROLE permission from Voting on Lido
4. Set RESUME_ROLE manager to Agent on Lido
5. Revoke PAUSE_ROLE permission from Voting on Lido
6. Set PAUSE_ROLE manager to Agent on Lido
7. Revoke UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE permission from Voting on Lido
8. Set UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE manager to Agent on Lido
9. Revoke STAKING_PAUSE_ROLE permission from Voting on Lido
10. Set STAKING_PAUSE_ROLE manager to Agent on Lido
11. Revoke APP_MANAGER_ROLE permission from Voting on DAOKernel
12. Set APP_MANAGER_ROLE manager to Agent on DAOKernel
13. Create UNSAFELY_MODIFY_VOTE_TIME_ROLE permission on Voting with manager Voting and grant it to Voting
14. Create MINT_ROLE permission on TokenManager with manager Voting and grant it to Voting
15. Create REVOKE_VESTINGS_ROLE permission on TokenManager with manager Voting and grant it to Voting
16. Create BURN_ROLE permission on TokenManager with manager Voting and grant it to Voting
17. Create ISSUE_ROLE permission on TokenManager with manager Voting and grant it to Voting
18. Create CHANGE_PERIOD_ROLE permission on Finance with manager Voting and grant it to Voting
19. Create CHANGE_BUDGETS_ROLE permission on Finance with manager Voting and grant it to Voting
20. Revoke REGISTRY_MANAGER_ROLE permission from Voting on EVMScriptRegistry
21. Set REGISTRY_MANAGER_ROLE manager to Agent on EVMScriptRegistry
22. Revoke REGISTRY_ADD_EXECUTOR_ROLE permission from Voting on EVMScriptRegistry
23. Set REGISTRY_ADD_EXECUTOR_ROLE manager to Agent on EVMScriptRegistry
24. Set STAKING_ROUTER_ROLE manager to Agent on Curated Module
25. Set MANAGE_NODE_OPERATOR_ROLE manager to Agent on Curated Module
26. Revoke SET_NODE_OPERATOR_LIMIT_ROLE permission from Voting on Curated Module
27. Set SET_NODE_OPERATOR_LIMIT_ROLE manager to Agent on Curated Module
28. Revoke MANAGE_SIGNING_KEYS permission from Voting on Curated Module
29. Set MANAGE_SIGNING_KEYS manager to Agent on Curated Module
30. Revoke STAKING_ROUTER_ROLE permission from Voting on Simple DVT Module
31. Set STAKING_ROUTER_ROLE manager to Agent on Simple DVT Module
32. Revoke MANAGE_NODE_OPERATOR_ROLE permission from Voting on Simple DVT Module
33. Set MANAGE_NODE_OPERATOR_ROLE manager to Agent on Simple DVT Module
34. Revoke SET_NODE_OPERATOR_LIMIT_ROLE permission from Voting on Simple DVT Module
35. Set SET_NODE_OPERATOR_LIMIT_ROLE manager to Agent on Simple DVT Module
36. Grant CREATE_PERMISSIONS_ROLE permission to Agent on ACL
37. Revoke CREATE_PERMISSIONS_ROLE permission from Voting on ACL
38. Set CREATE_PERMISSIONS_ROLE manager to Agent on ACL
39. Grant RUN_SCRIPT_ROLE permission to DualGovernance Executor on Agent
40. Grant RUN_SCRIPT_ROLE permission to Agent Manager on Agent
41. Set RUN_SCRIPT_ROLE manager to Agent on Agent
42. Grant EXECUTE_ROLE to DualGovernance Executor on Agent
43. Set EXECUTE_ROLE manager to Agent on Agent
44. Grant PAUSE_ROLE to ResealManager on WithdrawalQueue
45. Grant RESUME_ROLE to ResealManager on WithdrawalQueue
46. Grant PAUSE_ROLE to ResealManager on ValidatorsExitBusOracle
47. Grant RESUME_ROLE to ResealManager on ValidatorsExitBusOracle
48. Grant DEFAULT_ADMIN_ROLE to Voting on AllowedTokensRegistry
49. Revoke DEFAULT_ADMIN_ROLE from Agent on AllowedTokensRegistry
50. Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Agent on AllowedTokensRegistry
51. Revoke REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE from Agent on AllowedTokensRegistry
52. Set admin to Agent on WithdrawalVault
53. Validate transferred roles
54. Submit a proposal to the Dual Governance to revoke RUN_SCRIPT_ROLE and EXECUTE_ROLE from Aragon Voting
55. Verify Dual Governance launch state
56. Introduce an expiration deadline after which the omnibus can no longer be enacted

Vote passed & executed on May 8, 2025 at 13:40 UTC, block 350291
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

voting_contract = "0x54637835765a367389aa849F008BA0F6DBC64ca3"
description = "Dual Governance Launch on Hoodi testnet"


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
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    assert interface.DGLaunchOmnibus(voting_contract).isValidVoteScript(vote_id)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
