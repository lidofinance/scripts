"""
Tests for voting 20/06/2023.

"""
from scripts.vote_2023_06_20 import start_vote

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.burner import validate_steth_burn_requested_event, StETH_burn_request
from utils.test.event_validators.erc20_token import (
    ERC20Transfer,
    ERC20Approval,
    validate_erc20_approval_event,
    validate_erc20_transfer_event,
)
from utils.test.event_validators.permission import (
    Permission,
    validate_grant_role_event,
    validate_revoke_role_event,
    validate_permission_create_event,
    validate_permission_revoke_event
)
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    validate_node_operator_reward_address_set_event,
    NodeOperatorNameSetItem,
    NodeOperatorRewardAddressSetItem,
)
from utils.test.event_validators.payout import Payout, validate_token_payout_event
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.easy_track import create_permissions

from utils.test.helpers import almostEqWithDiff

from utils.test.easy_track_helpers import (
    create_and_enact_payment_motion,
    create_and_enact_add_recipient_motion,
    create_and_enact_remove_recipient_motion,
    check_add_and_remove_recipient_with_voting,
)

#####
# CONSTANTS
#####

STETH_ERROR_MARGIN_WEI = 2

def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
    ldo_holder,
    stranger,
):

    finance = contracts.finance
    voting = contracts.voting
    easy_track = contracts.easy_track
    agent = contracts.agent
    ldo_token = contracts.ldo_token
    no_registry = contracts.node_operators_registry

    ## parameters
    # I. RockLogic Slashing Incident Staker Compensation
    burn_request: StETH_burn_request = StETH_burn_request(
        requestedBy=contracts.agent.address,
        amountOfStETH=1345978634 * 10**10,  # 13.45978634 stETH
        amountOfShares=contracts.lido.getSharesByPooledEth(1345978634 * 10**10),
        isCover=True,
    )

    transfer_from_insurance_fund: ERC20Transfer = ERC20Transfer(
        from_addr=contracts.insurance_fund.address,
        to_addr=contracts.agent.address,
        value=burn_request.amountOfStETH,
    )

    approval_to_burner: ERC20Approval = ERC20Approval(
        owner=contracts.agent.address, spender=contracts.burner.address, amount=burn_request.amountOfStETH
    )
    # II. Add Gas Supply stETH setup to Easy Track
    stETH_token = contracts.lido
    gas_supply_stETH_registry = interface.AllowedRecipientRegistry("0x49d1363016aA899bba09ae972a1BF200dDf8C55F")
    gas_supply_stETH_topup_factory = interface.TopUpAllowedRecipients("0x200dA0b6a9905A377CF8D469664C65dB267009d1")
    gas_supply_stETH_add_recipient_factory = interface.AddAllowedRecipient("0x48c135Ff690C2Aa7F5B11C539104B5855A4f9252")
    gas_supply_stETH_remove_recipient_factory = interface.RemoveAllowedRecipient("0x7E8eFfAb3083fB26aCE6832bFcA4C377905F97d7")
    gas_supply_stETH_multisig = accounts.at("0x5181d5D56Af4f823b96FE05f062D7a09761a5a53", {"force": True})

    # III. Add reWARDS stETH setup to Easy Track
    reWARDS_stETH_registry = interface.AllowedRecipientRegistry("0x48c4929630099b217136b64089E8543dB0E5163a")
    reWARDS_stETH_topup_factory = interface.TopUpAllowedRecipients("0x1F2b79FE297B7098875930bBA6dd17068103897E")
    reWARDS_stETH_add_recipient_factory = interface.AddAllowedRecipient("0x935cb3366Faf2cFC415B2099d1F974Fd27202b77")
    reWARDS_stETH_remove_recipient_factory = interface.RemoveAllowedRecipient("0x22010d1747CaFc370b1f1FBBa61022A313c5693b")
    reWARDS_stETH_multisig = accounts.at("0x87D93d9B2C672bf9c9642d853a8682546a5012B5", {"force": True})

    # IV. Remove reWARDS LDO setup from Easy Track
    reWARDS_LDO_topup_factory = interface.TopUpAllowedRecipients("0x85d703B2A4BaD713b596c647badac9A1e95bB03d")
    reWARDS_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C")
    reWARDS_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E")

    # V. Remove LDO and DAI referral program from Easy Track
    referral_program_LDO_topup_factory = interface.TopUpAllowedRecipients("0x54058ee0E0c87Ad813C002262cD75B98A7F59218")
    referral_program_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51")
    referral_program_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C")
    referral_program_DAI_topup_factory = interface.TopUpAllowedRecipients("0x009ffa22ce4388d2F5De128Ca8E6fD229A312450")
    referral_program_DAI_add_recipient_factory = interface.AddAllowedRecipient("0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151")
    referral_program_DAI_remove_recipient_factory = interface.RemoveAllowedRecipient("0xd8f9B72Cd97388f23814ECF429cd18815F6352c1")

    # VI. Polygon team incentives
    polygon_team_address = "0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290"
    polygon_team_incentives_amount = 150_000 * 10**18
    polygon_team_ldo_payout = Payout(
        token_addr=ldo_token,
        from_addr=agent,
        to_addr=polygon_team_address,
        amount=polygon_team_incentives_amount,
    )

    # VII. Transfer 200k LDO to PML multisig 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
    PML_multisig = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
    PML_topup_amount = 200_000 * 10**18
    PML_ldo_payout = Payout(
        token_addr=ldo_token,
        from_addr=agent,
        to_addr=PML_multisig,
        amount=PML_topup_amount,
    )

    # VIII. Change NO names and addresses
    permission_manage_no = Permission(
        entity=voting,
        app=no_registry,
        role=no_registry.MANAGE_NODE_OPERATOR_ROLE(),
    )

    CertusOne_Jumpcrypto_id = 1
    CertusOne_Jumpcrypto_name_before = "Certus One"
    CertusOne_Jumpcrypto_name_after = "Jump Crypto"

    ConsenSysCodefi_Consensys_id = 21
    ConsenSysCodefi_Consensys_name_before = "ConsenSys Codefi"
    ConsenSysCodefi_Consensys_name_after = "Consensys"

    SkillZ_Kiln_id = 8
    SkillZ_Kiln_name_before = "SkillZ"
    SkillZ_Kiln_name_after = "Kiln"
    SkillZ_Kiln_address_before = "0xe080E860741b7f9e8369b61645E68AD197B1e74C"
    SkillZ_Kiln_address_after = "0xD6B7d52E15678B9195F12F3a6D6cb79dcDcCb690"

    RockLogic_id = 22
    RockLogic_address_before = "0x49Df3CCa2670eB0D591146B16359fe336e476F29"
    RockLogic_address_after = "0x765c6a8f20c842E8C826B0D9425015784F982aFc"


    ## checks before the vote
    # I.
    insurance_fund_steth_balance_before: int = contracts.lido.balanceOf(contracts.insurance_fund.address)
    insurance_fund_shares_before: int = contracts.lido.sharesOf(contracts.insurance_fund.address)

    # https://research.lido.fi/t/redirecting-incoming-revenue-stream-from-insurance-fund-to-dao-treasury/2528/28
    assert insurance_fund_shares_before == 5466460000000000000000
    # retrieved 2023-06-16 at 08:20 UTC
    assert insurance_fund_steth_balance_before >= 6168933603752703174674

    agent_lido_alowance_before: int = contracts.lido.allowance(contracts.agent.address, contracts.burner.address)
    assert agent_lido_alowance_before <= STETH_ERROR_MARGIN_WEI

    request_burn_my_steth_role_holders_before: int = contracts.burner.getRoleMemberCount(
        contracts.burner.REQUEST_BURN_MY_STETH_ROLE()
    )
    assert request_burn_my_steth_role_holders_before == 0

    burner_total_burnt_for_cover_before: int = contracts.burner.getCoverSharesBurnt()
    assert burner_total_burnt_for_cover_before == 0

    burner_total_burnt_for_noncover_before: int = contracts.burner.getNonCoverSharesBurnt()
    # retrieved 2023-06-16 at 08:20 UTC
    assert burner_total_burnt_for_noncover_before >= 506385577569080968748810

    burner_assigned_for_cover_burn_before: int = contracts.burner.getSharesRequestedToBurn()[0]
    assert burner_assigned_for_cover_burn_before == 0

    burner_assigned_for_noncover_burn_before: int = contracts.burner.getSharesRequestedToBurn()[1]
    assert burner_assigned_for_noncover_burn_before == 0

    # II.
    old_factories_list = easy_track.getEVMScriptFactories()
    assert len(old_factories_list) == 16

    assert gas_supply_stETH_topup_factory not in old_factories_list
    assert gas_supply_stETH_add_recipient_factory not in old_factories_list
    assert gas_supply_stETH_remove_recipient_factory not in old_factories_list

    # III.
    assert reWARDS_stETH_topup_factory not in old_factories_list
    assert reWARDS_stETH_add_recipient_factory not in old_factories_list
    assert reWARDS_stETH_remove_recipient_factory not in old_factories_list

    # IV.
    assert reWARDS_LDO_topup_factory in old_factories_list
    assert reWARDS_LDO_add_recipient_factory in old_factories_list
    assert reWARDS_LDO_remove_recipient_factory in old_factories_list

    # V.
    assert referral_program_LDO_topup_factory in old_factories_list
    assert referral_program_LDO_add_recipient_factory in old_factories_list
    assert referral_program_LDO_remove_recipient_factory in old_factories_list

    assert referral_program_DAI_topup_factory in old_factories_list
    assert referral_program_DAI_add_recipient_factory in old_factories_list
    assert referral_program_DAI_remove_recipient_factory in old_factories_list

    # VI - VII.
    agent_ldo_before = ldo_token.balanceOf(agent)
    polygon_team_ldo_before = ldo_token.balanceOf(polygon_team_address)
    PML_ldo_before = ldo_token.balanceOf(PML_multisig)

    # VIII.
    assert not contracts.acl.hasPermission(*permission_manage_no)

    # get NO's data before
    CertusOne_Jumpcrypto_data_before = no_registry.getNodeOperator(CertusOne_Jumpcrypto_id, True)
    ConsenSysCodefi_Consensys_data_before = no_registry.getNodeOperator(ConsenSysCodefi_Consensys_id, True)
    SkillZ_Kiln_data_before = no_registry.getNodeOperator(SkillZ_Kiln_id, True)
    RockLogic_data_before = no_registry.getNodeOperator(RockLogic_id, True)

    # check names before
    assert CertusOne_Jumpcrypto_data_before['name'] == CertusOne_Jumpcrypto_name_before, "Incorrect NO#1 name before"
    assert ConsenSysCodefi_Consensys_data_before['name'] == ConsenSysCodefi_Consensys_name_before, "Incorrect NO#21 name before"
    assert SkillZ_Kiln_data_before['name'] == SkillZ_Kiln_name_before, "Incorrect NO#8 name before"

    # check reward addresses before
    assert SkillZ_Kiln_data_before['rewardAddress'] == SkillZ_Kiln_address_before, "Incorrect NO#8 reward address before"
    assert RockLogic_data_before['rewardAddress'] == RockLogic_address_before, "Incorrect NO#22 reward address before"


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    ## checks after the vote
    # I.
    insurance_fund_steth_balance_after: int = contracts.lido.balanceOf(contracts.insurance_fund.address)
    insurance_fund_shares_after: int = contracts.lido.sharesOf(contracts.insurance_fund.address)

    assert almostEqWithDiff(
        insurance_fund_steth_balance_before - insurance_fund_steth_balance_after,
        burn_request.amountOfStETH,
        STETH_ERROR_MARGIN_WEI,
    )

    agent_lido_alowance_after: int = contracts.lido.allowance(contracts.agent.address, contracts.burner.address)
    assert agent_lido_alowance_after <= STETH_ERROR_MARGIN_WEI  # with tolerance

    request_burn_my_steth_role_holders_after: int = contracts.burner.getRoleMemberCount(
        contracts.burner.REQUEST_BURN_MY_STETH_ROLE()
    )
    assert request_burn_my_steth_role_holders_after == 0

    burner_total_burnt_for_cover_after: int = contracts.burner.getCoverSharesBurnt()
    assert burner_total_burnt_for_cover_after == burner_total_burnt_for_cover_before

    burner_total_burnt_for_noncover_after: int = contracts.burner.getNonCoverSharesBurnt()
    assert burner_total_burnt_for_noncover_after == burner_total_burnt_for_noncover_before

    burner_assigned_for_cover_burn_after: int = contracts.burner.getSharesRequestedToBurn()[0]
    assert insurance_fund_shares_before - insurance_fund_shares_after == burner_assigned_for_cover_burn_after
    assert almostEqWithDiff(burner_assigned_for_cover_burn_after, burn_request.amountOfShares, STETH_ERROR_MARGIN_WEI)

    burner_assigned_for_noncover_burn_after: int = contracts.burner.getSharesRequestedToBurn()[1]
    assert burner_assigned_for_noncover_burn_after == burner_assigned_for_noncover_burn_before

    # II.
    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 13

    assert gas_supply_stETH_topup_factory in updated_factories_list
    assert gas_supply_stETH_add_recipient_factory in updated_factories_list
    assert gas_supply_stETH_remove_recipient_factory in updated_factories_list

    create_and_enact_payment_motion(
        easy_track,
        gas_supply_stETH_multisig,
        gas_supply_stETH_topup_factory,
        stETH_token,
        [gas_supply_stETH_multisig],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(gas_supply_stETH_registry, helpers, ldo_holder, voting)
    create_and_enact_add_recipient_motion(
        easy_track,
        gas_supply_stETH_multisig,
        gas_supply_stETH_registry,
        gas_supply_stETH_add_recipient_factory,
        stranger,
        "New recipient",
        ldo_holder,
    )
    create_and_enact_remove_recipient_motion(
        easy_track,
        gas_supply_stETH_multisig,
        gas_supply_stETH_registry,
        gas_supply_stETH_remove_recipient_factory,
        stranger,
        ldo_holder,
    )

    # III.
    assert reWARDS_stETH_topup_factory in updated_factories_list
    assert reWARDS_stETH_add_recipient_factory in updated_factories_list
    assert reWARDS_stETH_remove_recipient_factory in updated_factories_list

    create_and_enact_payment_motion(
        easy_track,
        reWARDS_stETH_multisig,
        reWARDS_stETH_topup_factory,
        stETH_token,
        [reWARDS_stETH_multisig],
        [10 * 10**18],
        stranger,
    )
    check_add_and_remove_recipient_with_voting(reWARDS_stETH_registry, helpers, ldo_holder, voting)
    create_and_enact_add_recipient_motion(
        easy_track,
        reWARDS_stETH_multisig,
        reWARDS_stETH_registry,
        reWARDS_stETH_add_recipient_factory,
        stranger,
        "New recipient",
        ldo_holder,
    )
    create_and_enact_remove_recipient_motion(
        easy_track,
        reWARDS_stETH_multisig,
        reWARDS_stETH_registry,
        reWARDS_stETH_remove_recipient_factory,
        stranger,
        ldo_holder,
    )

    # IV.
    assert reWARDS_LDO_topup_factory not in updated_factories_list
    assert reWARDS_LDO_add_recipient_factory not in updated_factories_list
    assert reWARDS_LDO_remove_recipient_factory not in updated_factories_list

    # V.
    assert referral_program_LDO_topup_factory not in updated_factories_list
    assert referral_program_LDO_add_recipient_factory not in updated_factories_list
    assert referral_program_LDO_remove_recipient_factory not in updated_factories_list

    assert referral_program_DAI_topup_factory not in updated_factories_list
    assert referral_program_DAI_add_recipient_factory not in updated_factories_list
    assert referral_program_DAI_remove_recipient_factory not in updated_factories_list

    # VI-VII
    assert (
        agent_ldo_before
        == ldo_token.balanceOf(agent) + polygon_team_incentives_amount + PML_topup_amount
    )
    assert (
        ldo_token.balanceOf(polygon_team_address)
        == polygon_team_ldo_before + polygon_team_incentives_amount
    )
    assert (
        ldo_token.balanceOf(PML_multisig)
        == PML_ldo_before + PML_topup_amount
    )

    # VIII.
    assert not contracts.acl.hasPermission(*permission_manage_no)
    # get NO's data after
    CertusOne_Jumpcrypto_data_after = no_registry.getNodeOperator(CertusOne_Jumpcrypto_id, True)
    ConsenSysCodefi_Consensys_data_after = no_registry.getNodeOperator(ConsenSysCodefi_Consensys_id, True)
    SkillZ_Kiln_data_after = no_registry.getNodeOperator(SkillZ_Kiln_id, True)
    RockLogic_data_after = no_registry.getNodeOperator(RockLogic_id, True)

    # compare NO#1 (CertusOne -> Jump Crypto) data before and after
    assert CertusOne_Jumpcrypto_data_before['active'] == CertusOne_Jumpcrypto_data_after['active']
    assert CertusOne_Jumpcrypto_name_after == CertusOne_Jumpcrypto_data_after['name']
    assert CertusOne_Jumpcrypto_data_before['rewardAddress'] == CertusOne_Jumpcrypto_data_after['rewardAddress']
    compare_NO_validators_data(CertusOne_Jumpcrypto_data_before, CertusOne_Jumpcrypto_data_after)

    # compare NO#21 (ConsenSysCodefi -> Consensys) data before and after
    assert ConsenSysCodefi_Consensys_data_before['active'] == ConsenSysCodefi_Consensys_data_after['active']
    assert ConsenSysCodefi_Consensys_name_after == ConsenSysCodefi_Consensys_data_after['name']
    assert ConsenSysCodefi_Consensys_data_before['rewardAddress'] == ConsenSysCodefi_Consensys_data_after['rewardAddress']
    compare_NO_validators_data(ConsenSysCodefi_Consensys_data_before, ConsenSysCodefi_Consensys_data_after)

    # compare NO#8 (SkillZ -> Kiln) data before and after
    assert SkillZ_Kiln_data_before['active'] == SkillZ_Kiln_data_after['active']
    assert SkillZ_Kiln_name_after == SkillZ_Kiln_data_after['name']
    assert SkillZ_Kiln_address_after == SkillZ_Kiln_data_after['rewardAddress']
    compare_NO_validators_data(SkillZ_Kiln_data_before, SkillZ_Kiln_data_after)

    # compare NO#22 (RockLogic) data before and after
    assert RockLogic_data_before['active'] == RockLogic_data_after['active']
    assert RockLogic_data_before['name'] == RockLogic_data_after['name']
    assert RockLogic_address_after == RockLogic_data_after['rewardAddress']
    compare_NO_validators_data(RockLogic_data_before, RockLogic_data_after)


    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 29, "Incorrect voting items count"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_erc20_transfer_event(evs[0], transfer_from_insurance_fund, is_steth=True)
    validate_erc20_approval_event(evs[1], approval_to_burner)
    validate_grant_role_event(
        evs[2], contracts.burner.REQUEST_BURN_MY_STETH_ROLE(), contracts.agent.address, contracts.agent.address
    )
    validate_steth_burn_requested_event(evs[3], burn_request)
    validate_revoke_role_event(
        evs[4], contracts.burner.REQUEST_BURN_MY_STETH_ROLE(), contracts.agent.address, contracts.agent.address
    )
    validate_evmscript_factory_added_event(
        evs[5],
        EVMScriptFactoryAdded(
            factory_addr=gas_supply_stETH_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(gas_supply_stETH_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[6],
        EVMScriptFactoryAdded(
            factory_addr=gas_supply_stETH_add_recipient_factory,
            permissions=create_permissions(gas_supply_stETH_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[7],
        EVMScriptFactoryAdded(
            factory_addr=gas_supply_stETH_remove_recipient_factory,
            permissions=create_permissions(gas_supply_stETH_registry, "removeRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[8],
        EVMScriptFactoryAdded(
            factory_addr=reWARDS_stETH_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(reWARDS_stETH_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[9],
        EVMScriptFactoryAdded(
            factory_addr=reWARDS_stETH_add_recipient_factory,
            permissions=create_permissions(reWARDS_stETH_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[10],
        EVMScriptFactoryAdded(
            factory_addr=reWARDS_stETH_remove_recipient_factory,
            permissions=create_permissions(reWARDS_stETH_registry, "removeRecipient"),
        ),
    )
    validate_evmscript_factory_removed_event(evs[11], reWARDS_LDO_topup_factory)
    validate_evmscript_factory_removed_event(evs[12], reWARDS_LDO_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[13], reWARDS_LDO_remove_recipient_factory)
    validate_evmscript_factory_removed_event(evs[14], referral_program_LDO_topup_factory)
    validate_evmscript_factory_removed_event(evs[15], referral_program_LDO_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[16], referral_program_LDO_remove_recipient_factory)
    validate_evmscript_factory_removed_event(evs[17], referral_program_DAI_topup_factory)
    validate_evmscript_factory_removed_event(evs[18], referral_program_DAI_add_recipient_factory)
    validate_evmscript_factory_removed_event(evs[19], referral_program_DAI_remove_recipient_factory)
    validate_token_payout_event(evs[20], polygon_team_ldo_payout, False)
    validate_token_payout_event(evs[21], PML_ldo_payout, False)
    validate_permission_create_event(evs[22], permission_manage_no, manager=voting)
    validate_node_operator_name_set_event(
        evs[23],
        NodeOperatorNameSetItem(
            nodeOperatorId=CertusOne_Jumpcrypto_id,
            name=CertusOne_Jumpcrypto_name_after
        )
    )
    validate_node_operator_name_set_event(
        evs[24],
        NodeOperatorNameSetItem(
            nodeOperatorId=ConsenSysCodefi_Consensys_id,
            name=ConsenSysCodefi_Consensys_name_after
        )
    )
    validate_node_operator_name_set_event(
        evs[25],
        NodeOperatorNameSetItem(
            nodeOperatorId=SkillZ_Kiln_id,
            name=SkillZ_Kiln_name_after
        )
    )
    validate_node_operator_reward_address_set_event(
        evs[26],
        NodeOperatorRewardAddressSetItem(
            nodeOperatorId=SkillZ_Kiln_id,
            reward_address=SkillZ_Kiln_address_after
        )
    )
    validate_node_operator_reward_address_set_event(
        evs[27],
        NodeOperatorRewardAddressSetItem(
            nodeOperatorId=RockLogic_id,
            reward_address=RockLogic_address_after
        )
    )
    validate_permission_revoke_event(evs[28], permission_manage_no)


def compare_NO_validators_data(data_before, data_after):
    assert data_before['totalVettedValidators'] == data_after['totalVettedValidators']
    assert data_before['totalExitedValidators'] == data_after['totalExitedValidators']
    assert data_before['totalAddedValidators'] == data_after['totalAddedValidators']
    assert data_before['totalDepositedValidators'] == data_after['totalDepositedValidators']
