"""
Voting 18/03/2024.
Sepolia => Binance a.DI test voting.
!! Sepolia only
"""

import time

import eth_abi

from typing import Dict, Tuple, Optional

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
#    -> Bridges: LZ, HL, CCIP, Wormhole -> ...
# 3) (Binance) ... -> LZ, HL, CCIP, Wormhole
#    -> CrossChainController -> consensus 2/4
# 4) -> CrossChainExecutor (Binance) -> receiveCrossChainMessage
# 5) -> MockDestination -> test

SEPOLIA_CCC: str = "0xb5896839eD2e5c56345335bd4bD3b1507398e262"

BINANCE_CHAIN_ID: int = 97  # BNB Testnet
BINANCE_CHAIN_EXECUTOR: str = "0xEB43648C6e4F75Dd3397017Db3206b2bf1196bD0"
BINANCE_MOCK_DEST: str = "0x068c8DbA83E71E9146F9894399c2F3a560288889"

TEST_MESSAGE: str = "Voting 18/03/2024. Sepolia => Binance a.DI test voting."


def encode_cross_chain_executor_payload() -> str:
    cc_executor = interface.CrossChainExecutor(SEPOLIA_CCC)

    params = eth_abi.encode(["string"], [TEST_MESSAGE])

    return eth_abi.encode(
        ["address[]", "uint256[]", "string[]", "bytes[]", "bool[]"],
        [[BINANCE_MOCK_DEST], [0], ["test(string)"], [params], [False]],
    )


def encode_cross_chain_controller_forward(chain_id: int, to: str, gas_limit: int, calldata: str) -> str:
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
            10**17,
            encode_cross_chain_controller_forward(
                BINANCE_CHAIN_ID, BINANCE_CHAIN_EXECUTOR, 300_000, encode_cross_chain_executor_payload()
            ),
        )
    ]

    vote_desc_items = [
        "1) Run test function on BNB Testnet chain mock destination contract.",
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
