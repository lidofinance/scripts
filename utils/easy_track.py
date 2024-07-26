from typing import Tuple
from utils.config import contracts

from brownie import Contract


def add_evmscript_factory(factory: Contract | str, permissions: str) -> Tuple[str, str]:
    easy_track = contracts.easy_track

    return (
        easy_track.address,
        easy_track.addEVMScriptFactory.encode_input(
            factory,
            permissions
        )
    )


def remove_evmscript_factory(factory: Contract | str) -> Tuple[str, str]:
    easy_track = contracts.easy_track

    return (
        easy_track.address,
        easy_track.removeEVMScriptFactory.encode_input(
            factory
        )
    )

def create_permissions_for_overloaded_method(contract: Contract, method: str, paramethers: Tuple[str, ...] = None) -> str:
    method_description = getattr(contract, method)

    if len(method_description.methods) > 0:
        return method_description.methods[paramethers].signature[2:]

    return create_permissions(contract, method)

def create_permissions(contract: Contract, method: str) -> str:
    return contract.address + getattr(contract, method).signature[2:]


def set_motions_count_limit(motionsCountLimit: int) -> Tuple[str, str]:
    easy_track = contracts.easy_track

    return (
        easy_track.address,
        easy_track.setMotionsCountLimit.encode_input(motionsCountLimit)
    )
