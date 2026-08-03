from dataclasses import dataclass
from typing import Tuple, NewType

StakingModuleId = NewType("StakingModuleId", int)
NodeOperatorId = NewType("NodeOperatorId", int)
NodeOperatorGlobalIndex = Tuple[StakingModuleId, NodeOperatorId]


@dataclass
class LidoValidator:
    index: int
    pubkey: str
    key_index: int = 0  # position of the key in the module registry; only used for DATA_FORMAT_LIST_WITH_KEY_INDEX


# Mirrors ValidatorsExitBus.sol: format 1 (no keyIndex) and format 2 (with keyIndex).
DATA_FORMAT_LIST = 1
DATA_FORMAT_LIST_WITH_KEY_INDEX = 2

MODULE_ID_LENGTH = 3
NODE_OPERATOR_ID_LENGTH = 5
VALIDATOR_INDEX_LENGTH = 8
KEY_INDEX_LENGTH = 8
VALIDATOR_PUB_KEY_LENGTH = 48


def encode_data(
    validators_to_eject: list[tuple[NodeOperatorGlobalIndex, LidoValidator]],
    sort=True,
    data_format=DATA_FORMAT_LIST_WITH_KEY_INDEX,
):
    """
    Encodes report data for Exit Bus Contract into bytes, matching the packing in
    ValidatorsExitBus.sol. The `data_format` selects the layout (contract's
    submitReportData accepts only DATA_FORMAT_LIST_WITH_KEY_INDEX).

    Format 1 (DATA_FORMAT_LIST, 64 bytes/request):
      |  3 bytes  |  5 bytes  |    8 bytes     |    48 bytes     |
      | moduleId  | nodeOpId  | validatorIndex | validatorPubkey |

    Format 2 (DATA_FORMAT_LIST_WITH_KEY_INDEX, 72 bytes/request):
      |  3 bytes  |  5 bytes  |    8 bytes     |  8 bytes  |    48 bytes     |
      | moduleId  | nodeOpId  | validatorIndex | keyIndex  | validatorPubkey |
    """
    if data_format not in (DATA_FORMAT_LIST, DATA_FORMAT_LIST_WITH_KEY_INDEX):
        raise ValueError(f"Unsupported data_format: {data_format}")

    if sort:
        validators = sort_validators_to_eject(validators_to_eject)
    else:
        validators = validators_to_eject

    result = b""

    for (module_id, op_id), validator in validators:
        result += module_id.to_bytes(MODULE_ID_LENGTH, "big")
        result += op_id.to_bytes(NODE_OPERATOR_ID_LENGTH, "big")
        result += int(validator.index).to_bytes(VALIDATOR_INDEX_LENGTH, "big")

        if data_format == DATA_FORMAT_LIST_WITH_KEY_INDEX:
            result += int(validator.key_index).to_bytes(KEY_INDEX_LENGTH, "big")

        pubkey_bytes = bytes.fromhex(str(validator.pubkey)[2:])

        if len(pubkey_bytes) != VALIDATOR_PUB_KEY_LENGTH:
            raise ValueError(f"Unexpected size of validator pub key. Pub key size: {len(validator.pubkey)}")

        result += pubkey_bytes

    return result, data_format


def sort_validators_to_eject(
    validators_to_eject: list[tuple[NodeOperatorGlobalIndex, LidoValidator]],
) -> list[tuple[NodeOperatorGlobalIndex, LidoValidator]]:
    def _nog_validator_key(no_validator: tuple[NodeOperatorGlobalIndex, LidoValidator]) -> tuple[int, int, int]:
        (module_id, no_id), validator = no_validator
        return module_id, no_id, int(validator.index)

    validators = sorted(validators_to_eject, key=_nog_validator_key)

    return validators
