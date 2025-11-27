import pytest
from typing import List, NamedTuple

from brownie import chain, interface, reverts, accounts, ZERO_ADDRESS, convert, web3
from brownie.network.transaction import TransactionReceipt
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id
from utils.agent import agent_forward
from utils.ipfs import get_lido_vote_cid_from_str
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.allowed_tokens_registry import validate_add_token_event
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events
)
from utils.allowed_recipients_registry import (
    unsafe_set_spent_amount,
    set_limit_parameters,
)
from utils.test.event_validators.payout import (
    validate_token_payout_event,
    Payout,
)
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event,
    validate_set_spent_amount_event,
)
from utils.test.event_validators.permission import (
    validate_grant_role_event,
    validate_revoke_role_event,
    Permission,
    validate_permission_grantp_event,
    validate_permission_revoke_event,
)


class TokenLimit(NamedTuple):
    address: str
    limit: int


# ============================== Import vote =================================
from scripts.vote_2025_12_10 import start_vote, get_vote_items


# ============================== Addresses ===================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
ET_TRP_REGISTRY = "0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
ET_EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
DEPOSIT_SECURITY_MODULE = "0xffa96d84def2ea035c7ab153d8b991128e3d72fd"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
FINANCE = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"
ACL = "0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb"

TRP_COMMITTEE = "0x834560F580764Bc2e0B16925F8bF229bb00cB759"
TRP_TOP_UP_EVM_SCRIPT_FACTORY = "0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C"

STABLECOINS_ALLOWED_TOKENS_REGISTRY = "0x4AC40c34f8992bb1e5E856A448792158022551ca"
LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY = "0xE1f6BaBb445F809B97e3505Ea91749461050F780"
LIDO_LABS_TRUSTED_CALLER = "0x95B521B4F55a447DB89f6a27f951713fC2035f3F"
LIDO_LABS_ALLOWED_RECIPIENTS_REGISTRY = "0x68267f3D310E9f0FF53a37c141c90B738E1133c2"

LEGO_LDO_TRUSTED_CALLER = "0x12a43b049A7D330cB8aEAB5113032D18AE9a9030"
LEGO_LDO_TOP_UP_ALLOWED_RECIPIENTS_FACTORY = "0x00caAeF11EC545B192f16313F53912E453c91458"
LEGO_LDO_ALLOWED_RECIPIENTS_REGISTRY = "0x97615f72c3428A393d65A84A3ea6BBD9ad6C0D74"

GAS_SUPPLY_STETH_TRUSTED_CALLER = "0x5181d5D56Af4f823b96FE05f062D7a09761a5a53"
GAS_SUPPLY_STETH_TOP_UP_ALLOWED_RECIPIENTS_FACTORY = "0x200dA0b6a9905A377CF8D469664C65dB267009d1"
GAS_SUPPLY_STETH_ALLOWED_RECIPIENTS_REGISTRY = "0x49d1363016aA899bba09ae972a1BF200dDf8C55F"

LOL_MS = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
SDVT = "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433"
DEV_GAS_STORE = "0x7FEa69d107A77B5817379d1254cc80D9671E171b"
PSM_VARIANT1_ACTIONS = "0xd0A61F2963622e992e6534bde4D52fd0a89F39E0"


# ============================== Roles ===================================
CREATE_PAYMENTS_ROLE = "CREATE_PAYMENTS_ROLE"
ADD_TOKEN_TO_ALLOWED_LIST_ROLE = "ADD_TOKEN_TO_ALLOWED_LIST_ROLE"
REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE = "REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"


# ============================== Constants ===================================
CURATED_MODULE_ID = 1
CURATED_MODULE_TARGET_SHARE_BP = 10000
CURATED_MODULE_PRIORITY_EXIT_THRESHOLD_BP = 10000
CURATED_MODULE_OLD_MODULE_FEE_BP = 500
CURATED_MODULE_NEW_MODULE_FEE_BP = 350
CURATED_MODULE_OLD_TREASURY_FEE_BP = 500
CURATED_MODULE_NEW_TREASURY_FEE_BP = 650
CURATED_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
CURATED_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CURATED_MODULE_NAME = "curated-onchain-v1"

SDVT_MODULE_ID = 2
SDVT_MODULE_OLD_TARGET_SHARE_BP = 400
SDVT_MODULE_NEW_TARGET_SHARE_BP = 430
SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP = 444
SDVT_MODULE_MODULE_FEE_BP = 800
SDVT_MODULE_TREASURY_FEE_BP = 200
SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25
SDVT_MODULE_NAME = "SimpleDVT"

MATIC_IN_TREASURY_BEFORE = 508_106_165_781_175_837_137_177
MATIC_IN_TREASURY_AFTER = 165_781_175_837_137_177
MATIC_IN_LIDO_LABS_BEFORE = 0
MATIC_IN_LIDO_LABS_AFTER = 508_106 * 10**18

TRP_LIMIT_BEFORE = 9_178_284.42 * 10**18
TRP_ALREADY_SPENT_AFTER = 0
TRP_LIMIT_AFTER = 15_000_000 * 10**18
TRP_PERIOD_START_TIMESTAMP = 1735689600  # January 1, 2025 UTC
TRP_PERIOD_END_TIMESTAMP = 1767225600  # January 1, 2026 UTC
TRP_PERIOD_DURATION_MONTHS = 12

ALLOWED_TOKENS_BEFORE = 3
ALLOWED_TOKENS_AFTER = 4


# ============================== Tokens ===================================
MATIC_TOKEN = "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0"
LDO_TOKEN = "0x5a98fcbea516cf06857215779fd812ca3bef1b32"
STETH_TOKEN = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
WSTETH_TOKEN = "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"
SUSDS_TOKEN = "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD"
USDC_TOKEN = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT_TOKEN = "0xdac17f958d2ee523a2206206994597c13d831ec7"
DAI_TOKEN = "0x6b175474e89094c44da98b954eedeac495271d0f"


