"""
Voting 06/08/2024.

I. Replacing Rated Labs with MatrixedLink in Lido on Ethereum Oracle set
1. Remove the oracle member named 'Rated Labs' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a from HashConsensus for AccountingOracle on Lido on Ethereum
2. Remove the oracle member named 'Rated Labs' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a from HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum
3. Add oracle member named 'MatrixedLink' with address 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 to HashConsensus for AccountingOracle on Lido on Ethereum Oracle set
4. Add oracle member named 'MatrixedLink' with address 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 to HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set

II. Simple Delegation
1. Push new Voting app version to the Voting Repo 0x4ee3118e3858e8d7164a634825bfe0f73d99c792
2. Upgrade the Aragon Voting contract implementation 0xf165148978Fa3cE74d76043f833463c340CFB704
3. Upgrade TRP voting adapter 0x4b2AB543FA389Ca8528656282bF0011257071BED

"""

import time

from typing import Dict, Tuple
from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)
from utils.repo import add_implementation_to_voting_app_repo
from utils.kernel import update_app_implementation
from utils.agent import agent_forward

def encode_remove_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))

def encode_remove_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_add_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def encode_add_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))



updated_trp_voting_adapter = "0x4b2AB543FA389Ca8528656282bF0011257071BED"

updated_voting_app = {
    "address": "0xf165148978Fa3cE74d76043f833463c340CFB704",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (4, 0, 0),  # Current version is 3.0.0
}

description = """
1. Replacement of Rated Labs with MatrixedLink in Lido on Ethereum Oracle set. [Snapshot vote](https://snapshot.org/#/lido-snapshot.eth/proposal/0x5667528b50af1668ea246bde5bbf136f202629dee50747bbcc0839f48bf396b1).
2. Simple delegation Voting Upgrade
"""

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    rated_labs_oracle_member = "0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a"
    matrixed_link_oracle_member = "0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9"

    vote_desc_items, call_script_items = zip(
        #
        # I. Replacement in the Lido Oracle set
        #
        (
            "1) Remove the oracle member named 'Rated Labs' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a from HashConsensus for AccountingOracle on Lido on Ethereum",
             agent_forward(
                [
                    encode_remove_accounting_oracle_member(
                        rated_labs_oracle_member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    )
                ],
            ),
        ),
        (
            "2) Remove the oracle member named 'Rated Labs' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a from HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum",
             agent_forward(
                [
                    encode_remove_validators_exit_bus_oracle_member(
                        rated_labs_oracle_member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    )
                ],
            ),
        ),
        (
            "3) Add oracle member named 'MatrixedLink' with address 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 to HashConsensus for AccountingOracle on Lido on Ethereum Oracle set",
            agent_forward(
                [
                    encode_add_accounting_oracle_member(
                        matrixed_link_oracle_member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    ),
                ]
            ),
        ),
        (
            "4) Add oracle member named 'MatrixedLink' with address 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 to HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set",
            agent_forward(
                [
                    encode_add_validators_exit_bus_oracle_member(
                        matrixed_link_oracle_member, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM
                    ),
                ]
            ),
        ),
        #
        # II. Simple Delegation
        #
        (
            "1) Push new Voting app version to the Voting Repo",
            add_implementation_to_voting_app_repo(
                updated_voting_app["version"],
                updated_voting_app["address"],
                updated_voting_app["content_uri"],
            ),
        ),
        (
            "2) Upgrade the Aragon Voting contract implementation",
            update_app_implementation(updated_voting_app["id"], updated_voting_app["address"]),
        ),
        (
            "3) Upgrade TRP voting adapter",
            agent_forward(
                [
                    (
                        contracts.trp_escrow_factory.address,
                        contracts.trp_escrow_factory.update_voting_adapter.encode_input(updated_trp_voting_adapter),
                    )
                ]
            ),
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
