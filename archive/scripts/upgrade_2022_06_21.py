"""
Voting 21/06/2022.

1. Push new Voting app version to Voting Repo 0x4Ee3118E3858E8D7164A634825BfE0F73d99C792
2. Upgrade the Aragon Voting contract implementation 0x72fb5253AD16307B9E773d2A78CaC58E309d5Ba4
3. Push new Lido app version to Lido Repo 0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1
4. Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
5. Update Voting objection phase duration with `unsafelyChangeObjectionTime()` to 24 hours
6. Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e

Vote passed & executed on Jun-24-2022 03:03:28 PM +UTC, block 15018878.
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote, bake_vote_items
from utils.permissions import encode_permission_grant, encode_permission_revoke
from utils.repo import (
    add_implementation_to_voting_app_repo,
    add_implementation_to_lido_app_repo,
)
from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
)

update_voting_app = {
    "new_address": "0x72fb5253AD16307B9E773d2A78CaC58E309d5Ba4",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (3, 0, 0),
    "objection_time": 86_400,  # 24 hours
}

update_lido_app = {
    "address": "0x47EbaB13B806773ec2A2d16873e2dF770D130b50",
    "content_uri": "0x697066733a516d536359787a6d6d724156316344426a4c3369376a7a615a75694a373655716461465a694d6773786f46477a43",
    "version": (3, 1, 0),
}


def unsafely_change_objection_time(voting, new_time):
    return (
        voting.address,
        voting.unsafelyChangeObjectionPhaseTime.encode_input(new_time),
    )


def unsafely_change_vote_time(voting, new_time):
    return (voting.address, voting.unsafelyChangeVoteTime.encode_input(new_time))


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting: interface.Voting = contracts.voting

    vote_items = bake_vote_items(
        vote_desc_items=[
            "1) Push new Voting app version to Voting Repo",
            "2) Upgrade the DAO Voting contract implementation",
            "3) Push new Lido app version to Lido Repo",
            "4) Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to DAO Voting",
            "5) Update Voting objection phase duration to 24 hours",
            "6) Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from DAO Voting",
        ],
        call_script_items=[
            # 1. Push new Voting app version to Voting Repo 0x4Ee3118E3858E8D7164A634825BfE0F73d99C792
            add_implementation_to_voting_app_repo(
                update_voting_app["version"],
                update_voting_app["new_address"],
                update_voting_app["content_uri"],
            ),
            # 2. Upgrade the Aragon Voting contract implementation 0x72fb5253AD16307B9E773d2A78CaC58E309d5Ba4.
            update_app_implementation(update_voting_app["id"], update_voting_app["new_address"]),
            # 3. Push new Lido app version to Lido Repo 0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1
            add_implementation_to_lido_app_repo(
                update_lido_app["version"],
                update_lido_app["address"],
                update_lido_app["content_uri"],
            ),
            # 4. Grant `UNSAFELY_MODIFY_VOTE_TIME_ROLE` to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
            encode_permission_grant(
                target_app=voting,
                permission_name="UNSAFELY_MODIFY_VOTE_TIME_ROLE",
                grant_to=voting,
            ),
            # 5. Update Voting objection phase duration with `unsafelyChangeObjectionTime()` to 24 hours
            unsafely_change_objection_time(voting, update_voting_app["objection_time"]),
            # 6. Revoke `UNSAFELY_MODIFY_VOTE_TIME_ROLE` from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
            encode_permission_revoke(
                target_app=voting,
                permission_name="UNSAFELY_MODIFY_VOTE_TIME_ROLE",
                revoke_from=voting,
            ),
        ],
    )

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
