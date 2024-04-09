from utils.config import contracts
from brownie import interface, ZERO_ADDRESS

WEI_TOLERANCE = 5  # wei tolerance to avoid rounding issue


def deploy_reward_wrapper(split_wallet, deployer):
    factory = contracts.obol_lido_split_factory
    deploy_tx = factory.createSplit(split_wallet, {"from": deployer})

    deployed_instance_address = deploy_tx.events["CreateObolLidoSplit"]["split"]
    deployed_contract = interface.ObolLidoSplit(deployed_instance_address)

    return (deployed_contract, deploy_tx)


def wrap_and_split_rewards(reward_wrapper, stranger):
    WRAPPER_FEE_PERCENTAGE_SCALE = 10**5  # dvt provider fee percentage scale

    steth, wsteth = contracts.lido, contracts.wsteth
    split_wallet = reward_wrapper.splitWallet()

    # dvt provider fee variables
    dvt_provider_fee = reward_wrapper.feeShare()
    dvt_provider_fee_recipient = reward_wrapper.feeRecipient()

    # check initial contract balance
    reward_wrapper_balance_before = steth.balanceOf(reward_wrapper)

    steth_to_distribute = reward_wrapper_balance_before
    wsteth_to_distribute = wsteth.getWstETHByStETH(steth_to_distribute)

    assert steth_to_distribute > WEI_TOLERANCE, "no steth to distribute"
    assert wsteth_to_distribute > WEI_TOLERANCE, "no wsteth to distribute"

    # get split wallet balance before distribution
    split_wallet_wsteth_balance_before = wsteth.balanceOf(split_wallet)

    # distribute wrapped rewards and fee
    dvt_provider_wsteth_balance_before = wsteth.balanceOf(dvt_provider_fee_recipient)

    reward_wrapper.distribute({"from": stranger})
    split_wallet_wsteth_balance_after = wsteth.balanceOf(split_wallet)
    dvt_provider_wsteth_balance_after = wsteth.balanceOf(dvt_provider_fee_recipient)

    # check wrapper balance after distribution
    assert steth.balanceOf(reward_wrapper.address) < WEI_TOLERANCE

    # check fee charged to dvt provider
    expected_fee_charged = wsteth_to_distribute * dvt_provider_fee // WRAPPER_FEE_PERCENTAGE_SCALE
    dvt_provider_expected_wsteth_balance = dvt_provider_wsteth_balance_before + expected_fee_charged
    assert dvt_provider_wsteth_balance_after - dvt_provider_expected_wsteth_balance <= WEI_TOLERANCE

    # check split wallet balance after distribution
    split_wallet_expected_wsteth_balance = (
        split_wallet_wsteth_balance_before + wsteth_to_distribute - expected_fee_charged
    )
    assert split_wallet_wsteth_balance_after - split_wallet_expected_wsteth_balance <= WEI_TOLERANCE
