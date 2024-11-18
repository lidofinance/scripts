"""
Voting 26/11/2024.

I. Change the limits for ET on ATC & PML
1. ATC: increase from 1,5m per quarter to 7m USDC/USDT/DAI per quarter - set 7'000'000 limit on ATC registry `0xe07305F43B11F230EaA951002F6a55a16419B707` for 3 mos
2. PML: decrease from 6m per quarter to 4m USDC/USDT/DAI per quarter - set 4'000'000 limit on PML registry `0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB` for 3 mos

II. TMC limits update
3. Update TMC limit to 12,000 stETH on TMC registry `0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0` for 6 mos
4. Reset the TMC amount spent on TMC registry `0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0`

III. Simply staking reward address change
5. Change staking reward address to `0x1EC3Cbe8fb1D8019092500CcA2111C158a35bC82` for node operator with id = 16

Vote passed & executed on XXX-XX-XXXX XX:XX:XX PM UTC, block #XXXXXXXX.
"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.permission_parameters import Param, SpecialArgumentID, ArgumentValue, Op
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.node_operators import encode_set_node_operator_reward_address

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
)

from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
    remove_evmscript_factory
)
from utils.allowed_recipients_registry import (
    set_limit_parameters,
    update_spent_amount,
    unsafe_set_spent_amount
)

from utils.agent import agent_forward

description = """
I. Change the limits for ET on ATC & PML
1. ATC: increase from 1,5m per quarter to 7m USDC/USDT/DAI per quarter - set 7'000'000 limit on ATC registry `0xe07305F43B11F230EaA951002F6a55a16419B707` for 3 mos
2. PML: decrease from 6m per quarter to 4m USDC/USDT/DAI per quarter - set 4'000'000 limit on PML registry `0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB` for 3 mos

II. TMC limits update
3. Update TMC limit to 12,000 stETH on TMC registry `0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0` for 6 mos
4. Reset the TMC amount spent on TMC registry `0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0`

III. Simply staking reward address change
5. Change staking reward address to `0x1EC3Cbe8fb1D8019092500CcA2111C158a35bC82` for node operator with id = 16
"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    atc_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")
    pml_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")

    tmc_registry = interface.AllowedRecipientRegistry("0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0")

    NO_registry = contracts.node_operators_registry
    simply_staking_id = 16
    simply_staking_new_reward_address = "0x1EC3Cbe8fb1D8019092500CcA2111C158a35bC82"

    vote_desc_items, call_script_items = zip(
        #
        # I. Change the limits for ET on ATC & PML
        #
        (
            "1. Set 7'000'000 limit on ATC registry `0xe07305F43B11F230EaA951002F6a55a16419B707` for 3 mos",
            agent_forward(
                [
                set_limit_parameters(
                    registry_address=atc_registry,
                    limit=7_000_000 * 10 ** 18,
                    period_duration_months=3
                ),
                ]
            ),
        ),
        (
            "2. Set 4'000'000 limit on PML registry `0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB` for 3 mos",
            agent_forward(
                [
                set_limit_parameters(
                    registry_address=pml_registry,
                    limit=4_000_000 * 10 ** 18,
                    period_duration_months=3
                ),
                ]
            ),
        ),
        #
        # II. TMC limits update
        #
        (
            "3. Update TMC limit to 12,000 stETH on TMC registry `0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0` for 6 mos",
            agent_forward(
                [
                set_limit_parameters(
                    registry_address=tmc_registry,
                    limit=12_000 * 10 ** 18,
                    period_duration_months=6
                ),
                ]
            ),
        ),
        (
            "4. Reset the TMC amount spent on TMC registry `0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0`",
            agent_forward(
                [
                unsafe_set_spent_amount(
                    spent_amount=0,
                    registry_address=tmc_registry
                ),
                ]
            ),
        ),
        #
        # III. Simply staking reward address change
        #
        (
            "5. Change staking reward address to `0x1EC3Cbe8fb1D8019092500CcA2111C158a35bC82` for node operator with id = 16",
            agent_forward(
                [
                encode_set_node_operator_reward_address(
                    simply_staking_id,
                    simply_staking_new_reward_address,
                    NO_registry
                ),
                ]
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