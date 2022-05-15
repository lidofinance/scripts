"""
Tests for mev distribution for voting 17/05/2022
"""
import pytest
from brownie import interface, reverts

from utils.config import contracts
from scripts.vote_2022_05_17 import start_vote

LIDO_MEV_TX_FEE_VAULT = "0x"
TOTAL_BASIS_POINTS = 10000
MEV_TX_FEE_WITHDRAWAL_LIMIT_POINTS = 200  # 2 %


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def dao_voting_as_eoa(accounts, dao_voting):
    return accounts.at(dao_voting.address, force=True)


@pytest.fixture(scope="module")
def mev_tx_fee_vault_as_eoa(accounts):
    return accounts.at(LIDO_MEV_TX_FEE_VAULT, force=True)


@pytest.fixture(scope="module")
def lido_oracle():
    return contracts.lido_oracle


@pytest.fixture(scope="module")
def lido_mev_tx_fee_vault():
    return interface.LidoMevTxFeeVault(LIDO_MEV_TX_FEE_VAULT)


@pytest.fixture(scope="module")
def lido_oracle_as_eoa(accounts, stranger, lido_oracle, EtherFunder):
    EtherFunder.deploy(lido_oracle, {"from": stranger, "amount": 10**18})
    return accounts.at(lido_oracle, force=True)


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, ldo_holder, helpers, accounts, dao_voting):
    pass
    # vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]
    # helpers.execute_vote(
    #     vote_id=vote_id,
    #     accounts=accounts,
    #     dao_voting=dao_voting,
    #     skip_time=3 * 60 * 60 * 24,
    # )
    # print(f"vote {vote_id} was executed")


def test_mev_views_values_is_correct(lido, lido_mev_tx_fee_vault):
    # deployed LidoMevTxFeeVault has correct values
    assert lido_mev_tx_fee_vault.LIDO() == lido.address
    assert lido_mev_tx_fee_vault.TREASURY() == agent.address

    # Lido contract MEV values were set correctly
    assert lido.getTotalMevTxFeeCollected() == 0
    assert lido.getMevTxFeeWithdrawalLimitPoints() == MEV_TX_FEE_WITHDRAWAL_LIMIT_POINTS
    assert lido.getMevTxFeeVault() == LIDO_MEV_TX_FEE_VAULT


def test_set_mev_tx_fee(lido, stranger, dao_voting_as_eoa):
    # setMevTxFeeVault can't be called by stranger
    with reverts("APP_AUTH_FAILED"):
        lido.setMevTxFeeVault(stranger, {"from": stranger})

    # setMevTxFeeVault might be called by voting
    tx = lido.setMevTxFeeVault(stranger, {"from": dao_voting_as_eoa})
    assert tx.events["LidoMevTxFeeVaultSet"]["mevTxFeeVault"] == stranger
    assert lido.getMevTxFeeVault() == stranger


def test_set_mev_tx_withdrawal_limit(lido, stranger):
    # setMevTxFeeWithdrawalLimit can't be called by the stranger
    with reverts("APP_AUTH_FAILED"):
        lido.setMevTxFeeWithdrawalLimit(0, {"from": stranger})

    # setMevTxFeeWithdrawalLimit might be called by the stranger
    tx = lido.setMevTxFeeWithdrawalLimit(100, {"from": stranger})
    assert tx.events["MevTxFeeWithdrawalLimitSet"]["limitPoints"] == 100
    assert lido.getMevTxFeeWithdrawalLimitPoints() == 100


def test_receive_mev_tx_fee_permissions(lido, stranger, mev_tx_fee_vault_as_eoa):
    mev_amount = 10**18
    with reverts():
        lido.receiveMevTxFee({"from": stranger, "amount": mev_amount})

    stranger.transfer(mev_tx_fee_vault_as_eoa, mev_amount)
    tx = lido.receiveMevTxFee({"from": mev_tx_fee_vault_as_eoa, "amount": mev_amount})
    assert tx.events["MevTxFeeReceived"]["amount"] == mev_amount
    assert lido.getMevTxFeeVault() == mev_amount


@pytest.mark.parametrize("mev_reward", [0, 100 * 10**18])
@pytest.mark.parametrize("beacon_balance_delta", [1000 * 10**18, -1000 * 10**18])
def test_handle_oracle_report_with_non_zero_mev_rewards(
    lido,
    lido_oracle,
    lido_oracle_as_eoa,
    lido_mev_tx_fee_vault,
    stranger,
    mev_reward,
    beacon_balance_delta,
):
    # prepare LidoMevTxFeeVaule
    if mev_reward > 0:
        stranger.transfer(lido_mev_tx_fee_vault, mev_reward)
    assert lido_mev_tx_fee_vault.balance() == mev_reward

    # prepare new report data
    prev_report = lido.getBeaconStat().dict()
    beacon_validators = prev_report["beaconValidators"]
    beacon_balance = prev_report["beaconBalance"] + beacon_balance_delta
    buffered_ether_before = lido.getBufferedEther()

    # simulate oracle report
    tx = lido.handleOracleReport(
        beacon_validators, beacon_balance, {"from": lido_oracle_as_eoa}
    )

    # validate that MEV rewards were added to the buffered ether
    expected_mev_reward = (
        mev_reward * MEV_TX_FEE_WITHDRAWAL_LIMIT_POINTS // TOTAL_BASIS_POINTS
    )
    assert lido.getBufferedEther() == buffered_ether_before + expected_mev_reward

    # validate that rewards were distributed
    if beacon_balance_delta > 0:
        assert len(tx.events["Transfer"]) > 0
    else:
        assert len(tx.events["Transfer"]) == 0
