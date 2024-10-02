"""
Voting 08/10/2024.

I. Upgrade Ethereum Contracts
1. Upgrade L1ERC20TokenBridge contract to implementation 0x168Cfea1Ad879d7032B3936eF3b0E90790b6B6D4
2. Call L1ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter
3. Upgrade Lido Locator contract to implementation 0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463
4. Grant permission DEPOSITS_ENABLER_ROLE to Ethereum Emergency Brakes Multisig

II. Upgrade Optimism Contracts
1. Send Optimism upgrade call:
    (a) Upgrade L2ERC20TokenBridge contract to implementation 0x2734602C0CEbbA68662552CacD5553370B283E2E
    (b) Call L2ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter
    (c) Upgrade WstETH ERC20Bridged contract to implementation 0xFe57042De76c8D6B1DF0E9E2047329fd3e2B7334
    (d) Call WstETH ERC20Bridged's finalizeUpgrade_v2() to update internal version counter

"""

import time
import eth_abi

from brownie import interface, web3, accounts
from brownie.exceptions import VirtualMachineError
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.agent import agent_forward
from utils.config import (
    AGENT,
    network_name,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    L1_EMERGENCY_BRAKES_MULTISIG,
    L1_OPTIMISM_CROSS_DOMAIN_MESSENGER,
    LIDO_LOCATOR,
    LIDO_LOCATOR_IMPL,
    LIDO_LOCATOR_IMPL_NEW,
    L1_OPTIMISM_TOKENS_BRIDGE,
    L1_OPTIMISM_TOKENS_BRIDGE_IMPL,
    L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
    L2_OPTIMISM_GOVERNANCE_EXECUTOR,
    L2_OPTIMISM_TOKENS_BRIDGE,
    L2_OPTIMISM_WSTETH_TOKEN,
    L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW,
    L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
)

DESCRIPTION = """

This vote follows a [Lido DAO decision on Snapshot](https://snapshot.org/#/lido-snapshot.eth/proposal/0xb1a3c33a4911712770c351504bac0499611ceb0faff248eacb1e96354f8e21e8) and [proposes to upgrade](https://research.lido.fi/t/lip-22-steth-on-l2/6855) the Lido bridge on the mainnet, introducing rebaseable stETH token on Optimism.
All audit reports can be found here: [MixBytes Audit Report](https://github.com/lidofinance/audits/blob/main/L2/stETH-on-Optimism-2024-06-MixBytes-Audit-Report.pdf), [Ackee Audit Report](https://github.com/lidofinance/audits/blob/main/L2/stETH-on-Optimism-2024-06-Ackee-Blockchain-Audit-report.pdf)

**Upgrade L1ERC20TokenBridge and L2ERC20TokenBridge** contracts

**Upgrade Lido Locator** contract implementation

**Grant permission** DEPOSITS_ENABLER_ROLE to Ethereum Emergency Brakes Multisig

**Upgrade WstETH ERC20Bridged** contract on Optimism implementation

"""

DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"

