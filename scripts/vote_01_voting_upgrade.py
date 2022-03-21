"""
Voting 23/09/2021.

1. Push new voting version to repo
2. Upgrade voting implementation
3. Grant UNSAFELY_MODIFY_VOTE_TIME_ROLE to voting
4. Update vote time to 72 hours
"""

import time
from typing import (
    Dict, Tuple,
    Optional
)

from brownie.utils import color
from brownie.network.transaction import TransactionReceipt

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
    lido_dao_voting_address,
    lido_dao_token_manager_address,
    lido_dao_kernel,
    lido_dao_voting_repo
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


def add_implementation_to_repo(repo, version, address, content_uri):
    return (
        repo.address,
        repo.newVersion.encode_input(
            version,
            address,
            content_uri
        )
    )


def update_app_implementation(kernel, app_id, new_implementation):
    return (
        kernel.address,
        kernel.setApp.encode_input(
            kernel.APP_BASES_NAMESPACE(),
            app_id,
            new_implementation
        )
    )


def grant_permission(acl, repo, voting, permission):
    return (
        acl.address,
        acl.createPermission.encode_input(
            voting.address,
            repo.address,
            permission,
            voting.address
        )
    )


def unsafely_change_vote_time(voting, new_vote_time):
    return (
        voting.address,
        voting.unsafelyChangeVoteTime.encode_input(
            new_vote_time
        )
    )


def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    # Lido contracts and constants:
    repo = interface.Repo(lido_dao_voting_repo)
    kernel = interface.Kernel(lido_dao_kernel)
    voting = interface.Voting(lido_dao_voting_address)
    acl = interface.ACL(kernel.acl())
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    # Vote specific addresses and constants:
    # 1. Push new voting version to repo
    # 2. Upgrade voting implementation
    # 3. Grant UNSAFELY_MODIFY_VOTE_TIME_ROLE to voting
    # 4. Update vote time to 72 hours

    update_voting_app = {
        'new_address': '0xfd5952Ef8dE4707f95E754299e8c0FfD1e876F34',
        'content_uri': '0x697066733a516d5962774366374d6e6932797a31553358334769485667396f35316a6b53586731533877433257547755684859',
        'id': '0xee7f2abf043afe722001aaa900627a6e29adcbcce63a561fbd97e0a0c6429b94',
        'version': (2, 0, 0),
        'new_vote_time': 259200  # 72 hours
    }

    _add_implementation_to_repo = add_implementation_to_repo(
        repo,
        update_voting_app['version'],
        update_voting_app['new_address'],
        update_voting_app['content_uri'],
    )
    _update_app_implementation = update_app_implementation(
        kernel,
        update_voting_app['id'],
        update_voting_app['new_address'],
    )
    _grant_permission_UNSAFELY_MODIFY_VOTE_TIME_ROLE = grant_permission(
        acl,
        voting,
        voting,
        '068ca51c9d69625c7add396c98ca4f3b27d894c3b973051ad3ee53017d7094ea'
    )
    _unsafelyChangeVoteTime = unsafely_change_vote_time(
        voting,
        update_voting_app['new_vote_time'],
    )

    # Encoding vote scripts:
    encoded_call_script = encode_call_script([
        _add_implementation_to_repo,
        _update_app_implementation,
        _grant_permission_UNSAFELY_MODIFY_VOTE_TIME_ROLE,
        _unsafelyChangeVoteTime,
    ])

    # Show detailed description of prepared voting.
    if not silent:
        human_readable_script = decode_evm_script(
            encoded_call_script, verbose=False,
            specific_net='mainnet', repeat_is_error=True
        )

        print(f'\n{__doc__}\n')

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
        vote_desc=(
            'Omnibus vote: \n'
            '1. Push new voting version to repo\n'
            '2. Upgrade voting implementation\n'
            '3. Grant UNSAFELY_MODIFY_VOTE_TIME_ROLE to voting\n'
            '4. Update vote time to 72 hours'
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
