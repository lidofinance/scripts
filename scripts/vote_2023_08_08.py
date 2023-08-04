"""
Voting 08/08/2023.

1. Add Rewards Share Program top up EVM script factory 0xbD08f9D6BF1D25Cc7407E4855dF1d46C2043B3Ea
2. Add Rewards Share Program add recipient EVM script factory 0x1F809D2cb72a5Ab13778811742050eDa876129b6
3. Add Rewards Share Program remove recipient EVM script factory 0xd30Dc38EdEfc21875257e8A3123503075226E14B
4. Add Launchnodes Limited node operator with reward address 0x................
5. Add SenseiNode Inc node operator with reward address 0x................
6. Set 3.1531 stETH as the allowance of Burner over the Agent's tokens
7. Grant REQUEST_BURN_MY_STETH_ROLE to Agent
8. Request to burn 3.1531 stETH for cover
"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.agent import agent_forward
from utils.node_operators import encode_add_operator_lido

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
)

from utils.easy_track import add_evmscript_factory, create_permissions


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """ ET factories """
    rewards_share_topup_factory = interface.TopUpAllowedRecipients("0xbD08f9D6BF1D25Cc7407E4855dF1d46C2043B3Ea")
    rewards_share_add_recipient_factory = interface.AddAllowedRecipient("0x1F809D2cb72a5Ab13778811742050eDa876129b6")
    rewards_share_remove_recipient_factory = interface.RemoveAllowedRecipient("0xd30Dc38EdEfc21875257e8A3123503075226E14B")
    rewards_share_registry = interface.AllowedRecipientRegistry("0xdc7300622948a7AdaF339783F6991F9cdDD79776")

    """ Wave 5 NOs """
    launchnodes_limited_node_operator = {
        "name": "New op #1",
        "address": "0x0000000000000000000000000000000000000000",
    }
    senseinode_node_operator = {
        "name": "New op #2",
        "address": "0x0000000000000000000000000000000000000000",
    }

    """ Burning 3,1531 stETH """
    stETH_to_burn = ETH(3.1531)
    REQUEST_BURN_MY_STETH_ROLE = "0x28186f938b759084eea36948ef1cd8b40ec8790a98d5f1a09b70879fe054e5cc"

    call_script_items = [
        # 1. Add Rewards Share Program top up EVM script factory 0xbD08f9D6BF1D25Cc7407E4855dF1d46C2043B3Ea
        add_evmscript_factory(
            factory=rewards_share_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rewards_share_registry, "updateSpentAmount")[2:],
        ),
        # 2. Add Rewards Share Program add recipient EVM script factory 0x1F809D2cb72a5Ab13778811742050eDa876129b6
        add_evmscript_factory(
            factory=rewards_share_add_recipient_factory,
            permissions=create_permissions(rewards_share_registry, "addRecipient"),
        ),
        # 3. Add Rewards Share Program remove recipient EVM script factory 0xd30Dc38EdEfc21875257e8A3123503075226E14B
        add_evmscript_factory(
            factory=rewards_share_remove_recipient_factory,
            permissions=create_permissions(rewards_share_registry, "removeRecipient"),
        ),
        # 4. Add Launchnodes Limited node operator with reward address 0x................
        encode_add_operator_lido(**launchnodes_limited_node_operator),
        # 5. Add SenseiNode Inc node operator with reward address 0x................
        encode_add_operator_lido(**senseinode_node_operator),
        # 6. Set 3.1531 stETH as the allowance of Burner over the Agent's tokens
        agent_forward(
            [
                (
                    contracts.lido.address,
                    contracts.lido.approve.encode_input(contracts.burner.address, stETH_to_burn),
                )
            ]
        ),
        # 7. Grant REQUEST_BURN_MY_STETH_ROLE to Agent
        agent_forward(
            [
                (
                    contracts.burner.address,
                    contracts.burner.grantRole.encode_input(REQUEST_BURN_MY_STETH_ROLE, contracts.agent.address),
                )
            ]
        ),
        # 8. Request to burn 3.1531 stETH for cover
        agent_forward(
            [
                (
                    contracts.burner.address,
                    contracts.burner.requestBurnMyStETHForCover.encode_input(stETH_to_burn),
                )
            ]
        ),
    ]

    vote_desc_items = [
        "1) Add Rewards Share Program top up EVM script factory 0xbD08f9D6BF1D25Cc7407E4855dF1d46C2043B3Ea",
        "2) Add Rewards Share Program add recipient EVM script factory 0x1F809D2cb72a5Ab13778811742050eDa876129b6",
        "3) Add Rewards Share Program remove recipient EVM script factory 0xd30Dc38EdEfc21875257e8A3123503075226E14B",
        "4) Add Launchnodes Limited node operator with reward address 0x................",
        "5) Add SenseiNode Inc node operator with reward address 0x................",
        "6) Set 3.1531 stETH as the allowance of Burner over the Agent's tokens",
        "7) Grant REQUEST_BURN_MY_STETH_ROLE to Agent",
        "8) Request to burn 3.1531 stETH for cover",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