def encode_l2_upgrade_call(proxy1: str, new_impl1: str, proxy2: str, new_impl2: str):
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
        # I. Upgrade Ethereum Contracts

        # 1. Upgrade L1ERC20TokenBridge contract to implementation 0x168Cfea1Ad879d7032B3936eF3b0E90790b6B6D4
        agent_forward(
            [
                (
                    l1_token_bridge_as_proxy.address,
                    l1_token_bridge_as_proxy.proxy__upgradeTo.encode_input(L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW),
                )
            ]
        ),

        # 2. Call L1ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter
        agent_forward([(l1_token_bridge.address, l1_token_bridge.finalizeUpgrade_v2.encode_input())]),

        # 3. Upgrade Lido Locator contract to implementation 0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463"
        agent_forward(
            [
                (
                    lido_locator_as_proxy.address,
                    lido_locator_as_proxy.proxy__upgradeTo.encode_input(LIDO_LOCATOR_IMPL_NEW),
                )
            ]
        ),

        # 4. Grant permission DEPOSITS_ENABLER_ROLE to Ethereum Emergency Brakes Multisig
        agent_forward(
            [
                (
                    l1_token_bridge.address,
                    l1_token_bridge.grantRole.encode_input(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG),
                )
            ]
        ),

        # II. Upgrade Optimism Contracts
        # 1. Send Optimism upgrade call:
        #     (a) Upgrade L2ERC20TokenBridge contract to implementation 0x2734602C0CEbbA68662552CacD5553370B283E2E
        #     (b) Call L2ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter
        #     (c) Upgrade WstETH ERC20Bridged contract to implementation 0xFe57042De76c8D6B1DF0E9E2047329fd3e2B7334
        #     (d) Call WstETH ERC20Bridged's finalizeUpgrade_v2() to update internal version counter
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
                            L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW,
                        ),
                    ),
                )
            ]
        ),
    ]

    vote_desc_items = [
        "1) Upgrade L1ERC20TokenBridge contract to implementation 0x168Cfea1Ad879d7032B3936eF3b0E90790b6B6D4",
        "2) Call L1ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter",
        "3) Upgrade Lido Locator contract to implementation 0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463",
        "4) Grant permission DEPOSITS_ENABLER_ROLE to Ethereum Emergency Brakes Multisig",
        "5) Send Optimism upgrade call: (a) Upgrade L2ERC20TokenBridge contract to implementation 0x2734602C0CEbbA68662552CacD5553370B283E2E; (b) Call L2ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter; (c) Upgrade WstETH ERC20Bridged contract to implementation 0xFe57042De76c8D6B1DF0E9E2047329fd3e2B7334; (d) Call WstETH ERC20Bridged's finalizeUpgrade_v2() to update internal version counter;",
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

def check_pre_upgrade_state():
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    if network_name() in ("mainnet-fork") and l1_token_bridge.isDepositsEnabled():
        agent = accounts.at(AGENT, force=True)
        l1_token_bridge.disableDeposits({"from": agent})

    # Disabled deposits is the starting condition for the vote
    assert not l1_token_bridge.isDepositsEnabled()

    # L1 Bridge has old implementation
    assert l1_token_bridge_proxy.proxy__getImplementation() == L1_OPTIMISM_TOKENS_BRIDGE_IMPL, "Old address is incorrect"

    # L1 Bridge doesn't have version before update
    try:
        l1_token_bridge.getContractVersion()
    except VirtualMachineError:
        pass

    # Upgrade LidoLocator implementation
    assert lido_locator_proxy.proxy__getImplementation() == LIDO_LOCATOR_IMPL, "Old address is incorrect"

    # Multisig hasn't been assigned as deposit enabler
    assert not l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)

def check_post_upgrade_state(vote_tx):
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    # L1 Bridge has new implementation
    assert (
        l1_token_bridge_proxy.proxy__getImplementation() == L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW
    ), "New address is incorrect"

    # update L1 Bridge to 2 version
    assert l1_token_bridge.getContractVersion() == 2

    # check deposits are still paused
    assert not l1_token_bridge.isDepositsEnabled()

    # LidoLocator has new implementation
    assert lido_locator_proxy.proxy__getImplementation() == LIDO_LOCATOR_IMPL_NEW, "New LidoLocator address is incorrect"

    # Multisig has been assigned as deposit enabler
    assert l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)

    # Check bytecode that was sent to messenger to update L2 bridge and wstETH token
    sentMessage = vote_tx.events["SentMessage"]["message"]
    encoded_l2_upgrade_call = encode_l2_upgrade_call(
        L2_OPTIMISM_TOKENS_BRIDGE,
        L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
        L2_OPTIMISM_WSTETH_TOKEN,
        L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW,
    )
    assert sentMessage == encoded_l2_upgrade_call