# ============================== Voting ===================================
EXPECTED_VOTE_ID = 194
EXPECTED_DG_PROPOSAL_ID = 6
EXPECTED_VOTE_EVENTS_COUNT = 7
EXPECTED_DG_EVENTS_COUNT = 4
IPFS_DESCRIPTION_HASH = "bafkreigs2dewxxu7rj6eifpxsqvib23nsiw2ywsmh3lhewyqlmyn46obnm"


# ============================== Finance Limits ===================================
AMOUNT_LIMITS_LEN_BEFORE = 19
def amount_limits_before() -> List[Param]:
    ldo_limit = TokenLimit(LDO_TOKEN, 5_000_000 * (10**18))
    eth_limit = TokenLimit(ZERO_ADDRESS, 1_000 * 10**18)
    steth_limit = TokenLimit(STETH_TOKEN, 1_000 * (10**18))
    dai_limit = TokenLimit(DAI_TOKEN, 2_000_000 * (10**18))
    usdc_limit = TokenLimit(USDC_TOKEN, 2_000_000 * (10**6))
    usdt_limit = TokenLimit(USDT_TOKEN, 2_000_000 * (10**6))

    token_arg_index = 0
    amount_arg_index = 2

    limits = [
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
        # 18: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]

    assert len(limits) == AMOUNT_LIMITS_LEN_BEFORE

    return limits

AMOUNT_LIMITS_LEN_AFTER = 22
ldo_limit_after = TokenLimit(LDO_TOKEN, 5_000_000 * (10**18))
eth_limit_after = TokenLimit(ZERO_ADDRESS, 1_000 * 10**18)
steth_limit_after = TokenLimit(STETH_TOKEN, 1_000 * (10**18))
dai_limit_after = TokenLimit(DAI_TOKEN, 2_000_000 * (10**18))
usdc_limit_after = TokenLimit(USDC_TOKEN, 2_000_000 * (10**6))
usdt_limit_after = TokenLimit(USDT_TOKEN, 2_000_000 * (10**6))
susds_limit_after = TokenLimit(SUSDS_TOKEN, 2_000_000 * (10**18))
def amount_limits_after() -> List[Param]:

    token_arg_index = 0
    amount_arg_index = 2

    limits = [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth_limit_after.address)),
        # 2: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth_limit_after.limit)),
        #
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(dai_limit_after.address)),
        # 5: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(dai_limit_after.limit)),
        #
        # 6: else if (7) then (8) else (9)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=7, success=8, failure=9)
        ),
        # 7: (_token == LDO)
        Param(token_arg_index, Op.EQ, ArgumentValue(ldo_limit_after.address)),
        # 8: { return _amount <= 5_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(ldo_limit_after.limit)),
        #
        # 9: else if (10) then (11) else (12)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=10, success=11, failure=12),
        ),
        # 10: (_token == USDC)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdc_limit_after.address)),
        # 11: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdc_limit_after.limit)),
        #
        # 12: else if (13) then (14) else (15)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=13, success=14, failure=15),
        ),
        # 13: (_token == USDT)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdt_limit_after.address)),
        # 14: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdt_limit_after.limit)),
        #
        # 15: else if (16) then (17) else (18)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=16, success=17, failure=18),
        ),
        # 16: (_token == ETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(eth_limit_after.address)),
        # 17: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(eth_limit_after.limit)),
        #
        # 18: else if (19) then (20) else (21)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=19, success=20, failure=21),
        ),
        # 19: (_token == sUSDS)
        Param(token_arg_index, Op.EQ, ArgumentValue(susds_limit_after.address)),
        # 20: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(susds_limit_after.limit)),
        #
        # 21: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]

    # Verify that the first part of the after_limits matches the before_limits
    for i in range(AMOUNT_LIMITS_LEN_BEFORE - 1):
        assert limits[i].id == amount_limits_before()[i].id
        assert limits[i].op.value == amount_limits_before()[i].op.value
        assert limits[i].value == amount_limits_before()[i].value

    assert len(limits) == AMOUNT_LIMITS_LEN_AFTER

    return limits


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():

    staking_router = interface.StakingRouter(STAKING_ROUTER)

    dg_items = [
        agent_forward([
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
            unsafe_set_spent_amount(spent_amount=0, registry_address=ET_TRP_REGISTRY),
        ]),
        agent_forward([
            set_limit_parameters(
                limit=TRP_LIMIT_AFTER,
                period_duration_months=TRP_PERIOD_DURATION_MONTHS,
                registry_address=ET_TRP_REGISTRY,
            ),
        ]),
    ]

    # Convert each dg_item to the expected format
    proposal_calls = []
    for dg_item in dg_items:
        target, data = dg_item  # agent_forward returns (target, data)
        proposal_calls.append({
            "target": target,
            "value": 0,
            "data": data
        })

    return proposal_calls


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    matic_token = interface.ERC20(MATIC_TOKEN)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    et_trp_registry = interface.AllowedRecipientRegistry(ET_TRP_REGISTRY)
    acl = interface.ACL(ACL)
    stablecoins_allowed_tokens_registry = interface.AllowedTokensRegistry(STABLECOINS_ALLOWED_TOKENS_REGISTRY)


    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        if EXPECTED_VOTE_ID is not None:
            assert vote_id == EXPECTED_VOTE_ID
    elif EXPECTED_VOTE_ID is not None and voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
    onchain_script = voting.getVote(vote_id)["script"]
    assert onchain_script == encode_call_script(call_script_items)


    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        # Item 1 is DG - skipped here

        # Item 2
        matic_treasury_balance_before = matic_token.balanceOf(agent.address)
        assert matic_treasury_balance_before == MATIC_IN_TREASURY_BEFORE
        matic_labs_balance_before = matic_token.balanceOf(LOL_MS)
        assert matic_labs_balance_before == MATIC_IN_LIDO_LABS_BEFORE

        # Items 3,5
        assert not stablecoins_allowed_tokens_registry.hasRole(
            convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
            VOTING
        )

        # Item 4
        assert not stablecoins_allowed_tokens_registry.isTokenAllowed(SUSDS_TOKEN)
        allowed_tokens_before = stablecoins_allowed_tokens_registry.getAllowedTokens()
        assert len(allowed_tokens_before) == ALLOWED_TOKENS_BEFORE
        assert allowed_tokens_before[0] == DAI_TOKEN
        assert allowed_tokens_before[1] == USDT_TOKEN
        assert allowed_tokens_before[2] == USDC_TOKEN

        # Items 6,7
        assert acl.getPermissionParamsLength(
            ET_EVM_SCRIPT_EXECUTOR,
            FINANCE,
            convert.to_uint(web3.keccak(text=CREATE_PAYMENTS_ROLE))
        ) == AMOUNT_LIMITS_LEN_BEFORE
        for i in range(AMOUNT_LIMITS_LEN_BEFORE):
            id, op, val = acl.getPermissionParam(
                ET_EVM_SCRIPT_EXECUTOR,
                FINANCE,
                convert.to_uint(web3.keccak(text=CREATE_PAYMENTS_ROLE)),
                i
            )
            assert id == amount_limits_before()[i].id
            assert op == amount_limits_before()[i].op.value
            assert val == amount_limits_before()[i].value


        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        # Item 1 is DG - skipped here

        # Item 2
        matic_treasury_balance_after = matic_token.balanceOf(agent.address)
        assert matic_treasury_balance_after == MATIC_IN_TREASURY_AFTER
        matic_labs_balance_after = matic_token.balanceOf(LOL_MS)
        assert matic_labs_balance_after == MATIC_IN_LIDO_LABS_AFTER

        # make sure LOL can actually spend the received MATIC
        matic_token.transfer(DEV_GAS_STORE, MATIC_IN_LIDO_LABS_AFTER / 2, {"from": LOL_MS})
        assert matic_token.balanceOf(LOL_MS) == MATIC_IN_LIDO_LABS_AFTER / 2
        assert matic_token.balanceOf(DEV_GAS_STORE) == MATIC_IN_LIDO_LABS_AFTER / 2

        # Items 3,5
        assert not stablecoins_allowed_tokens_registry.hasRole(
            convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
            VOTING
        )

        # Item 4
        assert stablecoins_allowed_tokens_registry.isTokenAllowed(SUSDS_TOKEN)
        allowed_tokens_before = stablecoins_allowed_tokens_registry.getAllowedTokens()
        assert len(allowed_tokens_before) == ALLOWED_TOKENS_AFTER
        assert allowed_tokens_before[0] == DAI_TOKEN
        assert allowed_tokens_before[1] == USDT_TOKEN
        assert allowed_tokens_before[2] == USDC_TOKEN
        assert allowed_tokens_before[3] == SUSDS_TOKEN

        # Items 6,7
        assert acl.getPermissionParamsLength(
            ET_EVM_SCRIPT_EXECUTOR,
            FINANCE,
            convert.to_uint(web3.keccak(text=CREATE_PAYMENTS_ROLE))
        ) == AMOUNT_LIMITS_LEN_AFTER
        for i in range(AMOUNT_LIMITS_LEN_AFTER):
            id, op, val = acl.getPermissionParam(
                ET_EVM_SCRIPT_EXECUTOR,
                FINANCE,
                convert.to_uint(web3.keccak(text=CREATE_PAYMENTS_ROLE)),
                i
            )
            assert id == amount_limits_after()[i].id
            assert op == amount_limits_after()[i].op.value
            assert val == amount_limits_after()[i].value

        # check Finance create payment permissions with limits for all allowed tokens
        assert acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(susds_limit_after.address), convert.to_uint(stranger.address), susds_limit_after.limit],
        )
        assert not acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(susds_limit_after.address), convert.to_uint(stranger.address), susds_limit_after.limit + 1],
        )

        assert acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(usdt_limit_after.address), convert.to_uint(stranger.address), usdt_limit_after.limit],
        )
        assert not acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(usdt_limit_after.address), convert.to_uint(stranger.address), usdt_limit_after.limit + 1],
        )

        assert acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(usdc_limit_after.address), convert.to_uint(stranger.address), usdc_limit_after.limit],
        )
        assert not acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(usdc_limit_after.address), convert.to_uint(stranger.address), usdc_limit_after.limit + 1],
        )

        assert acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(dai_limit_after.address), convert.to_uint(stranger.address), dai_limit_after.limit],
        )
        assert not acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(dai_limit_after.address), convert.to_uint(stranger.address), dai_limit_after.limit + 1],
        ) 

        assert acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(steth_limit_after.address), convert.to_uint(stranger.address), steth_limit_after.limit],
        )
        assert not acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(steth_limit_after.address), convert.to_uint(stranger.address), steth_limit_after.limit + 1],
        ) 

        assert acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(eth_limit_after.address), convert.to_uint(stranger.address), eth_limit_after.limit],
        )
        assert not acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(eth_limit_after.address), convert.to_uint(stranger.address), eth_limit_after.limit + 1],
        ) 

        assert acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(ldo_limit_after.address), convert.to_uint(stranger.address), ldo_limit_after.limit],
        )
        assert not acl.hasPermission["address,address,bytes32,uint[]"](
            ET_EVM_SCRIPT_EXECUTOR, FINANCE, web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            [convert.to_uint(ldo_limit_after.address), convert.to_uint(stranger.address), ldo_limit_after.limit + 1],
        ) 

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT
        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            # validate DG Proposal Submit event
            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata="Upgrade Lido Protocol to change Curated Module fees, raise SDVT stake share limit and reset Easy Track TRP limit",
                proposal_calls=dual_governance_proposal_calls,
            )

            # validate all other voting events
            validate_token_payout_event(
                event=vote_events[1],
                p=Payout(
                    token_addr=MATIC_TOKEN,
                    from_addr=AGENT,
                    to_addr=LOL_MS,
                    amount=MATIC_IN_LIDO_LABS_AFTER),
                is_steth=False,
                emitted_by=AGENT
            )
            validate_grant_role_event(
                events=vote_events[2],
                role=web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE).hex(),
                grant_to=VOTING,
                sender=VOTING,
                emitted_by=STABLECOINS_ALLOWED_TOKENS_REGISTRY,
            )
            validate_add_token_event(
                event=vote_events[3],
                token=SUSDS_TOKEN,
                emitted_by=STABLECOINS_ALLOWED_TOKENS_REGISTRY
            )
            validate_revoke_role_event(
                events=vote_events[4],
                role=web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE).hex(),
                revoke_from=VOTING,
                sender=VOTING,
                emitted_by=STABLECOINS_ALLOWED_TOKENS_REGISTRY,
            )
            validate_permission_revoke_event(
                event=vote_events[5],
                p=Permission(
                    app=FINANCE,
                    entity=ET_EVM_SCRIPT_EXECUTOR,
                    role=web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
                ),
                emitted_by=ACL,
            )
            validate_permission_grantp_event(
                event=vote_events[6],
                p=Permission(
                    app=FINANCE,
                    entity=ET_EVM_SCRIPT_EXECUTOR,
                    role=web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
                ),
                params=amount_limits_after(),
                emitted_by=ACL,
            )

            # =======================================================================
            # =========================== Scenario tests ============================
            # =======================================================================

            # put a lot of tokens into Agent to check Finance/ET limits
            prepare_agent_for_dai_payment(30_000_000 * 10**18)
            prepare_agent_for_usdt_payment(30_000_000 * 10**6)
            prepare_agent_for_usdc_payment(30_000_000 * 10**6)
            prepare_agent_for_susds_payment(30_000_000 * 10**18)
            prepare_agent_for_ldo_payment(10_000_000 * 10**18)
            prepare_agent_for_steth_payment(2_000 * 10**18)

            # check ET limits via Easy Track motion
            ET_LIDO_LABS_STABLES_LIMIT = interface.AllowedRecipientRegistry(LIDO_LABS_ALLOWED_RECIPIENTS_REGISTRY).getPeriodState({"from": AGENT})[1] // 10**18
            et_limit_test(stranger, interface.ERC20(SUSDS_TOKEN), susds_limit_after.limit, ET_LIDO_LABS_STABLES_LIMIT * 10**18, LIDO_LABS_TRUSTED_CALLER, LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY)
            et_limit_test(stranger, interface.ERC20(USDC_TOKEN), usdc_limit_after.limit, ET_LIDO_LABS_STABLES_LIMIT * 10**6, LIDO_LABS_TRUSTED_CALLER, LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY)
            et_limit_test(stranger, interface.ERC20(DAI_TOKEN), dai_limit_after.limit, ET_LIDO_LABS_STABLES_LIMIT * 10**18, LIDO_LABS_TRUSTED_CALLER, LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY)
            et_limit_test(stranger, interface.ERC20(USDT_TOKEN), usdt_limit_after.limit, ET_LIDO_LABS_STABLES_LIMIT * 10**6, LIDO_LABS_TRUSTED_CALLER, LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY)
            et_limit_test(stranger, interface.ERC20(LDO_TOKEN), ldo_limit_after.limit, 1_000_000 * 10**18, LEGO_LDO_TRUSTED_CALLER, LEGO_LDO_TOP_UP_ALLOWED_RECIPIENTS_FACTORY)
            et_limit_test(stranger, interface.ERC20(STETH_TOKEN), steth_limit_after.limit, 1_000 * 10**18, GAS_SUPPLY_STETH_TRUSTED_CALLER, GAS_SUPPLY_STETH_TOP_UP_ALLOWED_RECIPIENTS_FACTORY)

            # check Finance limits via Easy Track motion
            finance_limit_test(stranger, interface.ERC20(SUSDS_TOKEN), susds_limit_after.limit, 18, LIDO_LABS_TRUSTED_CALLER, LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY, LIDO_LABS_ALLOWED_RECIPIENTS_REGISTRY)
            finance_limit_test(stranger, interface.ERC20(USDC_TOKEN), usdc_limit_after.limit, 6, LIDO_LABS_TRUSTED_CALLER, LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY, LIDO_LABS_ALLOWED_RECIPIENTS_REGISTRY)
            finance_limit_test(stranger, interface.ERC20(DAI_TOKEN), dai_limit_after.limit, 18, LIDO_LABS_TRUSTED_CALLER, LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY, LIDO_LABS_ALLOWED_RECIPIENTS_REGISTRY)
            finance_limit_test(stranger, interface.ERC20(USDT_TOKEN), usdt_limit_after.limit, 6, LIDO_LABS_TRUSTED_CALLER, LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY, LIDO_LABS_ALLOWED_RECIPIENTS_REGISTRY)
            finance_limit_test(stranger, interface.ERC20(LDO_TOKEN), ldo_limit_after.limit, 18, LEGO_LDO_TRUSTED_CALLER, LEGO_LDO_TOP_UP_ALLOWED_RECIPIENTS_FACTORY, LEGO_LDO_ALLOWED_RECIPIENTS_REGISTRY)
            finance_limit_test(stranger, interface.ERC20(STETH_TOKEN), steth_limit_after.limit, 18, GAS_SUPPLY_STETH_TRUSTED_CALLER, GAS_SUPPLY_STETH_TOP_UP_ALLOWED_RECIPIENTS_FACTORY, GAS_SUPPLY_STETH_ALLOWED_RECIPIENTS_REGISTRY)

            # sUSDS can be removed after being added to the allowed list
            chain.snapshot()
            stablecoins_allowed_tokens_registry.grantRole(
                convert.to_uint(web3.keccak(text=REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE)),
                VOTING,
                {"from": VOTING}
            )
            assert stablecoins_allowed_tokens_registry.isTokenAllowed(SUSDS_TOKEN)
            stablecoins_allowed_tokens_registry.removeToken(
                SUSDS_TOKEN,
                {"from": VOTING}
            )
            assert not stablecoins_allowed_tokens_registry.isTokenAllowed(SUSDS_TOKEN)
            with reverts("TOKEN_NOT_ALLOWED"):
                create_and_enact_payment_motion(
                    interface.EasyTrack(EASY_TRACK),
                    LIDO_LABS_TRUSTED_CALLER,
                    LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
                    interface.ERC20(SUSDS_TOKEN),
                    [accounts.at(LIDO_LABS_TRUSTED_CALLER, force=True)],
                    [1 * 10**18],
                stranger,
                )
            chain.revert()

            # spending tokens not from the allowed list should fail
            chain.snapshot()
            with reverts("TOKEN_NOT_ALLOWED"):
                create_and_enact_payment_motion(
                    interface.EasyTrack(EASY_TRACK),
                    LIDO_LABS_TRUSTED_CALLER,
                    LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
                    interface.ERC20(WSTETH_TOKEN),
                    [accounts.at(LIDO_LABS_TRUSTED_CALLER, force=True)],
                    [1 * 10**18],
                    stranger,
                )
            chain.revert()

            # spending the allowed token not from the Finance CREATE_PAYMENTS_ROLE's list should fail
            chain.snapshot()
            stablecoins_allowed_tokens_registry.grantRole(
                convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
                VOTING,
                {"from": VOTING}
            )
            assert not stablecoins_allowed_tokens_registry.isTokenAllowed(WSTETH_TOKEN)
            stablecoins_allowed_tokens_registry.addToken(
                WSTETH_TOKEN,
                {"from": VOTING}
            )
            assert stablecoins_allowed_tokens_registry.isTokenAllowed(WSTETH_TOKEN)
            with reverts("APP_AUTH_FAILED"):
                create_and_enact_payment_motion(
                    interface.EasyTrack(EASY_TRACK),
                    LIDO_LABS_TRUSTED_CALLER,
                    LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
                    interface.ERC20(WSTETH_TOKEN),
                    [accounts.at(LIDO_LABS_TRUSTED_CALLER, force=True)],
                    [1 * 10**18],
                stranger,
                )
            chain.revert()

            # happy path
            usds_wrap_happy_path(stranger)


    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================

            # Item 1.1
            curated_module_before = staking_router.getStakingModule(CURATED_MODULE_ID)
            assert curated_module_before['stakeShareLimit'] == CURATED_MODULE_TARGET_SHARE_BP
            assert curated_module_before['id'] == CURATED_MODULE_ID
            assert curated_module_before['priorityExitShareThreshold'] == CURATED_MODULE_PRIORITY_EXIT_THRESHOLD_BP
            assert curated_module_before['stakingModuleFee'] == CURATED_MODULE_OLD_MODULE_FEE_BP
            assert curated_module_before['treasuryFee'] == CURATED_MODULE_OLD_TREASURY_FEE_BP
            assert curated_module_before['maxDepositsPerBlock'] == CURATED_MODULE_MAX_DEPOSITS_PER_BLOCK
            assert curated_module_before['minDepositBlockDistance'] == CURATED_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE
            assert curated_module_before['name'] == CURATED_MODULE_NAME

            # Item 1.2
            sdvt_module_before = staking_router.getStakingModule(SDVT_MODULE_ID)
            assert sdvt_module_before['stakeShareLimit'] == SDVT_MODULE_OLD_TARGET_SHARE_BP
            assert sdvt_module_before['id'] == SDVT_MODULE_ID
            assert sdvt_module_before['priorityExitShareThreshold'] == SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP
            assert sdvt_module_before['stakingModuleFee'] == SDVT_MODULE_MODULE_FEE_BP
            assert sdvt_module_before['treasuryFee'] == SDVT_MODULE_TREASURY_FEE_BP
            assert sdvt_module_before['maxDepositsPerBlock'] == SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK
            assert sdvt_module_before['minDepositBlockDistance'] == SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE
            assert sdvt_module_before['name'] == SDVT_MODULE_NAME

            # Items 1.3,1.4
            trp_limit_before, trp_period_duration_months_before = et_trp_registry.getLimitParameters()
            trp_already_spent_amount_before, trp_spendable_balance_before, trp_period_start_before, trp_period_end_before = et_trp_registry.getPeriodState()
            assert trp_limit_before == TRP_LIMIT_BEFORE
            assert trp_period_duration_months_before == TRP_PERIOD_DURATION_MONTHS
            assert trp_spendable_balance_before == TRP_LIMIT_BEFORE - trp_already_spent_amount_before
            assert trp_period_start_before == TRP_PERIOD_START_TIMESTAMP
            assert trp_period_end_before == TRP_PERIOD_END_TIMESTAMP


            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)
                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_COUNT
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

                # validate all DG events
                validate_staking_module_update_event(
                    event=dg_events[0],
                    module_item=StakingModuleItem(
                        id=CURATED_MODULE_ID,
                        name=CURATED_MODULE_NAME,
                        address=None,
                        target_share=CURATED_MODULE_TARGET_SHARE_BP,
                        module_fee=CURATED_MODULE_NEW_MODULE_FEE_BP,
                        treasury_fee=CURATED_MODULE_NEW_TREASURY_FEE_BP,
                        priority_exit_share=CURATED_MODULE_PRIORITY_EXIT_THRESHOLD_BP),
                    emitted_by=STAKING_ROUTER
                )
                validate_staking_module_update_event(
                    event=dg_events[1],
                    module_item=StakingModuleItem(
                        id=SDVT_MODULE_ID,
                        name=SDVT_MODULE_NAME,
                        address=None,
                        target_share=SDVT_MODULE_NEW_TARGET_SHARE_BP,
                        module_fee=SDVT_MODULE_MODULE_FEE_BP,
                        treasury_fee=SDVT_MODULE_TREASURY_FEE_BP,
                        priority_exit_share=SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP),
                    emitted_by=STAKING_ROUTER
                )
                validate_set_spent_amount_event(
                    dg_events[2],
                    new_spent_amount=0,
                    emitted_by=ET_TRP_REGISTRY,
                )
                validate_set_limit_parameter_event(
                    dg_events[3],
                    limit=TRP_LIMIT_AFTER,
                    period_duration_month=TRP_PERIOD_DURATION_MONTHS,
                    period_start_timestamp=TRP_PERIOD_START_TIMESTAMP,
                    emitted_by=ET_TRP_REGISTRY,
                )

        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # Item 1.1
        curated_module_after = staking_router.getStakingModule(CURATED_MODULE_ID)
        assert curated_module_after['stakingModuleFee'] == CURATED_MODULE_NEW_MODULE_FEE_BP
        assert curated_module_after['treasuryFee'] == CURATED_MODULE_NEW_TREASURY_FEE_BP
        assert curated_module_after['id'] == CURATED_MODULE_ID
        assert curated_module_after['stakeShareLimit'] == CURATED_MODULE_TARGET_SHARE_BP
        assert curated_module_after['priorityExitShareThreshold'] == CURATED_MODULE_PRIORITY_EXIT_THRESHOLD_BP
        assert curated_module_after['maxDepositsPerBlock'] == CURATED_MODULE_MAX_DEPOSITS_PER_BLOCK
        assert curated_module_after['minDepositBlockDistance'] == CURATED_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE
        assert curated_module_after['name'] == CURATED_MODULE_NAME
        # additional checks to make sure no other fields were changed
        assert curated_module_after['id'] == curated_module_before['id']
        assert curated_module_after['stakingModuleAddress'] == curated_module_before['stakingModuleAddress']
        assert curated_module_after['stakeShareLimit'] == curated_module_before['stakeShareLimit']
        assert curated_module_after['status'] == curated_module_before['status']
        assert curated_module_after['name'] == curated_module_before['name']
        assert curated_module_after['lastDepositAt'] == curated_module_before['lastDepositAt']
        assert curated_module_after['lastDepositBlock'] == curated_module_before['lastDepositBlock']
        assert curated_module_after['exitedValidatorsCount'] == curated_module_before['exitedValidatorsCount']
        assert curated_module_after['maxDepositsPerBlock'] == curated_module_before['maxDepositsPerBlock']
        assert curated_module_after['minDepositBlockDistance'] == curated_module_before['minDepositBlockDistance']
        assert curated_module_after['priorityExitShareThreshold'] == curated_module_before['priorityExitShareThreshold']
        assert len(curated_module_after.items()) == len(curated_module_before.items())
        assert len(curated_module_after.items()) == 13

        # Item 1.2
        sdvt_module_after = staking_router.getStakingModule(SDVT_MODULE_ID)
        assert sdvt_module_after['stakeShareLimit'] == SDVT_MODULE_NEW_TARGET_SHARE_BP
        assert sdvt_module_after['id'] == SDVT_MODULE_ID
        assert sdvt_module_after['priorityExitShareThreshold'] == SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP
        assert sdvt_module_after['stakingModuleFee'] == SDVT_MODULE_MODULE_FEE_BP
        assert sdvt_module_after['treasuryFee'] == SDVT_MODULE_TREASURY_FEE_BP
        assert sdvt_module_after['maxDepositsPerBlock'] == SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK
        assert sdvt_module_after['minDepositBlockDistance'] == SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE
        assert sdvt_module_after['name'] == SDVT_MODULE_NAME
        # additional checks to make sure no other fields were changed
        assert sdvt_module_after['id'] == sdvt_module_before['id']
        assert sdvt_module_after['stakingModuleAddress'] == sdvt_module_before['stakingModuleAddress']
        assert sdvt_module_after['stakingModuleFee'] == sdvt_module_before['stakingModuleFee']
        assert sdvt_module_after['treasuryFee'] == sdvt_module_before['treasuryFee']
        assert sdvt_module_after['status'] == sdvt_module_before['status']
        assert sdvt_module_after['name'] == sdvt_module_before['name']
        assert sdvt_module_after['lastDepositAt'] == sdvt_module_before['lastDepositAt']
        assert sdvt_module_after['lastDepositBlock'] == sdvt_module_before['lastDepositBlock']
        assert sdvt_module_after['exitedValidatorsCount'] == sdvt_module_before['exitedValidatorsCount']
        assert sdvt_module_after['maxDepositsPerBlock'] == sdvt_module_before['maxDepositsPerBlock']
        assert sdvt_module_after['minDepositBlockDistance'] == sdvt_module_before['minDepositBlockDistance']
        assert sdvt_module_after['priorityExitShareThreshold'] == sdvt_module_before['priorityExitShareThreshold']
        assert len(sdvt_module_after.items()) == len(sdvt_module_before.items())
        assert len(sdvt_module_after.items()) == 13

        # Items 1.3,1.4
        trp_limit_after, trp_period_duration_months_after = et_trp_registry.getLimitParameters()
        trp_already_spent_amount_after, trp_spendable_balance_after, trp_period_start_after, trp_period_end_after = et_trp_registry.getPeriodState()
        assert trp_limit_after == TRP_LIMIT_AFTER
        assert trp_period_duration_months_after == TRP_PERIOD_DURATION_MONTHS
        assert trp_already_spent_amount_after == TRP_ALREADY_SPENT_AFTER
        assert trp_spendable_balance_after == TRP_LIMIT_AFTER - TRP_ALREADY_SPENT_AFTER
        assert trp_period_start_after == TRP_PERIOD_START_TIMESTAMP
        assert trp_period_end_after == TRP_PERIOD_END_TIMESTAMP

        # scenraio test for TRP ET factory behavior after the vote
        trp_limit_test(stranger)


