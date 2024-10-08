"""
Voting 08/10/2024.

Ia. Upgrade Ethereum Contracts
1. Upgrade L1ERC20TokenBridge contract to implementation 0x168Cfea1Ad879d7032B3936eF3b0E90790b6B6D4
2. Call L1ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter
3. Upgrade Lido Locator contract to implementation 0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463
4. Grant permission DEPOSITS_ENABLER_ROLE to Ethereum Emergency Brakes Multisig 0x73b047fe6337183A454c5217241D780a932777bD

Ib. Upgrade Optimism Contracts
5. Send Optimism upgrade call:
    (a) Upgrade L2ERC20TokenBridge contract to implementation 0x2734602C0CEbbA68662552CacD5553370B283E2E
    (b) Call L2ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter
    (c) Upgrade WstETH ERC20Bridged contract to implementation 0xFe57042De76c8D6B1DF0E9E2047329fd3e2B7334
    (d) Call WstETH ERC20Bridged's finalizeUpgrade_v2() to update internal version counter and set the name and version for EIP5267

II. Add Easy Track setup for funding Lido Alliance Operational Multisig
6. Add Alliance Ops stablecoins top up EVM script factory 0xe5656eEe7eeD02bdE009d77C88247BC8271e26Eb (AllowedRecipientsRegistry 0x3B525F4c059F246Ca4aa995D21087204F30c9E2F)

"""

import time
import eth_abi

from brownie import interface, web3, accounts
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
    contracts,
    L1_EMERGENCY_BRAKES_MULTISIG,
    L1_OPTIMISM_CROSS_DOMAIN_MESSENGER,
    LIDO_LOCATOR,
    LIDO_LOCATOR_IMPL_NEW,
    L1_OPTIMISM_TOKENS_BRIDGE,
    L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
    L2_OPTIMISM_GOVERNANCE_EXECUTOR,
    L2_OPTIMISM_TOKENS_BRIDGE,
    L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
    L2_OPTIMISM_WSTETH_TOKEN,
    L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW,
)
from utils.easy_track import add_evmscript_factory, create_permissions


DESCRIPTION = """
1. Upgrade **wstETH on Optimism bridge endpoints** to enable **rebasable stETH** on Optimism alongside wstETH. Following [Snapshot vote](https://snapshot.org/#/lido-snapshot.eth/proposal/0xb1a3c33a4911712770c351504bac0499611ceb0faff248eacb1e96354f8e21e8) and proposed [action plan](https://research.lido.fi/t/steth-on-optimism-upgrade-announcement-and-action-plan/8474).
Solution audited by [MixBytes](https://github.com/lidofinance/audits/blob/main/L2/stETH-on-Optimism-2024-06-MixBytes-Audit-Report.pdf) and [Ackee Blockchain](https://github.com/lidofinance/audits/blob/main/L2/stETH-on-Optimism-2024-06-Ackee-Blockchain-Audit-report.pdf). Items 1-5.

2. Add **Easy Track setup** for funding the [Lido Alliance Operational Multisig](https://app.safe.global/transactions/queue?safe=eth:0x606f77BF3dd6Ed9790D9771C7003f269a385D942) following the [Lido DAO Snapshot decision](https://snapshot.org/#/lido-snapshot.eth/proposal/0xa478fa5518769096eda2b7403a1d4104ca47de3102e8a9abab8640ef1b50650c). Item 6.
"""

DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"

