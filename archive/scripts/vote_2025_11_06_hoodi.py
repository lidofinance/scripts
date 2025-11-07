"""
Vote 2025_11_06 (HOODI)

1. Termporarily grant ADD_TOKEN_TO_ALLOWED_LIST_ROLE to Aragon Voting
2. Add sUSDS to the Sandbox stablecoins Allowed Tokens Registry
3. Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Aragon Voting
4. Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor on Aragon Finance
5. Grant CREATE_PAYMENTS_ROLE to EVMScriptExecutor on Aragon Finance with amount limits

# Vote #45 passed & executed on Nov-07-2025 02:14:24 PM UTC, block 1573439
.
"""

from typing import Dict, List, Tuple, NamedTuple

from brownie import interface, web3, convert

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.permissions import encode_permission_revoke, encode_permission_grant_p

class TokenLimit(NamedTuple):
    address: str
    limit: int

# ============================== Addresses ===================================
SUSDS_TOKEN = "0xDaE6a7669f9aB8b2C4E52464AA6FB7F9402aDc70"
USDC_TOKEN = "0x97bb030B93faF4684eAC76bA0bf3be5ec7140F36"
USDT_TOKEN = "0x64f1904d1b419c6889BDf3238e31A138E258eA68"
DAI_TOKEN = "0x17fc691f6EF57D2CA719d30b8fe040123d4ee319"
STETH_TOKEN = "0x3508a952176b3c15387c97be809eaffb1982176a"

SANDBOX_STABLES_ALLOWED_TOKENS_REGISTRY = "0x40Db7E8047C487bD8359289272c717eA3C34D1D3"
VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"
FINANCE = "0x254Ae22bEEba64127F0e59fe8593082F3cd13f6b"
ET_EVM_SCRIPT_EXECUTOR = "0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E"
ADD_TOKEN_TO_ALLOWED_LIST_ROLE = "ADD_TOKEN_TO_ALLOWED_LIST_ROLE"
CREATE_PAYMENTS_ROLE = "CREATE_PAYMENTS_ROLE"

STABLES_LIMIT = 1_000
USDC_LIMIT = TokenLimit(USDC_TOKEN, STABLES_LIMIT * 10**6)
USDT_LIMIT = TokenLimit(USDT_TOKEN, STABLES_LIMIT * 10**6)
DAI_LIMIT = TokenLimit(DAI_TOKEN, STABLES_LIMIT * 10**18)
SUSDS_LIMIT = TokenLimit(SUSDS_TOKEN, STABLES_LIMIT * 10**18)
STETH_LIMIT = TokenLimit(STETH_TOKEN, 200 * 10**18)

def amount_limits() -> List[Param]:
    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == USDC)
        Param(token_arg_index, Op.EQ, ArgumentValue(USDC_LIMIT.address)),
        # 2: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(USDC_LIMIT.limit)),
        #
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == USDT)
        Param(token_arg_index, Op.EQ, ArgumentValue(USDT_LIMIT.address)),
        # 5: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(USDT_LIMIT.limit)),
        #
        # 6: else if (7) then (8) else (9)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=7, success=8, failure=9)
        ),
        # 7: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(DAI_LIMIT.address)),
        # 8: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(DAI_LIMIT.limit)),
        #
        # 9: else if (10) then (11) else (12)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=10, success=11, failure=12),
        ),
        # 10: (_token == SUSDS)
        Param(token_arg_index, Op.EQ, ArgumentValue(SUSDS_LIMIT.address)),
        # 11: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(SUSDS_LIMIT.limit)),
        #
        # 12: else if (13) then (14) else (15)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=13, success=14, failure=15),
        ),
        # 13: (_token == STETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(STETH_LIMIT.address)),
        # 14: { return _amount <= 200 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(STETH_LIMIT.limit)),
        #
        # 15: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]

# ============================= Description ==================================
IPFS_DESCRIPTION = "sUSDS swaps (HOODI)"


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    sandbox_stables_allowed_tokens_registry = interface.AllowedTokensRegistry(SANDBOX_STABLES_ALLOWED_TOKENS_REGISTRY)
    
    vote_desc_items, call_script_items = zip(
        (
            "1. Termporarily grant ADD_TOKEN_TO_ALLOWED_LIST_ROLE to Aragon Voting",
            (
                sandbox_stables_allowed_tokens_registry.address, sandbox_stables_allowed_tokens_registry.grantRole.encode_input(
                    convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
                    VOTING,
                )
            )
        ),
        (
            "2. Add sUSDS to the Sandbox stablecoins Allowed Tokens Registry",
            (sandbox_stables_allowed_tokens_registry.address, sandbox_stables_allowed_tokens_registry.addToken.encode_input(SUSDS_TOKEN))
        ),
        (
            "3. Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Aragon Voting",
            (
                sandbox_stables_allowed_tokens_registry.address, sandbox_stables_allowed_tokens_registry.revokeRole.encode_input(
                    convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
                    VOTING,
                )
            )
        ),
        (
            "4. Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor on Aragon Finance",
            encode_permission_revoke(
                target_app=FINANCE,
                permission_name=CREATE_PAYMENTS_ROLE,
                revoke_from=ET_EVM_SCRIPT_EXECUTOR,
            ),
        ),
        (
            "5. Grant CREATE_PAYMENTS_ROLE to EVMScriptExecutor on Aragon Finance with amount limits",
            encode_permission_grant_p(
                target_app=FINANCE,
                permission_name=CREATE_PAYMENTS_ROLE,
                grant_to=ET_EVM_SCRIPT_EXECUTOR,
                params=amount_limits(),
            ),
        ),
    )


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
