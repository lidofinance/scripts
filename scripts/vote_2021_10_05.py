"""
Voting 05/10/2021.

1. Setting key limit for Node Operator #2 (p2p) to 5265
2. Setting key limit for Node Operator #4 (stakefish) to 5265
3. Setting key limit for Node Operator #5 (Blockscape) to 5265
4. Setting key limit for Node Operator #7 (Everstake) to 3000
5. Setting key limit for Node Operator #8 (SkillZ) to 5265
6. Setting key limit for Node Operator #9 (RockX) to 684
7. Setting key limit for Node Operator #10 (Figment) to 683
8. Setting key limit for Node Operator #11 (Allnodes) to 683
9. Setting key limit for Node Operator #12 (Anyblock Analytics) to 683
10. Setting key limit for Node Operator #13 (Blockdaemon) to 683

"""

import time
from functools import partial
from typing import (
    Dict, Tuple,
    Optional
)

from brownie.utils import color
from brownie.network.transaction import TransactionReceipt

from utils.voting import create_vote
from utils.finance import encode_token_transfer
from utils.node_operators import (
    encode_set_node_operator_staking_limit
)
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)
from utils.config import (
    prompt_bool,
    get_deployer_account,
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
)

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )


def set_console_globals(**kwargs):
    """Extract interface from brownie environment."""
    global interface
    interface = kwargs['interface']


def pp(text, value):
    """Pretty print with colorized."""
    print(text, color.highlight(str(value)), end='')


def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # Lido contracts and constants:
    registry = interface.NodeOperatorsRegistry(
        lido_dao_node_operators_registry
    )
    finance = interface.Finance(lido_dao_finance_address)
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    # Set Lido contracts as parameters:
    _encode_set_node_operator_staking_limit = partial(
        encode_set_node_operator_staking_limit, registry=registry
    )

    # Vote-specific addresses and constants:

    _limit_2 = {'id':2, 'limit': 5265}
    _limit_4 = {'id':4, 'limit': 5265}
    _limit_5 = {'id':5, 'limit': 5265}
    _limit_7 = {'id':7, 'limit': 3000}
    _limit_8 = {'id':8, 'limit': 5265}
    _limit_9 = {'id':9, 'limit': 684}
    _limit_10 = {'id':10, 'limit': 683}
    _limit_11 = {'id':11, 'limit': 683}
    _limit_12 = {'id':12, 'limit': 683}
    _limit_13 = {'id':13, 'limit': 683}

    # Encoding vote scripts:
    encoded_call_script = encode_call_script([
        _encode_set_node_operator_staking_limit(**_limit_2),
        _encode_set_node_operator_staking_limit(**_limit_4),
        _encode_set_node_operator_staking_limit(**_limit_5),
        _encode_set_node_operator_staking_limit(**_limit_7),
        _encode_set_node_operator_staking_limit(**_limit_8),
        _encode_set_node_operator_staking_limit(**_limit_9),
        _encode_set_node_operator_staking_limit(**_limit_10),
        _encode_set_node_operator_staking_limit(**_limit_11),
        _encode_set_node_operator_staking_limit(**_limit_12),
        _encode_set_node_operator_staking_limit(**_limit_13),

    ])
    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False,
        specific_net='mainnet', repeat_is_error=True
    )

    # Show detailed description of prepared voting.
    if not silent:
        print(f'\n{__doc__}\n')

        pp('Lido finance contract at:', finance.address)
        pp('Lido node operator registry at:', registry.address)
        pp('Lido voting contract at:', voting.address)
        pp('Lido token manager at:', token_manager.address)
        pp('LDO token at:', ldo_token_address)

        print('\nPoints of voting:')
        total = len(human_readable_script)
        print(human_readable_script)
        for ind, call in enumerate(human_readable_script):
            print(f'Point #{ind + 1}/{total}.')
            print(calls_info_pretty_print(call))
            print('---------------------------')

        print('Does it look good?')
        resume = prompt_bool()
        while resume is None:
            resume = prompt_bool()

        if not resume:
            print('Exit without running.')
            return -1, None

    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=(
            'Fixing key limits for Node Operators'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'gas_price': '100 gwei'
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5)  # hack for waiting thread #2.
