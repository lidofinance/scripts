"""
Voting 03/10/2023.

1. Add node operator 'A41' with reward address `0x2A64944eBFaFF8b6A0d07B222D3d83ac29c241a7`
2. Add node operator TBA with reward address TBA
3. Add node operator TBA with reward address TBA
4. Add node operator TBA with reward address TBA
5. Add node operator TBA with reward address TBA
6. Add node operator TBA with reward address TBA
7. Add node operator TBA with reward address TBA
8. Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent
9. Set Jump Crypto targetValidatorsLimits to 0
10. Update Anchor Vault implementation from `0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171` to TBA

Vote passed & executed on #, block #
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward
from utils.node_operators import encode_add_operator_lido

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
)


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # Vote specific addresses and constants:
    # Add node operator named A41
    a41_node_operator = {
        "name": "A41",
        "address": "0x2A64944eBFaFF8b6A0d07B222D3d83ac29c241a7",
    }
    # 6 more

    # web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    # contracts.node_operators_registry.getNodeOperator(1, True)
    JUMP_CRYPTO_ID = 1

    ANCHOR_NEW_IMPL_ADDRESS = "#TBA"

    # anchor vault finalize
    setup_calldata = contracts.anchor_vault.finalize_upgrade_v4.encode_input()

    call_script_items = [
        # I. Lido on ETH NOs onboarding (wave 5 st2)
        ## 1. Add node operator named A41
        encode_add_operator_lido(**a41_node_operator),
        ## 6 more
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
        # agent_forward(
        #     [
        #         (
        #             contracts.anchor_vault_proxy.address,
        #             contracts.anchor_vault_proxy.proxy_upgradeTo.encode_input(ANCHOR_NEW_IMPL_ADDRESS, setup_calldata),
        #         )
        #     ]
        # ),
    ]

    vote_desc_items = [
        "1) Add A41 node operator",
        # 6 more
        "8) Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent",
        "9) Set Jump Crypto targetValidatorsLimits to 0",
        # "10) Update Anchor Vault implementation from 0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171 to #TBA",
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
