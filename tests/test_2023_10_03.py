"""
Tests for voting 03/10/2023.
"""
from brownie import ZERO_ADDRESS, reverts
from scripts.vote_2023_10_03 import start_vote

from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_voting_events,
    group_voting_events,
)

from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS
)

from utils.test.event_validators.anchor import (
    validate_anchor_vault_implementation_upgrade_events
)

ANCHOR_OLD_IMPL_ADDRESS = "0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171"
ANCHOR_NEW_IMPL_ADDRESS = "#TBA"
OLD_EMERGENCY_ADMIN = "0x3cd9F71F80AB08ea5a7Dca348B5e94BC595f26A0"
NEW_EMERGENCY_ADMIN = ZERO_ADDRESS
TERRA_ADDRESS = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"
ANCHOR_NEW_IMPL_VERSION = 4

"""
Number of tokens that were burned after the incident the 2022-01-26 incident
caused by incorrect address encoding produced by cached UI code after onchain
migration to the Wormhole bridge.

Postmortem: https://hackmd.io/bxTICZOuQ5iOwoPMMZqysw?view

Tx 1: 0xc875f85f525d9bc47314eeb8dc13c288f0814cf06865fc70531241e21f5da09d
bETH burned: 4449999990000000000
Tx 2: 0x7abe086dd5619a577f50f87660a03ea0a1934c4022cd432ddf00734771019951
bETH burned: 439111118580000000000
"""
REFUND_BETH_AMOUNT = 4449999990000000000 + 439111118580000000000


def test_vote(helpers, accounts, vote_ids_from_env, interface, ldo_holder, stranger, bypass_events_decoding):

    max_uint256 = 2**256 - 1

    stETH_token = interface.ERC20(contracts.lido.address)

    proxy = contracts.anchor_vault_proxy
    vault = contracts.anchor_vault

    # check that implementation is petrified
    anchor_impl = interface.AnchorVault(ANCHOR_NEW_IMPL_ADDRESS)
    assert anchor_impl.version() == max_uint256

    address_implementation_before = proxy.implementation()
    assert address_implementation_before == ANCHOR_OLD_IMPL_ADDRESS, "Old address is incorrect"

    assert vault.version() == 3
    assert vault.emergency_admin() == OLD_EMERGENCY_ADMIN

    admin_before = vault.admin()
    beth_token_before = vault.beth_token()
    steth_token_before = vault.steth_token()
    operations_allowed_before = vault.operations_allowed()
    total_beth_refunded_before = vault.total_beth_refunded()
    steth_balance_before = stETH_token.balanceOf(vault.address)

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
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"

    address_implementation_after = proxy.implementation()
    assert address_implementation_before != address_implementation_after, "Implementation is not changed"
    assert address_implementation_after == ANCHOR_NEW_IMPL_ADDRESS, "New address is incorrect"

    assert vault.version() == ANCHOR_NEW_IMPL_VERSION
    assert vault.emergency_admin() == NEW_EMERGENCY_ADMIN

    admin_after = vault.admin()
    assert admin_before == admin_after == contracts.agent.address

    beth_token_after = vault.beth_token()
    assert beth_token_before == beth_token_after

    steth_token_after = vault.steth_token()
    assert steth_token_before == steth_token_after

    operations_allowed_after = vault.operations_allowed()
    assert operations_allowed_before == operations_allowed_after == True

    total_beth_refunded_after = vault.total_beth_refunded()
    assert total_beth_refunded_before == total_beth_refunded_after == REFUND_BETH_AMOUNT

    steth_balance_after = stETH_token.balanceOf(vault.address)
    assert steth_balance_before == steth_balance_after

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

    validate_anchor_vault_implementation_upgrade_events(evs[0], ANCHOR_NEW_IMPL_ADDRESS, ANCHOR_NEW_IMPL_VERSION)
