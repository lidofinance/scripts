"""
Voting xx/xx/2024.

1. Upgrade L1 Bridge implementation
2. Finalize L1 Bridge upgrade
3. Upgrade L1 LidoLocator implementation
4. Grant DEPOSITS_ENABLER_ROLE to Emergency Brakes Committee multisig
5. Send L2 upgrade call:
    (a) upgrade L2TokenBridge;
    (b) finalize L2TokenBridge upgrade;
    (c) upgrade wstETH on L2;
    (d) finalize wstETH upgrade";

"""

import time
import eth_abi
import brownie

from brownie import interface, web3
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.agent import agent_forward
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    L1_EMERGENCY_BRAKES_MULTISIG,
    LIDO_LOCATOR,
    LIDO_LOCATOR_IMPL,
    LIDO_LOCATOR_IMPL_NEW,
    L1_OPTIMISM_TOKENS_BRIDGE,
    L1_OPTIMISM_TOKENS_BRIDGE_IMPL,
    L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
    L1_OPTIMISM_CROSS_DOMAIN_MESSENGER,
    L2_OPTIMISM_TOKENS_BRIDGE,
    L2_OPTIMISM_GOVERNANCE_EXECUTOR,
    L2_OPTIMISM_WSTETH_TOKEN,
    L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
    L2_OPTIMISM_WSTETH_IMPL_NEW,
)

# from utils.test.easy_track_helpers import encode_function_call

DESCRIPTION = """
Voting xx/xx/2024.

Upgrade L1Bridge, L2Bridge, L2 wstETH

"""

DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"


def encode_l2_upgrade_call(proxy1: str, new_impl1: str, proxy2: str, new_impl2: str):
    # TODO: reuse the args string
    queue_definition = f"queue(address[],uint256[],string[],bytes[],bool[])"
    queue_selector = web3.keccak(text=queue_definition).hex()[:10]

    args_bytes = eth_abi.encode(
        ["address[]", "uint256[]", "string[]", "bytes[]", "bool[]"],
        [
            [proxy1, proxy1, proxy2, proxy2],
            [0, 0, 0, 0],
            [
                "proxy__upgradeTo(address)",
                "finalizeUpgrade_v2()",
                "proxy__upgradeTo(address)",
                "finalizeUpgrade_v2(string,string)",
            ],
            [
                eth_abi.encode(["address"], [new_impl1]),
                eth_abi.encode([], []),
                eth_abi.encode(["address"], [new_impl2]),
                eth_abi.encode(["string", "string"], ["Wrapped liquid staked Ether 2.0", "wstETH"]),
            ],
            [False, False, False, False],
        ],
    ).hex()
    assert args_bytes[1] != "x"  # just convenient debug check
    calldata = f"{queue_selector}{args_bytes}"
    return calldata


def encode_l1_l2_sendMessage(to: str, calldata: str):
    l1_l2_msg_service = interface.OpCrossDomainMessenger(L1_OPTIMISM_CROSS_DOMAIN_MESSENGER)
    min_gas_limit = 1_000_000
    return l1_l2_msg_service.sendMessage.encode_input(to, calldata, min_gas_limit)


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""
    check_pre_upgrade_state()

    lido_locator_as_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    l1_token_bridge_as_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)

    call_script_items = [
        # 1. L1 TokenBridge upgrade proxy
        agent_forward(
            [
                (
                    l1_token_bridge_as_proxy.address,
                    l1_token_bridge_as_proxy.proxy__upgradeTo.encode_input(L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW),
                )
            ]
        ),
        # 2. L1 TokenBridge finalize upgrade
        agent_forward([(l1_token_bridge.address, l1_token_bridge.finalizeUpgrade_v2.encode_input())]),
        # 3. Upgrade L1 LidoLocator implementation
        agent_forward(
            [
                (
                    lido_locator_as_proxy.address,
                    lido_locator_as_proxy.proxy__upgradeTo.encode_input(LIDO_LOCATOR_IMPL_NEW),
                )
            ]
        ),
        # 4. Grant DEPOSITS_ENABLER_ROLE to Emergency Brakes Committee multisig
        agent_forward(
            [
                (
                    l1_token_bridge.address,
                    l1_token_bridge.grantRole.encode_input(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG),
                )
            ]
        ),
        # 5. L2 TokenBridge
        agent_forward(
            [
                (
                    L1_OPTIMISM_CROSS_DOMAIN_MESSENGER,
                    encode_l1_l2_sendMessage(
                        L2_OPTIMISM_GOVERNANCE_EXECUTOR,
                        encode_l2_upgrade_call(
                            L2_OPTIMISM_TOKENS_BRIDGE,
                            L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
                            L2_OPTIMISM_WSTETH_TOKEN,
                            L2_OPTIMISM_WSTETH_IMPL_NEW,
                        ),
                    ),
                )
            ]
        ),
    ]

    vote_desc_items = [
        "1) Upgrade Optimism L1 Bridge implementation",
        "2) Finalize Optimism L1 Bridge upgrade",
        "3) Upgrade LidoLocator implementation",
        "4) Grant DEPOSITS_ENABLER_ROLE to Emergency Brakes Committee multisig",
        "5) Send Optimism L2 upgrade call: (a) upgrade L2TokenBridge; (b) finalize L2TokenBridge upgrade; (c) upgrade wstETH; (d) finalize wstETH upgrade",
    ]

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

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


