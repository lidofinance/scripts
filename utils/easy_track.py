from typing import Tuple
from utils.config import contracts

from brownie import Contract

def add_evmscript_factory(factory: Contract, permissions: str) -> Tuple[str, str]:
    easy_track = contracts.easy_track

    return (
        easy_track.address,
        easy_track.addEVMScriptFactory.encode_input(
            factory,
            permissions
        )
    )

def remove_evmscript_factory(factory: Contract) -> Tuple[str, str]:
    easy_track = contracts.easy_track

    return (
        easy_track.address,
        easy_track.removeEVMScriptFactory.encode_input(
            factory
        )
    )

def create_permissions(contract: Contract, method: str) -> str:
    return contract.address + getattr(contract, method).signature[2:]
