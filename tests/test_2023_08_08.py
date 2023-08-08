"""
Tests for voting 08/08/2023.
"""
from brownie import web3
from scripts.vote_2023_08_08 import start_vote
from utils.test.helpers import ETH, almostEqWithDiff


from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_voting_events,
    group_voting_events,
)

from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)

from utils.test.easy_track_helpers import (
    create_and_enact_payment_motion,
    create_and_enact_add_recipient_motion,
    create_and_enact_remove_recipient_motion,
    check_add_and_remove_recipient_with_voting,
)
from utils.easy_track import create_permissions
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.test.event_validators.node_operators_registry import (
    NodeOperatorItem,
    validate_node_operator_added_event,
)
from utils.test.event_validators.permission import (
    Permission,
    validate_grant_role_event,
    validate_permission_grant_event,
)
from utils.test.event_validators.burner import validate_steth_burn_requested_event, StETH_burn_request
from utils.test.event_validators.erc20_token import validate_erc20_approval_event, ERC20Approval


def test_vote(helpers, accounts, vote_ids_from_env, interface, ldo_holder, stranger, bypass_events_decoding):
    rewards_share_topup_factory = interface.TopUpAllowedRecipients("0xbD08f9D6BF1D25Cc7407E4855dF1d46C2043B3Ea")
    rewards_share_add_recipient_factory = interface.AddAllowedRecipient("0x1F809D2cb72a5Ab13778811742050eDa876129b6")
    rewards_share_remove_recipient_factory = interface.RemoveAllowedRecipient(
        "0xd30Dc38EdEfc21875257e8A3123503075226E14B"
    )
    rewards_share_registry = interface.AllowedRecipientRegistry("0xdc7300622948a7AdaF339783F6991F9cdDD79776")
    rewards_share_multisig = accounts.at("0xe2A682A9722354D825d1BbDF372cC86B2ea82c8C", {"force": True})

    MANAGE_NODE_OPERATOR_ROLE = web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")
    permission = Permission(
        entity=contracts.agent, app=contracts.node_operators_registry, role=MANAGE_NODE_OPERATOR_ROLE.hex()
    )
    new_node_op_1 = NodeOperatorItem("Launchnodes", 30, "0x5a8B929EDBf3CE44526465DD2087EC7EFB59A561", 0)
    new_node_op_2 = NodeOperatorItem("SenseiNode", 31, "0xE556Da28015c04F35A52B3111B9F4120E908056e", 0)

    stETH_to_burn = ETH(3.1531)
    shares_to_burn = contracts.lido.getSharesByPooledEth(stETH_to_burn)
    burn_request = StETH_burn_request(
        requestedBy=contracts.agent.address,
        amountOfStETH=stETH_to_burn,
        amountOfShares=shares_to_burn,
        isCover=True,
    )
    approval_to_burner = ERC20Approval(
        owner=contracts.agent.address, spender=contracts.burner.address, amount=stETH_to_burn
    )

    assert contracts.lido.allowance(contracts.agent, contracts.burner) == 0

    COVER_INDEX = 0
    NONCOVER_INDEX = 1
    burner_total_burnt_for_cover_before = contracts.burner.getCoverSharesBurnt()
    burner_total_burnt_for_noncover_before = contracts.burner.getNonCoverSharesBurnt()

    burner_assigned_for_cover_burn_before = contracts.burner.getSharesRequestedToBurn()[COVER_INDEX]
    assert burner_assigned_for_cover_burn_before == 0

    burner_assigned_for_noncover_burn_before = contracts.burner.getSharesRequestedToBurn()[NONCOVER_INDEX]
    assert burner_assigned_for_noncover_burn_before == 0

    agent_shares_before = contracts.lido.sharesOf(contracts.agent)

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
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 9, "Incorrect voting items count"

    assert contracts.acl.hasPermission(contracts.agent, contracts.node_operators_registry, MANAGE_NODE_OPERATOR_ROLE)

    no1 = contracts.node_operators_registry.getNodeOperator(new_node_op_1.id, True)

    assert no1["active"] is True
    assert no1["name"] == new_node_op_1.name
    assert no1["rewardAddress"] == new_node_op_1.reward_address
    assert no1["totalVettedValidators"] == 0
    assert no1["totalExitedValidators"] == 0
    assert no1["totalAddedValidators"] == 0
    assert no1["totalDepositedValidators"] == 0

    no2 = contracts.node_operators_registry.getNodeOperator(new_node_op_2.id, True)

    assert no2["active"] is True
    assert no2["name"] == new_node_op_2.name
    assert no2["rewardAddress"] == new_node_op_2.reward_address
    assert no2["totalVettedValidators"] == 0
    assert no2["totalExitedValidators"] == 0
    assert no2["totalAddedValidators"] == 0
    assert no2["totalDepositedValidators"] == 0

    request_burn_my_steth_role_holders = contracts.burner.getRoleMemberCount(
        contracts.burner.REQUEST_BURN_MY_STETH_ROLE()
    )
    assert request_burn_my_steth_role_holders == 1
    assert contracts.burner.getRoleMember(contracts.burner.REQUEST_BURN_MY_STETH_ROLE(), 0) == contracts.agent

    agent_shares_after = contracts.lido.sharesOf(contracts.agent)

    agent_lido_alowance_after = contracts.lido.allowance(contracts.agent.address, contracts.burner.address)
    assert almostEqWithDiff(agent_lido_alowance_after, 0, 2)

    burner_total_burnt_for_cover_after = contracts.burner.getCoverSharesBurnt()
    assert burner_total_burnt_for_cover_after == burner_total_burnt_for_cover_before

    burner_total_burnt_for_noncover_after = contracts.burner.getNonCoverSharesBurnt()
    assert burner_total_burnt_for_noncover_after == burner_total_burnt_for_noncover_before

    burner_assigned_for_cover_burn_after = contracts.burner.getSharesRequestedToBurn()[COVER_INDEX]
    assert burner_assigned_for_cover_burn_after == agent_shares_before - agent_shares_after
    assert burner_assigned_for_cover_burn_after == shares_to_burn

    burner_assigned_for_noncover_burn_after = contracts.burner.getSharesRequestedToBurn()[NONCOVER_INDEX]
    assert burner_assigned_for_noncover_burn_after == burner_assigned_for_noncover_burn_before

    updated_factories_list = contracts.easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 16

    assert rewards_share_topup_factory in updated_factories_list
    assert rewards_share_add_recipient_factory in updated_factories_list
    assert rewards_share_remove_recipient_factory in updated_factories_list

    create_and_enact_add_recipient_motion(
        contracts.easy_track,
        rewards_share_multisig,
        rewards_share_registry,
        rewards_share_add_recipient_factory,
        rewards_share_multisig,
        "New recipient",
        ldo_holder,
    )
    create_and_enact_payment_motion(
        contracts.easy_track,
        rewards_share_multisig,
        rewards_share_topup_factory,
        contracts.lido,
        [rewards_share_multisig],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(rewards_share_registry, helpers, ldo_holder, contracts.voting)
    create_and_enact_add_recipient_motion(
        contracts.easy_track,
        rewards_share_multisig,
        rewards_share_registry,
        rewards_share_add_recipient_factory,
        stranger,
        "New recipient",
        ldo_holder,
    )
    create_and_enact_remove_recipient_motion(
        contracts.easy_track,
        rewards_share_multisig,
        rewards_share_registry,
        rewards_share_remove_recipient_factory,
        stranger,
        ldo_holder,
    )

    display_voting_events(vote_tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=rewards_share_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rewards_share_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[1],
        EVMScriptFactoryAdded(
            factory_addr=rewards_share_add_recipient_factory,
            permissions=create_permissions(rewards_share_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[2],
        EVMScriptFactoryAdded(
            factory_addr=rewards_share_remove_recipient_factory,
            permissions=create_permissions(rewards_share_registry, "removeRecipient"),
        ),
    )
    validate_permission_grant_event(evs[3], permission)
    validate_node_operator_added_event(evs[4], new_node_op_1)
    validate_node_operator_added_event(evs[5], new_node_op_2)
    validate_erc20_approval_event(evs[6], approval_to_burner)
    validate_grant_role_event(
        evs[7], contracts.burner.REQUEST_BURN_MY_STETH_ROLE(), contracts.agent.address, contracts.agent.address
    )
    validate_steth_burn_requested_event(evs[8], burn_request)
