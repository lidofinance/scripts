import pytest
from brownie import interface  # type: ignore

from utils.config import (
    oracle_daemon_config,
    NORMALIZED_CL_REWARD_PER_EPOCH,
    NORMALIZED_CL_REWARD_MISTAKE_RATE_BP,
    REBASE_CHECK_NEAREST_EPOCH_DISTANCE,
    REBASE_CHECK_DISTANT_EPOCH_DISTANCE,
    VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS,
    VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS,
    PREDICTION_DURATION_IN_SLOTS,
    FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT,
    NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP,
)


mainnet_config: dict[str, int] = {
    "NORMALIZED_CL_REWARD_PER_EPOCH": NORMALIZED_CL_REWARD_PER_EPOCH,
    "NORMALIZED_CL_REWARD_MISTAKE_RATE_BP": NORMALIZED_CL_REWARD_MISTAKE_RATE_BP,
    "REBASE_CHECK_NEAREST_EPOCH_DISTANCE": REBASE_CHECK_NEAREST_EPOCH_DISTANCE,
    "REBASE_CHECK_DISTANT_EPOCH_DISTANCE": REBASE_CHECK_DISTANT_EPOCH_DISTANCE,
    "VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS": VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS,
    "VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS": VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS,
    "PREDICTION_DURATION_IN_SLOTS": PREDICTION_DURATION_IN_SLOTS,
    "FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT": FINALIZATION_MAX_NEGATIVE_REBASE_EPOCH_SHIFT,
    "NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP": NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP,
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
