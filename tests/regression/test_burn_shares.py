"""
Tests for lido burnShares method
"""
import eth_abi
import pytest
from utils.config import contracts
from brownie import reverts, ZERO_ADDRESS, web3, accounts

def test_burn_shares_by_stranger(stranger):
    lido = accounts.at(contracts.lido, force=True)

    # Stake ETH by stranger to receive stETH
    stranger_submit_amount = 10**18
    contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": stranger_submit_amount})
    stranger_steth_balance_before = contracts.lido.balanceOf(stranger)
    shares_to_burn = contracts.lido.sharesOf(stranger)
    assert abs(stranger_submit_amount - stranger_steth_balance_before) <= 2

    total_eth = contracts.lido.totalSupply()
    total_shares = contracts.lido.getTotalShares()

    # Test that stranger can't burnShares
    with reverts("typed error: 0x7e717823"): # keccak256("AppAuthLidoFailed()")
        contracts.burner.commitSharesToBurn(shares_to_burn, {"from": stranger})

    contracts.lido.approve(contracts.burner, 10**24, {"from": stranger})

    contracts.burner.requestBurnSharesForCover(stranger, shares_to_burn, {"from": lido})

    tx = contracts.burner.commitSharesToBurn(shares_to_burn, {"from": lido})



    assert contracts.lido.sharesOf(stranger) == 0
    assert contracts.lido.totalSupply() == total_eth
    assert contracts.lido.getTotalShares() == total_shares - shares_to_burn
