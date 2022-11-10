"""
Voting 11/11/2022.

!!! Görli network only

1. Add `0x...` to the Lido Oracle member comittee list
2. Add `0x...` to the Lido Oracle member comittee list
3. Set the Oracle comittee quorum to 3

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, get_is_live, network_name, contracts
from utils.brownie_prelude import *

new_oracle_committee_member_addr_1: str = "0x6432756feF0fb527C06eFd4689A7CE0E195bD327"
new_oracle_committee_member_addr_2: str = "0xeabE95AC5f3D64aE16AcBB668Ed0efcd81B721Bc"
new_quorum: int = 3


def encode_add_oracle_member(new_addr: str) -> Tuple[str, str]:
    oracle: interface.LidoOracle = contracts.lido_oracle

    return (oracle.address, oracle.addOracleMember.encode_input(new_addr))


def encode_set_quorum(new_quorum: int) -> Tuple[str, str]:
    oracle: interface.LidoOracle = contracts.lido_oracle

    return (oracle.address, oracle.setQuorum.encode_input(new_quorum))


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    if network_name() not in ("goerli", "goerli-fork"):
        raise EnvironmentError("Unexpected network")

    """Prepare and run voting."""

    call_script_items = [
        # 1. Add `0x...` to the Lido Oracle member comittee list
        encode_add_oracle_member(new_oracle_committee_member_addr_1),
        # 2. Add `0x...` to the Lido Oracle member comittee list
        encode_add_oracle_member(new_oracle_committee_member_addr_2),
        # 3. Set the Oracle comittee quorum to 3
        encode_set_quorum(new_quorum),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Add `0x...` to the Lido Oracle member comittee list",
        "2) Add `0x...` to the Lido Oracle member comittee list",
        "3) Set the Oracle comittee quorum to 3",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "200 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
