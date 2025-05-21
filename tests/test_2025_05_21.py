from brownie import interface, reverts, chain
from brownie.network.event import EventDict

from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS
from utils.test.easy_track_helpers import (
    TEST_RELAY,
    create_and_enact_add_mev_boost_relay_motion,
    create_and_enact_remove_mev_boost_relay_motion,
    create_and_enact_edit_mev_boost_relay_motion,
)
from utils.easy_track import create_permissions
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.test.event_validators.relay_allowed_list import validate_relay_allowed_list_manager_set
from utils.test.event_validators.csm import validate_set_key_removal_charge_event
from utils.test.event_validators.oracle_report_sanity_checker import (
    validate_exited_validators_per_day_limit_event,
    validate_appeared_validators_limit_event,
    validate_initial_slashing_and_penalties_event,
)
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.allowed_recipients_registry import validate_set_limit_parameter_event
from utils.test.tx_tracing_helpers import group_voting_events
from scripts.vote_2025_05_21 import start_vote
from utils.test.tx_tracing_helpers import display_voting_events
from utils.test.csm_helpers import csm_add_node_operator, get_ea_member
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

# Old values (sanity checker)
INITIAL_SLASHING_AMOUNT_PWEI_BEFORE = 1000
EXITED_VALIDATORS_PER_DAY_LIMIT_BEFORE = 9000
APPEARED_VALIDATORS_PER_DAY_LIMIT_BEFORE = 43200

KEY_REMOVAL_CHARGE_BEFORE = 0.05 * 10**18

STETH_LOL_LIMIT_BEFORE = 2100 * 10**18
STETH_LOL_PERIOD_BEFORE = 3

STETH_LOL_PERIOD_START_BEFORE = 1743465600  # Tue Apr 01 2025 00:00:00 GMT+0000
STETH_LOL_PERIOD_END_BEFORE = 1751328000  # Tue Jul 01 2025 00:00:00 GMT+0000

# New values
INITIAL_SLASHING_AMOUNT_PWEI_AFTER = 8
EXITED_VALIDATORS_PER_DAY_LIMIT_AFTER = 3600
APPEARED_VALIDATORS_PER_DAY_LIMIT_AFTER = 1800

KEY_REMOVAL_CHARGE_AFTER = 0.02 * 10**18

STETH_LOL_LIMIT_AFTER = 6000 * 10**18
STETH_LOL_PERIOD_AFTER = 6

STETH_LOL_PERIOD_START_AFTER = 1735689600  # Wed Jan 01 2025 00:00:00 GMT+0000
STETH_LOL_PERIOD_END_AFTER = 1751328000  # Tue Jul 01 2025 00:00:00 GMT+0000

# Addresses
RMC_MULTISIG_ADDRESS = "0x98be4a407Bff0c125e25fBE9Eb1165504349c37d"
STETH_LOL_TRUSTED_CALLER = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
STETH_LOL_TOP_UP_EVM_SCRIPT_FACTORY = "0x1F2b79FE297B7098875930bBA6dd17068103897E"

AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
CSM_PROXY = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
CSM_IMPL = "0x8daEa53b17a629918CDFAB785C5c74077c1D895B"
MEV_BOOST_ALLOWED_LIST = "0xF95f069F9AD107938F6ba802a3da87892298610E"
ORACLE_REPORT_SANITY_CHECKER = "0x6232397ebac4f5772e53285B26c47914E9461E75"

LIDO_AND_STETH = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
STETH_LOL_REGISTRY = "0x48c4929630099b217136b64089E8543dB0E5163a"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"

EASYTRACK_EVMSCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY = "0x00A3D6260f70b1660c8646Ef25D0820EFFd7bE60"
EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY = "0x9721c0f77E3Ea40eD592B9DCf3032DaF269c0306"
EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY = "0x6b7863f2c7dEE99D3b744fDAEDbEB1aeCC025535"

CS_ACCOUNTING_ADDRESS = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"

# Roles
MODULE_MANAGER_ROLE = "0x79dfcec784e591aafcf60db7db7b029a5c8b12aac4afd4e8c4eb740430405fa6"
EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE = "0x60b9982471bc0620c7b74959f48a86c55c92c11876fddc5b0b54d1ec47153e5d"
APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE = "0x14ca7b84baa11a976283347b0159b8ddf2dcf5fd5cf613cc567a3423cf510119"
INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE = "0xebfa317a5d279811b024586b17a50f48924bce86f6293b233927322d7209b507"

