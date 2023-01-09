"""
Voting 10/01/2023.

1. Add oracle named 'Rated' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a to Lido on Ethereum Oracle set
2. Add oracle named 'bloXroute' with address 0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8 to Lido on Ethereum Oracle set
3. Add oracle named 'Instadapp' with address 0x1ca0fec59b86f549e1f1184d97cb47794c8af58d to Lido on Ethereum Oracle set
4. Add oracle named 'Kyber Network' with address 0xA7410857ABbf75043d61ea54e07D57A6EB6EF186 to Lido on Ethereum Oracle set
5. Increase Lido on Ethereum Oracle set quorum to 5
6. Grant Relay Maintenance Committee 0x98be4a407Bff0c125e25fBE9Eb1165504349c37d the manager role
   in the MEV Boost Relay Allowed List smart contract 0xF95f069F9AD107938F6ba802a3da87892298610E

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, contracts
from utils.agent import agent_forward
from utils.brownie_prelude import *

new_oracle_committee_member_addr_1: str = "0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a"
new_oracle_committee_member_addr_2: str = "0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8"
new_oracle_committee_member_addr_3: str = "0x1ca0fec59b86f549e1f1184d97cb47794c8af58d"
new_oracle_committee_member_addr_4: str = "0xA7410857ABbf75043d61ea54e07D57A6EB6EF186"
new_quorum: int = 5
new_manager: str = "0x98be4a407Bff0c125e25fBE9Eb1165504349c37d"


def encode_add_oracle_member(new_addr: str) -> Tuple[str, str]:
    oracle: interface.LidoOracle = contracts.lido_oracle

    return (oracle.address, oracle.addOracleMember.encode_input(new_addr))


def encode_set_quorum(new_quorum: int) -> Tuple[str, str]:
    oracle: interface.LidoOracle = contracts.lido_oracle

    return (oracle.address, oracle.setQuorum.encode_input(new_quorum))


def encode_set_manager(new_manager: str) -> Tuple[str, str]:
    manager: interface.MEVBoostRelayAllowedList = contracts.relay_allowed_list

    return agent_forward([(manager.address, manager.set_manager.encode_input(new_manager))])


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items = [
        # 1. Add oracle named 'Rated' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a to Lido on Ethereum Oracle set
        encode_add_oracle_member(new_oracle_committee_member_addr_1),
        # 2. Add oracle named 'bloXroute' with address 0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8 to Lido on Ethereum Oracle set
        encode_add_oracle_member(new_oracle_committee_member_addr_2),
        # 3. Add oracle named 'Instadapp' with address 0x1ca0fec59b86f549e1f1184d97cb47794c8af58d to Lido on Ethereum Oracle set
        encode_add_oracle_member(new_oracle_committee_member_addr_3),
        # 4. Add oracle named 'Kyber Network' with address 0xA7410857ABbf75043d61ea54e07D57A6EB6EF186 to Lido on Ethereum Oracle set
        encode_add_oracle_member(new_oracle_committee_member_addr_4),
        # 5. Increase Lido on Ethereum Oracle set quorum to 5
        encode_set_quorum(new_quorum),
        # 6. Grant Relay Maintenance Committee 0x98be4a407Bff0c125e25fBE9Eb1165504349c37d
        # the manager role in the MEV Boost Relay Allowed List smart contract 0xF95f069F9AD107938F6ba802a3da87892298610E
        encode_set_manager(new_manager),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Add oracle named 'Rated' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a to Lido on Ethereum Oracle set",
        "2) Add oracle named 'bloXroute' with address 0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8 to Lido on Ethereum Oracle set",
        "3) Add oracle named 'Instadapp' with address 0x1ca0fec59b86f549e1f1184d97cb47794c8af58d to Lido on Ethereum Oracle set",
        "4) Add oracle named 'Kyber Network' with address 0xA7410857ABbf75043d61ea54e07D57A6EB6EF186 to Lido on Ethereum Oracle set",
        "5) Increase Lido on Ethereum Oracle set quorum to 5",
        "6) Grant 0x98be4a407Bff0c125e25fBE9Eb1165504349c37d the manager role in MEVBoostRelayAllowedList 0xF95f069F9AD107938F6ba802a3da87892298610E",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
