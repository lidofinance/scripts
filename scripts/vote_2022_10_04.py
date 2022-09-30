"""
Voting 04/10/2022.

1. Change Insurance address to [TBD]
2. Send 5466.46 shares to Insurance from Treasury
3. Rekove `ASSIGN_ROLE` from LDO Seller

"""
import time
from typing import Dict, Optional, Tuple
import brownie

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.brownie_prelude import *
from utils.config import get_deployer_account, get_is_live, contracts

INSURANCE_FUND_ADDRESS = "0x8B3f33234ABD88493c0Cd28De33D583B70beDe35"
INSURANCE_SHARES = 5466.46

lido: interface.Lido = contracts.lido


def encode_set_insurance():

    oracle = lido.getOracle()
    treasury = lido.getTreasury()

    return lido.address, lido.setProtocolContracts.encode_input(oracle, treasury, INSURANCE_FUND_ADDRESS)


def encode_send_shares():
    shares_wei = 5466.46 * 10**18
    return lido.address, lido.transferShares.encode_input(INSURANCE_FUND_ADDRESS, shares_wei)


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[brownie.network.TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items = [
        # 1. Change Insurance address to [TBD]
        encode_set_insurance(),
        encode_send_shares(),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = ["1) Change Insurance address", "2) Transfer self-insurance funds to Insurance Fund"]

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
