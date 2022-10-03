from utils.config import contracts
from dataclasses import dataclass, fields
from brownie import interface
from utils.l2 import send_message_to_optimism, ExecuteParams, send_message_to_arbitrum
from typing import (
    Tuple,
)

@dataclass(eq=True, frozen=True)
class Action:
    target: str
    signature: str
    calldata: str
    value_in_wei: int = 0
    delegate: bool = False


def queue_actions_calldata(actions: list[Action]) -> Tuple[str, str]:
    params = { key:[obj[key] for obj in actions ] for key in [field.name for field in fields(Action)]}
    return interface.L1CrossDomainMessenger.queue.encode_input(
        params.target,
        params.value_in_wei,
        params.signature,
        params.calldata,
        params.delegate
    )


def send_actions_to_optimism(actions: list[Action], gas_limit: int = 5_000_000) -> ExecuteParams:
    calldata = queue_actions_calldata(actions)
    return send_message_to_optimism(contracts.optimism_governance_executor.address, calldata, gas_limit)


def send_actions_to_arbitrum(actions: list[Action]) -> ExecuteParams:
    calldata = queue_actions_calldata(actions)
    return send_message_to_arbitrum(contracts.arbitrum_governance_executor.address, calldata)
