"""
Tests for voting 26/11/2024.
"""

from scripts.vote_2024_11_26 import start_vote
from brownie import interface, reverts, accounts, ZERO_ADDRESS, chain, web3
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS
from utils.config import contracts
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event,
    validate_set_spent_amount_event,
)
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_reward_address_set_event,
    NodeOperatorRewardAddressSetItem
)
from configs.config_mainnet import ( USDC_TOKEN )

STETH_TRANSFER_MAX_DELTA = 2

def test_vote(helpers, accounts, vote_ids_from_env, stranger):

    # misc
    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")
    nor = contracts.node_operators_registry
    prepare_agent_for_usdc_payment(15_000_000 * (10**6))
    prepare_agent_for_steth_payment(20_000 * 10**18)

    # Item 1
    atc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")
    atc_multisig_acc = accounts.at("0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956", force=True)
    atc_trusted_caller_acc = atc_multisig_acc
    atc_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab")
    atcBudgetLimitAfterExpected = 7_000_000 * 10**18
    atcSpendLimitAfterExpected = 5_500_000 * 10**18

    # Item 2
    pml_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    pml_multisig_acc = accounts.at("0x17F6b2C738a63a8D3A113a228cfd0b373244633D", force=True)
    pml_trusted_caller_acc = pml_multisig_acc
    pml_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D")
    pmlBudgetLimitAfterExpected = 4_000_000 * 10**18
    pmlSpendLimitAfterExpected = 3_000_000 * 10**18

    # Item 3, 4
    tmc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0")
    tmc_multisig = accounts.at("0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647", force=True)
    tmc_trusted_caller = tmc_multisig
    tmc_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x6e04aED774B7c89BB43721AcDD7D03C872a51B69")
    stETH_token = interface.ERC20("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
    stonks_steth_contract = accounts.at("0x3e2D251275A92a8169A3B17A2C49016e2de492a7", force=True)
    tmcBudgetAfterExpected = 12_000 * 10**18
    tmcNewSpentAmountExpected = 0

    # Item 5
    # NO's data indexes
    activeIndex = 0
    nameIndex = 1
    rewardAddressIndex = 2
    stakingLimitIndex = 3
    stoppedValidatorsIndex = 4
    # Simply Staking params
    SimplyStakingId = 16
    SimplyStakingName = "Simply Staking"
    SimplyStakingOldRewardAddress = "0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd"
    SimplyStakingNewRewardAddress = "0x1EC3Cbe8fb1D8019092500CcA2111C158a35bC82"


    # Item 1
    atcBudgetLimitBefore, atcPeriodDurationMonthsBefore = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getLimitParameters()
    assert atcBudgetLimitBefore == 1_500_000 * 10 ** 18
    assert atcPeriodDurationMonthsBefore == 3
    assert 0 == interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).spendableBalance()

    # Item 2
    pmlBudgetLimitBefore, pmlPeriodDurationMonthsBefore = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).getLimitParameters()
    assert pmlBudgetLimitBefore == 6_000_000 * 10 ** 18
    assert pmlPeriodDurationMonthsBefore == 3
    assert 5_000_000 * 10**18 == interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).spendableBalance()

    # Item 3
    tmcBudgetLimitBefore, tmcPeriodDurationMonthsBefore = interface.AllowedRecipientRegistry(tmc_allowed_recipients_registry).getLimitParameters()
    assert tmcBudgetLimitBefore == 9_000 * 10 ** 18
    assert tmcPeriodDurationMonthsBefore == 6

    # Item 4
    alreadySpentAmountBefore, spendableBalanceInPeriodBefore, periodStartTimestampBefore, periodEndTimestampBefore = tmc_allowed_recipients_registry.getPeriodState()
    assert alreadySpentAmountBefore > 0

    # Item 5
    SimplyStakingDataBefore = nor.getNodeOperator(SimplyStakingId, True)
    assert SimplyStakingOldRewardAddress == SimplyStakingDataBefore[rewardAddressIndex]
    assert SimplyStakingName == SimplyStakingDataBefore[nameIndex]


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")


    # Item 1
    atcBudgetLimitAfter, atcPeriodDurationMonthsAfter = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getLimitParameters()
    atc_spend_limit_after = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).getPeriodState()[1]
    atcSpendableBalanceAfter = interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).spendableBalance()
    assert atcBudgetLimitAfter == atcBudgetLimitAfterExpected
    assert atcPeriodDurationMonthsAfter == 3
    assert atc_spend_limit_after == atcSpendLimitAfterExpected
    assert interface.AllowedRecipientRegistry(atc_allowed_recipients_registry).isUnderSpendableBalance(atcSpendableBalanceAfter, 3)
    assert atcSpendableBalanceAfter == atcSpendLimitAfterExpected
    limit_test(easy_track,
               int(atcSpendableBalanceAfter / (10**18)) * 10**6,
               atc_trusted_caller_acc,
               atc_top_up_evm_script_factory,
               atc_multisig_acc,
               stranger,
               interface.Usdc(USDC_TOKEN),
               2_000_000 * 10**6
    )

    # Item 2
    pmlBudgetLimitAfter, pmlPeriodDurationMonthsAfter = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).getLimitParameters()
    pml_spend_limit_after = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).getPeriodState()[1]
    pmlSpendableBalanceAfter = interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).spendableBalance()
    assert pmlBudgetLimitAfter == pmlBudgetLimitAfterExpected
    assert pmlPeriodDurationMonthsAfter == 3
    assert pml_spend_limit_after == pmlSpendLimitAfterExpected
    assert interface.AllowedRecipientRegistry(pml_allowed_recipients_registry).isUnderSpendableBalance(pmlSpendableBalanceAfter, 3)
    assert pmlSpendableBalanceAfter == pmlSpendLimitAfterExpected
    limit_test(easy_track,
               int(pmlSpendableBalanceAfter / (10**18)) * 10**6,
               pml_trusted_caller_acc,
               pml_top_up_evm_script_factory,
               pml_multisig_acc,
               stranger,
               interface.Usdc(USDC_TOKEN),
               2_000_000 * 10**6
    )

    # Item 3
    tmcBudgetLimitAfter, tmcPeriodDurationMonthsAfter = interface.AllowedRecipientRegistry(tmc_allowed_recipients_registry).getLimitParameters()
    assert tmcBudgetLimitAfter == tmcBudgetAfterExpected
    assert tmcPeriodDurationMonthsAfter == 6

    # Item 4
    alreadySpentAmountAfter = tmc_allowed_recipients_registry.getPeriodState()[0]
    assert alreadySpentAmountAfter == tmcNewSpentAmountExpected
    tmcSpendableBalanceAfter = interface.AllowedRecipientRegistry(tmc_allowed_recipients_registry).spendableBalance()
    assert tmcSpendableBalanceAfter == tmcBudgetAfterExpected
    limit_test(easy_track,
               tmcSpendableBalanceAfter,
               tmc_trusted_caller,
               tmc_top_up_evm_script_factory,
               stonks_steth_contract,
               stranger,
               stETH_token,
               1_000 * 10 ** 18
    )

    # Item 5
    SimplyStakingDataAfter = nor.getNodeOperator(SimplyStakingId, True)
    assert SimplyStakingNewRewardAddress == SimplyStakingDataAfter[rewardAddressIndex]
    assert SimplyStakingDataBefore[nameIndex] == SimplyStakingDataAfter[nameIndex]
    assert SimplyStakingDataBefore[activeIndex] == SimplyStakingDataAfter[activeIndex]
    assert SimplyStakingDataBefore[stakingLimitIndex] == SimplyStakingDataAfter[stakingLimitIndex]
    assert SimplyStakingDataBefore[stoppedValidatorsIndex] == SimplyStakingDataAfter[stoppedValidatorsIndex]


    # events
    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)

    validate_set_limit_parameter_event(
        evs[0],
        limit=atcBudgetLimitAfterExpected,
        period_duration_month=3,
        period_start_timestamp=1727740800,
    )
    validate_set_limit_parameter_event(
        evs[1],
        limit=pmlBudgetLimitAfterExpected,
        period_duration_month=3,
        period_start_timestamp=1727740800,
    )
    validate_set_limit_parameter_event(
        evs[2],
        limit=tmcBudgetAfterExpected,
        period_duration_month=6,
        period_start_timestamp=1719792000,
    )
    validate_set_spent_amount_event(
        evs[3],
        new_spent_amount=tmcNewSpentAmountExpected,
    )
    validate_node_operator_reward_address_set_event(
        evs[4],
        NodeOperatorRewardAddressSetItem(
            nodeOperatorId=SimplyStakingId,
            reward_address=SimplyStakingNewRewardAddress
        )
    )

