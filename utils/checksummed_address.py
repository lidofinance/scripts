from eth_utils import keccak, to_bytes, ValidationError

# https://eips.ethereum.org/EIPS/eip-55
def checksum_encode(addr):  # Takes a 20-byte binary address as input
    hex_addr = addr.hex()
    checksummed_buffer = ""

    # Treat the hex address as ascii/utf-8 for keccak256 hashing
    hashed_address = keccak(text=hex_addr).hex()

    # Iterate over each character in the hex address
    for nibble_index, character in enumerate(hex_addr):

        if character in "0123456789":
            # We can't upper-case the decimal digits
            checksummed_buffer += character
        elif character in "abcdef":
            # Check if the corresponding hex digit (nibble) in the hash is 8 or higher
            hashed_address_nibble = int(hashed_address[nibble_index], 16)
            if hashed_address_nibble > 7:
                checksummed_buffer += character.upper()
            else:
                checksummed_buffer += character
        else:
            raise ValidationError(f"Unrecognized hex character {character!r} at position {nibble_index}")

    return "0x" + checksummed_buffer


def checksum_verify(address: str) -> bool:
    addr_bytes = to_bytes(hexstr=address)
    checksum_encoded = ""
    try:
        checksum_encoded = checksum_encode(addr_bytes)
    except:
        return False
    return checksum_encoded == address