IPFS_DESCRIPTION_HASH = "bafkreianaxww5wtng4nnqpni65vi2dtvvlqntd72y2wdh4xj7ae7qyqk4m"


def test_vote(helpers, accounts, vote_ids_from_env, ldo_holder, stranger):
    easy_track = interface.EasyTrack(EASY_TRACK)
    mev_boost_allowed_list = interface.MEVBoostRelayAllowedList(MEV_BOOST_ALLOWED_LIST)
    oracle_report_sanity_checker = interface.OracleReportSanityChecker(ORACLE_REPORT_SANITY_CHECKER)
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    csm = interface.CSModule(CSM_PROXY)

    trusted_caller = accounts.at(RMC_MULTISIG_ADDRESS, force=True)

    evm_script_factories_before = easy_track.getEVMScriptFactories()
    old_manager = mev_boost_allowed_list.get_manager()
    sanity_checker_limits = oracle_report_sanity_checker.getOracleReportLimits()

    stETH_LOL_registry = interface.AllowedRecipientRegistry(STETH_LOL_REGISTRY)
    stETH_LOL_topup_factory = interface.TopUpAllowedRecipients(STETH_LOL_TOP_UP_EVM_SCRIPT_FACTORY)
    stETH_LOL_multisig = accounts.at(STETH_LOL_TRUSTED_CALLER, force=True)
    stETH_token = interface.StETH(LIDO_AND_STETH)

    
    # =======================================================================
    # ========================= Before voting tests =========================
    # =======================================================================

    # 1,3) Aragon Agent should not have EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on OracleReportSanityChecker
    agent_has_role = oracle_report_sanity_checker.hasRole(EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role

    # 2) verify exitedValidatorsPerDayLimit is still at the old value
    assert sanity_checker_limits["exitedValidatorsPerDayLimit"] == EXITED_VALIDATORS_PER_DAY_LIMIT_BEFORE

    # 4,6) Aragon Agent should not have APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE on OracleReportSanityChecker
    agent_has_role = oracle_report_sanity_checker.hasRole(APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role

    # 5) verify appearedValidatorsPerDayLimit is still at the old value
    assert sanity_checker_limits["appearedValidatorsPerDayLimit"] == APPEARED_VALIDATORS_PER_DAY_LIMIT_BEFORE

    # 7,9) Aragon Agent should not have INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE on OracleReportSanityChecker
    agent_has_role = oracle_report_sanity_checker.hasRole(INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE, AGENT)
    assert not agent_has_role

    # 8) verify initialSlashingAmountPWei is still at the old value
    assert sanity_checker_limits["initialSlashingAmountPWei"] == INITIAL_SLASHING_AMOUNT_PWEI_BEFORE

    # ==================== Easy Track MEV-Boost setup ====================

    # 10) ensure AddMEVBoostRelays factory is not already in Easy Track
    assert EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY not in evm_script_factories_before

    # 11) ensure RemoveMEVBoostRelays factory is not already in Easy Track
    assert EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY not in evm_script_factories_before

    # 12) ensure EditMEVBoostRelays factory is not already in Easy Track
    assert EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY not in evm_script_factories_before

    # 13) ensure MEV-Boost Relay Allowed List manager is not set to EasyTrackEVMScriptExecutor
    assert old_manager != EASYTRACK_EVMSCRIPT_EXECUTOR

    # ======================== CSM keyRemovalCharge =======================

    # 14,16) agent should not have MODULE_MANAGER_ROLE on CSModule
    assert csm.hasRole(MODULE_MANAGER_ROLE, agent) is False

    # 15) verify keyRemovalCharge is still at the old value
    assert csm.keyRemovalCharge() == KEY_REMOVAL_CHARGE_BEFORE

    # ================= Liquidity Observation Lab (LOL) limits ==============

    # 17) verify LOL AllowedRecipientsRegistry still holds the old limit parameters and period state
    lol_budget_limit_before, lol_period_duration_months_before = stETH_LOL_registry.getLimitParameters()
    lol_amount_spent_before, _, lol_period_start_before, lol_period_end_before = stETH_LOL_registry.getPeriodState()
    lol_spendable_balance_before = stETH_LOL_registry.spendableBalance()

    assert lol_budget_limit_before == STETH_LOL_LIMIT_BEFORE
    assert lol_period_duration_months_before == STETH_LOL_PERIOD_BEFORE
    assert lol_period_start_before == STETH_LOL_PERIOD_START_BEFORE
    assert lol_period_end_before == STETH_LOL_PERIOD_END_BEFORE

    # =======================================================================
    # ========================= Voting and Events ===========================
    # =======================================================================

    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == IPFS_DESCRIPTION_HASH

    # =======================================================================
    # ========================= After voting tests ==========================
    # =======================================================================

    assert len(events) == 17

    # Check that all events and parameters for after pectra updates are correct when voting is executed
    validate_after_pectra_updates(
        oracle_report_sanity_checker,
        events[:9],
    )

    # Check that all events and parameters for MEV-Boost Relay Allowed List management factories are correct
    validate_mev_boost_relay_management_factories_added(
        helpers,
        ldo_holder,
        stranger,
        easy_track,
        voting,
        mev_boost_allowed_list,
        trusted_caller,
        events[9:13],
        evm_script_factories_before,
    )

    # Check that all events and parameters for CSModule key removal charge update are correct
    validate_csm_key_removal_charge_update(
        agent,
        csm,
        events[13:16],
    )

    # Check that all events and parameters for LOL registry limit parameters update are correct
    validate_stETH_LOL_registry_limit_parameters_update(
        events[16:],
        easy_track,
        stETH_LOL_registry,
        stETH_LOL_topup_factory,
        stETH_LOL_multisig,
        stETH_token,
        lol_spendable_balance_before,
        lol_amount_spent_before,
        stranger,
    )


def validate_after_pectra_updates(
    oracle_report_sanity_checker,
    events,
):
    sanity_checker_limits = oracle_report_sanity_checker.getOracleReportLimits()

    # 1,3) Aragon Agent doesn't have `EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = oracle_report_sanity_checker.hasRole(EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 2) Check `exitedValidatorsPerDayLimit` sanity checker value after voting equal to 3600
    assert sanity_checker_limits["exitedValidatorsPerDayLimit"] == EXITED_VALIDATORS_PER_DAY_LIMIT_AFTER
    # 4,6) Aragon Agent doesn't have `APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = oracle_report_sanity_checker.hasRole(APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 5) Check `appearedValidatorsPerDayLimit` sanity checker value after voting equal to 1800
    assert sanity_checker_limits["appearedValidatorsPerDayLimit"] == APPEARED_VALIDATORS_PER_DAY_LIMIT_AFTER
    # 7,9) Aragon Agent doesn't have `INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE` on `OracleReportSanityChecker` contract
    agent_has_role = oracle_report_sanity_checker.hasRole(INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE, AGENT)
    assert not agent_has_role
    # 8) Check `initialSlashingAmountPWei` sanity checker value to 8
    assert sanity_checker_limits["initialSlashingAmountPWei"] == INITIAL_SLASHING_AMOUNT_PWEI_AFTER

    # Validate exitedValidatorsPerDayLimit sanity checker value set to `EXITED_VALIDATORS_PER_DAY_LIMIT_AFTER`
    validate_sc_exited_validators_limit_update(events[:3], EXITED_VALIDATORS_PER_DAY_LIMIT_AFTER)
    # Validate appearedValidatorsPerDayLimit sanity checker value set to `APPEARED_VALIDATORS_PER_DAY_LIMIT_AFTER`
    validate_appeared_validators_limit_update(events[3:6], APPEARED_VALIDATORS_PER_DAY_LIMIT_AFTER)
    # Validate initialSlashingAmountPWei sanity checker value set to `INITIAL_SLASHING_AMOUNT_PWEI_AFTER`
    validate_initial_slashing_and_penalties_update(events[6:9], INITIAL_SLASHING_AMOUNT_PWEI_AFTER)


def validate_mev_boost_relay_management_factories_added(
    helpers,
    ldo_holder,
    stranger,
    easy_track,
    voting,
    mev_boost_allowed_list,
    trusted_caller,
    events,
    evm_script_factories_before,
):
    # II. EasyTrack Factories for Managing MEV-Boost Relay Allowed List
    evm_script_factories_after = easy_track.getEVMScriptFactories()

    # Check that the new factories have been added
    assert (
        len(evm_script_factories_after) == len(evm_script_factories_before) + 3
    ), "Number of EVM script factories is incorrect"

    # 10) Add `AddMEVBoostRelay` EVM script factory
    assert EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY in evm_script_factories_after, "AddMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        event=events[0],
        p=EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
            permissions=create_permissions(mev_boost_allowed_list, "add_relay"),
        ),
        emitted_by=EASY_TRACK,
    )

    create_and_enact_add_mev_boost_relay_motion(
        easy_track,
        trusted_caller,
        mev_boost_allowed_list,
        EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
        stranger,
        helpers,
        ldo_holder,
        voting,
    )

    # 11) Add `RemoveMEVBoostRelay` EVM script factory
    assert (
        EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY in evm_script_factories_after
    ), "RemoveMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        event=events[1],
        p=EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
            permissions=create_permissions(mev_boost_allowed_list, "remove_relay"),
        ),
        emitted_by=EASY_TRACK,
    )

    create_and_enact_remove_mev_boost_relay_motion(
        easy_track,
        trusted_caller,
        mev_boost_allowed_list,
        EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
        stranger,
        helpers,
        ldo_holder,
        voting,
    )

    # 12) Add `EditMEVBoostRelay` EVM script factory
    assert EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY in evm_script_factories_after, "EditMEVBoostRelay factory not found"

    validate_evmscript_factory_added_event(
        event=events[2],
        p=EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
            permissions=create_permissions(mev_boost_allowed_list, "add_relay")
            + create_permissions(mev_boost_allowed_list, "remove_relay")[2:],
        ),
        emitted_by=EASY_TRACK,
    )

    create_and_enact_edit_mev_boost_relay_motion(
        easy_track,
        trusted_caller,
        mev_boost_allowed_list,
        EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
        stranger,
        helpers,
        ldo_holder,
        voting,
    )

    # 13) Change manager role on MEV-Boost Relay Allowed List
    assert mev_boost_allowed_list.get_manager() == EASYTRACK_EVMSCRIPT_EXECUTOR
    validate_relay_allowed_list_manager_set(
        event=events[3],
        new_manager=EASYTRACK_EVMSCRIPT_EXECUTOR,
        emitted_by=MEV_BOOST_ALLOWED_LIST,
    )


