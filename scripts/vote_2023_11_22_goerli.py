"""
Voting 22/11/2023.
Linea upgrade test.
!! Goerli only
"""

import time

import eth_abi
from typing import Dict, Tuple, Optional

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward

from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)

#
# Calls chain:
# 1) Agent -> agent_forward
# 2) -> Linea Message service -> sendMessage
# 3) -> LineaBridgeExecutor -> queue
# 4) -> ProxyAdmin -> upgrade
#

LINEA_BRIDGE_EXECUTOR: str = "0x4b38D24E70079f2dd1D79B86E2B52f4b13872a3B"
LINEA_L1_L2_MESSAGE_SERVICE: str = "0x70BaD09280FD342D02fe64119779BC1f0791BAC2"

PROXY_ADMIN_ADDR: str = "0x71062fbc3da2d792285c3d5dabba12a42339e85c"
PROXY_TO_UPGRADE_ADDR: str = "0x9ceed01e39279a529f44deb9d35e09a04b1e67c8"
PROXY_NEW_IMPL_ADDR: str = "0x1c92Ff898f7c34fc6eD884aEC3859Fd6C655c1F0"  # USDC


def encode_upgrade_call(proxy_admin: str, proxy: str, new_impl: str):
    linea_executor = interface.LineaBridgeExecutor(
        "0x70BaD09280FD342D02fe64119779BC1f0791BAC2"
    )  # any address to bypass

    params = eth_abi.encode(["address", "address"], [proxy, new_impl])

    return linea_executor.queue.encode_input([proxy_admin], [0], ["upgrade(address,address)"], [params], [False])


def encode_l1_l2_sendMessage(to: str, fee: int, calldata: str):
    l1_l2_msg_service = interface.L1MessageService(LINEA_L1_L2_MESSAGE_SERVICE)

    return (l1_l2_msg_service.address, l1_l2_msg_service.sendMessage.encode_input(to, fee, calldata))


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    call_script_items = [
        agent_forward(
            [
                encode_l1_l2_sendMessage(
                    LINEA_BRIDGE_EXECUTOR,
                    0,
                    encode_upgrade_call(PROXY_ADMIN_ADDR, PROXY_TO_UPGRADE_ADDR, PROXY_NEW_IMPL_ADDR),
                )
            ]
        )
    ]

    vote_desc_items = [
        "1) Upgrade Linea Görli wstETH token",
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
