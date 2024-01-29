from typing import Tuple
from brownie import interface

from utils.config import contracts


def add_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def remove_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def add_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def remove_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))
