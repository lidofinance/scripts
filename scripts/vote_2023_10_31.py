"""
Voting 31/10/2023.

I. stETH transfers to  RCC PML ATC
1. Transfer 279 stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
2. Transfer 447 stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
3. Transfer 391 stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956

II. Change the on-chain name of node operator with id 27 from 'Prysmatic Labs' to 'Prysm Team at Offchain Labs'
4. Change node operator name from Prysmatic Labs to Prysm Team at Offchain Labs

"""

import time

from typing import Dict
from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
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

1. stETH transfer to the [Lido Contributors Group multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069) ([RCC](https://app.safe.global/settings/setup?safe=eth:0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437), [PML](https://app.safe.global/settings/setup?safe=eth:0x17F6b2C738a63a8D3A113a228cfd0b373244633D), and [ATC](https://app.safe.global/settings/setup?safe=eth:0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956)), as previously [requested on the forum](https://research.lido.fi/t/lido-v2-may-1-2023-december-31-2023-lido-ongoing-grant-request/4476/11). Items 1-3.
2. Changing the Node Operator's (#id - 27) name, as [requested on the forum](https://research.lido.fi/t/node-operator-registry-name-reward-address-change/4170/16). Item 4.
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
        # 1. Transfer 279 stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_steth_payout(
            target_address=rcc_multisig_address,
            steth_in_wei=279 * (10**18),
            reference="Fund RCC multisig"
        ),
        # 2. Transfer 447 stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
        make_steth_payout(
            target_address=pml_multisig_address,
            steth_in_wei=447 * (10**18),
            reference="Fund PML multisig"
        ),
        # 3. Transfer 391 stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956
        make_steth_payout(
            target_address=atc_multisig_address,
            steth_in_wei=391 * (10**18),
            reference="Fund ATC multisig"
        ),
        # II. Change the on-chain name of node operator with id 27 from 'Prysmatic Labs' to 'Prysm Team at Offchain Labs'
        # 4. Change node operator #27 name from `Prysmatic Labs` to `Prysm Team at Offchain Labs`
        agent_forward([
                encode_set_node_operator_name(
                    prysmatic_labs_node_id,
                    prysmatic_labs_node_new_name,
                    NO_registry
            )
        ])
    ]

    vote_desc_items = [
        f"1) Transfer 279 stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
        f"2) Transfer 447 stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
        f"3) Transfer 391 stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956",
        f"4) Change the on-chain name of node operator with id 27 from 'Prysmatic Labs' to 'Prysm Team at Offchain Labs'",
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
