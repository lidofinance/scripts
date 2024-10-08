import time
import os
from scripts.upgrade_2024_10_08 import start_vote
from brownie import interface, accounts, network
from tests.conftest import Helpers
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    network_name,
    L1_OPTIMISM_TOKENS_BRIDGE,
    AGENT
)

ENV_OMNIBUS_VOTE_IDS = "OMNIBUS_VOTE_IDS"

def pause_deposits():
    if not network_name() in ("mainnet-fork",):
        return

    network.gas_price("2 gwei")

    accounts[0].transfer(AGENT, "2 ethers")

    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    agent = accounts.at(AGENT, force=True)
    l1_token_bridge.disableDeposits({"from": agent})
    assert not l1_token_bridge.isDepositsEnabled()

def resume_deposits():
    if not network_name() in ("mainnet-fork",):
        return

    network.gas_price("2 gwei")

    accounts[0].transfer(AGENT, "2 ethers")

    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    agent = accounts.at(AGENT, force=True)
    l1_token_bridge.enableDeposits({"from": agent})
    assert l1_token_bridge.isDepositsEnabled()

def start_and_execute_for_fork_upgrade():
    if not network_name() in ("mainnet-fork",):
        return

    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    if l1_token_bridge.isDepositsEnabled():
        pause_deposits()

    deployerAccount = get_deployer_account()

    # Top up accounts
    accounts[0].transfer(AGENT, "2 ethers")
    accounts[0].transfer(deployerAccount.address, "2 ethers")

    tx_params = {"from": deployerAccount}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    if len(vote_ids_from_env()) > 0:
        (vote_id,) = vote_ids_from_env()
    else:
        vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    vote_tx = Helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.

def vote_ids_from_env() -> [int]:
    if os.getenv(ENV_OMNIBUS_VOTE_IDS):
        try:
            vote_ids_str = os.getenv(ENV_OMNIBUS_VOTE_IDS)
            vote_ids = [int(s) for s in vote_ids_str.split(",")]
            print(f"OMNIBUS_VOTE_IDS env var is set, using existing votes {vote_ids}")
            return vote_ids
        except:
            pass

    return []
