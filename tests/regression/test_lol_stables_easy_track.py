from brownie import chain, interface, reverts

from utils.config import contracts, DAI_TOKEN
from utils.test.easy_track_helpers import (
    _encode_calldata,
    assert_create_evm_script_reverts,
    create_and_enact_payment_motion,
    create_and_enact_add_recipient_motion,
    create_and_enact_remove_recipient_motion,
)

# LOL (Liquidity Observation Lab) stablecoins Easy Track setup, launched by the 2026-08-05 omnibus
LOL_STABLES_REGISTRY = "0x8d8b35cA51e7808098afF4918C21Ce428c943F89"
LOL_STABLES_TOP_UP_FACTORY = "0xc72d4C3e86b681D7c9EE306D41193C64D709C303"
LOL_STABLES_ADD_RECIPIENT_FACTORY = "0xe24230619e9218C1eed3de3489a22f6BC3ce18FF"
LOL_STABLES_REMOVE_RECIPIENT_FACTORY = "0xF4d5D97C85eD18f77F99B57f55E9E11d52992632"
LOL_TRUSTED_CALLER = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"  # LOL multisig, the only allowed recipient
ALLOWED_TOKENS_REGISTRY = "0x4AC40c34f8992bb1e5E856A448792158022551ca"  # shared across all stables setups
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

DAI_WARD = "0x9759A6Ac90977b93B58547b4A71c78317f391A28"  # authorized DAI minter, funds the Agent on a fork
# ACL cap on a single newImmediatePayment by the EVMScriptExecutor
FINANCE_DAI_MAX_PER_CALL = 2_000_000 * 10**18

PAYMENT_CALLDATA_SIGNATURE = ["address", "address[]", "uint256[]"]


def _assert_setup_is_live(registry):
    """What the omnibus set up: the factories are registered and the executor holds the registry roles."""
    factories = contracts.easy_track.getEVMScriptFactories()
    for factory_address in (
        LOL_STABLES_TOP_UP_FACTORY,
        LOL_STABLES_ADD_RECIPIENT_FACTORY,
        LOL_STABLES_REMOVE_RECIPIENT_FACTORY,
    ):
        assert factory_address in factories, f"{factory_address} not registered in Easy Track"
    assert registry.hasRole(registry.UPDATE_SPENT_AMOUNT_ROLE(), EVM_SCRIPT_EXECUTOR)
    assert registry.hasRole(registry.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE(), EVM_SCRIPT_EXECUTOR)
    assert registry.hasRole(registry.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE(), EVM_SCRIPT_EXECUTOR)


def _start_fresh_spending_period(registry):
    """Move past the stored period so the next payment opens a fresh one with spent == 0.

    getPeriodState reports stored values, and every enacted motion advances the chain by the motion
    duration — without this a run near a period boundary would measure a rollover as an under-spend.
    """
    _, _, _, period_end = registry.getPeriodState()
    chain.mine(1, max(chain.time(), period_end) + 1)
    return period_end


def _fund_agent_with_dai(amount, accounts):
    """Top the Agent up to `amount` DAI through a DAI ward."""
    if contracts.dai_token.balanceOf(contracts.agent) < amount:
        interface.Dai(DAI_TOKEN).mint(contracts.agent, amount, {"from": accounts.at(DAI_WARD, force=True)})
    assert contracts.dai_token.balanceOf(contracts.agent) >= amount, "Insufficient DAI balance on Agent"


def test_lol_stables_motion_guards(stranger):
    """The factories reject unauthorized and out-of-bounds motions at creation."""
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    top_up_factory = interface.TopUpAllowedRecipients(LOL_STABLES_TOP_UP_FACTORY)
    add_recipient_factory = interface.AddAllowedRecipient(LOL_STABLES_ADD_RECIPIENT_FACTORY)
    remove_recipient_factory = interface.RemoveAllowedRecipient(LOL_STABLES_REMOVE_RECIPIENT_FACTORY)
    _assert_setup_is_live(registry)

    # only the LOL multisig can create motions
    assert_create_evm_script_reverts(
        top_up_factory,
        stranger,
        _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [DAI_TOKEN, [LOL_TRUSTED_CALLER], [1]]),
        "CALLER_IS_FORBIDDEN",
    )
    assert_create_evm_script_reverts(
        add_recipient_factory,
        stranger,
        _encode_calldata(["address", "string"], [stranger.address, "Stranger"]),
        "CALLER_IS_FORBIDDEN",
    )
    assert_create_evm_script_reverts(
        remove_recipient_factory,
        stranger,
        _encode_calldata(["address"], [LOL_TRUSTED_CALLER]),
        "CALLER_IS_FORBIDDEN",
    )

    # only tokens listed in the AllowedTokensRegistry
    assert_create_evm_script_reverts(
        top_up_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [contracts.lido.address, [LOL_TRUSTED_CALLER], [1]]),
        "TOKEN_NOT_ALLOWED",
    )
    # only recipients the registry allows
    assert_create_evm_script_reverts(
        top_up_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [DAI_TOKEN, [stranger.address], [1]]),
        "RECIPIENT_NOT_ALLOWED",
    )
    # never more than the period limit
    limit, _ = registry.getLimitParameters()
    assert_create_evm_script_reverts(
        top_up_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [DAI_TOKEN, [LOL_TRUSTED_CALLER], [limit + 1]]),
        "SUM_EXCEEDS_SPENDABLE_BALANCE",
    )

    # no duplicates in the recipients list, and nothing to remove that is not there
    assert_create_evm_script_reverts(
        add_recipient_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(["address", "string"], [LOL_TRUSTED_CALLER, "LOL multisig once more"]),
        "ALLOWED_RECIPIENT_ALREADY_ADDED",
    )
    assert_create_evm_script_reverts(
        remove_recipient_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(["address"], [stranger.address]),
        "ALLOWED_RECIPIENT_NOT_FOUND",
    )


