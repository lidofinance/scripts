"""
Voting 07/04/2022.

1. Push new voting app version to Voting Repo 0x41D65FA420bBC714686E798a0eB0Df3799cEF092.
2. Upgrade the DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e contract implementation.
3. Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e.
4. Update voting duration with `unsafelyChangeVoteTime` to 72 hours.
5. Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e.

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.permissions import encode_permission_create, encode_permission_grant, encode_permission_revoke
from utils.repo import add_implementation_to_voting_app_repo
from utils.kernel import update_app_implementation
from utils.evm_script import encode_call_script
from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    network_name
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

    voting: interface.Voting = contracts.voting
    permission_name: str = 'UNSAFELY_MODIFY_VOTE_TIME_ROLE'

    update_voting_app_goerli = {
        'new_address': '0x9059e060113b7394FC964bf86CD246f3e9D4210d',
        'content_uri': '0x697066733a516d5962774366374d6e6932797a31553358334769485667396f35316a6b53586731533877433257547755684859',
        'id': '0xee7f2abf043afe722001aaa900627a6e29adcbcce63a561fbd97e0a0c6429b94',
        'version': (3, 0, 0),
        'new_vote_time': 259200  # 72 hours
    }

    update_voting_app_mainnet = {
        'new_address': '0x41D65FA420bBC714686E798a0eB0Df3799cEF092',
        'content_uri': '0x697066733a516d514d64696979653134765966724a7753594250646e68656a446f62417877584b72524e45663438735370444d',
        'id': '0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e',
        'version': (2, 0, 0),
        'new_vote_time': 259200  # 72 hours
    }

    update_voting_app = update_voting_app_mainnet
    create_permission_call = encode_permission_create(
        entity=voting,
        target_app=voting,
        permission_name=permission_name,
        manager=voting
    )

    if network_name() in ("goerli", "goerli-fork"):
        update_voting_app = update_voting_app_goerli
        create_permission_call = encode_permission_grant(
            target_app=voting,
            permission_name=permission_name,
            grant_to=voting
        )

    encoded_call_script = encode_call_script([
        # 1. Push new voting app version to Voting Repo 0x4ee3118e3858e8d7164a634825bfe0f73d99c792
        add_implementation_to_voting_app_repo(
            update_voting_app['version'],
            update_voting_app['new_address'],
            update_voting_app['content_uri']
        ),
        # 2. Upgrade the DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e contract implementation
        update_app_implementation(
            update_voting_app['id'],
            update_voting_app['new_address']
        ),
        # 3. Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        create_permission_call,
        # 4. Update voting duration with `unsafelyChangeVoteTime` to 72 hours.
        unsafely_change_vote_time(voting, update_voting_app['new_vote_time']),
        # 5. Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        encode_permission_revoke(
            target_app=voting,
            permission_name=permission_name,
            revoke_from=voting
        )
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Push new voting app version to Voting Repo 0x41D65FA420bBC714686E798a0eB0Df3799cEF092; '
            '2) Upgrade the DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e contract implementation; '
            '3) Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e; '
            '4) Update voting duration with `unsafelyChangeVoteTime` to 72 hours; '
            '5) Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e.'
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
