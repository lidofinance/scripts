"""
Voting 24/03/2022

1. Getting funds off 1inch rewards contract: call recover_erc20
    on 0xf5436129cf9d8fa2a1cb6e591347155276550635 with
    0x5a98fcbea516cf06857215779fd812ca3bef1b32 & 50000000000000000000000 (full 50,000 LDO)
    from Agent (note: should be done in a way that doesn’t block the entire tx if this fails)
"""

import time
from typing import (Dict, Tuple, Optional)
from utils.agent import agent_forward
from utils.config import ldo_token_address, get_deployer_account
from brownie.network.transaction import TransactionReceipt
from utils.evm_script import (
    encode_call_script
)
from utils.voting import confirm_vote_script, create_vote

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )

ONE_INCH_REWARDS_MANAGER = "0xf5436129Cf9d8fa2a1cb6e591347155276550635"
TOKENS_RECOVERER = '0xE7eD6747FaC5360f88a2EFC03E00d25789F69291'

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    rewards_manager = interface.OneInchRewardsManager(ONE_INCH_REWARDS_MANAGER)
    tokens_recoverer = interface.TokensRecoverer(TOKENS_RECOVERER)
    encoded_call_script = encode_call_script([
        agent_forward([
            (
                rewards_manager.address,
                rewards_manager.transfer_ownership.encode_input(TOKENS_RECOVERER)
            )
        ]),
        (
            TOKENS_RECOVERER,
            tokens_recoverer.recover.encode_input(
                rewards_manager.address,
                ldo_token_address,
                50_000 * 10 ** 18
            )
        )
    ])
    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Recover 50,000 LDO tokens from 1Inch rewards manager;'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )

def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'gas_price': '100 gwei',
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5)  # hack for waiting thread #2.