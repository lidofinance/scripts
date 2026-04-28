from brownie import interface
from brownie.network.transaction import TransactionReceipt

from utils.test.helpers import almostEqWithDiff
from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
)
from utils.evm_script import encode_call_script

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.event_validators.payout import Payout, validate_token_payout_event

# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2026_04_23 import (
    start_vote,
    get_vote_items,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"

STETH = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
LIDO_LABS_MULTISIG = "0x95B521B4F55a447DB89f6a27f951713fC2035f3F"

LDO = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"
USDT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
SUSDS = "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD"
DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WSTETH = "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0"

PAYMENT_AMOUNT = 2500 * 10**18


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = 200
EXPECTED_VOTE_EVENTS_COUNT = 1

IPFS_DESCRIPTION_HASH = "bafkreidq5uylzwlkr4pahs2pmxwekglv5shmhmvaol7vio6g2sdwkp4efi"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    steth = interface.Lido(STETH)

    treasury_tokens = [
        interface.MiniMeToken(LDO),
        interface.Usdt(USDT),
        interface.Susds(SUSDS),
        interface.Dai(DAI),
        interface.Usdc(USDC),
        interface.WstETH(WSTETH),
    ]

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
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()

    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        treasury_steth_balance_before = steth.balanceOf(AGENT)
        lido_labs_multisig_steth_balance_before = steth.balanceOf(LIDO_LABS_MULTISIG)
        other_treasury_token_balances_before = [token.balanceOf(AGENT) for token in treasury_tokens]

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        assert treasury_steth_balance_before >= PAYMENT_AMOUNT, "Not enough stETH in treasury"

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        treasury_steth_balance_after = steth.balanceOf(AGENT)
        lido_labs_multisig_steth_balance_after = steth.balanceOf(LIDO_LABS_MULTISIG)
        other_treasury_token_balances_after = [token.balanceOf(AGENT) for token in treasury_tokens]

        assert almostEqWithDiff(treasury_steth_balance_after, treasury_steth_balance_before - PAYMENT_AMOUNT, diff=2)
        assert almostEqWithDiff(
            lido_labs_multisig_steth_balance_after, lido_labs_multisig_steth_balance_before + PAYMENT_AMOUNT, diff=2
        )
        for token, token_balance_before, token_balance_after in zip(
            treasury_tokens, other_treasury_token_balances_before, other_treasury_token_balances_after
        ):
            assert token_balance_before == token_balance_after, f"Treasury balance of the token {token} changed"

        # Simulate the refund of the payment back to the Aragon Agent
        steth.transfer(AGENT, PAYMENT_AMOUNT // 2, {"from": LIDO_LABS_MULTISIG})
        assert almostEqWithDiff(
            steth.balanceOf(LIDO_LABS_MULTISIG), lido_labs_multisig_steth_balance_before + PAYMENT_AMOUNT // 2, diff=2
        )
        assert almostEqWithDiff(steth.balanceOf(AGENT), treasury_steth_balance_before - PAYMENT_AMOUNT // 2, diff=2)

        steth.transfer(AGENT, PAYMENT_AMOUNT // 2, {"from": LIDO_LABS_MULTISIG})
        assert almostEqWithDiff(steth.balanceOf(LIDO_LABS_MULTISIG), lido_labs_multisig_steth_balance_before, diff=2)
        assert almostEqWithDiff(steth.balanceOf(AGENT), treasury_steth_balance_before, diff=2)

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        validate_token_payout_event(
            vote_events[0],
            Payout(STETH, AGENT, LIDO_LABS_MULTISIG, PAYMENT_AMOUNT),
            is_steth=True,
            emitted_by=AGENT,
        )
