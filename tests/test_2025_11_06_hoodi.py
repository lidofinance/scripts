from brownie import chain, interface, web3, convert, reverts, accounts
from brownie.network.transaction import TransactionReceipt

from typing import List, NamedTuple

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
)
from utils.evm_script import encode_call_script
from utils.test.event_validators.allowed_tokens_registry import validate_add_token_event
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.event_validators.permission import (
    validate_grant_role_event,
    validate_revoke_role_event,
    Permission,
    validate_permission_grantp_event,
    validate_permission_revoke_event,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op

class TokenLimit(NamedTuple):
    address: str
    limit: int


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2025_11_06_hoodi import start_vote, get_vote_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
AGENT = "0x0534aA41907c9631fae990960bCC72d75fA7cfeD"
VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"
EASY_TRACK = "0x284D91a7D47850d21A6DEaaC6E538AC7E5E6fc2a"
ET_EVM_SCRIPT_EXECUTOR = "0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E"
ACL = "0x78780e70Eae33e2935814a327f7dB6c01136cc62"
FINANCE = "0x254Ae22bEEba64127F0e59fe8593082F3cd13f6b"

SANDBOX_STABLES_ALLOWED_TOKENS_REGISTRY = "0x40Db7E8047C487bD8359289272c717eA3C34D1D3"
SANDBOX_STABLES_TRUSTED_CALLER = "0x418B816A7c3ecA151A31d98e30aa7DAa33aBf83A"
SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY="0x9D735eeDfa96F53BF9d31DbE81B51a5d333198dB"
SANDBOX_STABLES_ALLOWED_RECIPIENTS_REGISTRY = "0xdf53b1cd4CFE43b6CdA3640Be0e4f1a45126ec61"
SANDBOX_STABLES_ALLOWED_TOKENS_BEFORE = 3
SANDBOX_STABLES_ALLOWED_TOKENS_AFTER = 4
ADD_TOKEN_TO_ALLOWED_LIST_ROLE = "ADD_TOKEN_TO_ALLOWED_LIST_ROLE"
REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE = "REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"
CREATE_PAYMENTS_ROLE = "CREATE_PAYMENTS_ROLE"

AMOUNT_LIMITS_LEN_BEFORE = 0
AMOUNT_LIMITS_LEN_AFTER = 16

SUSDS_TOKEN = "0xDaE6a7669f9aB8b2C4E52464AA6FB7F9402aDc70"
USDC_TOKEN = "0x97bb030B93faF4684eAC76bA0bf3be5ec7140F36"
USDT_TOKEN = "0x64f1904d1b419c6889BDf3238e31A138E258eA68"
DAI_TOKEN = "0x17fc691f6EF57D2CA719d30b8fe040123d4ee319"
STETH_TOKEN = "0x3508a952176b3c15387c97be809eaffb1982176a"
WSTETH_TOKEN = "0x7E99eE3C66636DE415D2d7C880938F2f40f94De4"

ET_SANDBOX_STABLES_LIMIT = 500
FINANCE_SANDBOX_STABLES_LIMIT = 1_000
USDC_LIMIT = TokenLimit(USDC_TOKEN, FINANCE_SANDBOX_STABLES_LIMIT * 10**6)
USDT_LIMIT = TokenLimit(USDT_TOKEN, FINANCE_SANDBOX_STABLES_LIMIT * 10**6)
DAI_LIMIT = TokenLimit(DAI_TOKEN, FINANCE_SANDBOX_STABLES_LIMIT * 10**18)
SUSDS_LIMIT = TokenLimit(SUSDS_TOKEN, FINANCE_SANDBOX_STABLES_LIMIT * 10**18)
STETH_LIMIT = TokenLimit(STETH_TOKEN, 200 * 10**18)

def amount_limits() -> List[Param]:
    token_arg_index = 0
    amount_arg_index = 2

    limits = [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == USDC)
        Param(token_arg_index, Op.EQ, ArgumentValue(USDC_LIMIT.address)),
        # 2: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(USDC_LIMIT.limit)),
        #
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == USDT)
        Param(token_arg_index, Op.EQ, ArgumentValue(USDT_LIMIT.address)),
        # 5: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(USDT_LIMIT.limit)),
        #
        # 6: else if (7) then (8) else (9)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=7, success=8, failure=9)
        ),
        # 7: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(DAI_LIMIT.address)),
        # 8: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(DAI_LIMIT.limit)),
        #
        # 9: else if (10) then (11) else (12)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=10, success=11, failure=12),
        ),
        # 10: (_token == SUSDS)
        Param(token_arg_index, Op.EQ, ArgumentValue(SUSDS_LIMIT.address)),
        # 11: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(SUSDS_LIMIT.limit)),
        #
        # 12: else if (13) then (14) else (15)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=13, success=14, failure=15),
        ),
        # 13: (_token == STETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(STETH_LIMIT.address)),
        # 14: { return _amount <= 200 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(STETH_LIMIT.limit)),
        #
        # 15: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]

    assert len(limits) == AMOUNT_LIMITS_LEN_AFTER

    return limits

