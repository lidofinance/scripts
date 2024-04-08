"""
Voting xx/xx/2024.

Upgrade L1Bridge, L2Bridge, L2 wstETH, L2 stETH, TokenRateOracle

"""

import time
from brownie import interface
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.agent import agent_forward, agent_execute


description = """

Upgrade L1Bridge, L2Bridge, L2 wstETH, L2 stETH, TokenRateOracle

"""

OPTIMISM_BRIDGE_EXECUTOR: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"
OPTIMISM_L1_L2_MESSAGE_SERVICE: str = "0x50c7d3e7f7c656493D1D76aaa1a836CedfCBB16A"

L1_TOKEN_BRIDGE_PROXY: str = "0x76943C0D61395d8F2edF9060e1533529cAe05dE6"
L1_TOKEN_BRIDGE_NEW_IMPL: str = "0xc4E3ff0b5B106f88Fc64c43031BE8b076ee9F21C"

L2_TOKEN_BRIDGE_PROXY: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"
L2_TOKEN_BRIDGE_NEW_IMPL: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"

L2_NON_REBASABLE_TOKEN_PROXY: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"
L2_NON_REBASABLE_TOKEN_NEW_IMPL: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"

L2_REBASABLE_TOKEN_PROXY: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"
L2_REBASABLE_TOKEN_NEW_IMPL: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"

L2_TOKEN_RATE_ORACLE_PROXY: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"
L2_TOKEN_RATE_ORACLE_NEW_IMPL: str = "0x6b314986E3737Ce23c2a13036e77b3f5A846F8AF"

PROXY_ADMIN_ADDR: str = "0xc6cdc2839378d50e03c9737723d96d117b09bda5"

def encode_upgrade_call(proxy_admin: str, proxy: str, new_impl: str):
    scroll_executor = interface.ScrollBridgeExecutor(
        "0xF22B24fa7c3168f30b17fd97b71bdd3162DDe029"
    )  # any address to bypass

    params = eth_abi.encode(["address", "address"], [proxy, new_impl])

    return scroll_executor.queue.encode_input([proxy_admin], [0], ["upgrade(address,address)"], [params], [False])


def encode_l1_l2_sendMessage(to: str, fee: int, calldata: str):
    l1_l2_msg_service = interface.L1ScrollMessenger(OPTIMISM_L1_L2_MESSAGE_SERVICE)

    return l1_l2_msg_service.sendMessage.encode_input(to, fee, calldata, 1_000_000)

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    l1_token_bridge_proxy = interface.OssifiableProxy(L1_TOKEN_BRIDGE_PROXY);

    call_script_items = [
            agent_forward(
            [
                (
                    l1_token_bridge_proxy.address,
                    l1_token_bridge_proxy.proxy__upgradeTo.encode_input(L1_TOKEN_BRIDGE_NEW_IMPL),
                )
            ]),
    #         # agent_execute(
    #         #     OPTIMISM_L1_L2_MESSAGE_SERVICE,
    #         #     10**17,
    #         #     encode_l1_l2_sendMessage(
    #         #         OPTIMISM_BRIDGE_EXECUTOR,
    #         #         0,
    #         #         encode_upgrade_call(PROXY_ADMIN_ADDR, L2_TOKEN_BRIDGE_PROXY, L2_TOKEN_BRIDGE_NEW_IMPL),
    #         # ),

    ]

    vote_desc_items = [
        "1) Upgrade L1 Bridge implementation",
        # "2) Upgrade L2 Bridge implementation",
        # "3) Upgrade L2 wstETH implementation",
        # "4) Upgrade L2 stETH implementation",
        # "5) Upgrade L2 TokenRateOracle implementation",
    ]


    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
