import pytest
from brownie import interface  # type: ignore

from utils.config import (
    oracle_daemon_config,
)


# TODO: check that config is mainnet ready
oracle_daemon_config_values = {
    "NORMALIZED_CL_REWARD_PER_EPOCH": 64,
    "NORMALIZED_CL_REWARD_MISTAKE_RATE_BP": 1000,
    "REBASE_CHECK_NEAREST_EPOCH_DISTANCE": 4,
    "REBASE_CHECK_DISTANT_EPOCH_DISTANCE": 10,
    "VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS": 7200,
    "VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS": 21600,
    "PREDICTION_DURATION_IN_SLOTS": 50400,
    "FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT": 1350,
    "NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP": 100,
}


@pytest.fixture(scope="module")
def contract() -> interface.OracleDaemonConfig:
    return interface.OracleDaemonConfig(oracle_daemon_config)


def test_oracle_daemon_config(contract):
    for key, value in oracle_daemon_config_values.items():
        assert int(str(contract.get(key)), 16) == value
