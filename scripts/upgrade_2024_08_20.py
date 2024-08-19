"""
Voting 13/08/2024.

I. Replace Rated Labs with MatrixedLink in Lido on Ethereum Oracle set
1. Remove the oracle member named 'Rated Labs' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a from HashConsensus for AccountingOracle on Lido on Ethereum
2. Remove the oracle member named 'Rated Labs' with address 0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a from HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum
3. Add oracle member named 'MatrixedLink' with address 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 to HashConsensus for AccountingOracle on Lido on Ethereum Oracle set
4. Add oracle member named 'MatrixedLink' with address 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 to HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set

II. Change NOs’ names and reward addresses
5. Grant permission MANAGE_NODE_OPERATOR_ROLE on NO_registry to Voting
6. Change the on-chain name of node operator with id 23 from 'CryptoManufaktur' to 'Galaxy'
7. Change the reward address of node operator with id 23 from 0x59eCf48345A221E0731E785ED79eD40d0A94E2A5 to 0x3C3F243263d3106Fdb31eCf2248f9bC82F723c4B
8. Change the on-chain name of node operator with id 36 from 'Numic' to 'Pier Two'
9. Change the reward address of node operator with id 36 from  0x0209a89b6d9F707c14eB6cD4C3Fb519280a7E1AC to 0x35921FB43cB92F5Bfef7cBA1e97Eb5A21Fc2d353
10. Revoke permission MANAGE_NODE_OPERATOR_ROLE on NO_registry from Voting

III. Simple Delegation
11. Push new Voting app version to the Lido Aragon Voting Repo 0x4ee3118e3858e8d7164a634825bfe0f73d99c792
12. Upgrade the Aragon Voting contract implementation 0xf165148978Fa3cE74d76043f833463c340CFB704
13. Upgrade TRP voting adapter 0x4b2AB543FA389Ca8528656282bF0011257071BED

Vote #177, initiated on 13/08/2024, did not reach a quorum.

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
from utils.permissions import encode_permission_grant, encode_permission_revoke
from utils.node_operators import encode_set_node_operator_name, encode_set_node_operator_reward_address


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


HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5

rated_labs_oracle_member = "0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a"

matrixed_link_oracle_member = "0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9"

CryptoManufaktur_id = 23
CryptoManufaktur_new_name = "Galaxy"
CryptoManufaktur_new_reward_address = "0x3C3F243263d3106Fdb31eCf2248f9bC82F723c4B"

Numic_id = 36
Numic_new_name = "Pier Two"
Numic_new_reward_address = "0x35921FB43cB92F5Bfef7cBA1e97Eb5A21Fc2d353"

updated_trp_voting_adapter = "0x4b2AB543FA389Ca8528656282bF0011257071BED"

updated_voting_app = {
    "address": "0xf165148978Fa3cE74d76043f833463c340CFB704",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (4, 0, 0),  # Current version is 3.0.0
}


description = """
1. **Replace Rated Labs with MatrixedLink in Lido on Ethereum Oracle set**, following the [Snapshot decision](https://snapshot.org/#/lido-snapshot.eth/proposal/0x5667528b50af1668ea246bde5bbf136f202629dee50747bbcc0839f48bf396b1). (Items 1-4)

2. **Rename Node Operator** with ID 23 from "CryptoManufaktur" to "Galaxy" **and update the reward address**, as [requested on the forum](https://research.lido.fi/t/node-operator-registry-name-reward-address-change/4170/26). (Items 5-7)

3. **On-Chain Delegation** (Items 8-10). [Approved on Snapshot](https://snapshot.org/#/lido-snapshot.eth/proposal/0x8ad1089720d2fd68cc49b74e138915af7fec35a06b04c2af2fcf4828d5bbd220), this proposal enhances Lido DAO's governance by updating two contracts:
    - [Aragon Voting:](https://etherscan.io/address/0xf165148978Fa3cE74d76043f833463c340CFB704) allows LDO holders to delegate voting power while retaining override rights and enabling delegates to participate in on-chain voting on behalf of their delegators. Includes a Lido Aragon Voting Repo upgrade. Audited by [Ackee](https://github.com/lidofinance/audits/blob/main/Ackee%20Blockchain%20Lido%20Simple%20Delegation%20audit%20report%2007-24.pdf) and [Statemind](https://github.com/lidofinance/audits/blob/main/Statemind%20Lido%20Simple%20Delegation%20audit%20report%2007-24.pdf).
    - [TRP Voting Adapter:](https://etherscan.io/address/0x4b2AB543FA389Ca8528656282bF0011257071BED) allows [TRP participants](https://research.lido.fi/t/lidodao-token-rewards-plan-trp/3364) to delegate their voting power. [Checked by MixBytes](https://research.lido.fi/t/lip-21-simple-on-chain-delegation/6840/21).
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    voting = contracts.voting
    NO_registry = contracts.node_operators_registry

    vote_desc_items, call_script_items = zip(
        #
        # I. Replace Rated Labs with MatrixedLink in Lido on Ethereum Oracle set
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
        # II. Change NO’s name and reward address
        #
        (
            "5) Grant permission MANAGE_NODE_OPERATOR_ROLE on NO_registry to Voting",
            encode_permission_grant(
                target_app=NO_registry,
                permission_name="MANAGE_NODE_OPERATOR_ROLE",
                grant_to=voting,
            ),
        ),
        (
            "6) Change the on-chain name of node operator with id 23 from 'CryptoManufaktur' to 'Galaxy'",
            encode_set_node_operator_name(CryptoManufaktur_id, CryptoManufaktur_new_name, NO_registry),
        ),
        (
            "7) Change the reward address of node operator with id 23 from 0x59eCf48345A221E0731E785ED79eD40d0A94E2A5 to 0x3C3F243263d3106Fdb31eCf2248f9bC82F723c4B",
            encode_set_node_operator_reward_address(
                CryptoManufaktur_id, CryptoManufaktur_new_reward_address, NO_registry
            ),
        ),
        (
            "8) Change the on-chain name of node operator with id 36 from 'Numic' to 'Pier Two'",
            encode_set_node_operator_name(Numic_id, Numic_new_name, NO_registry),
        ),
        (
            "9) Change the reward address of node operator with id 36 from  0x0209a89b6d9F707c14eB6cD4C3Fb519280a7E1AC to 0x35921FB43cB92F5Bfef7cBA1e97Eb5A21Fc2d353",
            encode_set_node_operator_reward_address(Numic_id, Numic_new_reward_address, NO_registry),
        ),
        (
            "10) Revoke permission MANAGE_NODE_OPERATOR_ROLE on NO_registry from Voting",
            encode_permission_revoke(
                target_app=NO_registry,
                permission_name="MANAGE_NODE_OPERATOR_ROLE",
                revoke_from=voting,
            ),
        ),
        # MANAGE_NODE_OPERATOR_ROLE was previously granted once on vote #160 (vote_2023_06_20), no need to revoke as it’s the second granting
        #
        # III. Simple Delegation
        #
        (
            "11) Push new Voting app version to the Voting Repo",
            add_implementation_to_voting_app_repo(
                updated_voting_app["version"],
                updated_voting_app["address"],
                updated_voting_app["content_uri"],
            ),
        ),
        (
            "12) Upgrade the Aragon Voting contract implementation",
            update_app_implementation(updated_voting_app["id"], updated_voting_app["address"]),
        ),
        (
            "13) Upgrade TRP voting adapter",
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
