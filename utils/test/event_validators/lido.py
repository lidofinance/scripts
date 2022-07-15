from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_set_version_event(event: EventDict, version: int):
    _events_chain = ['LogScriptCall', 'ContractVersionSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('ContractVersionSet') == 1

    assert event['ContractVersionSet']['version'] == version


def validate_set_el_rewards_vault_event(event: EventDict, address: str):
    _events_chain = ['LogScriptCall', 'ELRewardsVaultSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('ELRewardsVaultSet') == 1

    assert event['ELRewardsVaultSet']['executionLayerRewardsVault'] == address


def validate_set_el_rewards_vault_withdrawal_limit_event(event: EventDict, limit_points: int):
    _events_chain = ['LogScriptCall', 'ELRewardsWithdrawalLimitSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('ELRewardsWithdrawalLimitSet') == 1

    assert event['ELRewardsWithdrawalLimitSet']['limitPoints'] == limit_points


def validate_staking_resumed_event(event: EventDict):
    _events_chain = ['LogScriptCall', 'StakingResumed']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('StakingResumed') == 1


def validate_staking_limit_set(event: EventDict, max_staking_limit: int, stake_limit_increase: int):
    _events_chain = ['LogScriptCall', 'StakingLimitSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('StakingLimitSet') == 1

    assert event['StakingLimitSet']['maxStakeLimit'] == max_staking_limit
    assert event['StakingLimitSet']['stakeLimitIncreasePerBlock'] == stake_limit_increase


def validate_set_fee_distribution(event: EventDict, treasury_bp: int, insurance_bp: int, operators_bp: int):
    _events_chain = ['LogScriptCall', 'FeeDistributionSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('FeeDistributionSet') == 1

    assert event['FeeDistributionSet']['treasuryFeeBasisPoints'] == treasury_bp
    assert event['FeeDistributionSet']['insuranceFeeBasisPoints'] == insurance_bp
    assert event['FeeDistributionSet']['operatorsFeeBasisPoints'] == operators_bp
