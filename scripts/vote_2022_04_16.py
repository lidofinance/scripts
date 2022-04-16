"""
Voting 16/04/2022.

1. Unpause deposits

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.agent import agent_forward
from utils.evm_script import encode_call_script
from utils.config import (
    get_deployer_account,
    get_is_live,
    lido_dao_deposit_security_module_address
)

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )

def unpause_deposits(deposit_security_module) -> Tuple[str, str]:
    return agent_forward([(
        deposit_security_module.address,
        deposit_security_module.unpauseDeposits.encode_input()
    )])

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    deposit_security_module = interface.DepositSecurityModule(lido_dao_deposit_security_module_address)

    encoded_call_script = encode_call_script([
        # 1. Unpause deposits in the protocol calling unpauseDeposits on 0xdb149235b6f40dc08810aa69869783be101790e7
        # from Agent 0x3e40d73eb977dc6a537af587d48316fee66e9c8c
        unpause_deposits(deposit_security_module),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Unpause protocol deposits'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    tx_params = {'from': get_deployer_account()}

    if get_is_live():
        tx_params['max_fee'] = '300 gwei'
        tx_params['priority_fee'] = '2 gwei'

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