def validate_csm_key_removal_charge_update(
    agent,
    csm,
    events,
):
    # 14) Grant MODULE_MANAGER_ROLE on CSModule to Aragon Agent
    validate_grant_role_event(events[0], MODULE_MANAGER_ROLE, agent.address, agent.address)

    # 15) Reduce keyRemovalCharge from 0.05 to 0.02 ETH on CSModule
    assert csm.keyRemovalCharge() == KEY_REMOVAL_CHARGE_AFTER, "Key removal charge not updated"

    validate_set_key_removal_charge_event(events[1], KEY_REMOVAL_CHARGE_AFTER, emitted_by=CSM_IMPL)

    # 16) Revoke MODULE_MANAGER_ROLE on CSModule from Aragon Agent
    validate_revoke_role_event(events[2], MODULE_MANAGER_ROLE, agent.address, agent.address)

    assert csm.hasRole(MODULE_MANAGER_ROLE, agent.address) is False

    # scenario
    accounting = interface.CSAccounting(CS_ACCOUNTING_ADDRESS)
    address, proof = get_ea_member()
    node_operator = csm_add_node_operator(csm, accounting, address, proof)

    no = csm.getNodeOperator(node_operator)
    keys_before = no["totalAddedKeys"]
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]

    tx = csm.removeKeys(node_operator, 0, 1, {"from": manager_address})

    assert "KeyRemovalChargeApplied" in tx.events
    assert "BondCharged" in tx.events

    lido = interface.Lido(LIDO_AND_STETH)
    expected_charge_amount = lido.getPooledEthByShares(lido.getSharesByPooledEth(csm.keyRemovalCharge()))

    assert tx.events["BondCharged"]["toChargeAmount"] == expected_charge_amount

    no = csm.getNodeOperator(node_operator)

    assert no["totalAddedKeys"] == keys_before - 1