def trp_limit_test(stranger):

    easy_track = interface.EasyTrack(EASY_TRACK)
    ldo_token = interface.ERC20(LDO_TOKEN)
    to_spend = TRP_LIMIT_AFTER - TRP_ALREADY_SPENT_AFTER
    max_spend_at_once = 5_000_000 * 10**18
    trp_committee_account = accounts.at(TRP_COMMITTEE, force=True)

    chain.snapshot()

    # check that there is no way to spend more then expected
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            TRP_COMMITTEE,
            TRP_TOP_UP_EVM_SCRIPT_FACTORY,
            ldo_token,
            [trp_committee_account],
            [to_spend + 1],
            stranger,
        )
    
    # spend all in several transfers
    recipients = []
    amounts = []
    while to_spend > 0:
        recipients.append(trp_committee_account)
        amounts.append(min(max_spend_at_once, to_spend))
        to_spend -= min(max_spend_at_once, to_spend)

    create_and_enact_payment_motion(
        easy_track,
        TRP_COMMITTEE,
        TRP_TOP_UP_EVM_SCRIPT_FACTORY,
        ldo_token,
        recipients,
        amounts,
        stranger,
    )

    # make sure there is nothing left so that you can't spend anymore
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            TRP_COMMITTEE,
            TRP_TOP_UP_EVM_SCRIPT_FACTORY,
            ldo_token,
            [trp_committee_account],
            [1],
            stranger,
        )

    chain.revert()

