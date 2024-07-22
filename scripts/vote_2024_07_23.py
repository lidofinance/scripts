"""
Voting 23/07/2024.

1. Set targetShare = 400 (4%) for Simple DVT Module
2. Transfer 96,666.62 LDO from Treasury to PML multisig (0x17F6b2C738a63a8D3A113a228cfd0b373244633D)

Vote #175, initiated on 02/07/2024, did not reach a quorum.
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
1. **Expanding the Simple DVT Module:** Increase the Simple DVT module's staking share limit from 0.5% to 4%, as decided in the [Snapshot vote](https://snapshot.org/#/lido-snapshot.eth/proposal/0xaca2da3c932542e030db8bf5b6e4420bf4aa98bd57bd62b9b8008a4b7398abb2).

2. **Lido Contributors Group Funding:** Transfer 180,000 LDO within the [EGG st2024 v2 Grant Funding](https://snapshot.org/#/lido-snapshot.eth/proposal/0x2baf3275d15a8494ff94fef58d93bedd2fc28bfea8519f7e86474fc72dc25076) to the [PML multisig](https://app.safe.global/settings/setup?safe=eth:0x17F6b2C738a63a8D3A113a228cfd0b373244633D).
"""

# Values
new_SDVT_share = 400  # 4%
payout = Payout(
    token_addr=LDO_TOKEN,
    from_addr=AGENT,
    to_addr="0x17F6b2C738a63a8D3A113a228cfd0b373244633D",  # https://docs.lido.fi/multisigs/lido-contributors-group#41-pool-maintenance-labs-ltd-pml
    amount=180_000 * (10**18),  # 180000 LDO in wei
)


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Update Simple DVT module target share to 4%
        #
        (
            "1) Set Simple DVT Module targetShare to 400 (4%)",
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
        # II. Transfer 96,666.62 LDO from Treasury to PML multisig
        #
        (
            "2) Transfer 96,666.62 LDO from Treasury to PML multisig",
            make_ldo_payout(
                target_address=payout.to_addr,
                ldo_in_wei=payout.amount,
                reference="Transfer 96,666.62 LDO from Treasury to PML multisig",
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
