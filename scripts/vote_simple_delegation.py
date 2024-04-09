"""
Voting 23/04/2024.

1. Push new Voting app version to Voting Repo 0x4Ee3118E3858E8D7164A634825BfE0F73d99C792
2. Upgrade the Aragon Voting contract implementation 0x72fb5253AD16307B9E773d2A78CaC58E309d5Ba4
3. Push new Lido app version to Lido Repo 0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1
4. Upgrade TRP voting adapter

"""

import time

from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)
from utils.agent import agent_forward

from utils.repo import (
    add_implementation_to_voting_app_repo,
)
from utils.kernel import update_app_implementation

update_voting_app = {
    "new_address": "0x63C7F17210f6a7061e887D05BBF5412085e9DF43",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (4, 0, 0),
}

update_lido_app = {
    "address": "0x47EbaB13B806773ec2A2d16873e2dF770D130b50",
    "content_uri": "0x697066733a516d536359787a6d6d724156316344426a4c3369376a7a615a75694a373655716461465a694d6773786f46477a43",
    "version": (3, 1, 0),
}


description = """

"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    voting_adapter_with_delegation = contracts.voting_TRP_adapter.address

    vote_desc_items, call_script_items = zip(
        #
        # I. Simple Delegation
        #
        (
            "1) Push new Voting app version to Voting Repo",
            add_implementation_to_voting_app_repo(
                update_voting_app["version"],
                update_voting_app["new_address"],
                update_voting_app["content_uri"],
            ),
        ),
        (
            "2) Upgrade the DAO Voting contract implementation",
            update_app_implementation(update_voting_app["id"], update_voting_app["new_address"]),
        ),
        #
        # II. TRP adapter update
        #
        (
            "3) Change voting adapter to 0x5Ea73d6AE9B2E57eF865A3059bdC5C06b8e46072",
            agent_forward([(
                contracts.trp_escrow_factory.address,
                contracts.trp_escrow_factory.update_voting_adapter.encode_input(voting_adapter_with_delegation),
            )])
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
