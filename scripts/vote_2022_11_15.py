"""
Voting 15/11/2022.

1. Send DAI 1,500,000 to Pool Maintenance Labs Ltd. 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
2. Send LDO 220,000 to Pool Maintenance Labs Ltd. 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
3. Send DAI 500,000 to Argo Technology Consulting Ltd. 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956
4. Send DAI 250,000 to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
5. Send LDO 177,726 to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import (
    get_deployer_account,
    get_is_live,
)
from utils.finance import make_ldo_payout, make_dai_payout
from utils.brownie_prelude import *

rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
pool_maintenance_labs_address = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
argo_technology_consulting_address = "0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956"

pool_maintenance_labs_dai = 1_500_000 * 10**18
pool_maintenance_labs_ldo = 220_000 * 10**18
argo_technology_consulting_dai = 500_000 * 10**18
rcc_dai = 250_000 * 10**18
rcc_ldo = 177_726 * 10**18


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items = [
        # 1. Send DAI 1,500,000 to Pool Maintenance Labs Ltd. 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
        make_dai_payout(
            target_address=pool_maintenance_labs_address,
            dai_in_wei=pool_maintenance_labs_dai,
            reference="Initial DAI funding Pool Maintenance Labs Ltd. within Nov'22-Apr'23 budget",
        ),
        # 2. Send LDO 220,000 to Pool Maintenance Labs Ltd. 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
        make_ldo_payout(
            target_address=pool_maintenance_labs_address,
            ldo_in_wei=pool_maintenance_labs_ldo,
            reference="Initial LDO funding Pool Maintenance Labs Ltd. within Nov'22-Apr'23 budget",
        ),
        # 3. Send DAI 500,000 to Argo Technology Consulting Ltd. 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956
        make_dai_payout(
            target_address=argo_technology_consulting_address,
            dai_in_wei=argo_technology_consulting_dai,
            reference="Initial DAI funding Argo Technology Consulting Ltd. within Nov'22-Apr'23 budget",
        ),
        # 4. Send DAI 250,000 to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_dai_payout(
            target_address=rcc_multisig_address,
            dai_in_wei=rcc_dai,
            reference="Initial DAI funding RCC multisig within Nov'22-Apr'23 budget",
        ),
        # 5. Send LDO 177,726 to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_ldo_payout(
            target_address=rcc_multisig_address,
            ldo_in_wei=rcc_ldo,
            reference="Initial LDO funding RCC multisig within Nov'22-Apr'23 budget",
        ),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Send DAI 1,500,000 to Pool Maintenance Labs Ltd. 0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
        "2) Send LDO 220,000 to Pool Maintenance Labs Ltd. 0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
        "3) Send DAI 500,000 to Argo Technology Consulting Ltd. 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956",
        "4) Send DAI 250,000 to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
        "5) Send LDO 177,726 to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "100 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
