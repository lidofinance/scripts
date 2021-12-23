"""
Voting 23/12/2021.

1. Send 4,200 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 10,000 DAI Isidoros Passadis Dec comp
2. Send 6,900 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 16,666 DAI Jacob Blish Dec comp
3. Referral program payout of 235,290 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
4. Update Lido app IPFS hash to QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS
5. Update NOs app IPFS hash to Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G

"""

import time
from typing import (
    Dict, Tuple,
    Optional
)
from brownie.network.transaction import TransactionReceipt
from functools import partial

from utils.finance import encode_token_transfer
from utils.voting import create_vote
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)
from utils.config import (
    prompt_bool,
    get_deployer_account,
    ldo_token_address,
    lido_dao_steth_address,
    lido_dao_voting_address,
    lido_dao_token_manager_address,
    lido_dao_finance_address,
    lido_dao_lido_repo,
    lido_dao_node_operators_registry_repo,
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

def make_ldo_payout(
        *not_specified,
        target_address: str,
        ldo_in_wei: int,
        reference: str,
        finance: interface.Finance
) -> Tuple[str, str]:
    """Encode LDO payout."""
    if not_specified:
        raise ValueError(
            'Please, specify all arguments with keywords.'
        )

    return encode_token_transfer(
        token_address=ldo_token_address,
        recipient=target_address,
        amount=ldo_in_wei,
        reference=reference,
        finance=finance
    )

def add_implementation_to_repo(repo, version, address, content_uri):
    return (
      repo.address,
      repo.newVersion.encode_input(
          version,
          address,
          content_uri
      )
    )

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting = interface.Voting(lido_dao_voting_address)
    lido_repo = interface.Repo(lido_dao_lido_repo)
    nos_repo = interface.Repo(lido_dao_node_operators_registry_repo)
    finance = interface.Finance(lido_dao_finance_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    _make_ldo_payout = partial(make_ldo_payout, finance=finance)

    update_lido_app = {
        'address': '0xC7B5aF82B05Eb3b64F12241B04B2cF14469E39F7',
        'ipfsCid': 'QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS',
        'content_uri': '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053',
        'id': '0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320',
        'version': (2, 0, 1),
    }

    update_node_operators_registry_app = {
        'address': '0xec3567ae258639a0FF5A02F7eAF4E4aE4416C5fe',
        'ipfsCid': 'Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G',
        'content_uri': '0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847',
        'id': '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d',
        'version': (2, 0, 1),
    }

    encoded_call_script = encode_call_script([
        # 1. Send 4,200 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 10,000 DAI Isidoros Passadis Dec comp

        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=4_200 * (10 ** 18),
            reference='Master of Validators monthly comp'
        ),

        # 2. Send 6,900 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 16,666 DAI Jacob Blish Dec comp
        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=6_900 * (10 ** 18),
            reference='Jacob Blish monthly comp'
        ),

        # 3. Referral program payout of 235,290 LDO to financial multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=235_290 * (10 ** 18),
            reference="11th period referral rewards"
        ),

        # 4. Update Lido app IPFS hash to QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS

        add_implementation_to_repo(
            lido_repo,
            update_lido_app['version'],
            update_lido_app['address'],
            update_lido_app['content_uri'],
        ),

        # 2. Update NOS app IPFS hash to Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G

        add_implementation_to_repo(
            nos_repo,
            update_node_operators_registry_app['version'],
            update_node_operators_registry_app['address'],
            update_node_operators_registry_app['content_uri'],
        ),
    
    ])
    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False, specific_net='mainnet', repeat_is_error=True
    )

    # Show detailed description of prepared voting.
    if not silent:
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
            'Omnibus vote: '
            '1) Allocate 4,200 LDO tokens to Master of Validators Dec 2021 compensation;'
            '2) Allocate 6,900 LDO tokens to Jacob Blish Dec 2021 compensation;'
            '3) Allocate 235,290 LDO tokens for the 11th period referral rewards;'
            '4) Update Lido app IPFS hash to QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS;'
            '5) Update NOs app IPFS hash to Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G'
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
    print(f'Vote created: {vote_id}.')
    time.sleep(5) # hack for waiting thread #2.
