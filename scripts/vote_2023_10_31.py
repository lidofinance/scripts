"""
Voting 31/10/2023.

"""

import time

from typing import Dict
from brownie.network.transaction import TransactionReceipt
from brownie import interface
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.easy_track import add_evmscript_factory, create_permissions, remove_evmscript_factory

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
)


description = """
### Omnibus on-chain vote contains 3 motions:

1. Switch off TopUp ETs for RCC PML ACT
2. Switch on TopUpStable ETs for RCC PML ACT

"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    rcc_dai_topup_factory_old = interface.IEVMScriptFactory("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_dai_topup_factory_old = interface.IEVMScriptFactory("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_dai_topup_factory_old = interface.IEVMScriptFactory("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    call_script_items = [
        # 1. Switch off TopUp ETs for RCC PML ACT

        ## 1. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
        remove_evmscript_factory(factory=rcc_dai_topup_factory_old),
        ## 2. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
        remove_evmscript_factory(factory=pml_dai_topup_factory_old),
        ## 3. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
        remove_evmscript_factory(factory=atc_dai_topup_factory_old),

        # 2. Switch on TopUpStable ETs for RCC PML ACT
    ]

    vote_desc_items = [
        f"1) Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track",
        f"2) Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track",
        f"3) Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track",
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
