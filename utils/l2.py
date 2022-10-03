from utils.config import contracts, arb_node, lido_dao_agent_address, arbitrum_refund_address
from typing import (
    Tuple,
)
from dataclasses import dataclass, fields
from brownie import network

SUBMISSION_PRICE_MULTIPLIER = 5

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


def send_message_to_arbitrum(target: str, calldata: str, call_value: int = 0) -> ExecuteParams:
    arbitrum_inbox = contracts.arbitrum_inbox
    arb_gas_price_bid = arb_node.eth.gas_price
    submission_fee = arbitrum_inbox.calculateRetryableSubmissionFee(len(calldata), network.web3.eth.gas_price) * SUBMISSION_PRICE_MULTIPLIER
    max_gas = contracts.arbitrum_node_interface.functions.estimateRetryableTicket(
            lido_dao_agent_address,
            10 ** 18 + call_value,
            target,
            call_value,
            arbitrum_refund_address,
            arbitrum_refund_address,
            calldata
    ).estimateGas()

    return ExecuteParams(
        arbitrum_inbox.address,
        arbitrum_inbox.createRetryableTicket.encode_input(
            target,
            call_value,
            submission_fee,
            arbitrum_refund_address,
            arbitrum_refund_address,
            max_gas,
            arb_gas_price_bid,
            calldata,
        ),
        call_value + submission_fee + max_gas * arb_gas_price_bid
    )
