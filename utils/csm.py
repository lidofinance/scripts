from typing import Tuple
from brownie import interface

from utils.config import contracts

def activate_public_release(csm_address: str) -> Tuple[str, str]:
    csm = interface.CSModule(csm_address)
    return (csm.address, csm.activatePublicRelease.encode_input())
