import math
from brownie import ZERO_ADDRESS, chain

from utils.test.oracle_report_helpers import oracle_report
from utils.test.helpers import ETH, almostEqEth
from utils.config import contracts


def test_all_round_happy_path(accounts, stranger, steth_holder):
    amount = ETH(100)
    max_deposit = 150
    curated_module_id = 1


    contracts.lido.approve(contracts.withdrawal_queue.address, 1000, {"from": steth_holder})
    contracts.withdrawal_queue.requestWithdrawals([1000], steth_holder, {"from": steth_holder})

    steth_balance_before_submit = contracts.lido.balanceOf(stranger)
    eth_balance_before_submit = stranger.balance()

    assert steth_balance_before_submit == 0

    # Submitting ETH

    stakeLimitInfo = contracts.lido.getStakeLimitFullInfo()
    growthPerBlock = stakeLimitInfo["maxStakeLimit"] // stakeLimitInfo["maxStakeLimitGrowthBlocks"]

    print(growthPerBlock)

    total_supply_before_submit = contracts.lido.totalSupply()
    buffered_ether_before_submit = contracts.lido.getBufferedEther()
    staking_limit_before_submit = contracts.lido.getCurrentStakeLimit()

    print("block before: ", chain.height)

    # TODO: do calculation right

    submit_tx = contracts.lido.submit(ZERO_ADDRESS, {"from": stranger, "amount": amount})

    print("block after submit: ", chain.height)

    steth_balance_after_submit = contracts.lido.balanceOf(stranger)
    total_supply_after_submit = contracts.lido.totalSupply()
    buffered_ether_after_submit = contracts.lido.getBufferedEther()
    staking_limit_after_submit = contracts.lido.getCurrentStakeLimit()

    print("block after view: ", chain.height)
    assert almostEqEth(steth_balance_after_submit, steth_balance_before_submit + amount)
    assert eth_balance_before_submit == stranger.balance() + amount

    shares_to_be_minted = contracts.lido.getSharesByPooledEth(amount)

    submit_event = submit_tx.events["Submitted"]
    transfer_shares_event = submit_tx.events["TransferShares"]

    assert submit_event["sender"] == stranger
    assert submit_event["amount"] == amount
    assert submit_event["referral"] == ZERO_ADDRESS

    shares_minted_on_submit = contracts.lido.getSharesByPooledEth(amount)

    assert shares_to_be_minted == contracts.lido.sharesOf(stranger)
    assert shares_to_be_minted == shares_minted_on_submit
    assert transfer_shares_event["from"] == ZERO_ADDRESS
    assert transfer_shares_event["to"] == stranger
    assert almostEqEth(transfer_shares_event["sharesValue"], shares_minted_on_submit)

    assert total_supply_after_submit == total_supply_before_submit + amount
    assert buffered_ether_after_submit == buffered_ether_before_submit + amount

    if staking_limit_before_submit >= stakeLimitInfo["maxStakeLimit"] - growthPerBlock:
        assert staking_limit_after_submit == staking_limit_before_submit - amount
    else:
        assert staking_limit_after_submit == staking_limit_before_submit - amount + growthPerBlock

    # Depositing ETH
    dsm = accounts.at(contracts.deposit_security_module.address, force=True)
    deposited_validators_before_deposit, _, _ = contracts.lido.getBeaconStat()

    withdrawal_unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()

    assert contracts.lido.getDepositableEther() == buffered_ether_after_submit - withdrawal_unfinalized_steth

    deposit_tx = contracts.lido.deposit(max_deposit, curated_module_id, "0x0", {"from": dsm})
    buffered_ether_after_deposit = contracts.lido.getBufferedEther()

    unbuffered_event = deposit_tx.events["Unbuffered"]
    deposit_validators_changed_event = deposit_tx.events["DepositedValidatorsChanged"]

    deposits_count = math.floor(unbuffered_event["amount"] / ETH(32))

    assert buffered_ether_after_deposit == buffered_ether_after_submit - unbuffered_event["amount"]
    assert (
        deposit_validators_changed_event["depositedValidators"] == deposited_validators_before_deposit + deposits_count
    )

    # Rebasing (Increasing balance)

    treasury = contracts.lido_locator.treasury()
    nor = contracts.node_operators_registry.address
    nor_operators_count = contracts.node_operators_registry.getNodeOperatorsCount()
    treasury_balance_before_rebase = contracts.lido.sharesOf(treasury)

    report_tx, extra_tx = oracle_report(cl_diff=ETH(100))

    steth_balance_after_rebase = contracts.lido.balanceOf(stranger)
    treasury_balance_after_rebase = contracts.lido.sharesOf(treasury)

    token_rebased_event = report_tx.events["TokenRebased"]
    transfer_event = report_tx.events["Transfer"]

    assert extra_tx.events.count("Transfer") == nor_operators_count
    assert report_tx.events.count("TokenRebased") == 1
    assert report_tx.events.count("WithdrawalsFinalized") == 1
    assert report_tx.events.count("StETHBurnt") == 1

    assert (
        token_rebased_event["postTotalShares"]
        == token_rebased_event["preTotalShares"]
        + token_rebased_event["sharesMintedAsFees"]
        - report_tx.events["StETHBurnt"]["amountOfShares"]
    )

    assert transfer_event[0]["from"] == contracts.withdrawal_queue
    assert transfer_event[0]["to"] == contracts.burner

    assert transfer_event[1]["from"] == ZERO_ADDRESS
    assert transfer_event[1]["to"] == nor

    assert transfer_event[2]["from"] == ZERO_ADDRESS
    assert transfer_event[2]["to"] == treasury

    assert almostEqEth(
        treasury_balance_after_rebase,
        treasury_balance_before_rebase + contracts.lido.getSharesByPooledEth(transfer_event[2]["value"]),
    )

    assert treasury_balance_after_rebase > treasury_balance_before_rebase

    assert steth_balance_after_rebase - steth_balance_after_submit

    # Requesting withdrawal

    assert len(contracts.withdrawal_queue.getWithdrawalRequests(stranger, {"from": stranger})) == 0

    amount_with_rewards = contracts.lido.balanceOf(stranger)

    approve_tx = contracts.lido.approve(contracts.withdrawal_queue.address, amount_with_rewards, {"from": stranger})

    approve_event = approve_tx.events["Approval"]

    assert approve_event["value"] == amount_with_rewards
    assert approve_event["owner"] == stranger
    assert approve_event["spender"] == contracts.withdrawal_queue.address

    last_request_id_before = contracts.withdrawal_queue.getLastRequestId()

    withdrawal_request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [amount_with_rewards], stranger, {"from": stranger}
    )

    withdrawal_request_event = withdrawal_request_tx.events["WithdrawalRequested"]
    withdrawal_request_transfer_event = withdrawal_request_tx.events["Transfer"]

    request_ids = [withdrawal_request_event["requestId"]]

    assert withdrawal_request_transfer_event[0]["from"] == stranger
    assert withdrawal_request_transfer_event[0]["to"] == contracts.withdrawal_queue.address
    assert withdrawal_request_transfer_event[0]["value"] == amount_with_rewards

    assert withdrawal_request_transfer_event[1]["tokenId"] == request_ids[0]
    assert withdrawal_request_transfer_event[1]["from"] == ZERO_ADDRESS
    assert withdrawal_request_transfer_event[1]["to"] == stranger

    assert withdrawal_request_event["requestor"] == stranger
    assert withdrawal_request_event["owner"] == stranger
    assert withdrawal_request_event["amountOfStETH"] == amount_with_rewards

    steth_balance_after_withdrawal_request = contracts.lido.balanceOf(stranger)
    [(_, _, _, _, finalized, _)] = contracts.withdrawal_queue.getWithdrawalStatus(request_ids)

    assert almostEqEth(steth_balance_after_withdrawal_request, steth_balance_after_rebase - amount_with_rewards)
    assert len(contracts.withdrawal_queue.getWithdrawalRequests(stranger, {"from": stranger})) == 1
    assert contracts.withdrawal_queue.getLastRequestId() == last_request_id_before + 1
    assert not finalized

    # Rebasing (Withdrawal finalization)

    assert almostEqEth(contracts.lido.balanceOf(contracts.withdrawal_queue), amount_with_rewards)

    locked_ether_amount_before_finalization = contracts.withdrawal_queue.getLockedEtherAmount()
    report_tx, _ = oracle_report(cl_diff=ETH(100))

    locked_ether_amount_after_finalization = contracts.withdrawal_queue.getLockedEtherAmount()
    withdrawal_finalized_event = report_tx.events["WithdrawalsFinalized"]

    assert contracts.lido.balanceOf(contracts.withdrawal_queue) == 0
    assert withdrawal_finalized_event["amountOfETHLocked"] == amount_with_rewards
    assert withdrawal_finalized_event["from"] == request_ids[0]
    assert withdrawal_finalized_event["to"] == request_ids[0]
    assert locked_ether_amount_before_finalization == locked_ether_amount_after_finalization - amount_with_rewards

    # Withdrawing

    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    hints = contracts.withdrawal_queue.findCheckpointHints(request_ids, 1, lastCheckpointIndex)
    [(_, _, _, _, finalized, _)] = contracts.withdrawal_queue.getWithdrawalStatus(request_ids)

    [claimable_ether_before_claim] = contracts.withdrawal_queue.getClaimableEther(request_ids, hints)
    eth_balance_before_withdrawal = stranger.balance()

    assert finalized
    assert claimable_ether_before_claim == amount_with_rewards

    claim_tx = contracts.withdrawal_queue.claimWithdrawals(request_ids, hints, {"from": stranger})

    claim_event = claim_tx.events["WithdrawalClaimed"]
    transfer_event = claim_tx.events["Transfer"]

    assert claim_event["requestId"] == request_ids[0]
    assert claim_event["owner"] == stranger
    assert claim_event["receiver"] == stranger
    assert claim_event["amountOfETH"] == amount_with_rewards
    assert transfer_event["from"] == stranger
    assert transfer_event["to"] == ZERO_ADDRESS
    assert transfer_event["tokenId"] == request_ids[0]

    assert eth_balance_before_withdrawal == stranger.balance() - amount_with_rewards
    assert (
        locked_ether_amount_after_finalization
        == contracts.withdrawal_queue.getLockedEtherAmount() + amount_with_rewards
    )

    [(_, _, _, _, finalized, claimed)] = contracts.withdrawal_queue.getWithdrawalStatus(request_ids, {"from": stranger})
    [claimable_ether_after_claim] = contracts.withdrawal_queue.getClaimableEther(request_ids, hints)

    assert finalized
    assert claimed
    assert not claimable_ether_after_claim
