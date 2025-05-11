"""
Chorus One oracle rotation
1. Remove the oracle member with address 0x140bd8fbdc884f48da7cb1c09be8a2fadfea776e from HashConsensus for AccountingOracle
2. Remove the oracle member with address 0x140bd8fbdc884f48da7cb1c09be8a2fadfea776e from HashConsensus for ValidatorsExitBusOracle
3. Remove the oracle member with address 0x140bd8fbdc884f48da7cb1c09be8a2fadfea776e from CSHashConsensus for CSFeeOracle
4. Add oracle member with address 0x285f8537e1dAeEdaf617e96C742F2Cf36d63CcfB to HashConsensus for AccountingOracle
5. Add oracle member with address 0x285f8537e1dAeEdaf617e96C742F2Cf36d63CcfB to HashConsensus for ValidatorsExitBusOracle
6. Add oracle member with address 0x285f8537e1dAeEdaf617e96C742F2Cf36d63CcfB to CSHashConsensus for CSFeeOracle
"""

import time

try:
    from brownie import interface, accounts
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


from typing import Dict, Tuple, Optional
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.mainnet_fork import pass_and_exec_dao_vote

# Oracle quorum

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM = 5

# Oracles members
old_oracle_member_to_remove = "0x140bd8fbdc884f48da7cb1c09be8a2fadfea776e"
new_oracle_member_to_add = "0x285f8537e1dAeEdaf617e96C742F2Cf36d63CcfB"


description = """
**Emergency rotation of compromised Chorus One oracle.**

Rotate Chorus One's address in the Lido on Ethereum Oracle set. Full context on [Research forum](https://research.lido.fi/t/emergency-rotation-of-compromised-chorus-one-oracle/10037).
"""

def encode_remove_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_remove_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_remove_validators_cs_fee_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.csm_hash_consensus

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_add_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def encode_add_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def encode_add_cs_fee_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.csm_hash_consensus

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        # Chorus One oracle rotation
        (
            "1. Remove the oracle member with address 0x140bd8fbdc884f48da7cb1c09be8a2fadfea776e from HashConsensus for AccountingOracle",
            agent_forward(
                [
                    encode_remove_accounting_oracle_member(
                        old_oracle_member_to_remove, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    )
                ],
            ),
        ),
        (
            "2. Remove the oracle member with address 0x140bd8fbdc884f48da7cb1c09be8a2fadfea776e from HashConsensus for ValidatorsExitBusOracle",
            agent_forward(
                [
                    encode_remove_validators_exit_bus_oracle_member(
                        old_oracle_member_to_remove, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    )
                ],
            ),
        ),
        (
            "3. Remove the oracle member with address 0x140bd8fbdc884f48da7cb1c09be8a2fadfea776e from CSHashConsensus for CSFeeOracle",
            agent_forward(
                [
                    encode_remove_validators_cs_fee_oracle_member(
                        old_oracle_member_to_remove,
                        HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM,
                    )
                ],
            ),
        ),
        (
            "4. Add oracle member with address 0x285f8537e1dAeEdaf617e96C742F2Cf36d63CcfB to HashConsensus for AccountingOracle",
            agent_forward(
                [
                    encode_add_accounting_oracle_member(
                        new_oracle_member_to_add, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    ),
                ]
            ),
        ),
        (
            "5. Add oracle member with address 0x285f8537e1dAeEdaf617e96C742F2Cf36d63CcfB to HashConsensus for ValidatorsExitBusOracle",
            agent_forward(
                [
                    encode_add_validators_exit_bus_oracle_member(
                        new_oracle_member_to_add, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM
                    ),
                ]
            ),
        ),
        (
            "6. Add oracle member with address 0x285f8537e1dAeEdaf617e96C742F2Cf36d63CcfB to CSHashConsensus for CSFeeOracle",
            agent_forward(
                [
                    encode_add_cs_fee_oracle_member(new_oracle_member_to_add, HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM),
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


def start_and_execute_vote_on_fork():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id))
