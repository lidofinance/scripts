"""
Voting 21/06/2022.

1. Push new voting app version to Voting Repo 0x41D65FA420bBC714686E798a0eB0Df3799cEF092.
2. Upgrade the DAO Voting ##address TBA## contract implementation.
3. Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e.
4. Update objection phase duration with `unsafelyChangeObjectionTime()` to 24 hours.
5. Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e.


"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.permissions import encode_permission_create, encode_permission_grant, encode_permission_revoke
from utils.repo import add_implementation_to_voting_app_repo
from utils.kernel import update_app_implementation
from utils.evm_script import encode_call_script
from utils.config import get_deployer_account, contracts, get_is_live, network_name

update_voting_app = {
    "new_address": "",  # TBA
    "content_uri": "",  # TBA
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (3, 0, 0),
    "vote_time": 172_800 + 86_400,  # 48 + 24 hours
    "objection_time": 86_400,  # 24 hours
}

if network_name() in ("goerli", "goerli-fork"):
    update_voting_app["new_address"] = "0x12D103a07Ac0429519C77E96781dFD5186119582"  # TBA
    update_voting_app[
        "content_uri"
    ] = "0x697066733a516d5962774366374d6e6932797a31553358334769485667396f35316a6b53586731533877433257547755684859"  # TBA
    update_voting_app["id"] = "0xee7f2abf043afe722001aaa900627a6e29adcbcce63a561fbd97e0a0c6429b94"
    update_voting_app["version"] = (4, 0, 0)
    update_voting_app["objection_time"] = 5 * 60  # 5 min
    update_voting_app["vote_time"] = 10 * 60  # 10 min


def unsafely_change_objection_time(voting, new_time):
    return (voting.address, voting.unsafelyChangeObjectionPhaseTime.encode_input(new_time))


def unsafely_change_vote_time(voting, new_time):
    return (voting.address, voting.unsafelyChangeVoteTime.encode_input(new_time))


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting: interface.Voting = contracts.voting

    encoded_call_script = encode_call_script(
        [
            # 1. Push new voting app version to Voting Repo 0x41D65FA420bBC714686E798a0eB0Df3799cEF092
            add_implementation_to_voting_app_repo(
                update_voting_app["version"], update_voting_app["new_address"], update_voting_app["content_uri"]
            ),
            # 2. Upgrade the DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e contract implementation
            update_app_implementation(update_voting_app["id"], update_voting_app["new_address"]),
            # 3. Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
            encode_permission_grant(
                target_app=voting, permission_name="UNSAFELY_MODIFY_VOTE_TIME_ROLE", grant_to=voting
            ),
            # 4. Update objection duration with `unsafelyChangeObjectionTime()` to 24 hours
            unsafely_change_objection_time(voting, update_voting_app["objection_time"]),
            unsafely_change_vote_time(voting, update_voting_app["vote_time"]),  # for goerli only
            # 5. Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
            encode_permission_revoke(
                target_app=voting, permission_name="UNSAFELY_MODIFY_VOTE_TIME_ROLE", revoke_from=voting
            ),
        ]
    )

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            "Omnibus vote: "
            "1) Push new voting app version to Voting Repo; "
            "2) Upgrade the DAO Voting contract implementation; "
            "3) Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting; "
            "4) Update objection phase duration with `unsafelyChangeObjectionTime` to 24 hours; "
            "5) Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting."
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params,
    )


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