def et_limit_test(stranger, token, max_spend_at_once, to_spend, TRUSTED_CALLER, TOP_UP_ALLOWED_RECIPIENTS_FACTORY):

    easy_track = interface.EasyTrack(EASY_TRACK)
    trusted_caller_account = accounts.at(TRUSTED_CALLER, force=True)

    chain.snapshot()

    # check that there is no way to spend more then expected
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            TRUSTED_CALLER,
            TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
            token,
            [trusted_caller_account],
            [to_spend + 1],
            stranger,
        )
    
    # spend all in several transfers
    recipients = []
    amounts = []
    while to_spend > 0:
        recipients.append(trusted_caller_account)
        amounts.append(min(max_spend_at_once, to_spend))
        to_spend -= min(max_spend_at_once, to_spend)

    create_and_enact_payment_motion(
        easy_track,
        TRUSTED_CALLER,
        TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
        token,
        recipients,
        amounts,
        stranger,
    )

    # make sure there is nothing left so that you can't spend anymore
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            TRUSTED_CALLER,
            TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
            token,
            [trusted_caller_account],
            [1],
            stranger,
        )

    chain.revert()


def finance_limit_test(stranger, token, to_spend, decimals, TRUSTED_CALLER, TOP_UP_ALLOWED_RECIPIENTS_FACTORY, ALLOWED_RECIPIENTS_REGISTRY):

    easy_track = interface.EasyTrack(EASY_TRACK)
    trusted_caller_account = accounts.at(TRUSTED_CALLER, force=True)

    chain.snapshot()

    # for Finance limit check - we first raise ET limits to 10 x finance_limit to be able to spend via Finance
    interface.AllowedRecipientRegistry(ALLOWED_RECIPIENTS_REGISTRY).setLimitParameters(
        (to_spend / (10**decimals) * 10**18) * 10, # 10 x finance_limit
        3, # 3 months
        {"from": AGENT}
    )

    # check that there is no way to spend more then expected
    with reverts("APP_AUTH_FAILED"):
        create_and_enact_payment_motion(
            easy_track,
            TRUSTED_CALLER,
            TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
            token,
            [trusted_caller_account],
            [to_spend + 1],
            stranger,
        )
    
    # spend the allowed balance
    create_and_enact_payment_motion(
        easy_track,
        TRUSTED_CALLER,
        TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
        token,
        [trusted_caller_account],
        [to_spend],
        stranger,
    )

    chain.revert()


