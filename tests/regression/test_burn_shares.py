"""
Tests for lido burnShares method
"""
import pytest
from utils.config import contracts
from brownie import reverts, ZERO_ADDRESS, accounts, chain
from utils.evm_script import encode_error

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
    with reverts(encode_error("AppAuthLidoFailed()")):
        contracts.burner.commitSharesToBurn(shares_to_burn, {"from": stranger})

    contracts.lido.approve(contracts.burner, 10**24, {"from": stranger})

    contracts.burner.requestBurnSharesForCover(stranger, shares_to_burn, {"from": lido})

    prev_report = contracts.lido.getBeaconStat().dict()
    beacon_validators = prev_report["beaconValidators"]
    beacon_balance = prev_report["beaconBalance"]
    contracts.lido.handleOracleReport(
        chain.time(),
        0,
        beacon_validators,
        beacon_balance,
        0,
        0,
        shares_to_burn,
        [],
        0,
        {"from": contracts.accounting_oracle},
    )

    assert contracts.lido.sharesOf(stranger) == 0
    assert contracts.lido.totalSupply() == total_eth
    assert contracts.lido.getTotalShares() == total_shares - shares_to_burn
