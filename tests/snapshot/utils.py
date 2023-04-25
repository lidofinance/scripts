from typing import Literal, overload

from brownie import web3
from eth_typing.evm import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3


@overload
def get_slot(
    address: ChecksumAddress,
    *,
    name: str | None = ...,
    pos: int | None = ...,
    as_list: Literal[False] = ...,
    block: int | None = ...,
) -> HexBytes:
    ...


@overload
def get_slot(
    address: ChecksumAddress,
    *,
    name: str | None = ...,
    pos: int | None = ...,
    as_list: Literal[True],
    block: int | None = ...,
) -> list[HexBytes]:
    ...


def get_slot(
    address: ChecksumAddress,
    *,
    name: str | None = None,
    pos: int | None = None,
    as_list: bool = False,
    block: int | None = None,
) -> HexBytes | list[HexBytes]:
    """
    Get the value of a storage slot.

    If `name` is specified, the slot position is calculated as `keccak256(name)`.
    Otherwise, `pos` is used as the slot position.

    If `as_list` is True, the slot is interpreted as a list of 32 bytes values.
    """

    if pos is None and name is None:
        raise ValueError("Either name or pos must be specified")

    if pos is not None:
        idx = pos
    else:
        idx = Web3.toInt(Web3.keccak(text=name))

    if not as_list:
        return web3.eth.get_storage_at(
            address,
            idx,
            block_identifier=block,
        )

    length = Web3.toInt(
        web3.eth.get_storage_at(
            address,
            idx,
            block_identifier=block,
        )
    )
    if not length:
        return []

    res = []

    buf = Web3.toBytes(idx)
    while len(buf) < 32:
        buf = b"\x00" + buf

    p = Web3.toInt(Web3.keccak(buf))
    for i in range(length):
        res.append(
            web3.eth.get_storage_at(
                address,
                p + i,
                block_identifier=block,
            )
        )

    return res
