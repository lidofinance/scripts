import pytest
from brownie import interface  # type: ignore

from utils.config import (
    ORACLE_DAEMON_CONFIG,
    NORMALIZED_CL_REWARD_PER_EPOCH,
    NORMALIZED_CL_REWARD_MISTAKE_RATE_BP,
    REBASE_CHECK_NEAREST_EPOCH_DISTANCE,
    REBASE_CHECK_DISTANT_EPOCH_DISTANCE,
    EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS,
    PREDICTION_DURATION_IN_SLOTS,
    FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT,
)


mainnet_config: dict[str, int] = {
    "NORMALIZED_CL_REWARD_PER_EPOCH": NORMALIZED_CL_REWARD_PER_EPOCH,
    "NORMALIZED_CL_REWARD_MISTAKE_RATE_BP": NORMALIZED_CL_REWARD_MISTAKE_RATE_BP,
    "REBASE_CHECK_NEAREST_EPOCH_DISTANCE": REBASE_CHECK_NEAREST_EPOCH_DISTANCE,
    "REBASE_CHECK_DISTANT_EPOCH_DISTANCE": REBASE_CHECK_DISTANT_EPOCH_DISTANCE,
    "PREDICTION_DURATION_IN_SLOTS": PREDICTION_DURATION_IN_SLOTS,
    "FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT": FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT,
    "EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS": EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS,
}


@pytest.fixture(scope="module")
def contract() -> interface.OracleDaemonConfig:
    return interface.OracleDaemonConfig(ORACLE_DAEMON_CONFIG)


def test_oracle_daemon_config(contract):
    def values_to_int(values) -> list[int]:
        return list(map(lambda x: int(str(x), 16), values))

    contract_values = contract.getList(list(mainnet_config.keys()))
    contract_config = dict(zip(mainnet_config.keys(), values_to_int(contract_values)))

    assert mainnet_config == contract_config, "OracleDaemonConfig values are incorrect"