EXPECTED_VOTE_ID = 45
EXPECTED_VOTE_EVENTS_COUNT = 5
IPFS_DESCRIPTION_HASH = "bafkreiewx36sw74mspun3gwp4czkhw4gxgt75dosp6ukxo5tlmz7lgdzwy"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    acl = interface.ACL(ACL)
    sandbox_stables_allowed_tokens_registry = interface.AllowedTokensRegistry(SANDBOX_STABLES_ALLOWED_TOKENS_REGISTRY)


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

        # Items 1, 3
        assert not sandbox_stables_allowed_tokens_registry.hasRole(
            convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
            VOTING
        )

        # Item 2
        assert not sandbox_stables_allowed_tokens_registry.isTokenAllowed(SUSDS_TOKEN)
        allowed_tokens_before = sandbox_stables_allowed_tokens_registry.getAllowedTokens()
        assert len(allowed_tokens_before) == SANDBOX_STABLES_ALLOWED_TOKENS_BEFORE
        assert allowed_tokens_before[0] == USDC_TOKEN
        assert allowed_tokens_before[1] == USDT_TOKEN
        assert allowed_tokens_before[2] == DAI_TOKEN

        # Items 4, 5
        assert acl.hasPermission['address,address,bytes32,uint[]'](
            ET_EVM_SCRIPT_EXECUTOR,
            FINANCE,
            convert.to_uint(web3.keccak(text=CREATE_PAYMENTS_ROLE)),
            [0] # NO_PERMISSION
        )
        assert acl.getPermissionParamsLength(
            ET_EVM_SCRIPT_EXECUTOR,
            FINANCE,
            convert.to_uint(web3.keccak(text=CREATE_PAYMENTS_ROLE))
        ) == AMOUNT_LIMITS_LEN_BEFORE

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        # Items 1, 3
        assert not sandbox_stables_allowed_tokens_registry.hasRole(
            convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
            VOTING
        )

        # Item 2
        assert sandbox_stables_allowed_tokens_registry.isTokenAllowed(SUSDS_TOKEN)
        allowed_tokens_after = sandbox_stables_allowed_tokens_registry.getAllowedTokens()
        assert len(allowed_tokens_after) == SANDBOX_STABLES_ALLOWED_TOKENS_AFTER
        assert allowed_tokens_after[0] == USDC_TOKEN
        assert allowed_tokens_after[1] == USDT_TOKEN
        assert allowed_tokens_after[2] == DAI_TOKEN
        assert allowed_tokens_after[3] == SUSDS_TOKEN

        # Items 4, 5
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
            assert id == amount_limits()[i].id
            assert op == amount_limits()[i].op.value
            assert val == amount_limits()[i].value


        # =======================================================================
        # ============================ Events checks ============================
        # =======================================================================
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        validate_grant_role_event(
            events=vote_events[0],
            role=web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE).hex(),
            grant_to=VOTING,
            sender=VOTING,
            emitted_by=SANDBOX_STABLES_ALLOWED_TOKENS_REGISTRY,
            is_dg_event=False,
        )
        validate_add_token_event(
            event=vote_events[1],
            token=SUSDS_TOKEN,
            emitted_by=SANDBOX_STABLES_ALLOWED_TOKENS_REGISTRY
        )
        validate_revoke_role_event(
            events=vote_events[2],
            role=web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE).hex(),
            revoke_from=VOTING,
            sender=VOTING,
            emitted_by=SANDBOX_STABLES_ALLOWED_TOKENS_REGISTRY,
            is_dg_event=False,
        )
        validate_permission_revoke_event(
            event=vote_events[3],
            p=Permission(
                app=FINANCE,
                entity=ET_EVM_SCRIPT_EXECUTOR,
                role=web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_permission_grantp_event(
            event=vote_events[4],
            p=Permission(
                app=FINANCE,
                entity=ET_EVM_SCRIPT_EXECUTOR,
                role=web3.keccak(text=CREATE_PAYMENTS_ROLE).hex(),
            ),
            params=amount_limits(),
            emitted_by=ACL,
        )

        # =======================================================================
        # =========================== Scenario checks ===========================
        # =======================================================================

        # check ET limits
        et_limit_test(stranger, interface.ERC20(SUSDS_TOKEN), SUSDS_LIMIT.limit, ET_SANDBOX_STABLES_LIMIT * 10**18)
        et_limit_test(stranger, interface.ERC20(USDC_TOKEN), USDC_LIMIT.limit, ET_SANDBOX_STABLES_LIMIT * 10**6)
        et_limit_test(stranger, interface.ERC20(DAI_TOKEN), DAI_LIMIT.limit, ET_SANDBOX_STABLES_LIMIT * 10**18)
        et_limit_test(stranger, interface.ERC20(USDT_TOKEN), USDT_LIMIT.limit, ET_SANDBOX_STABLES_LIMIT * 10**6)

        # check Finance limits
        finance_limit_test(stranger, interface.ERC20(SUSDS_TOKEN), SUSDS_LIMIT.limit, 18)
        finance_limit_test(stranger, interface.ERC20(USDC_TOKEN), USDC_LIMIT.limit, 6)
        finance_limit_test(stranger, interface.ERC20(DAI_TOKEN), DAI_LIMIT.limit, 18)
        finance_limit_test(stranger, interface.ERC20(USDT_TOKEN), USDT_LIMIT.limit, 6)

        # sUSDS can be removed after being added to the allowed list
        chain.snapshot()
        sandbox_stables_allowed_tokens_registry.grantRole(
            convert.to_uint(web3.keccak(text=REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE)),
            VOTING,
            {"from": VOTING}
        )
        assert sandbox_stables_allowed_tokens_registry.isTokenAllowed(SUSDS_TOKEN)
        sandbox_stables_allowed_tokens_registry.removeToken(
            SUSDS_TOKEN,
            {"from": VOTING}
        )
        assert not sandbox_stables_allowed_tokens_registry.isTokenAllowed(SUSDS_TOKEN)
        with reverts("TOKEN_NOT_ALLOWED"):
            create_and_enact_payment_motion(
                interface.EasyTrack(EASY_TRACK),
                SANDBOX_STABLES_TRUSTED_CALLER,
                SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
                interface.ERC20(SUSDS_TOKEN),
                [accounts.at(SANDBOX_STABLES_TRUSTED_CALLER, force=True)],
                [1 * 10**18],
               stranger,
            )
        chain.revert()

        # spending tokens not from the allowed list should fail
        chain.snapshot()
        with reverts("TOKEN_NOT_ALLOWED"):
            create_and_enact_payment_motion(
                interface.EasyTrack(EASY_TRACK),
                SANDBOX_STABLES_TRUSTED_CALLER,
                SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
                interface.ERC20(STETH_TOKEN),
                [accounts.at(SANDBOX_STABLES_TRUSTED_CALLER, force=True)],
                [1 * 10**18],
                stranger,
            )
        chain.revert()

        # spending the allowed token not from the Finance CREATE_PAYMENTS_ROLE's list should fail
        chain.snapshot()
        sandbox_stables_allowed_tokens_registry.grantRole(
            convert.to_uint(web3.keccak(text=ADD_TOKEN_TO_ALLOWED_LIST_ROLE)),
            VOTING,
            {"from": VOTING}
        )
        assert not sandbox_stables_allowed_tokens_registry.isTokenAllowed(WSTETH_TOKEN)
        sandbox_stables_allowed_tokens_registry.addToken(
            WSTETH_TOKEN,
            {"from": VOTING}
        )
        assert sandbox_stables_allowed_tokens_registry.isTokenAllowed(WSTETH_TOKEN)
        with reverts("APP_AUTH_FAILED"):
            create_and_enact_payment_motion(
                interface.EasyTrack(EASY_TRACK),
                SANDBOX_STABLES_TRUSTED_CALLER,
                SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
                interface.ERC20(WSTETH_TOKEN),
                [accounts.at(SANDBOX_STABLES_TRUSTED_CALLER, force=True)],
                [1 * 10**18],
               stranger,
            )
        chain.revert()

        # happy path
        usds_wrap_happy_path(stranger)


def et_limit_test(stranger, token, max_spend_at_once, to_spend):

    easy_track = interface.EasyTrack(EASY_TRACK)
    trusted_caller_account = accounts.at(SANDBOX_STABLES_TRUSTED_CALLER, force=True)

    chain.snapshot()

    # check that there is no way to spend more then expected
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            SANDBOX_STABLES_TRUSTED_CALLER,
            SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
            token,
            [trusted_caller_account],
            [to_spend + 1],
            stranger,
        )
    
    # spend all step by step
    while to_spend > 0:
        create_and_enact_payment_motion(
            easy_track,
            SANDBOX_STABLES_TRUSTED_CALLER,
            SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
            token,
            [trusted_caller_account],
            [min(max_spend_at_once, to_spend)],
            stranger,
        )
        to_spend -= min(max_spend_at_once, to_spend)

    # make sure there is nothing left so that you can't spend anymore
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            SANDBOX_STABLES_TRUSTED_CALLER,
            SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
            token,
            [trusted_caller_account],
            [1],
            stranger,
        )

    chain.revert()