def validate_stETH_LOL_registry_limit_parameters_update(
    event,
    easy_track,
    stETH_LOL_registry,
    stETH_LOL_topup_factory,
    stETH_LOL_multisig,
    stETH_token,
    lol_spendable_balance_before,
    lol_amount_spent_before,
    stranger,
):
    # 17) Increase the limit from 2,100 to 6,000 stETH and extend the duration from 3 to 6 months on LOL AllowedRecipientsRegistry
    lol_budget_limit_after, lol_period_duration_months_after = stETH_LOL_registry.getLimitParameters()
    lol_amount_spent_after, _, lol_period_start_after, lol_period_end_after = stETH_LOL_registry.getPeriodState()
    lol_spendable_balance_after = stETH_LOL_registry.spendableBalance()

    assert lol_period_start_after == STETH_LOL_PERIOD_START_AFTER
    assert lol_period_end_after == STETH_LOL_PERIOD_END_AFTER
    assert lol_budget_limit_after == STETH_LOL_LIMIT_AFTER
    assert lol_period_duration_months_after == STETH_LOL_PERIOD_AFTER
    assert (
        lol_spendable_balance_before + (STETH_LOL_LIMIT_AFTER - STETH_LOL_LIMIT_BEFORE) == lol_spendable_balance_after
    )
    assert lol_amount_spent_before == lol_amount_spent_after

    validate_set_limit_parameter_event(
        event[0],
        limit=STETH_LOL_LIMIT_AFTER,
        period_duration_month=STETH_LOL_PERIOD_AFTER,
        period_start_timestamp=STETH_LOL_PERIOD_START_AFTER,
        emitted_by=STETH_LOL_REGISTRY,
    )

    limit_test(
        easy_track,
        stETH_LOL_registry.spendableBalance(),
        stETH_LOL_multisig,
        stETH_LOL_topup_factory,
        stETH_LOL_multisig,
        stranger,
        stETH_token,
        1000 * 10**18,
    )

    # partial withdrawal of 3000 steth in H2'2025

    # scenario test values
    h2_motion_time = 1751328001  # Tue Jul 01 2025 00:00:01 GMT+0000
    h2_period_start = 1751328000  # Tue Jul 01 2025 00:00:00 GMT+0000
    h2_period_end = 1767225600  # Thu Jan 01 2026 00:00:00 GMT+0000

    # wait until H2'2025
    chain.sleep(h2_motion_time - chain.time())
    chain.mine()
    assert chain.time() == h2_motion_time

    # pay 1000 steth
    create_and_enact_payment_motion(
        easy_track,
        stETH_LOL_multisig,
        stETH_LOL_topup_factory,
        stETH_token,
        [stETH_LOL_multisig],
        [1000 * 10**18],
        stranger,
    )

    # pay 1000 steth
    create_and_enact_payment_motion(
        easy_track,
        stETH_LOL_multisig,
        stETH_LOL_topup_factory,
        stETH_token,
        [stETH_LOL_multisig],
        [1000 * 10**18],
        stranger,
    )

    # pay 1000 steth
    create_and_enact_payment_motion(
        easy_track,
        stETH_LOL_multisig,
        stETH_LOL_topup_factory,
        stETH_token,
        [stETH_LOL_multisig],
        [1000 * 10**18],
        stranger,
    )

    lol_already_spent_h2, _, lol_period_start_h2, lol_period_end_h2 = stETH_LOL_registry.getPeriodState()
    assert lol_already_spent_h2 == 3000 * 10**18
    assert lol_period_start_h2 == h2_period_start
    assert lol_period_end_h2 == h2_period_end
    assert stETH_LOL_registry.spendableBalance() == 3000 * 10**18

