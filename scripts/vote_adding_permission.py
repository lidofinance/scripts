"""
"""

import time
from typing import (Dict, Optional, List, Tuple)

from brownie.network.transaction import TransactionReceipt

from utils.config import (
    get_deployer_account,
    lido_dao_finance_address,
    lido_dao_acl_address,
    ldo_token_address,
    lido_dao_steth_address,
)
from utils.evm_script import encode_call_script
from utils.permission_parameters import *
from utils.permissions import encode_permission_grant_p, encode_permission_revoke
from utils.voting import confirm_vote_script, create_vote

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )


def construct_permission_params() -> List[Param]:
    """
        Here we want to create such a permission that checks the _token and _amount pairs
        when EVMScriptExecutor launches newImmediatePayment
        Auth params provided from that method:
        `authP(CREATE_PAYMENTS_ROLE, _arr(_token, _receiver, _amount, MAX_UINT256, uint256(1), getTimestamp()))`
    """
    token = 0
    amount = 2

    eth_limit = 1_000
    steth_limit = 1_000
    ldo_limit = 1_000_000

    return [
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(1, 2, 3)),  # if
        Param(token, Op.EQ, ArgumentValue(0)),  # (_token == ETH)
        Param(amount, Op.LTE, ArgumentValue(eth_limit)),  # then: return _amount <= 1000

        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(4, 5, 6)),  # else: if
        Param(token, Op.EQ, ArgumentValue(ldo_token_address)),  # (_token == LDO)
        Param(amount, Op.LTE, ArgumentValue(ldo_limit)),  # then: return _amount <= 1_000_000

        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(7, 8, 9)),  # else: if
        Param(token, Op.EQ, ArgumentValue(lido_dao_steth_address)),  # (_token == stETH)
        Param(amount, Op.LTE, ArgumentValue(steth_limit)),  # then: return _amount <= 1000

        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0))  # else: return false
    ]


def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    acl = interface.ACL(lido_dao_acl_address)
    finance = interface.Finance(lido_dao_finance_address)

    encoded_call_script = encode_call_script([
        encode_permission_grant_p(finance, 'CREATE_PAYMENTS_ROLE',
                                  tx_params['from'], acl, construct_permission_params())
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Test vote Aragon ACL:'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'max_fee': '100 gwei',
        'priority_fee': '2 gwei'
    })

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
