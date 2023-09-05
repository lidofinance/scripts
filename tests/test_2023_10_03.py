"""
Tests for voting 03/10/2023.
"""
from brownie import ZERO_ADDRESS, convert, reverts
from scripts.vote_2023_10_03 import start_vote

from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_voting_events,
    group_voting_events,
)

from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    AGENT
)

from utils.test.event_validators.anchor import (
    validate_anchor_vault_implementation_upgrade_events,
    validate_anchor_vault_version_upgrade_events
)

ANCHOR_OLD_IMPL_ADDRESS = "0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171"
ANCHOR_NEW_IMPL_ADDRESS = "0x26f15335BB1C6a4C0B660eDd694a0555A9F1cce3"
EMERGENCY_ADMIN = "0x3cd9F71F80AB08ea5a7Dca348B5e94BC595f26A0"
TERRA_ADDRESS = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"
REFUND_BETH_AMOUNT = 4449999990000000000 + 439111118580000000000
ANCHOR_NEW_VERSION = 4

def test_vote(helpers, accounts, vote_ids_from_env, interface, ldo_holder, stranger, bypass_events_decoding):

    max_uint256 = convert.to_uint(
        "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )

    proxy = contracts.anchor_vault_proxy
    vault = contracts.anchor_vault

    # check that implementation is petrified
    anchor_impl = interface.AnchorVault(ANCHOR_NEW_IMPL_ADDRESS)
    assert anchor_impl.version() == max_uint256

    address_implementation_before = proxy.implementation()
    assert address_implementation_before == ANCHOR_OLD_IMPL_ADDRESS, "Old address is incorrect"

    assert vault.version() == 3
    assert vault.emergency_admin() == EMERGENCY_ADMIN

    admin_before = vault.admin()
    beth_token_before = vault.beth_token()
    steth_token_before = vault.steth_token()
    operations_allowed_before = vault.operations_allowed()
    total_beth_refunded_before = vault.total_beth_refunded()

    # START VOTE
    vote_ids = []
    if len(vote_ids_from_env) > 0:
        vote_ids = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
        vote_ids = [vote_id]

    [vote_tx] = helpers.execute_votes(accounts, vote_ids, contracts.voting)

    print(f"voteId = {vote_ids}, gasUsed = {vote_tx.gas_used}")
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 2, "Incorrect voting items count"


    address_implementation_after = proxy.implementation()
    assert address_implementation_before != address_implementation_after, "Implementation is not changed"
    assert address_implementation_after == ANCHOR_NEW_IMPL_ADDRESS, "New address is incorrect"

    assert vault.version() == ANCHOR_NEW_VERSION
    assert vault.emergency_admin() == ZERO_ADDRESS

    admin_after = vault.admin()
    assert admin_before == admin_after == AGENT

    beth_token_after = vault.beth_token()
    assert beth_token_before == beth_token_after

    steth_token_after = vault.steth_token()
    assert steth_token_before == steth_token_after

    operations_allowed_after = vault.operations_allowed()
    assert operations_allowed_before == operations_allowed_after == True

    total_beth_refunded_after = vault.total_beth_refunded()
    assert total_beth_refunded_before == total_beth_refunded_after == REFUND_BETH_AMOUNT

    with reverts("Collect rewards stopped"):
        vault.collect_rewards({"from": stranger})

    with reverts("Minting is discontinued"):
        vault.submit(
            10**18,
            TERRA_ADDRESS,
            "0x8bada2e",
            vault.version(),
            {"from": stranger}
        )

    display_voting_events(vote_tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(vote_tx)

    validate_anchor_vault_implementation_upgrade_events(evs[0], ANCHOR_NEW_IMPL_ADDRESS)
    validate_anchor_vault_version_upgrade_events(evs[1], ANCHOR_NEW_VERSION, ZERO_ADDRESS)