def usds_wrap_happy_path(stranger):
    USDC_FOR_TRANSFER = 1000
    USDS_TOKEN = "0xdC035D45d973E3EC169d2276DDab16f1e407384F"
    
    easy_track = interface.EasyTrack(EASY_TRACK)
    usdc = interface.Usdc(USDC_TOKEN)     
    psmVariant1Actions = interface.PSMVariant1Actions(PSM_VARIANT1_ACTIONS)
    usds_token = interface.Usds(USDS_TOKEN)
    susds_token = interface.Susds(SUSDS_TOKEN)
    
    eoa = accounts[0]

    chain.snapshot()

    initial_susds_agent_balance = susds_token.balanceOf(AGENT)

    # fund EOA with USDC from Treasury
    interface.AllowedRecipientRegistry(LIDO_LABS_ALLOWED_RECIPIENTS_REGISTRY).addRecipient(
        eoa.address,
        "EOA_test",
        {"from": AGENT}
    )
    create_and_enact_payment_motion(
        easy_track,
        LIDO_LABS_TRUSTED_CALLER,
        LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
        usdc,
        [eoa],
        [USDC_FOR_TRANSFER * 10**6],
        stranger,
    )
    assert usdc.balanceOf(eoa.address) == USDC_FOR_TRANSFER * 10**6
    assert usds_token.balanceOf(eoa.address) == 0
    assert susds_token.balanceOf(eoa.address) == 0

    # wrap USDC to sUSDS via PSM
    usdc.approve(PSM_VARIANT1_ACTIONS, USDC_FOR_TRANSFER * 10**6, {"from": eoa})
    psmVariant1Actions.swapAndDeposit(eoa.address, USDC_FOR_TRANSFER * 10**6, USDC_FOR_TRANSFER * 10**18, {"from": eoa})
    assert usdc.balanceOf(eoa.address) == 0
    assert usds_token.balanceOf(eoa.address) == 0
    susds_balance = susds_token.balanceOf(eoa.address)
    assert susds_balance <= USDC_FOR_TRANSFER * 10**18
    assert susds_balance >= USDC_FOR_TRANSFER * 10**18 * 0.9

    # send sUSDS back to Treasury
    susds_token.transfer(AGENT, susds_balance, {"from": eoa})
    assert susds_token.balanceOf(eoa.address) == 0
    assert susds_token.balanceOf(AGENT) == susds_balance + initial_susds_agent_balance
    print("swapped", USDC_FOR_TRANSFER, "USDC to", susds_balance / 10**18, "sUSDS")

    # send sUSDS again to EOA via Easy Track payment from Treasury
    create_and_enact_payment_motion(
        easy_track,
        LIDO_LABS_TRUSTED_CALLER,
        LIDO_LABS_TOP_UP_ALLOWED_RECIPIENTS_FACTORY,
        susds_token,
        [eoa],
        [susds_balance],
        stranger,
    )
    assert susds_token.balanceOf(eoa.address) == susds_balance
    assert susds_token.balanceOf(AGENT) == initial_susds_agent_balance

    # wait 1 year to accumulate interest on sUSDS
    chain.sleep(365 * 24 * 3600)
    chain.mine()
    susds_token.drip({"from": eoa})
    INTEREST_RATE = 0.04

    # unwrap sUSDS to USDC
    susds_token.approve(PSM_VARIANT1_ACTIONS, susds_balance, {"from": eoa})
    psmVariant1Actions.withdrawAndSwap(eoa.address, USDC_FOR_TRANSFER * 10**6 * (1 + INTEREST_RATE), USDC_FOR_TRANSFER * 10**18 * (1 + INTEREST_RATE), {"from": eoa})
    usdc_balance = usdc.balanceOf(eoa.address)
    print("swapped", susds_balance / 10**18, "sUSDS to", usdc_balance / 10**6, "USDC, leftover:", susds_token.balanceOf(eoa.address) / 10**18, "sUSDS")
    assert susds_token.balanceOf(eoa.address) < 5.0 * 10**18 # leftover from interest surplus
    assert usdc.balanceOf(eoa.address) == USDC_FOR_TRANSFER * 10**6 * (1 + INTEREST_RATE)

    chain.revert()


