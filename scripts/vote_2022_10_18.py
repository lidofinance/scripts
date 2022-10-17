"""
Voting 18/10/2022.

1. Change Insurance address to `0x8B3f33234ABD88493c0Cd28De33D583B70beDe35`
2. Send 5466.46 shares of stETH to Insurance Fund at `0x8B3f33234ABD88493c0Cd28De33D583B70beDe35`
3. Revoke `ASSIGN_ROLE` from the LDO purchase executor contract at `0xA9b2F5ce3aAE7374a62313473a74C98baa7fa70E`

"""
import time
from typing import Dict, Optional, Tuple

from brownie.network.transaction import TransactionReceipt
from utils.permissions import encode_permission_revoke
from utils.agent import agent_forward

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.brownie_prelude import *
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    lido_dao_token_manager_address,
)


INSURANCE_FUND_ADDRESS = "0x8B3f33234ABD88493c0Cd28De33D583B70beDe35"
INSURANCE_SHARES = 546646 * 10**16
LDO_PURCHASE_EXECUTOR = "0xA9b2F5ce3aAE7374a62313473a74C98baa7fa70E"


def encode_set_insurance_address():
    lido: interface.Lido = contracts.lido

    oracle = lido.getOracle()
    treasury = lido.getTreasury()

    return lido.address, lido.setProtocolContracts.encode_input(oracle, treasury, INSURANCE_FUND_ADDRESS)


def encode_send_shares_to_insurance():
    lido: interface.Lido = contracts.lido

    return agent_forward([(lido.address, lido.transferShares.encode_input(INSURANCE_FUND_ADDRESS, INSURANCE_SHARES))])


def encode_revoke_assign_role_from_ldo_purchase_executor():
    token_manager = interface.TokenManager(lido_dao_token_manager_address)

    return encode_permission_revoke(
        target_app=token_manager, permission_name="ASSIGN_ROLE", revoke_from=LDO_PURCHASE_EXECUTOR
    )


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items = [
        # 1. Change Insurance address to `0x8B3f33234ABD88493c0Cd28De33D583B70beDe35`
        encode_set_insurance_address(),
        # 2. Send 5466.46 shares of stETH to Insurance Fund at `0x8B3f33234ABD88493c0Cd28De33D583B70beDe35`
        encode_send_shares_to_insurance(),
        # 3. Revoke `ASSIGN_ROLE` from the LDO purchase executor contract at `0xA9b2F5ce3aAE7374a62313473a74C98baa7fa70E`
        encode_revoke_assign_role_from_ldo_purchase_executor(),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Change Insurance address to `0x8B3f33234ABD88493c0Cd28De33D583B70beDe35`",
        "2) Send 5466.46 shares of stETH to Insurance Fund at `0x8B3f33234ABD88493c0Cd28De33D583B70beDe35`",
        "3) Revoke `ASSIGN_ROLE` from the LDO purchase executor contract at `0xA9b2F5ce3aAE7374a62313473a74C98baa7fa70E`",
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
