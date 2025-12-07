"""
# Vote 2025_12_10

=== 1. DG PROPOSAL ===
I. Change Curated Module fees
1.1. Change Curated Module (MODULE_ID = 1) fees in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999: Module fee from 500 BP to 350 BP and Treasury fee from 500 BP to 650 BP

II. Raise SDVT module stake share limit
1.2. Raise SDVT (MODULE_ID = 2) stake share limit from 400 BP to 430 BP and priority exit threshold from 444 BP to 478 BP in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999

III. Set A41 soft target validator limit to 0
1.3. Set soft-mode target validators limit to 0 for Node operator A41 (ID = 32) in Curated Module (MODULE_ID = 1) in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999

IV. Set Easy Track TRP limit
1.4. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 15'000'000 LDO with unchanged period duration of 12 months

=== NON-DG ITEMS ===
V. Add sUSDS token to stablecoins Allowed Tokens Registry and sUSDS transfer permission to Easy Track EVM Script Executor in Aragon Finance
2. Temporarily grant ADD_TOKEN_TO_ALLOWED_LIST_ROLE to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
3. Add sUSDS token 0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD to stablecoins Allowed Tokens Registry 0x4AC40c34f8992bb1e5E856A448792158022551ca
4. Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
5. Revoke CREATE_PAYMENTS_ROLE from Easy Track EVM Script Executor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86
6. Grant CREATE_PAYMENTS_ROLE to Easy Track EVM Script Executor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86 with appended transfer limit of 2,000,000 sUSDS

VI. Transfer MATIC from Lido Treasury to Liquidity Observation Lab (LOL) Multisig
7. Transfer 508,106 MATIC 0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Liquidity Observation Lab (LOL) Multisig 0x87D93d9B2C672bf9c9642d853a8682546a5012B5

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
from utils.allowed_recipients_registry import set_limit_parameters


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
SDVT_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 478
SDVT_MODULE_MODULE_FEE_BP = 800
SDVT_MODULE_TREASURY_FEE_BP = 200
SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25

TRP_PERIOD_DURATION_MONTHS = 12
TRP_NEW_LIMIT = 15_000_000 * 10**18

MATIC_FOR_TRANSFER = 508_106 * 10**18

A41_NO_ID = 32
NO_TARGET_LIMIT_SOFT_MODE = 1
NEW_A41_TARGET_LIMIT = 0

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
IPFS_DESCRIPTION = """
1. **Change Curated Staking Module fee to 3.5%**, as per [Snapshot decision](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x3a5d10fcd3fad6d5ccf05f5bd49244046600ad9cbed9a5e07845200b3ae97e09). Item 1.1.
2. **Raise SDVT Staking Module stake share limit to 4.3% and priority exit threshold to 4.78%**, as [proposed on the Forum](https://research.lido.fi/t/staking-router-module-proposal-simple-dvt/5625/127). Item 1.2.
3. **Set A41 Node Operator soft target validators limit to 0**, as [requested on the Forum](https://research.lido.fi/t/a41-node-operator-intention-to-wind-down-operations-request-for-dao-vote/10954). Item 1.3.
4. **Set Easy Track TRP limit to 15'000'000 LDO**, as per [Snapshot decision](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x16ecb51631d67213d44629444fcc6275bc2abe4d7e955bebaf15c60a42cba471). Item 1.4.
5. **Add sUSDS token to stablecoins Allowed Tokens Registry and sUSDS transfer permission to Easy Track EVM Script Executor in Aragon Finance**, as proposed in [TMC-6 on the Forum](https://research.lido.fi/t/tmc-6-convert-dao-treasury-stablecoins-into-susds-and-update-config-on-easy-track-and-aragon-finance-accordingly/10868). Items 2-6.
6. **Transfer MATIC from Lido Treasury to Liquidity Observation Lab (LOL) Multisig**, as proposed in [TMC-5 on the Forum](https://research.lido.fi/t/tmc-5-convert-matic-to-usdc/10814). Item 7."""


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    stablecoins_allowed_tokens_registry = interface.AllowedTokensRegistry(STABLECOINS_ALLOWED_TOKENS_REGISTRY)

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
            # 1.2. Raise SDVT (MODULE_ID = 2) stake share limit from 400 BP to 430 BP and priority exit threshold from 444 BP to 478 BP in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
            (
                staking_router.address,
                staking_router.updateStakingModule.encode_input(
                    SDVT_MODULE_ID,
                    SDVT_MODULE_NEW_TARGET_SHARE_BP,
                    SDVT_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
                    SDVT_MODULE_MODULE_FEE_BP,
                    SDVT_MODULE_TREASURY_FEE_BP,
                    SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK,
                    SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                ),
            ),
        ]),
        agent_forward([
            # 1.3. Set soft-mode target validators limit to 0 for Node operator A41 (ID = 32) in Curated Module (MODULE_ID = 1) in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
            (
                staking_router.address,
                staking_router.updateTargetValidatorsLimits.encode_input(CURATED_MODULE_ID, A41_NO_ID, NO_TARGET_LIMIT_SOFT_MODE, NEW_A41_TARGET_LIMIT),
            )
        ]),
        agent_forward([
            # 1.4. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 15'000'000 LDO with unchanged period duration of 12 months
            set_limit_parameters(
                limit=TRP_NEW_LIMIT,
                period_duration_months=TRP_PERIOD_DURATION_MONTHS,
                registry_address=ET_TRP_REGISTRY,
            ),
        ]),
    ]
    
    dg_call_script = submit_proposals([
        (dg_items, "Change Curated Module fees, raise SDVT stake share limit, set A41 soft target validator limit to 0, set Easy Track TRP limit")
    ])
    
    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to change Curated Module fees, raise SDVT stake share limit, set A41 soft target validator limit to 0, set Easy Track TRP limit",
            dg_call_script[0]
        ),
        (
            "2. Temporarily grant ADD_TOKEN_TO_ALLOWED_LIST_ROLE to Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            (
                stablecoins_allowed_tokens_registry.address, stablecoins_allowed_tokens_registry.grantRole.encode_input(
                    convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
                    VOTING,
                )
            ),
        ),
        (
            "3. Add sUSDS token 0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD to stablecoins Allowed Tokens Registry 0x4AC40c34f8992bb1e5E856A448792158022551ca",
            (stablecoins_allowed_tokens_registry.address, stablecoins_allowed_tokens_registry.addToken.encode_input(SUSDS_TOKEN))
        ),
        (
            "4. Revoke ADD_TOKEN_TO_ALLOWED_LIST_ROLE from Aragon Voting 0x2e59A20f205bB85a89C53f1936454680651E618e",
            (
                stablecoins_allowed_tokens_registry.address, stablecoins_allowed_tokens_registry.revokeRole.encode_input(
                    convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
                    VOTING,
                )
            )
        ),
        (
            "5. Revoke CREATE_PAYMENTS_ROLE from Easy Track EVM Script Executor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86",
            encode_permission_revoke(
                target_app=FINANCE,
                permission_name=CREATE_PAYMENTS_ROLE,
                revoke_from=ET_EVM_SCRIPT_EXECUTOR,
            ),
        ),
        (
            "6. Grant CREATE_PAYMENTS_ROLE to Easy Track EVM Script Executor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Aragon Finance 0xB9E5CBB9CA5b0d659238807E84D0176930753d86 with appended transfer limit of 2,000,000 sUSDS",
            encode_permission_grant_p(
                target_app=FINANCE,
                permission_name=CREATE_PAYMENTS_ROLE,
                grant_to=ET_EVM_SCRIPT_EXECUTOR,
                params=amount_limits(),
            ),
        ),
        (
            "7. Transfer 508,106 MATIC 0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Liquidity Observation Lab (LOL) Multisig 0x87D93d9B2C672bf9c9642d853a8682546a5012B5",
            make_matic_payout(
                target_address=LOL_MS,
                matic_in_wei=MATIC_FOR_TRANSFER,
                reference="Transfer 508,106 MATIC from Treasury to Liquidity Observation Lab (LOL) Multisig",
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
