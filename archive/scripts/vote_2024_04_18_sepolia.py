"""
Voting 18/04/2024.
Sepolia => Binance a.DI test voting (validate CCIP bridge setup)
!! Sepolia only
"""

import time

import eth_abi

from typing import Dict, Tuple, Optional, Any

from brownie import interface
from brownie.network.transaction import TransactionReceipt

from utils.agent import agent_execute

from utils.voting import (
    bake_vote_items,
    confirm_vote_script,
    create_vote,
)

from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)

# Calls chain:
# 1) (Sepolia) Agent -> agent_execute
# 2) -> CrossChainController -> forwardMessage
#    -> Bridges: LZ, HL, CCIP (added LINK token), Wormhole -> ...
# 3) (Binance) ... -> LZ, HL, CCIP, Wormhole
#    -> CrossChainController -> consensus 3/4
# 4) -> CrossChainExecutor (Binance) -> receiveCrossChainMessage
# 5) -> MockDestination -> test

SEPOLIA_CCC: str = "0x87c806B9f2b3d40Df7FdAd691F17915Db7983d5d"

BINANCE_CHAIN_ID: int = 97  # BNB Testnet
BINANCE_CCE: str = "0x5D0d422223C13F3324F2A9c8aA8f73E286419aeB"
BINANCE_TARGET: str = "0xf8ef983ACF0aBb154B2469E94DE0eC676ced9a04"

TEST_MESSAGE: str = "Voting 18/04/2024. Sepolia => Binance a.DI test voting (validate CCIP bridge setup)."


class CrossChainExecutorQueuePayload:
    def __init__(self, to: str, value: int, signature: str, data: Tuple[list[str], list[Any]], with_delegates: bool):
        self.to = to
        self.value = value
        self.signature = signature
        self.data_types = data[0]
        self.data_values = data[1]
        self.with_delegates = with_delegates

    def data(self) -> str:
        return eth_abi.encode(self.data_types, self.data_values)


def encode_cross_chain_executor_queue_call(payloads: list[CrossChainExecutorQueuePayload]) -> str:
    return eth_abi.encode(
        ["address[]", "uint256[]", "string[]", "bytes[]", "bool[]"],
        [
            [payload.to for payload in payloads],
            [payload.value for payload in payloads],
            [payload.signature for payload in payloads],
            [payload.data() for payload in payloads],
            [payload.with_delegates for payload in payloads],
        ],
    )


def encode_cross_chain_controller_forward_call(chain_id: int, to: str, gas_limit: int, calldata: str) -> str:
    return interface.CrossChainController(SEPOLIA_CCC).forwardMessage.encode_input(
        chain_id,
        to,
        gas_limit,
        calldata,
    )


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> bool | Tuple[int, Optional[TransactionReceipt]]:
    call_script_items = [
        agent_execute(
            SEPOLIA_CCC,
            0,
            encode_cross_chain_controller_forward_call(
                BINANCE_CHAIN_ID,
                BINANCE_CCE,
                1_000_000,
                encode_cross_chain_executor_queue_call(
                    [
                        CrossChainExecutorQueuePayload(
                            BINANCE_TARGET,
                            0,
                            "test(string)",
                            (["string"], [TEST_MESSAGE]),
                            False,
                        )
                    ]
                ),
            ),
        )
    ]

    vote_desc_items = [
        "1) Run `test(string)` function on BNB Testnet chain mock destination contract. Testing quorum 3/4.",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
