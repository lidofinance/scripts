"""
Vote 2026_08_05

Launch of the NEST Automated Buybacks system in treasury-only mode (LIP-36).

=== 1. DG PROPOSAL ===
1.1. Add OpStackTokenRatePusher 0xd54c1c6413caac3477ac14b2a80d5398e3c32ffe as NoArgs (kind = 0) to the new TokenRateNotifier 0xbe05d12Fd10919F1881125006523452F6aFF791b
1.2. Add StakingRevenueSource 0x6220212a33a87Ed7Cc386B67eB2c393974F28C38 as WithArgs (kind = 1) to the new TokenRateNotifier 0xbe05d12Fd10919F1881125006523452F6aFF791b
1.3. Upgrade LidoLocator proxy 0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb implementation to 0xF2Ffb952e129a63F0614Ff87126E1d4a494A2313
1.4. Add BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889 as allowed recipient "Buyback Allocator" on the Stonks stETH top-up AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0

=== NON-DG ITEMS ===
2. Set Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 as manager on OracleRouter 0x79ef3a538200Fe4981D67E7e886bfb36D4Cb5a31
3. Set treasury-mode Stonks 0xb368586CB980895E51e1D82102E63b3F69d3F151 on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
4. Grant Buybacks.BuybackExecutor.ALLOCATOR_ROLE 0x87905334ad07701d0cd9b21ea0599de1a0cab067e0ab49596d423d87159ac7f2 to BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889 on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
5. Grant Buybacks.MANAGER_ROLE 0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
6. Grant Buybacks.BuybackExecutor.EMERGENCY_ROLE 0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
7. Grant Buybacks.BuybackExecutor.EMERGENCY_ROLE 0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd to Emergency Committee 0x73b047fe6337183A454c5217241D780a932777bD on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
8. Grant Buybacks.MANAGER_ROLE 0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 on BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889
9. Call activate() on BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889

TODO (after vote) Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from brownie import interface
from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals

from utils.agent import agent_forward


# ============================== Addresses ===================================
ARAGON_AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
TMC = "0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647"  # Treasury Management Committee (MANAGER_ROLE)
EMERGENCY_COMMITTEE = "0x73b047fe6337183A454c5217241D780a932777bD"  # Emergency Brakes (EMERGENCY_ROLE)
ORACLE_ROUTER = "0x79ef3a538200Fe4981D67E7e886bfb36D4Cb5a31"
LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
OP_STACK_TOKEN_RATE_PUSHER = "0xd54c1c6413caac3477ac14b2a80d5398e3c32ffe"
STONKS_STETH_TOPUP_REGISTRY = "0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0"

# NEST contracts
NEW_TOKEN_RATE_NOTIFIER = "0xbe05d12Fd10919F1881125006523452F6aFF791b"
NEW_LIDO_LOCATOR_IMPL = "0xF2Ffb952e129a63F0614Ff87126E1d4a494A2313"
STAKING_REVENUE_SOURCE = "0x6220212a33a87Ed7Cc386B67eB2c393974F28C38"
BUYBACK_EXECUTOR = "0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7"
BUYBACK_STONKS_TREASURY = "0xb368586CB980895E51e1D82102E63b3F69d3F151"
BUYBACK_ALLOCATOR = "0xAA568141c051f2D1132b110f8391F18D48E8D889"


# ============================== Constants ===================================
MANAGER_ROLE = "0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e"  # keccak256("Buybacks.MANAGER_ROLE")
ALLOCATOR_ROLE = "0x87905334ad07701d0cd9b21ea0599de1a0cab067e0ab49596d423d87159ac7f2"  # keccak256("Buybacks.BuybackExecutor.ALLOCATOR_ROLE")
EMERGENCY_ROLE = "0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd"  # keccak256("Buybacks.BuybackExecutor.EMERGENCY_ROLE")

# TokenRateNotifier.ObserverKind
OBSERVER_KIND_NO_ARGS = 0
OBSERVER_KIND_WITH_ARGS = 1

DG_PROPOSAL_METADATA = "Register the StakingRevenueSource on the TokenRateNotifier to enable NEST"

# ipfs description
IPFS_DESCRIPTION = """
# Launch NEST Automated Buybacks in treasury-only mode

