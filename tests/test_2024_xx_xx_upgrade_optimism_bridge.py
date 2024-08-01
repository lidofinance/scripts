"""
Tests for voting xx/xx/2024
"""
import eth_abi
from scripts.vote_2024_xx_xx_upgrade_optimism_bridge import start_vote
from brownie import interface, reverts
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    network_name,
    get_deployer_account,
    AGENT
)

L1_TOKEN_BRIDGE_PROXY: str = "0x4Abf633d9c0F4aEebB4C2E3213c7aa1b8505D332"
L1_TOKEN_BRIDGE_OLD_IMPL: str = "0x02825dbCaFbBfda57511dBD73d22c2787B653814"
L1_TOKEN_BRIDGE_NEW_IMPL: str = "0x8375029773953d91CaCfa452b7D24556b9F318AA"

LIDO_LOCATOR_PROXY: str = "0x8f6254332f69557A72b0DA2D5F0Bc07d4CA991E7"
LIDO_LOCATOR_OLD_IMPL: str = "0x604dc1776eEbe7ddCf4cf5429226Ad20a5a294eE"
LIDO_LOCATOR_NEW_IMPL: str = "0x314Ab8D774c0580942E832f971Bbc7A27B1c2552"

DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"
L1_EMERGENCY_BRAKES_MULTISIG = "0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1"

L2_OPTIMISM_BRIDGE_EXECUTOR = "0xf695357C66bA514150Da95b189acb37b46DDe602"
L2_TOKENS_BRIDGE_PROXY = "0xdBA2760246f315203F8B716b3a7590F0FFdc704a"
L2_TOKENS_BRIDGE_NEW_IMPL = "0xD48c69358193a34aC035ea7dfB70daDea1600112"
L2_OPTIMISM_WSTETH_TOKEN = "0x24B47cd3A74f1799b32B2de11073764Cb1bb318B"
L2_OPTIMISM_WSTETH_TOKEN_NEW_IMPL = "0x298953B9426eba4F35a137a4754278a16d97A063"

def test_vote(helpers, accounts, vote_ids_from_env):
    if not network_name() in ("sepolia", "sepolia-fork"):
        return

    depoyerAccount = get_deployer_account()

    # Top up accounts
    accountWithEth = accounts.at('0x4200000000000000000000000000000000000023', force=True)
    accountWithEth.transfer(depoyerAccount.address, "2 ethers")
    accountWithEth.transfer(AGENT, "2 ethers")

    l1_token_bridge_proxy = interface.OssifiableProxy(L1_TOKEN_BRIDGE_PROXY);
    l1_token_bridge = interface.L1LidoTokensBridge(L1_TOKEN_BRIDGE_PROXY);

    # L1 Bridge has old implementation
    l1_token_bridge_implementation_address_before = l1_token_bridge_proxy.proxy__getImplementation()
    assert l1_token_bridge_implementation_address_before == L1_TOKEN_BRIDGE_OLD_IMPL, "Old address is incorrect"

    # L1 Bridge doesn't have version before update
    with reverts():
        l1_token_bridge.getContractVersion()

    # Upgrade LidoLocator implementation
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR_PROXY);
    lido_locator_implementation_address_before = lido_locator_proxy.proxy__getImplementation()
    assert lido_locator_implementation_address_before == LIDO_LOCATOR_OLD_IMPL, "Old address is incorrect"

    # Multisig hasn't been assigned as deposit enabler
    assert l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG) is False

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    if not network_name() in ("sepolia", "sepolia-fork"):
        assert count_vote_items_by_events(vote_tx, contracts.voting) == 5, "Incorrect voting items count"

    # L1 Bridge has new implementation
    l1_token_bridge_implementation_address_after = l1_token_bridge_proxy.proxy__getImplementation()
    assert l1_token_bridge_implementation_address_before != l1_token_bridge_implementation_address_after, "Implementation is not changed"
    assert l1_token_bridge_implementation_address_after == L1_TOKEN_BRIDGE_NEW_IMPL, "New address is incorrect"

    # update L1 Bridge to 2 version
    assert l1_token_bridge.getContractVersion() == 2

    # LidoLocator has new implementation
    lido_locator_implementation_address_after = lido_locator_proxy.proxy__getImplementation()
    assert lido_locator_implementation_address_before != lido_locator_implementation_address_after, "Implementation is not changed"
    assert lido_locator_implementation_address_after == LIDO_LOCATOR_NEW_IMPL, "New address is incorrect"

    # Multisig has been assigned as deposit enabler
    assert l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG) is True

    # Check bytecode that was send to messenger to update L2 bridge and wstETH token
    sentMessage = vote_tx.events['SentMessage']['message']
    encoded_l2_upgrade_call =  encode_l2_upgrade_call(
        L2_TOKENS_BRIDGE_PROXY,
        L2_TOKENS_BRIDGE_NEW_IMPL,
        L2_OPTIMISM_WSTETH_TOKEN,
        L2_OPTIMISM_WSTETH_TOKEN_NEW_IMPL,
    )
    assert sentMessage == encoded_l2_upgrade_call

def encode_l2_upgrade_call(proxy1: str, new_impl1: str, proxy2: str, new_impl2: str):
    govBridgeExecutor = interface.OpBridgeExecutor(L2_OPTIMISM_BRIDGE_EXECUTOR)

    return govBridgeExecutor.queue.encode_input(
        [proxy1, proxy1, proxy2, proxy2],
        [0, 0, 0, 0],
        [
            "proxy__upgradeTo(address)",
            "finalizeUpgrade_v2()",
            "proxy__upgradeTo(address)",
            "finalizeUpgrade_v2(string,string)"
        ],
        [
            eth_abi.encode(["address"], [new_impl1]),
            eth_abi.encode([],[]),
            eth_abi.encode(["address"], [new_impl2]),
            eth_abi.encode(["string", "string"], ["Wrapped liquid staked Ether 2.0","wstETH"]),
        ],
        [False, False, False, False],
    )
