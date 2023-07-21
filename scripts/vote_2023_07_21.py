"""
Voting 21/07/2023 IPFS test

1) Increase Easy Track motions amount limit: set motionsCountLimit to 20

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import web3  # type: ignore

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)

from utils.easy_track import set_motions_count_limit

description = """
This vote was created for testing purposes only.
This vote will load long description from IPFS storage.

Links and eth addresses will be show like this:
0xD6B7d52E15678B9195F12F3a6D6cb79dcDcCb690 and https://vote.lido.fi/vote/161

IPFS hashes also will be show as links:
bafkreidrecpiv3tacoi6kmerfrrwopyfbr4ekhacdzyxhe75bfflnlhh5m
QmefSCAWVhJq4Ya7149gPBdXUjr1UeymPzyBRHFpnQW9ih

Since now there is no limit on the length of the file, you can add some documentation

What is Lido?
Lido is the name of a family of open-source peer-to-system software tools deployed and functioning on the Ethereum, Solana, and Polygon blockchain networks. The software enables users to mint transferable utility tokens, which receive rewards linked to the related validation activities of writing data to the blockchain, while the tokens can be used in other on-chain activities.

How does Lido work?
While each network works differently, generally, the Lido protocols batch user tokens to stake with validators and route the staking packages to network staking contracts. Users mint amounts of stTokens which correspond to the amount of tokens sent as stake and they receive staking rewards. When they unstake, they burn the stToken to initiate the network-specific withdrawal process to withdraw the balance of stake and rewards.

Why Lido?
Lido protocols give the user liquidity - the stTokens are on the execution layer, so they can be transferred. Users receive staking rewards from validation activities but can sell stTokens anytime they want to exit their staking position.
Participate in DeFi - users can use stTokens as building blocks in DeFi protocols at the same time as getting staking rewards from validating activities.
Lido protocols are governed by the Lido DAO - this means there is no central point for making decisions, and there is no one person who has access, control, or decision power to define what to do with users’ tokens. All decisions with respect to the protocol are voted up by the DAO, and all LDO holders may vote.
Uses time-proven node operators. Lido DAO works with experienced node operators, which decreases the likelihood of technical mistakes that could lead to slashing or penalties. Users supply the stake, and the node operators supply the know-how.

What is liquid staking?
Liquid staking protocols allow users to get staking rewards without locking tokens or maintaining staking infrastructure. Users can deposit tokens and receive tradable liquid tokens in return. The DAO-controlled smart contract stakes these tokens using elected staking providers.
As users' funds are controlled by the DAO, staking providers never have direct access to the users' tokens.

Is it safe to work with Lido?
Lido is a liquid staking solution and fits the next points:
Open-sourcing & continuous review of all code.
Committee of elected, best-in-class validators to minimise staking risk.
Use of non-custodial staking service to eliminate counter-party risk.
Use of DAO for governance decisions & to manage risk factors.
Usually when staking ETH you choose only one validator. In the case of Lido you stake across many validators, minimising your staking risk.

Audits
Lido has been audited by Quantstamp, Sigma Prime and MixBytes. Lido audits can be found in more detail https://github.com/lidofinance/audits.

Do Ethereum staking rewards with Lido compound?
Your Ethereum staking rewards with Lido compound automatically.
After the Shapella upgrade, which enabled ETH withdrawals, earned staking rewards are no longer locked on the beacon chain and periodically flow into the Lido withdrawal vault. After fulfilling withdrawal requests, the rest of rewards are restaked on a daily basis. Therefore, you don't need to do anything to for your ETH staking rewards to compound.
To see the compounding effect, check out Lido dune dashboard https://dune.com/LidoAnalytical/lido-execution-layer-rewards.

"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    motions_count_limit = 21
    call_script_items = [
        # Set max EasyTrack motions limit to 21
        set_motions_count_limit(motions_count_limit),
    ]

    vote_desc_items = [
        "1) Increase Easy Track motions amount limit: set motionsCountLimit to 21",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params, description=description))


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
