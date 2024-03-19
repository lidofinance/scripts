"""
Tests for voting 19/03/2024

"""

from scripts.vote_2024_03_19 import start_vote
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS
from configs.config_mainnet import (
    DAI_TOKEN,
    USDC_TOKEN,
    USDT_TOKEN,
)
from utils.test.easy_track_helpers import create_and_enact_payment_motion, check_add_and_remove_recipient_with_voting

STETH_TRANSFER_MAX_DELTA = 2


def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder):
    steth = contracts.lido
    easy_track = contracts.easy_track

    evm_script_factories_before = easy_track.getEVMScriptFactories()

    tmc_steth_top_up_evm_script_factory_new = "0x6e04aED774B7c89BB43721AcDD7D03C872a51B69"
    assert tmc_steth_top_up_evm_script_factory_new not in evm_script_factories_before

    tmc_stables_top_up_evm_script_factory_new = "0x0d2aefA542aFa8d9D1Ec35376068B88042FEF5f6"
    assert tmc_stables_top_up_evm_script_factory_new not in evm_script_factories_before

    stonks_multisig_acc = accounts.at("0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647", force=True)
    stonks_steth_contract = accounts.at("0x3e2D251275A92a8169A3B17A2C49016e2de492a7", force=True)
    stonks_dai_usdc_contract = accounts.at("0x79f5E20996abE9f6a48AF6f9b13f1E55AED6f06D", force=True)
    stonks_usdc_dai_contract = accounts.at("0x2B5a3944A654439379B206DE999639508bA2e850", force=True)
    stonks_usdt_dai_contract = accounts.at("0x64B6aF9A108dCdF470E48e4c0147127F26221A7C", force=True)


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")


    #
    # Easy Track stETH and stables top up setups for Lido stonks
    #

    evm_script_factories_after = easy_track.getEVMScriptFactories()

    # 1. Add TMC stETH top up EVM script factory address TBA (AllowedRecipientsRegistry address TBA)
    assert tmc_steth_top_up_evm_script_factory_new in evm_script_factories_after
    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=stonks_multisig_acc,
        factory=tmc_steth_top_up_evm_script_factory_new,
        token=steth,
        recievers=[stonks_steth_contract],
        transfer_amounts=[10 * 10**18],
        stranger=stranger,
    )

    tmc_steth_allowed_recipients_registry = interface.AllowedRecipientRegistry(
        "0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0"
    )
    check_add_and_remove_recipient_with_voting(
        registry=tmc_steth_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    dai_transfer_amount = 1_000 * 10**18
    prepare_agent_for_steth_payment(4 * dai_transfer_amount)

    usdc_transfer_amount = 1_000 * 10**6
    prepare_agent_for_usdc_payment(4 * usdc_transfer_amount)

    usdt_transfer_amount = 1_000 * 10**6
    prepare_agent_for_usdt_payment(4 * usdt_transfer_amount)

    # 2. Add TMC stables top up EVM script factory address TBA (AllowedRecipientsRegistry address TBA, AllowedTokensRegistry address TBA)
    assert tmc_stables_top_up_evm_script_factory_new in evm_script_factories_after

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=stonks_multisig_acc,
        factory=tmc_stables_top_up_evm_script_factory_new,
        token=interface.Dai(DAI_TOKEN),
        recievers=[stonks_dai_usdc_contract],
        transfer_amounts=[dai_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=stonks_multisig_acc,
        factory=tmc_stables_top_up_evm_script_factory_new,
        token=interface.Usdc(USDC_TOKEN),
        recievers=[stonks_usdc_dai_contract],
        transfer_amounts=[usdc_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=stonks_multisig_acc,
        factory=tmc_stables_top_up_evm_script_factory_new,
        token=interface.Usdt(USDT_TOKEN),
        recievers=[stonks_usdt_dai_contract],
        transfer_amounts=[usdt_transfer_amount],
        stranger=stranger,
    )

    with reverts("TOKEN_NOT_ALLOWED"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=stonks_multisig_acc,
            factory=tmc_stables_top_up_evm_script_factory_new,
            token=steth,
            recievers=[stonks_dai_usdc_contract],
            transfer_amounts=[1],
            stranger=stranger,
        )

    rcc_stables_allowed_recipients_registry = interface.AllowedRecipientRegistry(
        "0x3f0534CCcFb952470775C516DC2eff8396B8A368"
    )
    check_add_and_remove_recipient_with_voting(
        registry=rcc_stables_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )


def prepare_agent_for_steth_payment(amount: int):
    agent, steth = contracts.agent, contracts.lido
    eth_whale = accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)
    if steth.balanceOf(agent) < amount:
        steth.submit(ZERO_ADDRESS, {"from": eth_whale, "value": amount + 2 * STETH_TRANSFER_MAX_DELTA})
        steth.transfer(agent, amount + STETH_TRANSFER_MAX_DELTA, {"from": eth_whale})
    assert steth.balanceOf(agent) >= amount, "Insufficient stETH balance"


def prepare_agent_for_dai_payment(amount: int):
    agent, dai = contracts.agent, interface.Dai(DAI_TOKEN)
    if dai.balanceOf(agent) < amount:
        dai_ward_impersonated = accounts.at("0x9759A6Ac90977b93B58547b4A71c78317f391A28", force=True)
        dai.mint(agent, amount, {"from": dai_ward_impersonated})

    assert dai.balanceOf(agent) >= amount, f"Insufficient DAI balance"


def prepare_agent_for_usdc_payment(amount: int):
    agent, usdc = contracts.agent, interface.Usdc(USDC_TOKEN)
    if usdc.balanceOf(agent) < amount:
        usdc_minter = accounts.at("0x5B6122C109B78C6755486966148C1D70a50A47D7", force=True)
        usdc_controller = accounts.at("0x79E0946e1C186E745f1352d7C21AB04700C99F71", force=True)
        usdc_master_minter = interface.UsdcMasterMinter("0xE982615d461DD5cD06575BbeA87624fda4e3de17")
        usdc_master_minter.incrementMinterAllowance(amount, {"from": usdc_controller})
        usdc.mint(agent, amount, {"from": usdc_minter})

    assert usdc.balanceOf(agent) >= amount, "Insufficient USDC balance"


def prepare_agent_for_usdt_payment(amount: int):
    agent, usdt = contracts.agent, interface.Usdt(USDT_TOKEN)
    if usdt.balanceOf(agent) < amount:
        usdt_owner = accounts.at("0xC6CDE7C39eB2f0F0095F41570af89eFC2C1Ea828", force=True)
        usdt.issue(amount, {"from": usdt_owner})
        usdt.transfer(agent, amount, {"from": usdt_owner})

    assert usdt.balanceOf(agent) >= amount, "Insufficient USDT balance"