def prepare_agent_for_dai_payment(amount: int):
    agent, dai = interface.Agent(AGENT), interface.Dai(DAI_TOKEN)
    if dai.balanceOf(agent) < amount:
        dai_ward_impersonated = accounts.at("0x9759A6Ac90977b93B58547b4A71c78317f391A28", force=True)
        dai.mint(agent, amount, {"from": dai_ward_impersonated})

    assert dai.balanceOf(agent) >= amount, f"Insufficient DAI balance"


def prepare_agent_for_usdc_payment(amount: int):
    agent, usdc = interface.Agent(AGENT), interface.Usdc(USDC_TOKEN)
    if usdc.balanceOf(agent) < amount:
        usdc_minter = accounts.at("0x5B6122C109B78C6755486966148C1D70a50A47D7", force=True)
        usdc_controller = accounts.at("0x79E0946e1C186E745f1352d7C21AB04700C99F71", force=True)
        usdc_master_minter = interface.UsdcMasterMinter("0xE982615d461DD5cD06575BbeA87624fda4e3de17")
        usdc_master_minter.incrementMinterAllowance(amount, {"from": usdc_controller})
        usdc.mint(agent, amount, {"from": usdc_minter})

    assert usdc.balanceOf(agent) >= amount, "Insufficient USDC balance"


