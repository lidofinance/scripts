import pytest
from brownie import interface  # type: ignore

from utils.config import (
    oracle_daemon_config,
)


# Source of truth: https://hackmd.io/pdix1r4yR46fXUqiHaNKyw?view
mainnet_config: dict[str, int] = {
    "NORMALIZED_CL_REWARD_PER_EPOCH": 64,
    "NORMALIZED_CL_REWARD_MISTAKE_RATE_BP": 1000,
    "REBASE_CHECK_NEAREST_EPOCH_DISTANCE": 1,
    "REBASE_CHECK_DISTANT_EPOCH_DISTANCE": 23,
    "VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS": 7200,
    "VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS": 28800,
    "PREDICTION_DURATION_IN_SLOTS": 50400,
    "FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT": 1350,
    "NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP": 100,
}


@pytest.fixture(scope="module")
def contract() -> interface.OracleDaemonConfig:
    return interface.OracleDaemonConfig(oracle_daemon_config)


def test_oracle_daemon_config(contract):
    def values_to_int(values) -> list[int]:
        return list(map(lambda x: int(str(x), 16), values))

    contract_values = contract.getList(list(mainnet_config.keys()))
    contract_config = dict(zip(mainnet_config.keys(), values_to_int(contract_values)))

    assert mainnet_config == contract_config, "OracleDaemonConfig values are incorrect"