# Helpers
def limit_test(
    easy_track, to_spend, trusted_caller_acc, top_up_evm_script_factory, send_to, stranger, token, max_spend_at_once
):
    # check that there is no way to spend more then expected
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            token,
            [send_to],
            [to_spend + 1],
            stranger,
        )

    # spend all step by step
    while to_spend > 0:
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            token,
            [send_to],
            [min(max_spend_at_once, to_spend)],
            stranger,
        )
        to_spend -= min(max_spend_at_once, to_spend)

    # make sure there is nothing left so that you can't spend anymore
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            token,
            [send_to],
            [1],
            stranger,
        )


def validate_sc_exited_validators_limit_update(events: list[EventDict], exitedValidatorsPerDayLimit):
    validate_grant_role_event(
        events[0],
        EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_exited_validators_per_day_limit_event(events[1], exitedValidatorsPerDayLimit, ORACLE_REPORT_SANITY_CHECKER)
    validate_revoke_role_event(
        events[2],
        EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )


def validate_appeared_validators_limit_update(events: list[EventDict], appearedValidatorsPerDayLimit):
    validate_grant_role_event(
        events[0],
        APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_appeared_validators_limit_event(events[1], appearedValidatorsPerDayLimit, ORACLE_REPORT_SANITY_CHECKER)
    validate_revoke_role_event(
        events[2],
        APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )


def validate_initial_slashing_and_penalties_update(events: list[EventDict], initialSlashingAmountPWei):
    validate_grant_role_event(
        events[0],
        INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_initial_slashing_and_penalties_event(events[1], initialSlashingAmountPWei, ORACLE_REPORT_SANITY_CHECKER)
    validate_revoke_role_event(
        events[2],
        INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
