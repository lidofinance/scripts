"""
Technical vote for Goerli network

1. Revoke role CREATE_PAYMENTS_ROLE from Easy Track EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
2. Grant role CREATE_PAYMENTS_ROLE to Easy Track EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
with limits: 1000 ETH, 1000 stETH, 5M LDO, 100K DAI

"""

import time

from typing import Dict, Tuple, Optional, List

from brownie.network.transaction import TransactionReceipt
from utils.finance import ZERO_ADDRESS
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.permissions import encode_permission_revoke, encode_permission_grant_p
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import (
    get_deployer_account,
    get_is_live,
    lido_dao_finance_address,
    lido_dao_acl_address,
    lido_dao_steth_address,
    ldo_token_address,
    dai_token_address,
    lido_easytrack_evmscriptexecutor,
)
from utils.brownie_prelude import *

evmscriptexecutor = lido_easytrack_evmscriptexecutor

eth = {
    "limit": 1_000 * (10**18),
    "address": ZERO_ADDRESS,
}

steth = {
    "limit": 1_000 * (10**18),
    "address": lido_dao_steth_address,
}

ldo = {
    "limit": 5_000_000 * (10**18),
    "address": ldo_token_address,
}

dai = {
    "limit": 100_000 * (10**18),
    "address": dai_token_address,
}


def amount_limits() -> List[Param]:
    """Here we want to build such permissions that checks the _token and _amount pairs
    on each Finance#newImmediatePayment launch.

    Arguments provided from that method:
    `authP(CREATE_PAYMENTS_ROLE, _arr(_token, _receiver, _amount, MAX_UINT256, uint256(1), getTimestamp()))`

    See https://etherscan.io/address/0x836835289a2e81b66ae5d95b7c8dbc0480dcf9da#code#L1549
    """
    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == LDO)
        Param(token_arg_index, Op.EQ, ArgumentValue(ldo["address"])),
        # 2: { return _amount <= 5_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(ldo["limit"])),
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == ETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(eth["address"])),
        # 5: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(eth["limit"])),
        # 6: else if (7) then (8) else (9)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=7, success=8, failure=9)
        ),
        # 7: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(dai["address"])),
        # 8: { return _amount <= 100_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(dai["limit"])),
        # 9: else if (10) then (11) else (12)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=10, success=11, failure=12),
        ),
        # 10: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth["address"])),
        # 11: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth["limit"])),
        # 12: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    acl = interface.ACL(lido_dao_acl_address)
    finance = interface.Finance(lido_dao_finance_address)

    call_script_items = [
        # 1. Revoke role CREATE_PAYMENTS_ROLE from Easy Track EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
        encode_permission_revoke(
            target_app=finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            revoke_from=evmscriptexecutor,
        ),
        # 2. Grant role CREATE_PAYMENTS_ROLE to Easy Track EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
        # with limits: 1000 ETH, 1000 stETH, 5M LDO, 100K DAI
        encode_permission_grant_p(
            target_app=finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            grant_to=evmscriptexecutor,
            params=amount_limits(),
        ),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Revoke role CREATE_PAYMENTS_ROLE from Easy Track EVMScriptExecutor;",
        "2) Grant role CREATE_PAYMENTS_ROLE to Easy Track EVMScriptExecutor with limits.",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
