from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_set_version_event(event: EventDict, version: int):
    _events_chain = ['LogScriptCall', 'ContractVersionSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('ContractVersionSet') == 1

    assert event['ContractVersionSet']['version'] == version


def validate_set_mev_vault_event(event: EventDict, address: str):
    _events_chain = ['LogScriptCall', 'LidoMevTxFeeVaultSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('LidoMevTxFeeVaultSet') == 1

    assert event['LidoMevTxFeeVaultSet']['mevTxFeeVault'] == address


def validate_set_mev_vault_withdrawal_limit_event(event: EventDict, limit_points: int):
    _events_chain = ['LogScriptCall', 'MevTxFeeWithdrawalLimitSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('MevTxFeeWithdrawalLimitSet') == 1

    assert event['MevTxFeeWithdrawalLimitSet']['limitPoints'] == limit_points


def validate_staking_resumed_event(event: EventDict, max_staking_limit: int, stake_limit_increase: int):
    _events_chain = ['LogScriptCall', 'StakingResumed']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('StakingResumed') == 1

    assert event['StakingResumed']['maxStakeLimit'] == max_staking_limit
    assert event['StakingResumed']['stakeLimitIncreasePerBlock'] == stake_limit_increase
