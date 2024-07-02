import pytest

from utils.test.helpers import ETH
from utils.config import contracts

from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.node_operators_helpers import distribute_reward
from utils.test.reward_wrapper_helpers import deploy_reward_wrapper, wrap_and_split_rewards
from utils.test.split_helpers import (
    deploy_split_wallet,
    get_split_percent_allocation,
    get_split_percentage_scale,
    split_and_withdraw_wsteth_rewards,
)
from utils.test.simple_dvt_helpers import simple_dvt_add_keys, simple_dvt_vet_keys, simple_dvt_add_node_operators
from utils.test.staking_router_helpers import StakingModuleStatus, set_staking_module_status
from utils.test.oracle_report_helpers import oracle_report


@pytest.fixture(scope="module")
def cluster_participants(accounts):
    CLUSTER_PARTICIPANTS = 5

    return sorted(map(lambda participant: participant.address, accounts[0:CLUSTER_PARTICIPANTS]))


@pytest.fixture(scope="module")
def split_wallet(cluster_participants):
    percentage_scale = get_split_percentage_scale()
    percent_allocation = get_split_percent_allocation(len(cluster_participants), percentage_scale)
    (deployed_contract, _) = deploy_split_wallet(cluster_participants, percent_allocation, cluster_participants[0])

    return deployed_contract


@pytest.fixture(scope="module")
def reward_wrapper(split_wallet, cluster_participants):
    (deployed_contract, _) = deploy_reward_wrapper(split_wallet, cluster_participants[0])
    return deployed_contract


@pytest.fixture(scope="function")
def simple_dvt_module_id():
    modules = contracts.staking_router.getStakingModules()
    return next(filter(lambda module: module[1] == contracts.simple_dvt.address, modules))[0]


# staking router <> simple dvt tests


def test_sdvt_module_connected_to_router():
    """
    Test that simple dvt module is connected to staking router
    """
    modules = contracts.staking_router.getStakingModules()
    assert any(map(lambda module: module[1] == contracts.simple_dvt.address, modules))


# full happy path test
def test_rewards_distribution_happy_path(simple_dvt_module_id, cluster_participants, reward_wrapper, sdvt, stranger):
    """
    Test happy path of rewards distribution
    Test adding new cluster to simple dvt module, depositing to simple dvt module, distributing and claiming rewards
    """
    simple_dvt, staking_router = contracts.simple_dvt, contracts.staking_router
    lido, deposit_security_module = contracts.lido, contracts.deposit_security_module

    new_dvt_operator = cluster_participants[0]

    new_cluster_name = "new cluster"
    new_manager_address = "0x1110000000000000000000000000000011111111"
    new_reward_address = reward_wrapper.address

    # add operator to simple dvt module
    input_params = [(new_cluster_name, new_reward_address, new_manager_address)]
    (node_operators_count_before, node_operator_count_after) = simple_dvt_add_node_operators(
        simple_dvt, new_dvt_operator, input_params
    )
    operator_id = node_operator_count_after - 1
    assert node_operator_count_after == node_operators_count_before + len(input_params)

    # add keys to the operator
    simple_dvt_add_keys(simple_dvt, operator_id, 10)

    # vet operator keys
    simple_dvt_vet_keys(operator_id, new_dvt_operator)


    # pause deposit to all modules except simple dvt
    # to be sure that all deposits go to simple dvt
    modules = staking_router.getStakingModules()
    for module in modules:
        if module[0] != simple_dvt_module_id:
            set_staking_module_status(module[0], StakingModuleStatus.Stopped)

    # fill the deposit buffer
    deposits_count = 10
    fill_deposit_buffer(deposits_count)

    # deposit to simple dvt
    module_summary_before = staking_router.getStakingModuleSummary(simple_dvt_module_id)
    lido.deposit(deposits_count, simple_dvt_module_id, "0x", {"from": deposit_security_module})
    module_summary_after = staking_router.getStakingModuleSummary(simple_dvt_module_id)

    assert (
        module_summary_after["totalDepositedValidators"]
        == module_summary_before["totalDepositedValidators"] + deposits_count
    )

    # check that there is no steth on the cluster reward address
    cluster_rewards_before_report = lido.balanceOf(new_reward_address)
    assert cluster_rewards_before_report == 0

    # oracle report
    oracle_report(cl_diff=ETH(100))
    distribute_reward(contracts.simple_dvt, stranger.address)
    cluster_rewards_after_report = lido.balanceOf(new_reward_address)

    # check that cluster reward address balance increased
    assert cluster_rewards_after_report > 0

    # wrap rewards and split between dvt provider and split wallet
    wrap_and_split_rewards(reward_wrapper, new_dvt_operator)

    # split wsteth rewards between participants and withdraw
    split_and_withdraw_wsteth_rewards(
        reward_wrapper.splitWallet(),
        cluster_participants,
        get_split_percent_allocation(len(cluster_participants), get_split_percentage_scale()),
        get_split_percentage_scale(),
        new_dvt_operator,
    )
