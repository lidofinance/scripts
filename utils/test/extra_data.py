from dataclasses import dataclass
from itertools import groupby
from enum import Enum
from typing import List, NewType, Sequence, Tuple

from hexbytes import HexBytes
from brownie import web3

StakingModuleId = NewType("StakingModuleId", int)
NodeOperatorId = NewType("NodeOperatorId", int)
NodeOperatorGlobalIndex = Tuple[StakingModuleId, NodeOperatorId]

ZERO_HASH = bytes([0] * 32)


class ItemType(Enum):
    EXTRA_DATA_TYPE_STUCK_VALIDATORS = 1
    EXTRA_DATA_TYPE_EXITED_VALIDATORS = 2
    UNSUPPORTED = 3


class FormatList(Enum):
    EXTRA_DATA_FORMAT_LIST_EMPTY = 0
    EXTRA_DATA_FORMAT_LIST_NON_EMPTY = 1


class VoterState(Enum):
    Absent = 0
    Yea = 1
    Nay = 2
    DelegateYea = 3
    DelegateNay = 4


@dataclass
class ItemPayload:
    module_id: bytes
    node_ops_count: bytes
    node_operator_ids: bytes
    vals_counts: bytes


@dataclass
class ExtraDataItem:
    item_index: bytes
    item_type: ItemType
    item_payload: ItemPayload


@dataclass
class ExtraData:
    extra_data_list: List[bytes]
    extra_data_hash_list: HexBytes
    format: int
    items_count: int


@dataclass
class ItemPayload:
    module_id: int
    node_operator_ids: Sequence[int]
    vals_counts: Sequence[int]

class ExtraDataLengths:
    NEXT_HASH = 32
    ITEM_INDEX = 3
    ITEM_TYPE = 2
    MODULE_ID = 3
    NODE_OPS_COUNT = 8
    NODE_OPERATOR_IDS = 8
    STUCK_OR_EXITED_VALS_COUNT = 16

class ExtraDataService:
    """
    Service that encodes extra data into bytes in correct order.

    Extra data is an array of items, each item being encoded as follows:
    | 32 bytes |  3 bytes  | 2 bytes  |   X bytes   |
    | nextHash | itemIndex | itemType | itemPayload |

    itemPayload format:
    | 3 bytes  |   8 bytes    |  nodeOpsCount * 8 bytes  |  nodeOpsCount * 16 bytes  |
    | moduleId | nodeOpsCount |      nodeOperatorIds     |   stuckOrExitedValsCount  |

    max_items_count - max itemIndex in extra data.
    max_no_in_payload_count - max nodeOpsCount that could be used in itemPayload.
    """
    @classmethod
    def collect(
        cls,
        stuck_validators: dict[NodeOperatorGlobalIndex, int],
        exited_validators: dict[NodeOperatorGlobalIndex, int],
        max_items_count: int,
        max_no_in_payload_count: int,
    ) -> ExtraData:
        stuck_payloads = cls.build_validators_payloads(stuck_validators, max_no_in_payload_count)
        exited_payloads = cls.build_validators_payloads(exited_validators, max_no_in_payload_count)
        items_count, txs = cls.build_extra_transactions_data(stuck_payloads, exited_payloads, max_items_count)
        extra_data_hash_list, hashed_txs = cls.add_hashes_to_transactions(txs)

        if items_count:
            extra_data_format = FormatList.EXTRA_DATA_FORMAT_LIST_NON_EMPTY
        else:
            extra_data_format = FormatList.EXTRA_DATA_FORMAT_LIST_EMPTY

        return ExtraData(
            items_count=items_count,
            extra_data_list=hashed_txs,
            extra_data_hash_list=extra_data_hash_list,
            format=extra_data_format.value,
        )

    @classmethod
    def build_validators_payloads(
        cls,
        validators: dict[NodeOperatorGlobalIndex, int],
        max_no_in_payload_count: int,
    ) -> list[ItemPayload]:
        operator_validators = sorted(validators.items(), key=lambda x: x[0])

        payloads = []

        for module_id, operators_by_module in groupby(operator_validators, key=lambda x: x[0][0]):
            for nos_in_batch in cls.batch(list(operators_by_module), max_no_in_payload_count):
                operator_ids = []
                vals_count = []

                for ((_, no_id), validators_count) in nos_in_batch:
                    operator_ids.append(no_id)
                    vals_count.append(validators_count)

                payloads.append(
                    ItemPayload(
                        module_id=module_id,
                        node_operator_ids=operator_ids,
                        vals_counts=vals_count,
                    )
                )

        return payloads

    @classmethod
    def build_extra_transactions_data(
        cls,
        stuck_payloads: list[ItemPayload],
        exited_payloads: list[ItemPayload],
        max_items_count: int,
    ) -> tuple[int, list[bytes]]:
        all_payloads = [
            *[(ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, payload) for payload in stuck_payloads],
            *[(ItemType.EXTRA_DATA_TYPE_EXITED_VALIDATORS, payload) for payload in exited_payloads],
        ]

        index = 0
        result = []

        for payload_batch in cls.batch(all_payloads, max_items_count):
            tx = b''
            for item_type, payload in payload_batch:
                tx += index.to_bytes(ExtraDataLengths.ITEM_INDEX, byteorder='big')
                tx += item_type.value.to_bytes(ExtraDataLengths.ITEM_TYPE, byteorder='big')
                tx += payload.module_id.to_bytes(ExtraDataLengths.MODULE_ID, byteorder='big')
                tx += len(payload.node_operator_ids).to_bytes(ExtraDataLengths.NODE_OPS_COUNT, byteorder='big')
                tx += b''.join(
                    no_id.to_bytes(ExtraDataLengths.NODE_OPERATOR_IDS, byteorder='big')
                    for no_id in payload.node_operator_ids
                )
                tx += b''.join(
                    count.to_bytes(ExtraDataLengths.STUCK_OR_EXITED_VALS_COUNT, byteorder='big')
                    for count in payload.vals_counts
                )

                index += 1

            result.append(tx)

        return index, result

    @staticmethod
    def add_hashes_to_transactions(txs_data: list[bytes]) -> tuple[bytes, list[bytes]]:
        txs_data.reverse()

        txs_with_hashes = []
        txs_hashes = []
        next_hash = ZERO_HASH

        for tx in txs_data:
            full_tx_data = next_hash + tx
            txs_with_hashes.append(full_tx_data)
            next_hash = web3.keccak(full_tx_data)
            txs_hashes.append(next_hash)

        txs_with_hashes.reverse()
        txs_hashes.reverse()

        return txs_hashes, txs_with_hashes

    @staticmethod
    def batch(iterable, n):
        """
        Collect data into fixed-length chunks or blocks.
        """
        length = len(iterable)
        for ndx in range(0, length, n):
            yield iterable[ndx:min(ndx + n, length)]
