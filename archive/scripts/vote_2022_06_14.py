"""
Voting 14/06/2022.

1. Revoke DEPOSIT_ROLE from old DepositSecurityModule 0xDb149235B6F40dC08810AA69869783Be101790e7
2. Grant DEPOSIT_ROLE to new DepositSecurityModule 0x710B3303fB508a84F10793c1106e32bE873C24cd
3. Set lastDepositBlock of DepositSecurityModule to 14985614

Vote passed & executed on Jun-17-2022 05:12:00 PM +UTC, block 14980329.

"""
# noinspection PyUnresolvedReferences

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import web3

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward
from utils.config import get_deployer_account, get_is_live, contracts
from utils.permissions import encode_permission_grant, encode_permission_revoke
from utils.brownie_prelude import *


def encode_set_last_deposit_block(new_dsm_address: str, last_deposit_block: int) -> Tuple[str, str]:
    deposit_security_module = interface.DepositSecurityModule(new_dsm_address)

    return agent_forward(
        [
            (
                deposit_security_module.address,
                deposit_security_module.setLastDepositBlock.encode_input(last_deposit_block),
            )
        ]
    )


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    lido: interface.Lido = contracts.lido

    current_deposit_security_module_address = "0xDb149235B6F40dC08810AA69869783Be101790e7"
    proposed_deposit_security_module_address = "0x710B3303fB508a84F10793c1106e32bE873C24cd"
    last_deposit_block: int = 14985614

    call_script_items = [
        # 1. Revoke DEPOSIT_ROLE from the old DepositSecurityModule
        encode_permission_revoke(
            target_app=lido,
            permission_name="DEPOSIT_ROLE",
            revoke_from=current_deposit_security_module_address,
        ),
        # 2. Grant DEPOSIT_ROLE to the new DepositSecurityModule
        encode_permission_grant(
            target_app=lido,
            permission_name="DEPOSIT_ROLE",
            grant_to=proposed_deposit_security_module_address,
        ),
        # 3. Set lastDepositBlock of DepositSecurityModule to 14985614
        encode_set_last_deposit_block(proposed_deposit_security_module_address, last_deposit_block),
    ]

    vote_desc_items = [
        "1) Revoke DEPOSIT_ROLE from the old DepositSecurityModule",
        "2) Grant DEPOSIT_ROLE to the new DepositSecurityModule",
        "3) Set lastDepositBlock of DepositSecurityModule to 14985614",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
