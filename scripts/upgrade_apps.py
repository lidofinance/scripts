"""
Update 
"""
import time
from typing import Dict, Tuple, Optional
from utils import config
from brownie.network.transaction import TransactionReceipt
from brownie import accounts

from utils.voting import create_vote

from utils.config import (
    prompt_bool,
    get_deployer_account,
    lido_dao_voting_address,
    lido_dao_token_manager_address,
    lido_dao_lido_repo,
    lido_dao_node_operators_registry_repo,
)
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)

try:
    from brownie import interface
except ImportError:
    print(
        "You're probably running inside Brownie console. "
        "Please call:\n"
        "set_console_globals(interface=interface)"
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


def main():
    from_account = config.get_deployer_account()
    print("Deployer:", from_account)
    vote_id, _ = start_vote(
        {
            "from": from_account,
            # "max_fee": "3 gwei",
            "priority_fee": "3 gwei",
        }
    )
    print(f"Vote created: {vote_id}.")
    time.sleep(5)  # hack for waiting thread #2.


def start_vote(
    tx_params: Dict[str, str], silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting = interface.Voting(lido_dao_voting_address)
    lido_repo = interface.Repo(lido_dao_lido_repo)
    nos_repo = interface.Repo(lido_dao_node_operators_registry_repo)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

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

    _add_implementation_lido_to_repo = add_implementation_to_repo(
        lido_repo,
        update_lido_app['version'],
        update_lido_app['address'],
        update_lido_app['content_uri'],
    )

    _add_implementation_nos_to_repo = add_implementation_to_repo(
        nos_repo,
        update_node_operators_registry_app['version'],
        update_node_operators_registry_app['address'],
        update_node_operators_registry_app['content_uri'],
    )
    
    encoded_call_script = encode_call_script([
            _add_implementation_lido_to_repo,
            _add_implementation_nos_to_repo,
    ])
    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False, specific_net="mainnet", repeat_is_error=True
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
            '1) upgrade lido app frontend ipfs link'
            '2) Allocate 124,987.5031 LDO tokens for the 9th period referral rewards;'
            '3) Raise key limit for Node Operator #12 (Anyblock Analytics) to 2300.'
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

    # helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting)

    time.sleep(5) # hack for waiting thread #2.