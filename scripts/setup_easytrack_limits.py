"""
"""

import time
from typing import (Dict, Optional, Tuple, List)

from brownie.network.transaction import TransactionReceipt

from utils.config import (
    get_deployer_account,
    lido_dao_finance_address,
    lido_dao_acl_address,
)
from utils.evm_script import encode_call_script
from utils.finance import ZERO_ADDRESS
from utils.permission_parameters import SpecialArgumentID, encode_argument_value_if, Param, ArgumentValue, Op
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

evmscriptexecutor_address = '0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977'

eth = {
    'limit': 1_000 * (10 ** 18),
    'address': ZERO_ADDRESS,
}

steth = {
    'limit': 1_000 * (10 ** 18),
    'address': '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',
}

ldo = {
    'limit': 5_000_000 * (10 ** 18),
    'address': '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32',
}


def require_amount_limits() -> List[Param]:
    """ Here we want to build such permissions that checks the _token and _amount pairs
        on each Finance#newImmediatePayment launch.

        Arguments provided from that method:
        `authP(CREATE_PAYMENTS_ROLE, _arr(_token, _receiver, _amount, MAX_UINT256, uint256(1), getTimestamp()))`

        See https://etherscan.io/address/0x836835289a2e81b66ae5d95b7c8dbc0480dcf9da#code#L1549
    """
    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE,
              encode_argument_value_if(condition=1, success=2, failure=3)),
        # 1: (_token == ETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(eth['address'])),
        # 2: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(eth['limit'])),
        # 3: else if (4) then (5) else (6)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE,
              encode_argument_value_if(condition=4, success=5, failure=6)),
        # 4: (_token == LDO)
        Param(token_arg_index, Op.EQ, ArgumentValue(ldo['address'])),
        # 5: { return _amount <= 1_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(ldo['limit'])),
        # 6: else if (7) then (8) else (9)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE,
              encode_argument_value_if(condition=7, success=8, failure=9)),
        # 7: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth['address'])),
        # 8: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth['limit'])),
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
        encode_permission_revoke(finance, 'CREATE_PAYMENTS_ROLE', evmscriptexecutor_address, acl),
        encode_permission_grant_p(finance, 'CREATE_PAYMENTS_ROLE', evmscriptexecutor_address, acl, require_amount_limits())
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote:',
            '1) Revoke role CREATE_PAYMENTS_ROLE from EVMScriptExecutor',
            '2) Grant role CREATE_PAYMENTS_ROLE to EVMScriptExecutor with amount limits'
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