def encode_l2_upgrade_call(l2_token_bridge_proxy: str, l2_token_bridge_new_impl: str, l2_wst_token_proxy: str, l2_wst_token_new_impl: str):
    queue_definition = f"queue(address[],uint256[],string[],bytes[],bool[])"
    queue_selector = web3.keccak(text=queue_definition).hex()[:10]

    args_bytes = eth_abi.encode(
        ["address[]", "uint256[]", "string[]", "bytes[]", "bool[]"],
        [
            [l2_token_bridge_proxy, l2_token_bridge_proxy, l2_wst_token_proxy, l2_wst_token_proxy],
            [0, 0, 0, 0],
            [
                "proxy__upgradeTo(address)",
                "finalizeUpgrade_v2()",
                "proxy__upgradeTo(address)",
                "finalizeUpgrade_v2(string,string)",
            ],
            [
                eth_abi.encode(["address"], [l2_token_bridge_new_impl]),
                eth_abi.encode([], []),
                eth_abi.encode(["address"], [l2_wst_token_new_impl]),
                eth_abi.encode(["string", "string"], ["Wrapped liquid staked Ether 2.0", "2"]),
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

    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_as_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    l1_token_bridge_as_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)

    alliance_ops_registry = interface.AllowedRecipientRegistry("0x3B525F4c059F246Ca4aa995D21087204F30c9E2F")
    alliance_ops_topup_factory = interface.TopUpAllowedRecipients("0xe5656eEe7eeD02bdE009d77C88247BC8271e26Eb")

    if network_name() in ("mainnet-fork",) and l1_token_bridge.isDepositsEnabled():
        agent = accounts.at(AGENT, force=True)
        l1_token_bridge.disableDeposits({"from": agent})

    vote_desc_items, call_script_items = zip(
        # Ia. Upgrade Ethereum Contracts
        (
            "1) Upgrade L1ERC20TokenBridge contract to implementation 0x168Cfea1Ad879d7032B3936eF3b0E90790b6B6D4",
            agent_forward(
                [
                    (
                        l1_token_bridge_as_proxy.address,
                        l1_token_bridge_as_proxy.proxy__upgradeTo.encode_input(L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW),
                    )
                ]
            ),
        ),
        (
            "2) Call L1ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter",
            agent_forward([(l1_token_bridge.address, l1_token_bridge.finalizeUpgrade_v2.encode_input())]),
        ),
        (
            "3) Upgrade Lido Locator contract to implementation 0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463",
            agent_forward(
                [
                    (
                        lido_locator_as_proxy.address,
                        lido_locator_as_proxy.proxy__upgradeTo.encode_input(LIDO_LOCATOR_IMPL_NEW),
                    )
                ]
            ),
        ),
        (
            "4) Grant permission DEPOSITS_ENABLER_ROLE to Ethereum Emergency Brakes Multisig 0x73b047fe6337183A454c5217241D780a932777bD",
            agent_forward(
                [
                    (
                        l1_token_bridge.address,
                        l1_token_bridge.grantRole.encode_input(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG),
                    )
                ]
            ),
        ),
        # Ib. Upgrade Optimism Contracts
        (
            "5) Send Optimism upgrade call:"
            + " (a) Upgrade L2ERC20TokenBridge contract to implementation 0x2734602C0CEbbA68662552CacD5553370B283E2E;"
            + " (b) Call L2ERC20TokenBridge's finalizeUpgrade_v2() to update internal version counter;"
            + " (c) Upgrade WstETH ERC20Bridged contract to implementation 0xFe57042De76c8D6B1DF0E9E2047329fd3e2B7334;"
            + " (d) Call WstETH ERC20Bridged's finalizeUpgrade_v2() to update internal version counter and set the name and version for EIP5267;",
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
        ),
        #
        # II. Add Easy Track setup for funding Lido Alliance Operational Multisig
        #
        (
            "6) Add Alliance Ops stablecoins top up EVM script factory 0xe5656eEe7eeD02bdE009d77C88247BC8271e26Eb (AllowedRecipientsRegistry 0x3B525F4c059F246Ca4aa995D21087204F30c9E2F)",
            add_evmscript_factory(
                factory=alliance_ops_topup_factory,
                permissions=create_permissions(contracts.finance, "newImmediatePayment")
                            + create_permissions(alliance_ops_registry, "updateSpentAmount")[2:],
            )
        )
    )

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
