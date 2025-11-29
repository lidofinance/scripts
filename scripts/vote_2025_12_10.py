"""
# Vote 2025_12_10

=== 1. DG PROPOPSAL ===
I. Change Curated Module fees
1.1. Change Curated Module (MODULE_ID = 1) module fee from 500 BP to 350 BP and Treasury fee from 500 BP to 650 BP in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999

II. Raise SDVT stake share limit
1.2. Raise SDVT (MODULE_ID = 2) stake share limit from 400 bps to 430 bps in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999

III. Reset Easy Track TRP limit
1.3. Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0 LDO
1.4. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 15'000'000 LDO with unchanged period duration of 12 months

IV. Grant Stonks allowed recipients management permissions to Easy Track EVM Script Executor
1.5 Grant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0
1.6 Grant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Stonks Stablecoins AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368
1.7 Grant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0
1.8 Grant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Stonks Stablecoins AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368

=== NON-DG ITEMS ===
V. Transfer MATIC from Lido Treasury to Liquidity Observation Lab (LOL) Multisig
2. Transfer 508,106 MATIC 0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Liquidity Observation Lab (LOL) Multisig 0x87D93d9B2C672bf9c9642d853a8682546a5012B5

VI. Add sUSDS to stablecoins Allowed Tokens Registry
3. Termporarily grant ADD_TOKEN_TO_ALLOWED_LIST_ROLE to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
4. Add sUSDS token 0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD to stablecoins Allowed Tokens Registry 0x4AC40c34f8992bb1e5E856A448792158022551ca
5. Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e

VII. Add sUSDS transfer permission to Easy Track EVM Script Executor in Aragon Finance
6. Revoke CREATE_PAYMENTS_ROLE from Easy Track EVM Script Executor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86
7. Grant CREATE_PAYMENTS_ROLE to Easy Track EVM Script Executor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86 with appended transfer limit of 2,000,000 sUSDS

VIII. Add Stonks allowed recipients management factories to Easy Track
8. Add Stonks stETH AddAllowedRecipient Factory 0x8b18e9b7c17c20Ae2f4F825429e9b5e788194E22 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea with addRecipient permission on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0
9. Add Stonks stETH RemoveAllowedRecipient Factory 0x5F6Db5A060Ac5145Af3C5590a4E1eaB080A8143A to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea with removeRecipient permission on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0
10. Add Stonks stablecoins AddAllowedRecipient Factory 0x56bcff69e1d06e18C46B65C00D41B4ae82890184 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea with addRecipient permission on Stonks stablecoins AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368
11. Add Stonks stablecoins RemoveAllowedRecipient Factory 0x4C75070Aa6e7f89fd5Cb6Ce77544e9cB2AC585DD to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea with removeRecipient permission on Stonks stablecoins AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from typing import Dict, List, Tuple, NamedTuple
from brownie import interface, ZERO_ADDRESS, convert, web3

from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.finance import make_matic_payout
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from utils.agent import agent_forward
from utils.permissions import encode_permission_revoke, encode_permission_grant_p
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.allowed_recipients_registry import (
    unsafe_set_spent_amount,
    set_limit_parameters,
)


# ============================== Types ===================================
class TokenLimit(NamedTuple):
    address: str
    limit: int


# ============================== Addresses ===================================
ET_TRP_REGISTRY = "0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
LOL_MS = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
FINANCE = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"
ET_EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
STABLECOINS_ALLOWED_TOKENS_REGISTRY = "0x4AC40c34f8992bb1e5E856A448792158022551ca"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"

STONKS_STETH_ADD_ALLOWED_RECIPIENT_FACTORY = "0x8b18e9b7c17c20Ae2f4F825429e9b5e788194E22"
STONKS_STETH_REM_ALLOWED_RECIPIENT_FACTORY = "0x5F6Db5A060Ac5145Af3C5590a4E1eaB080A8143A"
STONKS_STETH_ALLOWED_RECIPIENTS_REGISTRY = "0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0"

STONKS_STABLECOINS_ADD_ALLOWED_RECIPIENT_FACTORY = "0x56bcff69e1d06e18C46B65C00D41B4ae82890184"
STONKS_STABLECOINS_REM_ALLOWED_RECIPIENT_FACTORY = "0x4C75070Aa6e7f89fd5Cb6Ce77544e9cB2AC585DD"
STONKS_STABLECOINS_ALLOWED_RECIPIENTS_REGISTRY = "0x3f0534CCcFb952470775C516DC2eff8396B8A368"


# ============================== Roles ===================================
CREATE_PAYMENTS_ROLE = "CREATE_PAYMENTS_ROLE"
ADD_TOKEN_TO_ALLOWED_LIST_ROLE = "ADD_TOKEN_TO_ALLOWED_LIST_ROLE"


# ============================== Tokens ===================================
SUSDS_TOKEN = "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD"
USDC_TOKEN = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT_TOKEN = "0xdac17f958d2ee523a2206206994597c13d831ec7"
DAI_TOKEN = "0x6b175474e89094c44da98b954eedeac495271d0f"
LDO_TOKEN = "0x5a98fcbea516cf06857215779fd812ca3bef1b32"
STETH_TOKEN = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"


# ============================== Constants ===================================
CURATED_MODULE_ID = 1
CURATED_MODULE_TARGET_SHARE_BP = 10000
CURATED_MODULE_PRIORITY_EXIT_THRESHOLD_BP = 10000
CURATED_MODULE_NEW_MODULE_FEE_BP = 350
CURATED_MODULE_NEW_TREASURY_FEE_BP = 650
CURATED_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
CURATED_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25

SDVT_MODULE_ID = 2
SDVT_MODULE_NEW_TARGET_SHARE_BP = 430
SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP = 444
SDVT_MODULE_MODULE_FEE_BP = 800
SDVT_MODULE_TREASURY_FEE_BP = 200
SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25

TRP_PERIOD_DURATION_MONTHS = 12
TRP_NEW_LIMIT = 15_000_000 * 10**18
TRP_NEW_SPENT_AMOUNT = 0

MATIC_FOR_TRANSFER = 508_106 * 10**18

def amount_limits() -> List[Param]:
    ldo_limit = TokenLimit(LDO_TOKEN, 5_000_000 * (10**18))
    eth_limit = TokenLimit(ZERO_ADDRESS, 1_000 * 10**18)
    steth_limit = TokenLimit(STETH_TOKEN, 1_000 * (10**18))
    dai_limit = TokenLimit(DAI_TOKEN, 2_000_000 * (10**18))
    usdc_limit = TokenLimit(USDC_TOKEN, 2_000_000 * (10**6))
    usdt_limit = TokenLimit(USDT_TOKEN, 2_000_000 * (10**6))
    susds_limit = TokenLimit(SUSDS_TOKEN, 2_000_000 * (10**18))

    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth_limit.address)),
        # 2: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth_limit.limit)),
        #
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(dai_limit.address)),
        # 5: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(dai_limit.limit)),
        #
        # 6: else if (7) then (8) else (9)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=7, success=8, failure=9)
        ),
        # 7: (_token == LDO)
        Param(token_arg_index, Op.EQ, ArgumentValue(ldo_limit.address)),
        # 8: { return _amount <= 5_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(ldo_limit.limit)),
        #
        # 9: else if (10) then (11) else (12)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=10, success=11, failure=12),
        ),
        # 10: (_token == USDC)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdc_limit.address)),
        # 11: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdc_limit.limit)),
        #
        # 12: else if (13) then (14) else (15)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=13, success=14, failure=15),
        ),
        # 13: (_token == USDT)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdt_limit.address)),
        # 14: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdt_limit.limit)),
        #
        # 15: else if (16) then (17) else (18)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=16, success=17, failure=18),
        ),
        # 16: (_token == ETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(eth_limit.address)),
        # 17: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(eth_limit.limit)),
        #
        # 18: else if (19) then (20) else (21)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=19, success=20, failure=21),
        ),
        # 19: (_token == sUSDS)
        Param(token_arg_index, Op.EQ, ArgumentValue(susds_limit.address)),
        # 20: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(susds_limit.limit)),
        #
        # 21: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]


# ============================= Description ==================================
# TODO <a description for IPFS (will appear in the voting description on vote.lido.fi)>
IPFS_DESCRIPTION = "omni nov 2025"


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    stablecoins_allowed_tokens_registry = interface.AllowedTokensRegistry(STABLECOINS_ALLOWED_TOKENS_REGISTRY)

    stonks_steth_allowed_recipients_registry = interface.AllowedRecipientRegistry(STONKS_STETH_ALLOWED_RECIPIENTS_REGISTRY)
    stonks_stablecoins_allowed_recipients_registry = interface.AllowedRecipientRegistry(STONKS_STABLECOINS_ALLOWED_RECIPIENTS_REGISTRY)

    dg_items = [
        agent_forward([
            # 1.1. Change Curated Module (MODULE_ID = 1) module fee from 500 BP to 350 BP and Treasury fee from 500 BP to 650 BP in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
            (
                staking_router.address,
                staking_router.updateStakingModule.encode_input(
                    CURATED_MODULE_ID,
                    CURATED_MODULE_TARGET_SHARE_BP,
                    CURATED_MODULE_PRIORITY_EXIT_THRESHOLD_BP,
                    CURATED_MODULE_NEW_MODULE_FEE_BP,
                    CURATED_MODULE_NEW_TREASURY_FEE_BP,
                    CURATED_MODULE_MAX_DEPOSITS_PER_BLOCK,
                    CURATED_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                ),
            ),
        ]),
        agent_forward([
            # 1.2. Raise SDVT (MODULE_ID = 2) stake share limit from 400 bps to 430 bps in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
            (
                staking_router.address,
                staking_router.updateStakingModule.encode_input(
                    SDVT_MODULE_ID,
                    SDVT_MODULE_NEW_TARGET_SHARE_BP,
                    SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP,
                    SDVT_MODULE_MODULE_FEE_BP,
                    SDVT_MODULE_TREASURY_FEE_BP,
                    SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK,
                    SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                ),
            ),
        ]),
        agent_forward([
            # 1.3. Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0 LDO
            unsafe_set_spent_amount(spent_amount=TRP_NEW_SPENT_AMOUNT, registry_address=ET_TRP_REGISTRY),
        ]),
        agent_forward([
            # 1.4. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 15'000'000 LDO with unchanged period duration of 12 months
            set_limit_parameters(
                limit=TRP_NEW_LIMIT,
                period_duration_months=TRP_PERIOD_DURATION_MONTHS,
                registry_address=ET_TRP_REGISTRY,
            ),
        ]),
        agent_forward([
            # 1.5 Grant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0
            (
                stonks_steth_allowed_recipients_registry.address, stonks_steth_allowed_recipients_registry.grantRole.encode_input(
                    convert.to_uint(web3.keccak(text="ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE")),
                    ET_EVM_SCRIPT_EXECUTOR,
                )
            ),
        ]),
        agent_forward([
            # 1.6 Grant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Stonks Stablecoins AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368
            (
                stonks_stablecoins_allowed_recipients_registry.address, stonks_stablecoins_allowed_recipients_registry.grantRole.encode_input(
                    convert.to_uint(web3.keccak(text="ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE")),
                    ET_EVM_SCRIPT_EXECUTOR,
                )
            ),
        ]),
        agent_forward([
            # 1.7 Grant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0
            (
                stonks_steth_allowed_recipients_registry.address, stonks_steth_allowed_recipients_registry.grantRole.encode_input(
                    convert.to_uint(web3.keccak(text="REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE")),
                    ET_EVM_SCRIPT_EXECUTOR,
                )
            ),
        ]),
        agent_forward([
            # 1.8 Grant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Stonks Stablecoins AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368
            (
                stonks_stablecoins_allowed_recipients_registry.address, stonks_stablecoins_allowed_recipients_registry.grantRole.encode_input(
                    convert.to_uint(web3.keccak(text="REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE")),
                    ET_EVM_SCRIPT_EXECUTOR,
                )
            ),
        ]),
    ]
    
    dg_call_script = submit_proposals([
        (dg_items, "Change Curated Module fees, raise SDVT stake share limit, reset Easy Track TRP limit and grant Stonks allowed recipients management permissions to Easy Track EVM Script Executor")
    ])
    
    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to change Curated Module fees, raise SDVT stake share limit, reset Easy Track TRP limit and grant Stonks allowed recipients management permissions to Easy Track EVM Script Executor",
            dg_call_script[0]
        ),
        (
            "2. Transfer 508,106 MATIC 0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Liquidity Observation Lab (LOL) Multisig 0x87D93d9B2C672bf9c9642d853a8682546a5012B5",
            make_matic_payout(
                target_address=LOL_MS,
                matic_in_wei=MATIC_FOR_TRANSFER,
                reference="Transfer 508,106 MATIC from Treasury to Liquidity Observation Lab (LOL) Multisig",
            ),
        ),
        (
            "3. Termporarily grant ADD_TOKEN_TO_ALLOWED_LIST_ROLE to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            (
                stablecoins_allowed_tokens_registry.address, stablecoins_allowed_tokens_registry.grantRole.encode_input(
                    convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
                    VOTING,
                )
            ),
        ),
        (
            "4. Add sUSDS token 0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD to stablecoins Allowed Tokens Registry 0x4AC40c34f8992bb1e5E856A448792158022551ca",
            (stablecoins_allowed_tokens_registry.address, stablecoins_allowed_tokens_registry.addToken.encode_input(SUSDS_TOKEN))
        ),
        (
            "5. Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            (
                stablecoins_allowed_tokens_registry.address, stablecoins_allowed_tokens_registry.revokeRole.encode_input(
                    convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
                    VOTING,
                )
            )
        ),
        (
            "6. Revoke CREATE_PAYMENTS_ROLE from Easy Track EVM Script Executor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86",
            encode_permission_revoke(
                target_app=FINANCE,
                permission_name=CREATE_PAYMENTS_ROLE,
                revoke_from=ET_EVM_SCRIPT_EXECUTOR,
            ),
        ),
        (
            "7. Grant CREATE_PAYMENTS_ROLE to Easy Track EVM Script Executor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86 with appended transfer limit of 2,000,000 sUSDS",
            encode_permission_grant_p(
                target_app=FINANCE,
                permission_name=CREATE_PAYMENTS_ROLE,
                grant_to=ET_EVM_SCRIPT_EXECUTOR,
                params=amount_limits(),
            ),
        ),
        (
            "8. Add Stonks stETH AddAllowedRecipient Factory 0x8b18e9b7c17c20Ae2f4F825429e9b5e788194E22 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea with addRecipient permission on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0",
            add_evmscript_factory(
                factory=STONKS_STETH_ADD_ALLOWED_RECIPIENT_FACTORY,
                permissions=create_permissions(stonks_steth_allowed_recipients_registry, "addRecipient"),
            ),
        ),
        (
            "9. Add Stonks stETH RemoveAllowedRecipient Factory 0x5F6Db5A060Ac5145Af3C5590a4E1eaB080A8143A to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea with removeRecipient permission on Stonks stETH AllowedRecipientsRegistry 0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0",
            add_evmscript_factory(
                factory=STONKS_STETH_REM_ALLOWED_RECIPIENT_FACTORY,
                permissions=create_permissions(stonks_steth_allowed_recipients_registry, "removeRecipient"),
            ),
        ),
        (
            "10. Add Stonks stablecoins AddAllowedRecipient Factory 0x56bcff69e1d06e18C46B65C00D41B4ae82890184 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea with addRecipient permission on Stonks stablecoins AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368",
            add_evmscript_factory(
                factory=STONKS_STABLECOINS_ADD_ALLOWED_RECIPIENT_FACTORY,
                permissions=create_permissions(stonks_stablecoins_allowed_recipients_registry, "addRecipient"),
            ),
        ),
        (
            "11. Add Stonks stablecoins RemoveAllowedRecipient Factory 0x4C75070Aa6e7f89fd5Cb6Ce77544e9cB2AC585DD to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea with removeRecipient permission on Stonks stablecoins AllowedRecipientsRegistry 0x3f0534CCcFb952470775C516DC2eff8396B8A368",
            add_evmscript_factory(
                factory=STONKS_STABLECOINS_REM_ALLOWED_RECIPIENT_FACTORY,
                permissions=create_permissions(stonks_stablecoins_allowed_recipients_registry, "removeRecipient"),
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
