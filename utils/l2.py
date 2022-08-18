from utils.config import contracts
from typing import (
    Tuple,
)
from dataclasses import dataclass, fields

@dataclass(eq=True, frozen=True)
class ExecuteParams:
    target: str
    calldata: str
    value_in_wei: int = 0


def send_message_to_optimism(target: str, calldata: str, gas_limit: int = 5_000_000) -> ExecuteParams:
    optimism_messenger = contracts.optimism_messenger
    return ExecuteParams(
        optimism_messenger.address,
        optimism_messenger.sendMessage.encode_input(
            target,
            calldata,
            gas_limit
        )
    )


def send_message_to_arbitrum(target: str, calldata: str, call_value: int = 0, refund_address: str = contracts.arbitrum_governance_executor.address) -> ExecuteParams:
    arbitrum_inbox = contracts.arbitrum_inbox
    
    return ExecuteParams(
        arbitrum_inbox.address,
        arbitrum_inbox.createRetryableTicket.encode_input(
            target,
            call_value,
            maxSubmissionCost,
            refund_address,
            refund_address,
            maxGas,
            gasPriceBid,
            calldata,
        )
    )
