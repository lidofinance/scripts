"""
Voting 07/02/2024.
Scroll upgrade test.
!! Sepolia only
"""

import time

import eth_abi
from typing import Dict, Tuple, Optional

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward, agent_execute

from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)

#
# Calls chain:
# 1) Agent -> agent_execute
# 2) -> Scroll message service -> sendMessage
# 3) -> ScrollBridgeExecutor -> queue
# 4) -> ProxyAdmin -> upgrade
#

SCROLL_BRIDGE_EXECUTOR: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"
SCROLL_L1_L2_MESSAGE_SERVICE: str = "0x50c7d3e7f7c656493D1D76aaa1a836CedfCBB16A"

PROXY_ADMIN_ADDR: str = "0xc6cdc2839378d50e03c9737723d96d117b09bda5"
PROXY_TO_UPGRADE_ADDR: str = "0x2DAf22Caf40404ad8ff0Ab1E77F9C08Fef3953e2"
# PROXY_NEW_IMPL_ADDR: str = "0x2C9678042D52B97D27f2bD2947F7111d93F3dD0D"  # USDC
PROXY_NEW_IMPL_ADDR: str = "0xaed405fc13d66e2f1055f6efe9a5ce736652fa55"  # wstETH


def encode_upgrade_call(proxy_admin: str, proxy: str, new_impl: str):
    scroll_executor = interface.ScrollBridgeExecutor(
        "0xF22B24fa7c3168f30b17fd97b71bdd3162DDe029"
    )  # any address to bypass

    params = eth_abi.encode(["address", "address"], [proxy, new_impl])

    return scroll_executor.queue.encode_input([proxy_admin], [0], ["upgrade(address,address)"], [params], [False])


def encode_l1_l2_sendMessage(to: str, fee: int, calldata: str):
    l1_l2_msg_service = interface.L1ScrollMessenger(SCROLL_L1_L2_MESSAGE_SERVICE)

    return l1_l2_msg_service.sendMessage.encode_input(to, fee, calldata, 1_000_000)


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    call_script_items = [
        agent_execute(
            SCROLL_L1_L2_MESSAGE_SERVICE,
            10**17,
            encode_l1_l2_sendMessage(
                SCROLL_BRIDGE_EXECUTOR,
                0,
                encode_upgrade_call(PROXY_ADMIN_ADDR, PROXY_TO_UPGRADE_ADDR, PROXY_NEW_IMPL_ADDR),
            ),
        )
    ]

    vote_desc_items = [
        "1) Upgrade Scroll Sepolia wstETH token",
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