def finance_limit_test(stranger, token, to_spend, decimals):

    easy_track = interface.EasyTrack(EASY_TRACK)
    trusted_caller_account = accounts.at(SANDBOX_STABLES_TRUSTED_CALLER, force=True)

    chain.snapshot()

    # for Finance limit check - we first raise ET limits to 2 x finance_limit to be able to spend via Finance
    interface.AllowedRecipientRegistry(SANDBOX_STABLES_ALLOWED_RECIPIENTS_REGISTRY).setLimitParameters(
        (to_spend / (10**decimals) * 10**18) * 2, # 2 x finance_limit
        3, # 3 months
        {"from": AGENT}
    )

    # check that there is no way to spend more then expected
    with reverts("APP_AUTH_FAILED"):
        create_and_enact_payment_motion(
            easy_track,
            SANDBOX_STABLES_TRUSTED_CALLER,
            SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
            token,
            [trusted_caller_account],
            [to_spend + 1],
            stranger,
        )
    
    # spend the allowed balance
    create_and_enact_payment_motion(
        easy_track,
        SANDBOX_STABLES_TRUSTED_CALLER,
        SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
        token,
        [trusted_caller_account],
        [to_spend],
        stranger,
    )

    chain.revert()


def usds_wrap_happy_path(stranger):
    easy_track = interface.EasyTrack(EASY_TRACK)
    susds_token = interface.SusdsMock(SUSDS_TOKEN)

    USDS_ADMIN = "0x38E553824Da02022dcE9782d73439e35d28709f2"
    usds_admin = accounts.at(USDS_ADMIN, force=True)
    USDS_TOKEN = "0xd20E228221CB188da431fc227F2cc4B63a7Cb64F"
    usds_token = interface.Usds(USDS_TOKEN)
    USDS_FOR_TRANSFER = 200 * 10**18
    SUSDS_IN_AGENT = 1_000_000 * 10 ** 18

    eoa = accounts[0]

    chain.snapshot()

    # fund EOA with USDS
    usds_token.mint(
        eoa.address,
        USDS_FOR_TRANSFER,
        {"from": usds_admin}
    )
    assert usds_token.balanceOf(eoa.address) == USDS_FOR_TRANSFER
    assert susds_token.balanceOf(eoa.address) == 0

    # wrap USDS to sUSDS
    usds_token.approve(susds_token.address, USDS_FOR_TRANSFER, {"from": eoa})
    susds_token.deposit(USDS_FOR_TRANSFER, eoa.address, {"from": eoa})
    assert susds_token.balanceOf(eoa.address) == USDS_FOR_TRANSFER
    assert usds_token.balanceOf(eoa.address) == 0
    
    # transfers to the Treasury, balances check
    assert usds_token.balanceOf(AGENT) == 0
    assert susds_token.balanceOf(AGENT) == SUSDS_IN_AGENT
    susds_token.transfer(AGENT, USDS_FOR_TRANSFER, {"from": eoa})
    assert usds_token.balanceOf(AGENT) == 0
    assert susds_token.balanceOf(AGENT) == SUSDS_IN_AGENT + USDS_FOR_TRANSFER

    # transfer Y sUSDS back to the EOA by ET motion
    interface.AllowedRecipientRegistry(SANDBOX_STABLES_ALLOWED_RECIPIENTS_REGISTRY).addRecipient(
        eoa.address,
        "EOA_test",
        {"from": AGENT}
    )
    create_and_enact_payment_motion(
        easy_track,
        SANDBOX_STABLES_TRUSTED_CALLER,
        SANDBOX_STABLES_TOP_UP_EVM_SCRIPT_FACTORY,
        susds_token,
        [eoa],
        [USDS_FOR_TRANSFER],
        stranger,
    )
    assert usds_token.balanceOf(AGENT) == 0
    assert susds_token.balanceOf(AGENT) == SUSDS_IN_AGENT
    assert usds_token.balanceOf(eoa.address) == 0
    assert susds_token.balanceOf(eoa.address) == USDS_FOR_TRANSFER

    # unwrap Y sUSDS for USDS
    susds_token.withdraw(USDS_FOR_TRANSFER, eoa.address, eoa.address, {"from": eoa})
    assert susds_token.balanceOf(eoa.address) == 0
    assert usds_token.balanceOf(eoa.address) == USDS_FOR_TRANSFER

    chain.revert()