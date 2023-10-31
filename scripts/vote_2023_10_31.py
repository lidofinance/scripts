"""
Voting 31/10/2023.

I. stETH transfers to  RCC PML ATC
1. Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
2. Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
3. Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956

II. Change the on-chain name of node operator with id 27 from 'Prysmatic Labs' to 'Prysm Team at Offchain Labs'


"""

import time

from typing import Dict
from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_permission_revoke, encode_permission_grant
from utils.node_operators import encode_set_node_operator_name
from utils.finance import make_steth_payout
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)

description = """
### Omnibus on-chain vote contains:

Two motions to **optimize [Lido Contributors Group's multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069) funding operations by [upgrading the Easy Track setup](https://research.lido.fi/t/updating-the-easy-track-setups-to-allow-dai-usdt-usdc-payments-for-lido-contributors-group/5738)**, allowing it to work with DAI, USDT, USDC instead of DAI-only.

1. Grant to `EVMScripExecutor` the permissions to transfer USDT and USDC in addition to current ETH, stETH, LDO, and DAI. Items 1,2.
2. Switch the Easy Track DAI top-up setup to the Easy Track DAI, USDT, and USDC top-up setup for all [Lido Contributors Group multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069) ([RCC](https://app.safe.global/settings/setup?safe=eth:0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437), [PML](https://app.safe.global/settings/setup?safe=eth:0x17F6b2C738a63a8D3A113a228cfd0b373244633D), and [ATC](https://app.safe.global/settings/setup?safe=eth:0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956)). Items 3-8.

The new version of contracts was [audited by Oxorio](LINK_TO_AUDIT).

And last motion is

3. **stETH transfer to the [Lido Contributor's Group multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069)** ([RCC](https://app.safe.global/settings/setup?safe=eth:0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437), [PML](https://app.safe.global/settings/setup?safe=eth:0x17F6b2C738a63a8D3A113a228cfd0b373244633D), and [ATC](https://app.safe.global/settings/setup?safe=eth:0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956)), as previously [requested on the forum](https://research.lido.fi/t/lido-v2-may-1-2023-december-31-2023-lido-ongoing-grant-request/4476/11). Items 9-11.
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
    pml_multisig_address = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
    atc_multisig_address = "0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956"

    NO_registry = interface.NodeOperatorsRegistry(contracts.node_operators_registry)
    prysmatic_labs_node_id = 27
    prysmatic_labs_node_new_name = "Prysm Team at Offchain Labs"

    call_script_items = [
        # I. stETH transfers to RCC PML ATC
        # 1. Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_steth_payout(
            target_address=rcc_multisig_address,
            steth_in_wei=1 * (10**18),
            reference="Fund RCC multisig"
        ),
        # 2. Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
        make_steth_payout(
            target_address=pml_multisig_address,
            steth_in_wei=1 * (10**18),
            reference="Fund PML multisig"
        ),
        # 3. Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956
        make_steth_payout(
            target_address=atc_multisig_address,
            steth_in_wei=1 * (10**18),
            reference="Fund ATC multisig"
        ),
        # II. Change the on-chain name of node operator with id 27 from 'Prysmatic Labs' to 'Prysm Team at Offchain Labs'
        # 4. Grant NodeOperatorsRegistry.MANAGE_NODE_OPERATOR_ROLE to voting
        encode_permission_grant(
            target_app=NO_registry,
            permission_name="MANAGE_NODE_OPERATOR_ROLE",
            grant_to=contracts.voting
        ),
        # 5. Change node operator #27 name from `Prysmatic Labs` to `Prysm Team at Offchain Labs`
        encode_set_node_operator_name(
            prysmatic_labs_node_id,
            prysmatic_labs_node_new_name,
            NO_registry
        ),
        # 6. Revoke MANAGE_NODE_OPERATOR_ROLE from Voting
        encode_permission_revoke(
            NO_registry,
            "MANAGE_NODE_OPERATOR_ROLE",
            revoke_from=contracts.voting
        )
    ]

    vote_desc_items = [
        f"1) Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
        f"2) Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
        f"3) Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956",
        f"4) Grant NodeOperatorsRegistry.MANAGE_NODE_OPERATOR_ROLE to voting",
        f"5) Change node operator name from Prysmatic Labs to Prysm Team at Offchain Labs",
        f"6) Revoke MANAGE_NODE_OPERATOR_ROLE from Voting",
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