def prepare_agent_for_usdt_payment(amount: int):
    agent, usdt = interface.Agent(AGENT), interface.Usdt(USDT_TOKEN)
    if usdt.balanceOf(agent) < amount:
        usdt_owner = accounts.at("0xC6CDE7C39eB2f0F0095F41570af89eFC2C1Ea828", force=True)
        usdt.issue(amount, {"from": usdt_owner})
        usdt.transfer(agent, amount, {"from": usdt_owner})

    assert usdt.balanceOf(agent) >= amount, "Insufficient USDT balance"


def prepare_agent_for_susds_payment(amount: int):
    agent, susds = interface.Agent(AGENT), interface.ERC20(SUSDS_TOKEN)
    if susds.balanceOf(agent) < amount:
        susds_whale = accounts.at("0xBc65ad17c5C0a2A4D159fa5a503f4992c7B545FE", force=True)
        susds.transfer(agent, amount, {"from": susds_whale})

    assert susds.balanceOf(agent) >= amount, "Insufficient sUSDS balance"


def prepare_agent_for_ldo_payment(amount: int):
    agent, ldo = interface.Agent(AGENT), interface.ERC20(LDO_TOKEN)
    assert ldo.balanceOf(agent) >= amount, "Insufficient LDO balance 🫡"


def prepare_agent_for_steth_payment(amount: int):
    STETH_TRANSFER_MAX_DELTA = 2

    agent, steth = interface.Agent(AGENT), interface.Lido(STETH_TOKEN)
    eth_whale = accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)
    if steth.balanceOf(agent) < amount:
        steth.submit(ZERO_ADDRESS, {"from": eth_whale, "value": amount + 2 * STETH_TRANSFER_MAX_DELTA})
        steth.transfer(agent, amount + STETH_TRANSFER_MAX_DELTA, {"from": eth_whale})
    assert steth.balanceOf(agent) >= amount, "Insufficient stETH balance"