def limit_test(easy_track, to_spend, trusted_caller_acc, top_up_evm_script_factory, multisig_acc, stranger, token, max_spend_at_once):

    chain.snapshot()

    # check that there is no way to spend more then expected
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller_acc,
            top_up_evm_script_factory,
            token,
            [multisig_acc],
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
            [multisig_acc],
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
            [multisig_acc],
            [1],
            stranger,
        )

    chain.revert()

def prepare_agent_for_steth_payment(amount: int):
    agent, steth = contracts.agent, contracts.lido
    eth_whale = accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)
    if steth.balanceOf(agent) < amount:
        steth.submit(ZERO_ADDRESS, {"from": eth_whale, "value": amount + 2 * STETH_TRANSFER_MAX_DELTA})
        steth.transfer(agent, amount + STETH_TRANSFER_MAX_DELTA, {"from": eth_whale})
    assert steth.balanceOf(agent) >= amount, "Insufficient stETH balance"

def prepare_agent_for_usdc_payment(amount: int):
    agent, usdc = contracts.agent, interface.Usdc(USDC_TOKEN)
    if usdc.balanceOf(agent) < amount:
        usdc_minter = accounts.at("0x5B6122C109B78C6755486966148C1D70a50A47D7", force=True)
        usdc_controller = accounts.at("0x79E0946e1C186E745f1352d7C21AB04700C99F71", force=True)
        usdc_master_minter = interface.UsdcMasterMinter("0xE982615d461DD5cD06575BbeA87624fda4e3de17")

        web3.provider.make_request("evm_setAccountBalance", [usdc_controller.address, hex(100_000 * 10**18)])
        assert usdc_controller.balance() >= 100_000 * 10**18

        usdc_master_minter.incrementMinterAllowance(amount, {"from": usdc_controller})
        usdc.mint(agent, amount, {"from": usdc_minter})

    assert usdc.balanceOf(agent) >= amount, "Insufficient USDC balance"
