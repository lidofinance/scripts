# @version 0.3.7
# @licence MIT

SLOTS_PER_EPOCH: immutable(uint64)
SECONDS_PER_SLOT: immutable(uint64)
GENESIS_TIME: immutable(uint64)
INITIAL_REF_SLOT: immutable(uint256)


@external
def __init__(slots_per_epoch: uint64, seconds_per_slot: uint64, genesis_time: uint64, initial_ref_slot: uint256):
    SLOTS_PER_EPOCH = slots_per_epoch
    SECONDS_PER_SLOT = seconds_per_slot
    GENESIS_TIME = genesis_time
    INITIAL_REF_SLOT = initial_ref_slot


@external
def getChainConfig() -> (uint64, uint64, uint64):
    return SLOTS_PER_EPOCH, SECONDS_PER_SLOT, GENESIS_TIME


@external
def getInitialRefSlot() -> uint256:
    return INITIAL_REF_SLOT