def test_lol_stables_add_and_remove_recipient(accounts, stranger):
    """Whitelist a recipient, pay it, drop it — all three factories in one flow."""
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    _assert_setup_is_live(registry)

    payment_amount = 1_000 * 10**18
    _fund_agent_with_dai(payment_amount, accounts)
    recipients_before = registry.getAllowedRecipients()
    _start_fresh_spending_period(registry)

    create_and_enact_add_recipient_motion(
        contracts.easy_track,
        multisig,
        registry,
        LOL_STABLES_ADD_RECIPIENT_FACTORY,
        stranger,
        "Stranger",
        stranger,
    )
    create_and_enact_payment_motion(
        contracts.easy_track,
        multisig,
        LOL_STABLES_TOP_UP_FACTORY,
        contracts.dai_token,
        [stranger],
        [payment_amount],
        stranger,
    )
    create_and_enact_remove_recipient_motion(
        contracts.easy_track,
        multisig,
        registry,
        LOL_STABLES_REMOVE_RECIPIENT_FACTORY,
        stranger,
        stranger,
    )

    spent_after, _, _, _ = registry.getPeriodState()
    assert spent_after == payment_amount, "the payment was not counted against the period limit"
    assert registry.getAllowedRecipients() == recipients_before, "the allowed recipients list was not restored"


def test_lol_stables_every_allowed_token_counts_against_the_limit(accounts, stranger):
    """Each token the shared registry allows can be paid out, and counts normalized to 18 decimals.

    USDC and USDT hold 6 decimals, so a factory that skipped normalizeAmount would let them spend
    orders of magnitude past the budget while the registry barely noticed.
    """
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    tokens_registry = interface.AllowedTokensRegistry(ALLOWED_TOKENS_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    _assert_setup_is_live(registry)

    allowed_tokens = tokens_registry.getAllowedTokens()
    assert len(allowed_tokens) > 0, "the shared tokens registry allows no tokens"
    _start_fresh_spending_period(registry)

    expected_spent = 0
    for token_address in allowed_tokens:
        token = interface.ERC20(token_address)
        payment_amount = 1_000 * 10 ** token.decimals()
        assert token.balanceOf(contracts.agent) >= payment_amount, f"Agent holds too little {token.symbol()}"

        create_and_enact_payment_motion(
            contracts.easy_track,
            multisig,
            LOL_STABLES_TOP_UP_FACTORY,
            token,
            [multisig],
            [payment_amount],
            stranger,
        )

        expected_spent += tokens_registry.normalizeAmount(payment_amount, token_address)
        spent, _, _, _ = registry.getPeriodState()
        assert spent == expected_spent, f"{token.symbol()} was not counted normalized to 18 decimals"


def test_lol_stables_single_payment_capped_by_acl(accounts, stranger):
    """A single newImmediatePayment cannot exceed the executor's ACL cap, even well under the limit."""
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    _assert_setup_is_live(registry)

    over_the_cap = FINANCE_DAI_MAX_PER_CALL + 1
    limit, _ = registry.getLimitParameters()
    assert over_the_cap < limit, "the ACL cap must bite before the period limit does"
    _fund_agent_with_dai(over_the_cap, accounts)
    _start_fresh_spending_period(registry)

    with reverts("APP_AUTH_FAILED"):
        create_and_enact_payment_motion(
            contracts.easy_track,
            multisig,
            LOL_STABLES_TOP_UP_FACTORY,
            contracts.dai_token,
            [multisig],
            [over_the_cap],
            stranger,
        )


def test_lol_stables_period_limit(accounts, stranger):
    """A whole period's limit can be spent — and not a wei more."""
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    _assert_setup_is_live(registry)

    limit, _ = registry.getLimitParameters()
    _fund_agent_with_dai(limit, accounts)
    period_end_before = _start_fresh_spending_period(registry)

    # the whole budget, as several payments batched into one motion, each within the ACL cap
    recipients = []
    amounts = []
    to_spend = limit
    while to_spend > 0:
        chunk_amount = min(FINANCE_DAI_MAX_PER_CALL, to_spend)
        recipients.append(multisig)
        amounts.append(chunk_amount)
        to_spend -= chunk_amount

    create_and_enact_payment_motion(
        contracts.easy_track,
        multisig,
        LOL_STABLES_TOP_UP_FACTORY,
        contracts.dai_token,
        recipients,
        amounts,
        stranger,
    )

    spent_after, spendable_after, _, period_end_after = registry.getPeriodState()
    assert period_end_after > period_end_before, "the spending period should have rolled over to a fresh one"
    assert spent_after == limit
    assert spendable_after == 0

    # not a single wei beyond the limit
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            contracts.easy_track,
            multisig,
            LOL_STABLES_TOP_UP_FACTORY,
            contracts.dai_token,
            [multisig],
            [1],
            stranger,
        )
