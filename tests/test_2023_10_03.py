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

from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, network_name
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.event_validators.node_operators_registry import (
    NodeOperatorItem,
    TargetValidatorsCountChanged,
    validate_node_operator_added_event,
    validate_target_validators_count_changed_event,
)
from utils.test.event_validators.permission import validate_grant_role_event

from utils.test.event_validators.anchor import validate_anchor_vault_implementation_upgrade_events

NEW_NODE_OPERATORS = [
    # name, id, address
    # to get current id use Node Operators registry's getNodeOperatorsCount function
    # https://etherscan.io/address/0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5#readProxyContract
    NodeOperatorItem("A41", 32, "0x2A64944eBFaFF8b6A0d07B222D3d83ac29c241a7", 0),
    # and 6 more
]


# web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

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


def test_vote(helpers, accounts, vote_ids_from_env, bypass_events_decoding):
    # params
    agent = contracts.agent
    nor = contracts.node_operators_registry
    staking_router = contracts.staking_router
    target_NO_id = 1
    target_validators_count_change_request = TargetValidatorsCountChanged(
        nodeOperatorId=target_NO_id, targetValidatorsCount=0
    )

    # Before vote checks
    # Check that all NOs are unknown yet (1-7)
    for node_operator in NEW_NODE_OPERATORS:
        # with reverts("NODE_OPERATOR_NOT_FOUND"):
        with reverts("OUT_OF_RANGE"):
            no = nor.getNodeOperator(node_operator.id, True)

    # 8)
    assert staking_router.hasRole(STAKING_MODULE_MANAGE_ROLE, agent.address) == False

    # 9)
    NO_summary_before = nor.getNodeOperatorSummary(target_NO_id)
    assert NO_summary_before[0] == False
    assert NO_summary_before[1] == 0
    assert NO_summary_before[2] == 0
    assert NO_summary_before[3] == 0
    assert NO_summary_before[4] == 0
    assert NO_summary_before[5] == 0
    assert NO_summary_before[6] == 1000
    assert NO_summary_before[7] == 0

    # 10)
    # max_uint256 = 2**256 - 1

    # proxy = contracts.anchor_vault_proxy
    # vault = contracts.anchor_vault

    # # check that implementation is petrified
    # anchor_impl = interface.AnchorVault(ANCHOR_NEW_IMPL_ADDRESS)
    # assert anchor_impl.version() == max_uint256

    # address_implementation_before = proxy.implementation()
    # assert address_implementation_before == ANCHOR_OLD_IMPL_ADDRESS, "Old address is incorrect"

    # assert vault.version() == 3
    # assert vault.emergency_admin() == OLD_EMERGENCY_ADMIN

    # admin_before = vault.admin()
    # steth_token_address_before = vault.steth_token()
    # beth_token_address_before = vault.beth_token()
    # operations_allowed_before = vault.operations_allowed()
    # total_beth_refunded_before = vault.total_beth_refunded()

    # stETH_token = interface.ERC20(steth_token_address_before)
    # bETH_token = interface.ERC20(beth_token_address_before)

    # steth_vault_balance_before = stETH_token.balanceOf(vault.address)
    # beth_total_supply_before = bETH_token.totalSupply()

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    print(f"accounts = {accounts[0]}")
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 10, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)

    assert get_lido_vote_cid_from_str(metadata) == "bafkreiapvuobyrudww3oqhfopbs2fdmtebi6jnvpeb3plxkajnhafw25im"

    # I
    # Check that all NO were added
    for node_operator in NEW_NODE_OPERATORS:
        no = nor.getNodeOperator(node_operator.id, True)

        message = f"Failed on {node_operator.name}"
        assert no[0] is True, message  # is active
        assert no[1] == node_operator.name, message  # name
        assert no[2] == node_operator.reward_address, message  # rewards address
        assert no[3] == 0  # staking limit

    # II
    # 8)
    assert staking_router.hasRole(STAKING_MODULE_MANAGE_ROLE, agent.address) == True

    # 9)
    NO_summary_after = nor.getNodeOperatorSummary(target_NO_id)
    assert NO_summary_after[0] == True
    assert NO_summary_after[1] == 0
    assert NO_summary_after[2] == 0
    assert NO_summary_after[3] == 0
    assert NO_summary_after[4] == 0
    assert NO_summary_after[5] == 0
    assert NO_summary_after[6] == 1000
    assert NO_summary_after[7] == 0

    # III
    # address_implementation_after = proxy.implementation()
    # assert address_implementation_before != address_implementation_after, "Implementation is not changed"
    # assert address_implementation_after == ANCHOR_NEW_IMPL_ADDRESS, "New address is incorrect"

    # assert vault.version() == ANCHOR_NEW_IMPL_VERSION
    # assert vault.emergency_admin() == NEW_EMERGENCY_ADMIN

    # admin_after = vault.admin()
    # assert admin_before == admin_after == contracts.agent.address

    # beth_token_address_after = vault.beth_token()
    # assert beth_token_address_before == beth_token_address_after

    # steth_token_address_after = vault.steth_token()
    # assert steth_token_address_before == steth_token_address_after

    # beth_total_supply_after = bETH_token.totalSupply()
    # assert beth_total_supply_before == beth_total_supply_after

    # operations_allowed_after = vault.operations_allowed()
    # assert operations_allowed_before == operations_allowed_after == True

    # total_beth_refunded_after = vault.total_beth_refunded()
    # assert total_beth_refunded_before == total_beth_refunded_after == REFUND_BETH_AMOUNT

    # steth_vault_balance_after = stETH_token.balanceOf(vault.address)
    # assert steth_vault_balance_before == steth_vault_balance_after

    # with reverts("Collect rewards stopped"):
    #     vault.collect_rewards({"from": stranger})

    # with reverts("Minting is discontinued"):
    #     vault.submit(10**18, TERRA_ADDRESS, "0x8bada2e", vault.version(), {"from": stranger})

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    # Check events
    evs = group_voting_events(vote_tx)

    for i in range(len(NEW_NODE_OPERATORS)):
        validate_node_operator_added_event(evs[i], NEW_NODE_OPERATORS[i])

    validate_grant_role_event(evs[0], STAKING_MODULE_MANAGE_ROLE, agent.address, agent.address)

    validate_target_validators_count_changed_event(evs[1], target_validators_count_change_request)

    # validate_anchor_vault_implementation_upgrade_events(evs[0], ANCHOR_NEW_IMPL_ADDRESS, ANCHOR_NEW_IMPL_VERSION)
