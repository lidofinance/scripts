from utils.config import contracts
from brownie import interface, ZERO_ADDRESS

SPLIT_DISTRIBUTOR_FEE = 0
SPLIT_CONTROLLER = ZERO_ADDRESS

WEI_TOLERANCE = 5  # wei tolerance to avoid rounding issue


def deploy_split_wallet(members, percent_allocation, deployer):
    factory = contracts.split_main

    deploy_tx = factory.createSplit(
        members,
        percent_allocation,
        SPLIT_DISTRIBUTOR_FEE,
        SPLIT_CONTROLLER,
        {"from": deployer or members[0]},
    )

    deployed_instance_address = deploy_tx.events["CreateSplit"]["split"]
    deployed_contract = interface.SplitWallet(deployed_instance_address)

    return (deployed_contract, deploy_tx)


def get_split_percentage_scale():
    return contracts.split_main.PERCENTAGE_SCALE()


def get_split_percent_allocation(total_members, percentage_scale):
    # distribute shares evenly between participants

    shares = [percentage_scale // total_members] * total_members
    remainder = percentage_scale % total_members

    for i in range(remainder):
        shares[i] += 1

    return shares


def get_balances_on_split_main(participants, token):
    split_main = contracts.split_main

    balances = []
    for participant in participants:
        balance = split_main.getERC20Balance(participant, token)
        balances.append(balance)

    return balances


def split_and_withdraw_wsteth_rewards(split_wallet, participants, percent_allocation, percentage_scale, stranger):
    split_main = contracts.split_main
    wsteth = contracts.wsteth

    # check split wallet balance initial state
    split_wallet_balance_before = wsteth.balanceOf(split_wallet)
    wsteth_to_distribute = split_wallet_balance_before
    assert wsteth_to_distribute > WEI_TOLERANCE, "no wsteth to distribute"

    # collect participants balances on split main contract before distribution
    participant_balances_on_split_main_before = get_balances_on_split_main(participants, wsteth)

    # distribute rewards
    distribute_tx = split_main.distributeERC20(
        split_wallet,
        wsteth.address,
        participants,
        percent_allocation,
        0,
        ZERO_ADDRESS,
        {"from": stranger},
    )
    distribute_event = distribute_tx.events["DistributeERC20"]
    assert distribute_event["split"] == split_wallet
    assert distribute_event["token"] == wsteth.address
    assert wsteth_to_distribute - distribute_event["amount"] <= WEI_TOLERANCE
    assert distribute_event["distributorAddress"] == ZERO_ADDRESS

    # check participants balances on split main contract after distribution
    participant_balances_on_split_main_after = get_balances_on_split_main(participants, wsteth)
    for index, balance_on_split_main_after in enumerate(participant_balances_on_split_main_after):
        balance_on_split_main_before = participant_balances_on_split_main_before[index]
        participant_income = balance_on_split_main_after - balance_on_split_main_before

        expected_participant_income = wsteth_to_distribute * percent_allocation[index] // percentage_scale

        assert participant_income > 0
        assert expected_participant_income - participant_income <= WEI_TOLERANCE

    # check that all wsteth was distributed on split main contract
    total_wsteth_distributed = sum(participant_balances_on_split_main_after)
    assert wsteth_to_distribute - total_wsteth_distributed <= len(participants) * WEI_TOLERANCE

    # check that a participant can withdraw wsteth from split main
    participant = participants[0]
    participant_balance_on_split_main = participant_balances_on_split_main_after[0]

    participant_wsteth_balance_before = wsteth.balanceOf(participant)

    withdraw_eth = 0  # withdraw only erc20
    withdraw_tx = split_main.withdraw(participant, withdraw_eth, [wsteth.address], {"from": participant})

    participant_wsteth_balance_after = wsteth.balanceOf(participant)
    withdrawn_wsteth = participant_wsteth_balance_after - participant_wsteth_balance_before

    withdraw_event = withdraw_tx.events["Withdrawal"]
    assert len(withdraw_event["tokens"]) == 1
    assert withdraw_event["tokens"][0] == wsteth.address
    assert withdraw_event["tokenAmounts"][0] == withdrawn_wsteth

    assert participant_balance_on_split_main - withdrawn_wsteth <= WEI_TOLERANCE
