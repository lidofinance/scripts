"""
Vote 2026_08_05

1. Submit a Dual Governance proposal containing a single Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c forward call to Dual Governance 0xC1db28B3301331277e307FDCfF8DE28242A4486E

I. NEST Activation
1.1. Add OpStackTokenRatePusher 0xd54c1c6413caac3477AC14b2a80D5398E3c32FfE as NoArgs observer kind 0 to TokenRateNotifier 0xbe05d12Fd10919F1881125006523452F6aFF791b
1.2. Add StakingRevenueSource 0x6220212a33a87Ed7Cc386B67eB2c393974F28C38 as WithArgs observer kind 1 to TokenRateNotifier 0xbe05d12Fd10919F1881125006523452F6aFF791b
1.3. Upgrade Lido Locator 0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb to implementation 0xF2Ffb952e129a63F0614Ff87126E1d4a494A2313
1.4. Add BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889 as allowed recipient with name Buyback Allocator on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0
2. Set Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 as manager on OracleRouter 0x79ef3a538200Fe4981D67E7e886bfb36D4Cb5a31
3. Set treasury-mode Stonks 0xb368586CB980895E51e1D82102E63b3F69d3F151 on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
4. Grant Buybacks.BuybackExecutor.ALLOCATOR_ROLE 0x87905334ad07701d0cd9b21ea0599de1a0cab067e0ab49596d423d87159ac7f2 to BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889 on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
5. Grant Buybacks.MANAGER_ROLE 0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
6. Grant Buybacks.BuybackExecutor.EMERGENCY_ROLE 0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
7. Grant Buybacks.BuybackExecutor.EMERGENCY_ROLE 0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd to Ethereum Emergency Brakes multisig 0x73b047fe6337183A454c5217241D780a932777bD on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7
8. Grant Buybacks.MANAGER_ROLE 0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 on BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889
9. Call activate() on BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889

II. LOL ET stablecoins payment factories activation
1.5. Grant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE 0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276 to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on LOL stablecoins AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89
1.6. Grant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE 0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on LOL stablecoins AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89
12. Add LOL stablecoins TopUpAllowedRecipients EVM script factory 0xc72d4C3e86b681D7c9EE306D41193C64D709C303 with newImmediatePayment permission on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86 and updateSpentAmount permission on LOL stablecoins AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89 to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
13. Add LOL stablecoins AddAllowedRecipient EVM script factory 0xe24230619e9218C1eed3de3489a22f6BC3ce18FF with addRecipient permission on LOL stablecoins AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89 to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
14. Add LOL stablecoins RemoveAllowedRecipient EVM script factory 0xF4d5D97C85eD18f77F99B57f55E9E11d52992632 with removeRecipient permission on LOL stablecoins AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89 to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea

III. ET factory for CSM share limit updates replacement
10. Remove UpdateStakingModuleShareLimits EVM script factory 0x0C6703F1d8D9DdfB6c6e5F57b4f7432a6500D6D8 from EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
11. Add UpdateStakingModuleShareLimits EVM script factory 0xde3e46E3129fA4e4e3f66c9024B0A3Ad509b27a1 with validateParams permission on itself and updateModuleShares permission on Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999 to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea

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
from utils.allowed_recipients_registry import create_top_up_allowed_recipient_permission
from utils.easy_track import add_evmscript_factory, create_permissions, remove_evmscript_factory
from utils.permissions import encode_oz_grant_role


# ============================== Addresses ===================================
TMC = "0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647"  # Treasury Management Committee (MANAGER_ROLE)
EMERGENCY_COMMITTEE = "0x73b047fe6337183A454c5217241D780a932777bD"  # Ethereum Emergency Brakes multisig (EMERGENCY_ROLE)
ORACLE_ROUTER = "0x79ef3a538200Fe4981D67E7e886bfb36D4Cb5a31"
LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
OP_STACK_TOKEN_RATE_PUSHER = "0xd54c1c6413caac3477AC14b2a80D5398E3c32FfE"
STONKS_STETH_TOPUP_REGISTRY = "0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

# NEST contracts
NEW_TOKEN_RATE_NOTIFIER = "0xbe05d12Fd10919F1881125006523452F6aFF791b"
NEW_LIDO_LOCATOR_IMPL = "0xF2Ffb952e129a63F0614Ff87126E1d4a494A2313"
STAKING_REVENUE_SOURCE = "0x6220212a33a87Ed7Cc386B67eB2c393974F28C38"
BUYBACK_EXECUTOR = "0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7"
BUYBACK_STONKS_TREASURY = "0xb368586CB980895E51e1D82102E63b3F69d3F151"
BUYBACK_ALLOCATOR = "0xAA568141c051f2D1132b110f8391F18D48E8D889"

# Easy Track factories
OLD_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x0C6703F1d8D9DdfB6c6e5F57b4f7432a6500D6D8"
NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0xde3e46E3129fA4e4e3f66c9024B0A3Ad509b27a1"

# LOL (Liquidity Observation Lab) stablecoins Easy Track setup
LOL_STABLES_REGISTRY = "0x8d8b35cA51e7808098afF4918C21Ce428c943F89"
LOL_STABLES_TOP_UP_FACTORY = "0xc72d4C3e86b681D7c9EE306D41193C64D709C303"
LOL_STABLES_ADD_RECIPIENT_FACTORY = "0xe24230619e9218C1eed3de3489a22f6BC3ce18FF"
LOL_STABLES_REMOVE_RECIPIENT_FACTORY = "0xF4d5D97C85eD18f77F99B57f55E9E11d52992632"


# ============================== Constants ===================================
MANAGER_ROLE = "0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e"  # keccak256("Buybacks.MANAGER_ROLE")
ALLOCATOR_ROLE = "0x87905334ad07701d0cd9b21ea0599de1a0cab067e0ab49596d423d87159ac7f2"  # keccak256("Buybacks.BuybackExecutor.ALLOCATOR_ROLE")
EMERGENCY_ROLE = "0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd"  # keccak256("Buybacks.BuybackExecutor.EMERGENCY_ROLE")

# TokenRateNotifier.ObserverKind
OBSERVER_KIND_NO_ARGS = 0
OBSERVER_KIND_WITH_ARGS = 1

DG_PROPOSAL_METADATA = "Activate NEST, add LOL stablecoins Easy Track payment factories (limit of $8M per 6 months), replace CSM Update Share Limits Easy Track factory"

# ipfs description
IPFS_DESCRIPTION = """
# NEST Activation, LOL stablecoins ET Payment Factories Activation, CSM Update Share Limits ET Factory Replacement
1. **Launch NEST (Automated LDO Buyback and Liquidity Provisioning)** in [treasury-only mode](https://research.lido.fi/t/liquid-buybacks-nest-execution-with-ldo-wsteth-liquidity/10894/109#p-25979-h-3-launch-mode-treasury-only-5), with all purchased LDO sent directly to the DAO Treasury. Under the [DAO-approved](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x022e901a6368573d18b150eecda563dd2ee17ad2aa6a0ef9772151cc7ba55187) cumulative surplus model described in [LIP-36](https://github.com/lidofinance/lido-improvement-proposals/blob/develop/LIPS/lip-36.md#surplus-mechanics), NEST converts a fixed portion of staking revenue above the operating baseline into LDO via CoW Swap. Audit & deployment verification: [Ack3](https://github.com/lidofinance/audits/blob/main/Ack3%20Lido%20NEST%20Audit%20Report%2007-2026.pdf). Items 1.1 - 1.4, 2 - 9.
2. **Add LOL stablecoins Easy Track factories for payments and adding/removing allowed recipients**, with a limit of $8M per 6 months, [as per Snapshot decision](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x863859d857c7429a0dcb85a4b324de803e2f66ddd8f50e4c2f04a31c35c6ae6f). Items 1.5, 1.6, 12 - 14.
3. **Replace CSM Update Share Limits Easy Track factory** to correct the per-motion change cap to 0.5%, [as proposed on the forum](https://research.lido.fi/t/community-staking-module/5917/231). Audit & deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20Easy%20Track%20Factories%20(SRv3%20CSMv3%20CMv2)%20Security%20Audit%20Report%2007-2026.pdf). Items 10, 11.
"""


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    new_token_rate_notifier = interface.TokenRateNotifierV2(NEW_TOKEN_RATE_NOTIFIER)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    stonks_topup_registry = interface.AllowedRecipientRegistry(STONKS_STETH_TOPUP_REGISTRY)
    lol_stables_registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)

    return [
        agent_forward([
            # 1.1. Add OpStackTokenRatePusher 0xd54c1c6413caac3477AC14b2a80D5398E3c32FfE as NoArgs observer kind 0 to TokenRateNotifier 0xbe05d12Fd10919F1881125006523452F6aFF791b
            (
                new_token_rate_notifier.address,
                new_token_rate_notifier.addObserver.encode_input(OP_STACK_TOKEN_RATE_PUSHER, OBSERVER_KIND_NO_ARGS),
            ),
            # 1.2. Add StakingRevenueSource 0x6220212a33a87Ed7Cc386B67eB2c393974F28C38 as WithArgs observer kind 1 to TokenRateNotifier 0xbe05d12Fd10919F1881125006523452F6aFF791b
            (
                new_token_rate_notifier.address,
                new_token_rate_notifier.addObserver.encode_input(STAKING_REVENUE_SOURCE, OBSERVER_KIND_WITH_ARGS),
            ),
            # 1.3. Upgrade Lido Locator 0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb to implementation 0xF2Ffb952e129a63F0614Ff87126E1d4a494A2313
            (
                lido_locator_proxy.address,
                lido_locator_proxy.proxy__upgradeTo.encode_input(NEW_LIDO_LOCATOR_IMPL),
            ),
            # 1.4. Add BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889 as allowed recipient with name Buyback Allocator on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0
            (
                stonks_topup_registry.address,
                stonks_topup_registry.addRecipient.encode_input(BUYBACK_ALLOCATOR, "Buyback Allocator"),
            ),
            # 1.5. Grant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE 0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276 to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on LOL stablecoins AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89
            encode_oz_grant_role(
                contract=lol_stables_registry,
                role_name="ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE",
                grant_to=EVM_SCRIPT_EXECUTOR,
            ),
            # 1.6. Grant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE 0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on LOL stablecoins AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89
            encode_oz_grant_role(
                contract=lol_stables_registry,
                role_name="REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE",
                grant_to=EVM_SCRIPT_EXECUTOR,
            ),
        ]),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    oracle_router = interface.OracleRouter(ORACLE_ROUTER)
    buyback_executor = interface.BuybackExecutor(BUYBACK_EXECUTOR)
    buyback_allocator = interface.BuybackAllocator(BUYBACK_ALLOCATOR)
    new_update_staking_module_share_limits_factory = interface.UpdateStakingModuleShareLimits(
        NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY
    )
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    lol_stables_registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)

    dg_items = get_dg_items()
    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_METADATA)])

    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to activate NEST, add LOL stablecoins Easy Track payment factories (limit of $8M per 6 months), replace CSM Update Share Limits Easy Track factory",
            dg_call_script[0],
        ),
        (
            "2. Set Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 as manager "
            "on OracleRouter 0x79ef3a538200Fe4981D67E7e886bfb36D4Cb5a31",
            (
                oracle_router.address,
                oracle_router.setManager.encode_input(TMC),
            ),
        ),
        (
            "3. Set treasury-mode Stonks 0xb368586CB980895E51e1D82102E63b3F69d3F151 "
            "on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7",
            (
                buyback_executor.address,
                buyback_executor.setStonks.encode_input(BUYBACK_STONKS_TREASURY),
            ),
        ),
        (
            "4. Grant Buybacks.BuybackExecutor.ALLOCATOR_ROLE "
            "0x87905334ad07701d0cd9b21ea0599de1a0cab067e0ab49596d423d87159ac7f2 "
            "to BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889 "
            "on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7",
            (
                buyback_executor.address,
                buyback_executor.grantRole.encode_input(ALLOCATOR_ROLE, BUYBACK_ALLOCATOR),
            ),
        ),
        (
            "5. Grant Buybacks.MANAGER_ROLE 0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e "
            "to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 "
            "on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7",
            (
                buyback_executor.address,
                buyback_executor.grantRole.encode_input(MANAGER_ROLE, TMC),
            ),
        ),
        (
            "6. Grant Buybacks.BuybackExecutor.EMERGENCY_ROLE "
            "0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd "
            "to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 "
            "on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7",
            (
                buyback_executor.address,
                buyback_executor.grantRole.encode_input(EMERGENCY_ROLE, TMC),
            ),
        ),
        (
            "7. Grant Buybacks.BuybackExecutor.EMERGENCY_ROLE "
            "0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd "
            "to Ethereum Emergency Brakes multisig 0x73b047fe6337183A454c5217241D780a932777bD "
            "on BuybackExecutor 0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7",
            (
                buyback_executor.address,
                buyback_executor.grantRole.encode_input(EMERGENCY_ROLE, EMERGENCY_COMMITTEE),
            ),
        ),
        (
            "8. Grant Buybacks.MANAGER_ROLE 0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e "
            "to Treasury Management Committee 0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647 "
            "on BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889",
            (
                buyback_allocator.address,
                buyback_allocator.grantRole.encode_input(MANAGER_ROLE, TMC),
            ),
        ),
        (
            "9. Call activate() on BuybackAllocator 0xAA568141c051f2D1132b110f8391F18D48E8D889",
            (
                buyback_allocator.address,
                buyback_allocator.activate.encode_input(),
            ),
        ),
        (
            "10. Remove UpdateStakingModuleShareLimits EVM script factory "
            "0x0C6703F1d8D9DdfB6c6e5F57b4f7432a6500D6D8 from EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory(OLD_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY),
        ),
        (
            "11. Add UpdateStakingModuleShareLimits EVM script factory 0xde3e46E3129fA4e4e3f66c9024B0A3Ad509b27a1 "
            "with validateParams permission on itself and updateModuleShares permission on Staking Router "
            "0xFdDf38947aFB03C621C71b06C9C70bce73f12999 to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            add_evmscript_factory(
                NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
                create_permissions(new_update_staking_module_share_limits_factory, "validateParams")
                + create_permissions(staking_router, "updateModuleShares")[2:],
            ),
        ),
        (
            "12. Add LOL stablecoins TopUpAllowedRecipients EVM script factory "
            "0xc72d4C3e86b681D7c9EE306D41193C64D709C303 with newImmediatePayment permission on Aragon Finance "
            "0xB9E5CBB9CA5b0d659238807E84D0176930753d86 and updateSpentAmount permission on LOL stablecoins "
            "AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89 "
            "to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            add_evmscript_factory(
                factory=LOL_STABLES_TOP_UP_FACTORY,
                permissions=create_top_up_allowed_recipient_permission(registry_address=LOL_STABLES_REGISTRY),
            ),
        ),
        (
            "13. Add LOL stablecoins AddAllowedRecipient EVM script factory "
            "0xe24230619e9218C1eed3de3489a22f6BC3ce18FF with addRecipient permission on LOL stablecoins "
            "AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89 "
            "to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            add_evmscript_factory(
                factory=LOL_STABLES_ADD_RECIPIENT_FACTORY,
                permissions=create_permissions(lol_stables_registry, "addRecipient"),
            ),
        ),
        (
            "14. Add LOL stablecoins RemoveAllowedRecipient EVM script factory "
            "0xF4d5D97C85eD18f77F99B57f55E9E11d52992632 with removeRecipient permission on LOL stablecoins "
            "AllowedRecipientsRegistry 0x8d8b35cA51e7808098afF4918C21Ce428c943F89 "
            "to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            add_evmscript_factory(
                factory=LOL_STABLES_REMOVE_RECIPIENT_FACTORY,
                permissions=create_permissions(lol_stables_registry, "removeRecipient"),
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