# def startAndExecuteForForkUpgrade():
#     ACCOUNT_WITH_MONEY = "0x4200000000000000000000000000000000000023"
#     deployerAccount = get_deployer_account()

#     # Top up accounts
#     accountWithEth = accounts.at(ACCOUNT_WITH_MONEY, force=True)
#     accountWithEth.transfer(deployerAccount.address, "2 ethers")
#     accountWithEth.transfer(AGENT, "2 ethers")

#     tx_params = {"from": deployerAccount}
#     if get_is_live():
#         tx_params["priority_fee"] = get_priority_fee()

#     vote_id, _ = start_vote(tx_params=tx_params, silent=True)
#     vote_tx = Helpers.execute_vote(accounts, vote_id, contracts.voting)

#     print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

#     vote_id >= 0 and print(f"Vote created: {vote_id}.")

#     time.sleep(5)  # hack for waiting thread #2.


def check_pre_upgrade_state():
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    # Disabled deposits is the starting condition for the vote
    assert not l1_token_bridge.isDepositsEnabled()

    # L1 Bridge has old imbrownieplementation
    l1_token_bridge_implementation_address_before = l1_token_bridge_proxy.proxy__getImplementation()
    assert l1_token_bridge_implementation_address_before == L1_OPTIMISM_TOKENS_BRIDGE_IMPL, "Old address is incorrect"

    # L1 Bridge doesn't have version before update
    with brownie.reverts():
        l1_token_bridge.getContractVersion()

    # Upgrade LidoLocator implementation
    lido_locator_impl_before = lido_locator_proxy.proxy__getImplementation()
    assert lido_locator_impl_before == LIDO_LOCATOR_IMPL, "Old address is incorrect"

    # Multisig hasn't been assigned as deposit enabler
    assert not l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)


def check_post_upgrade_state(vote_tx):
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    # L1 Bridge has new implementation
    l1_token_bridge_implementation_address_after = l1_token_bridge_proxy.proxy__getImplementation()
    assert (
        l1_token_bridge_implementation_address_after == L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW
    ), "New address is incorrect"

    # update L1 Bridge to 2 version
    assert l1_token_bridge.getContractVersion() == 2

    # LidoLocator has new implementation
    lido_locator_impl_after = lido_locator_proxy.proxy__getImplementation()
    assert lido_locator_impl_after == LIDO_LOCATOR_IMPL_NEW, "New LidoLocator address is incorrect"

    # Multisig has been assigned as deposit enabler
    assert l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)
    # TODO: check multisig can renounce the role

    # Check bytecode that was send to messenger to update L2 bridge and wstETH token
    sentMessage = vote_tx.events["SentMessage"]["message"]
    encoded_l2_upgrade_call = encode_l2_upgrade_call(
        L2_OPTIMISM_TOKENS_BRIDGE,
        L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
        L2_OPTIMISM_WSTETH_TOKEN,
        L2_OPTIMISM_WSTETH_IMPL_NEW,
    )
    assert sentMessage == encoded_l2_upgrade_call
