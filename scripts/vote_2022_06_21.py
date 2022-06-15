"""
Voting 21/06/2022.

1. Push new voting app version to Voting Repo 0x41D65FA420bBC714686E798a0eB0Df3799cEF092.
2. Upgrade the DAO Voting ##address TBA## contract implementation.
3. Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e.
4. Update objection phase duration with `unsafelyChangeObjectionTime()` to 24 hours.
5. Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e.


"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote, bake_vote_items
from utils.permissions import encode_permission_grant, encode_permission_revoke
from utils.repo import add_implementation_to_voting_app_repo
from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
)

update_voting_app = {
    'new_address': '',  # TBA
    'content_uri':
        '0x697066733a516d514d64696979653134765966724a7753594250646e68656a446f62417877584b72524e45663438735370444d',
    # TBA
    'id': '0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e',
    'version': (3, 0, 0),
    'objection_time': 86_400  # 24 hours
}


def unsafely_change_objection_time(voting, new_time):
    return (
        voting.address,
        voting.unsafelyChangeObjectionPhaseTime.encode_input(new_time)
    )


def unsafely_change_vote_time(voting, new_time):
    return (
        voting.address,
        voting.unsafelyChangeVoteTime.encode_input(new_time)
    )


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting: interface.Voting = contracts.voting

    vote_items = bake_vote_items(
        vote_desc_items=[
            '1) Push new voting app version to Voting Repo; ',
            '2) Upgrade the DAO Voting contract implementation; ',
            '3) Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting; ',
            '4) Update objection phase duration with `unsafelyChangeObjectionTime` to 24 hours; ',
            '5) Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting.',
        ],
        call_script_items=[
            # 1. Push new voting app version to Voting Repo 0x41D65FA420bBC714686E798a0eB0Df3799cEF092
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
            encode_permission_grant(
                target_app=voting,
                permission_name='UNSAFELY_MODIFY_VOTE_TIME_ROLE',
                grant_to=voting
            ),
            # 4. Update objection duration with `unsafelyChangeObjectionTime()` to 24 hours
            unsafely_change_objection_time(voting, update_voting_app['objection_time']),
            # 5. Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
            encode_permission_revoke(
                target_app=voting,
                permission_name='UNSAFELY_MODIFY_VOTE_TIME_ROLE',
                revoke_from=voting
            )
        ]
    )

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {'from': get_deployer_account()}

    if get_is_live():
        tx_params['max_fee'] = '300 gwei'
        tx_params['priority_fee'] = '2 gwei'

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
