"""
"""

import time
from typing import (Dict, Optional, Tuple)

from brownie.network.transaction import TransactionReceipt

from utils.config import (
    get_deployer_account,
    lido_dao_finance_address,
    lido_dao_acl_address,
    ldo_token_address,
    lido_dao_steth_address,
)
from utils.evm_script import encode_call_script
from utils.finance import ZERO_ADDRESS
from utils.permission_parameters import *
from utils.permissions import encode_permission_grant_p
from utils.voting import confirm_vote_script, create_vote

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )

eth_limit = 1_000
steth_limit = 1_000
ldo_limit = 1_000_000


def safety_permission_params() -> List[Param]:
    """ Here we want to build such permissions that checks the _token and _amount pairs
        on each Finance#newImmediatePayment launch.

        Arguments provided from that method:
        `authP(CREATE_PAYMENTS_ROLE, _arr(_token, _receiver, _amount, MAX_UINT256, uint256(1), getTimestamp()))`

        See https://etherscan.io/address/0x836835289a2e81b66ae5d95b7c8dbc0480dcf9da#code#L1549
    """
    token = 0
    amount = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(1, 2, 3)),
        # 1: (_token == ETH)
        Param(token, Op.EQ, ArgumentValue(ZERO_ADDRESS)),
        # 2: { return _amount <= 1000 }
        Param(amount, Op.LTE, ArgumentValue(eth_limit)),
        # 3: else if (4) then (5) else (6)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(4, 5, 6)),
        # 4: (_token == LDO)
        Param(token, Op.EQ, ArgumentValue(ldo_token_address)),
        # 5: { return _amount <= 1_000_000 }
        Param(amount, Op.LTE, ArgumentValue(ldo_limit)),
        # 6: else if (7) then (8) else (9)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(7, 8, 9)),
        # 7: (_token == stETH)
        Param(token, Op.EQ, ArgumentValue(lido_dao_steth_address)),
        # 8: { return _amount <= 1000 }
        Param(amount, Op.LTE, ArgumentValue(steth_limit)),
        # 9: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0))
    ]


def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    acl = interface.ACL(lido_dao_acl_address)
    finance = interface.Finance(lido_dao_finance_address)

    encoded_call_script = encode_call_script([
        encode_permission_grant_p(finance, 'CREATE_PAYMENTS_ROLE', tx_params['from'], acl, safety_permission_params())
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
