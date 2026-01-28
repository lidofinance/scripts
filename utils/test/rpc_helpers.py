from brownie import web3


def set_storage_at(address: str, slot: str, value: str) -> bool:
    """
    Set storage at a specific slot for a contract address.
    Tries multiple RPC methods for compatibility with different node implementations.

    Args:
        address: Contract address (checksummed or not)
        slot: Storage slot as hex string (with or without 0x prefix)
        value: Value to set as hex string (with or without 0x prefix, must be 32 bytes)

    Returns:
        True if storage was set successfully

    Raises:
        RuntimeError: If all RPC methods fail
    """
    # Ensure proper hex formatting
    if not slot.startswith("0x"):
        slot = "0x" + slot
    if not value.startswith("0x"):
        value = "0x" + value

    # Ensure value is 32 bytes (64 hex chars + 0x prefix)
    if len(value) < 66:
        value = "0x" + value[2:].zfill(64)

    # We have to try different RPC methods
    # because different node implementations support different methods,
    # network_name is not reliable way to get the correct name.
    rpc_methods = [
        "hardhat_setStorageAt",
        "anvil_setStorageAt",
        "evm_setAccountStorageAt",
    ]

    last_error = None
    for method in rpc_methods:
        try:
            result = web3.provider.make_request(method, [address, slot, value])
            if "error" not in result:
                return True
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(
        f"Failed to set storage at {address} slot {slot}. "
        f"Tried methods: {rpc_methods}. Last error: {last_error}"
    )
