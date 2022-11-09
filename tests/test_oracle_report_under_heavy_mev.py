import pytest
from functools import partial
from brownie import interface, web3, chain
from scripts.vote_2022_11_09 import start_vote

from utils.config import contracts, lido_dao_execution_layer_rewards_vault


LIDO_EXECUTION_LAYER_REWARDS_VAULT = lido_dao_execution_layer_rewards_vault
TOTAL_BASIS_POINTS = 10000
EL_REWARDS_FEE_WITHDRAWAL_LIMIT = 2


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def eth_whale(accounts):
    return accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)


@pytest.fixture(scope="module")
def lido_oracle():
    return contracts.lido_oracle


@pytest.fixture(scope="module")
def lido_execution_layer_rewards_vault():
    return interface.LidoExecutionLayerRewardsVault(LIDO_EXECUTION_LAYER_REWARDS_VAULT)


@pytest.fixture(scope="module", autouse=True)
def autoexecute_vote(vote_id_from_env, helpers, accounts, dao_voting, ldo_holder):
    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24)


def test_report_beacon_with_el_rewards(
    acl,
    lido,
    lido_oracle,
    dao_voting,
    lido_execution_layer_rewards_vault,
    eth_whale,
):
    el_reward = 1_000_000 * 10**18
    beacon_balance_delta = 500 * 10**18

    if lido.getELRewardsWithdrawalLimit() == 0:
        el_rewards_withdrawal_limit = 2
        set_el_rewards_withdrawal_limit_role = "SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE"
        has_set_el_rewards_withdrawal_limit_role = partial(
            has_role, acl=acl, app=lido, role=set_el_rewards_withdrawal_limit_role
        )
        if not has_set_el_rewards_withdrawal_limit_role(entity=dao_voting):
            acl.createPermission(
                dao_voting,
                lido,
                web3.keccak(text=set_el_rewards_withdrawal_limit_role),
                dao_voting,
                {"from": dao_voting},
            )
        lido.setELRewardsWithdrawalLimit(el_rewards_withdrawal_limit, {"from": dao_voting})
        assert lido.getELRewardsWithdrawalLimit() == el_rewards_withdrawal_limit

    el_balance_before = lido_execution_layer_rewards_vault.balance()
    # prepare EL rewards
    if el_reward > 0:
        eth_whale.transfer(lido_execution_layer_rewards_vault, el_reward)
    el_balance_after = lido_execution_layer_rewards_vault.balance()
    assert (el_balance_after - el_balance_before) == el_reward

    epochsPerFrame, _, _, _ = lido_oracle.getBeaconSpec()

    for days in range(1, 10):
        print(f" Oracle report: {days}")
        chain.sleep(24 * 60 * 60)
        chain.mine()

        prev_report = lido.getBeaconStat().dict()
        beacon_validators = prev_report["beaconValidators"]
        beacon_balance = prev_report["beaconBalance"] + beacon_balance_delta
        buffered_ether_before = lido.getBufferedEther()

        max_allowed_el_reward = (
            (lido.getTotalPooledEther() + beacon_balance_delta)
            * lido.getELRewardsWithdrawalLimit()
            // TOTAL_BASIS_POINTS
        )

        expectedEpoch = lido_oracle.getExpectedEpochId()
        reporters = lido_oracle.getOracleMembers()
        quorum = lido_oracle.getQuorum()

        if days == 1:
            expectedEpoch += epochsPerFrame * 4  # 3 days for the voting + 1 in for-loop

        for reporter in reporters[:quorum]:
            lido_oracle.reportBeacon(expectedEpoch, beacon_balance // 10**9, beacon_validators, {"from": reporter})

        expected_el_reward = min(max_allowed_el_reward, el_balance_after)
        assert lido.getBufferedEther() == buffered_ether_before + expected_el_reward


def has_role(acl, entity, app, role):
    encoded_role = web3.keccak(text=role)
    return acl.hasPermission["address,address,bytes32,uint[]"](entity, app, encoded_role, [])


def assert_role(acl, entity, app, role, is_granted):
    encoded_role = web3.keccak(text=role)
    assert acl.hasPermission["address,address,bytes32,uint[]"](entity, app, encoded_role, []) == is_granted