1. **Register the StakingRevenueSource on the TokenRateNotifier to enable NEST** through a Dual
Governance proposal. Migrate the OpStack token rate pusher and register the StakingRevenueSource
on the new TokenRateNotifier, upgrade the LidoLocator implementation to use the new notifier as
the post-token-rebase receiver, and allow the BuybackAllocator on the Stonks stETH top-up Easy
Track registry. Item 1.
2. **Launch NEST Automated Buybacks in treasury-only mode** (LIP-36). Set the Treasury Management
Committee as the OracleRouter manager, configure the treasury-mode Stonks on the BuybackExecutor,
grant the manager, allocator, and emergency roles on the BuybackExecutor and BuybackAllocator,
and activate the BuybackAllocator. Items 2-9.
"""


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    new_token_rate_notifier = interface.TokenRateNotifierV2(NEW_TOKEN_RATE_NOTIFIER)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    stonks_topup_registry = interface.AllowedRecipientRegistry(STONKS_STETH_TOPUP_REGISTRY)

    return [
        agent_forward([
            # 1.1. Add OpStackTokenRatePusher as NoArgs (kind = 0) to the new TokenRateNotifier
            (
                new_token_rate_notifier.address,
                new_token_rate_notifier.addObserver.encode_input(OP_STACK_TOKEN_RATE_PUSHER, OBSERVER_KIND_NO_ARGS),
            ),
            # 1.2. Add StakingRevenueSource as WithArgs (kind = 1) to the new TokenRateNotifier
            (
                new_token_rate_notifier.address,
                new_token_rate_notifier.addObserver.encode_input(STAKING_REVENUE_SOURCE, OBSERVER_KIND_WITH_ARGS),
            ),
            # 1.3. Upgrade LidoLocator proxy implementation to the new implementation
            (
                lido_locator_proxy.address,
                lido_locator_proxy.proxy__upgradeTo.encode_input(NEW_LIDO_LOCATOR_IMPL),
            ),
            # 1.4. Add BuybackAllocator as allowed recipient "Buyback Allocator" on the Stonks stETH top-up AllowedRecipientsRegistry
            (
                stonks_topup_registry.address,
                stonks_topup_registry.addRecipient.encode_input(BUYBACK_ALLOCATOR, "Buyback Allocator"),
            ),
        ]),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    oracle_router = interface.OracleRouter(ORACLE_ROUTER)
    buyback_executor = interface.BuybackExecutor(BUYBACK_EXECUTOR)
    buyback_allocator = interface.BuybackAllocator(BUYBACK_ALLOCATOR)

    dg_items = get_dg_items()
    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_METADATA)])

    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to register the StakingRevenueSource on the new TokenRateNotifier and enable NEST",
            dg_call_script[0],
        ),
        (
            "2. Set the Treasury Management Committee as manager on the OracleRouter",
            (
                oracle_router.address,
                oracle_router.setManager.encode_input(TMC),
            ),
        ),
        (
            "3. Set the treasury-mode Stonks on the BuybackExecutor",
            (
                buyback_executor.address,
                buyback_executor.setStonks.encode_input(BUYBACK_STONKS_TREASURY),
            ),
        ),
        (
            "4. Grant Buybacks.BuybackExecutor.ALLOCATOR_ROLE to the BuybackAllocator on the BuybackExecutor",
            (
                buyback_executor.address,
                buyback_executor.grantRole.encode_input(ALLOCATOR_ROLE, BUYBACK_ALLOCATOR),
            ),
        ),
        (
            "5. Grant Buybacks.MANAGER_ROLE to the Treasury Management Committee on the BuybackExecutor",
            (
                buyback_executor.address,
                buyback_executor.grantRole.encode_input(MANAGER_ROLE, TMC),
            ),
        ),
        (
            "6. Grant Buybacks.BuybackExecutor.EMERGENCY_ROLE to the Treasury Management Committee on the BuybackExecutor",
            (
                buyback_executor.address,
                buyback_executor.grantRole.encode_input(EMERGENCY_ROLE, TMC),
            ),
        ),
        (
            "7. Grant Buybacks.BuybackExecutor.EMERGENCY_ROLE to the Emergency Committee on the BuybackExecutor",
            (
                buyback_executor.address,
                buyback_executor.grantRole.encode_input(EMERGENCY_ROLE, EMERGENCY_COMMITTEE),
            ),
        ),
        (
            "8. Grant Buybacks.MANAGER_ROLE to the Treasury Management Committee on the BuybackAllocator",
            (
                buyback_allocator.address,
                buyback_allocator.grantRole.encode_input(MANAGER_ROLE, TMC),
            ),
        ),
        (
            "9. Call activate() on the BuybackAllocator",
            (
                buyback_allocator.address,
                buyback_allocator.activate.encode_input(),
            ),
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
