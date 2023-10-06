"""
Voting 03/10/2023.

1. Add node operator A41 with reward address `0x2A64944eBFaFF8b6A0d07B222D3d83ac29c241a7`
2. Add node operator Develp GmbH with reward address `0x0a6a0b60fFeF196113b3530781df6e747DdC565e`
3. Add node operator Ebunker with reward address `0x2A2245d1f47430b9f60adCFC63D158021E80A728`
4. Add node operator Gateway.fm AS with reward address `0x78CEE97C23560279909c0215e084dB293F036774`
5. Add node operator Numic with reward address `0x0209a89b6d9F707c14eB6cD4C3Fb519280a7E1AC`
6. Add node operator ParaFi Technologies LLC with reward address `0x5Ee590eFfdf9456d5666002fBa05fbA8C3752CB7`
7. Add node operator RockawayX Infra with reward address `0xcA6817DAb36850D58375A10c78703CE49d41D25a`
8. Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent
9. Set Jump Crypto targetValidatorsLimits to 0
10. Update Anchor Vault implementation from `0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171` to `0x9530708033E7262bD7c005d0e0D47D8A9184277d`

Vote passed & executed on Oct-06-2023 06:51:23 PM +UTC, block 18293362

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward
from utils.node_operators import encode_add_operator_lido
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
)

description = """
### Omnibus on-chain vote contains 3 motions:
1. **Onboard seven new Node Operators to the Lido on Ethereum Node Operator Set**. NOs addresses and verifications can be found on the [Research forum](https://research.lido.fi/t/announcement-onboarding-for-ethereum-wave-5/4809/17). The snapshot link is [here](https://snapshot.org/#/lido-snapshot.eth/proposal/0x780d8397c4325757f3506c35274da47c87727fb15dd592e8c4455de92bf2de27). Items 1-7.

2. Support **Jump Crypto voluntarily exit from the Node Operator Set** by setting `targetValidatorsCount` to 0. The algorithm would prioritize exiting Jump Crypto validators to fulfil users' withdrawal requests. Jump Crypto request is [on the forum](https://research.lido.fi/t/lido-dao-proposal-to-set-targetvalidatorscount-for-jump-crypto-operator-to-0-to-wind-down-the-jump-crypto-legacy-set/5259). Items 8,9.

3. **Anchor Sunset**.
[Snapshot](https://snapshot.org/#/lido-snapshot.eth/proposal/0xe964fb2b0ad887673a0748b025c68a957a4b05b604d306bdc66125e7b758e524) to discontinue the stETH <> bETH Anchor integration passed on Jun 22, 2022. And tech details of the upgrade were provided on the [Research forum](https://research.lido.fi/t/anchor-vault-upgrade-on-chain-voting-announcement/5538) on Sep 23, 2023. The code was [reviewed by statemind.io](https://research.lido.fi/t/anchor-vault-upgrade-on-chain-voting-announcement/5538/2). Item 10.
"""


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # Vote specific addresses and constants:
    a41_node_operator = {
        "name": "A41",
        "address": "0x2A64944eBFaFF8b6A0d07B222D3d83ac29c241a7",
    }
    develp_node_operator = {
        "name": "Develp GmbH",
        "address": "0x0a6a0b60fFeF196113b3530781df6e747DdC565e",
    }
    ebunker_node_operator = {
        "name": "Ebunker",
        "address": "0x2A2245d1f47430b9f60adCFC63D158021E80A728",
    }
    gatewayfm_node_operator = {
        "name": "Gateway.fm AS",
        "address": "0x78CEE97C23560279909c0215e084dB293F036774",
    }
    numic_node_operator = {
        "name": "Numic",
        "address": "0x0209a89b6d9F707c14eB6cD4C3Fb519280a7E1AC",
    }
    parafi_node_operator = {
        "name": "ParaFi Technologies LLC",
        "address": "0x5Ee590eFfdf9456d5666002fBa05fbA8C3752CB7",
    }
    rockawayx_node_operator = {
        "name": "RockawayX Infra",
        "address": "0xcA6817DAb36850D58375A10c78703CE49d41D25a",
    }

    # web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    # contracts.node_operators_registry.getNodeOperator(1, True)
    JUMP_CRYPTO_ID = 1

    # tx: https://etherscan.io/tx/0x99caa0eb5c081814135e9d375e7858682516195da084d1ed225b0ee1a4c5cfb1
    ANCHOR_NEW_IMPL_ADDRESS = "0x9530708033E7262bD7c005d0e0D47D8A9184277d"

    # anchor vault finalize
    setup_calldata = contracts.anchor_vault.finalize_upgrade_v4.encode_input()

    call_script_items = [
        # I. Lido on ETH NOs onboarding (wave 5 st2)
        ## 1. Add node operator A41
        agent_forward([encode_add_operator_lido(**a41_node_operator)]),
        ## 2. Add node operator Develp GmbH
        agent_forward([encode_add_operator_lido(**develp_node_operator)]),
        ## 3. Add node operator Ebunker
        agent_forward([encode_add_operator_lido(**ebunker_node_operator)]),
        ## 4. Add node operator Gateway.fm AS
        agent_forward([encode_add_operator_lido(**gatewayfm_node_operator)]),
        ## 5. Add node operator Numic
        agent_forward([encode_add_operator_lido(**numic_node_operator)]),
        ## 6. Add node operator ParaFi Technologies LLC
        agent_forward([encode_add_operator_lido(**parafi_node_operator)]),
        ## 7. Add node operator RockawayX Infra
        agent_forward([encode_add_operator_lido(**rockawayx_node_operator)]),
        # II. Support Jump Crypto voluntarily exits from the validator set
        ## 8. Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.grantRole.encode_input(
                        STAKING_MODULE_MANAGE_ROLE, contracts.agent.address
                    ),
                )
            ]
        ),
        ## 9. Set Jump Crypto targetValidatorsCount to 0
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.updateTargetValidatorsLimits.encode_input(1, JUMP_CRYPTO_ID, True, 0),
                )
            ]
        ),
        # III. Anchor sunset
        ## 10. Update Anchor Vault implementation
        agent_forward(
            [
                (
                    contracts.anchor_vault_proxy.address,
                    contracts.anchor_vault_proxy.proxy_upgradeTo.encode_input(ANCHOR_NEW_IMPL_ADDRESS, setup_calldata),
                )
            ]
        ),
    ]

    vote_desc_items = [
        "1) Add node operator A41 with reward address `0x2A64944eBFaFF8b6A0d07B222D3d83ac29c241a7`",
        "2) Add node operator Develp GmbH with reward address `0x0a6a0b60fFeF196113b3530781df6e747DdC565e`",
        "3) Add node operator Ebunker with reward address `0x2A2245d1f47430b9f60adCFC63D158021E80A728`",
        "4) Add node operator Gateway.fm AS with reward address `0x78CEE97C23560279909c0215e084dB293F036774`",
        "5) Add node operator Numic with reward address `0x0209a89b6d9F707c14eB6cD4C3Fb519280a7E1AC`",
        "6) Add node operator ParaFi Technologies LLC with reward address `0x5Ee590eFfdf9456d5666002fBa05fbA8C3752CB7`",
        "7) Add node operator RockawayX Infra with reward address `0xcA6817DAb36850D58375A10c78703CE49d41D25a`",
        "8) Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent",
        "9) Set Jump Crypto targetValidatorsLimits to 0",
        "10) Update Anchor Vault implementation from `0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171` to `0x9530708033E7262bD7c005d0e0D47D8A9184277d`",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

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
