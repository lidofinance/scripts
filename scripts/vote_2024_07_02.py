"""
Voting 02/07/2024.

1. Set targetShare = 400 (4%) for Simple DVT Module
2. Transfer 180,000 LDO from Treasury to PML multisig (0x17F6b2C738a63a8D3A113a228cfd0b373244633D)
"""

import time

from typing import Dict
from brownie.network.transaction import TransactionReceipt

from configs.config_mainnet import SIMPLE_DVT_MODULE_ID, LDO_TOKEN, AGENT
from utils.agent import agent_forward
from utils.finance import make_ldo_payout
from utils.test.event_validators.payout import Payout
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    SIMPLE_DVT_MODULE_MODULE_FEE_BP,
    SIMPLE_DVT_MODULE_TREASURY_FEE_BP,
)

description = """
This vote follows a decisions made on snapshots:
 1. [Expanding the Simple DVT Module](https://snapshot.org/#/lido-snapshot.eth/proposal/0xaca2da3c932542e030db8bf5b6e4420bf4aa98bd57bd62b9b8008a4b7398abb2).
 2. [Vote for Hasu to join Lido as Strategic Advisor](https://snapshot.org/#/lido-snapshot.eth/proposal/0x84fe09312756471dd040e3cdaba112e822a2ae3dcf58ab8993e389e1b75e0831).

The proposed actions include:

1. Expand SimpleDVT share from 0.5% to 4%.  Item 1.
2. Transfer 180K LDO to PML multisig to do payments for Hasu. Items 2.
"""

# Values
new_SDVT_share = 400  # 4%

payout = Payout(
    token_addr=LDO_TOKEN,
    from_addr=AGENT,
    to_addr="0x17F6b2C738a63a8D3A113a228cfd0b373244633D",  # https://docs.lido.fi/multisigs/lido-contributors-group#41-pool-maintenance-labs-ltd-pml
    amount=180_000 * (10**18),  # 180K LDO in wei,
)


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Update Simple DVT module share to 4%
        #
        (
            "1) Expand SimpleDVT share from 0.5% to 4%",
            agent_forward(
                [
                    (
                        contracts.staking_router.address,
                        contracts.staking_router.updateStakingModule.encode_input(
                            SIMPLE_DVT_MODULE_ID,
                            new_SDVT_share,
                            SIMPLE_DVT_MODULE_MODULE_FEE_BP,
                            SIMPLE_DVT_MODULE_TREASURY_FEE_BP,
                        ),
                    ),
                ]
            ),
        ),
        #
        # II. Transfer 180,000 LDO from Treasury to PML multisig
        #
        (
            "2) Transfer 180,000 LDO from Treasury to PML multisig",
            make_ldo_payout(
                target_address=payout.to_addr,
                ldo_in_wei=payout.amount,
                reference="Transfer 180,000 LDO from Treasury to PML multisig",
            ),
        ),
    )

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
