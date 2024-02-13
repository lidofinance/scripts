import random
import textwrap

PUBKEY_LENGTH = 48
SIGNATURE_LENGTH = 96


def random_pubkeys_batch(pubkeys_count: int):
    return random_hexstr(pubkeys_count * PUBKEY_LENGTH)


def random_signatures_batch(signautes_count: int):
    return random_hexstr(signautes_count * SIGNATURE_LENGTH)


def parse_pubkeys_batch(pubkeys_batch: str):
    return hex_chunks(pubkeys_batch, PUBKEY_LENGTH)


def parse_signatures_batch(signatures_batch: str):
    return hex_chunks(signatures_batch, SIGNATURE_LENGTH)


def hex_chunks(hexstr: str, chunk_length: int):
    stripped_hexstr = strip_0x(hexstr)
    assert len(stripped_hexstr) % chunk_length == 0, "invalid hexstr length"
    return [prefix_0x(chunk) for chunk in textwrap.wrap(stripped_hexstr, 2 * chunk_length)]


def random_hexstr(length: int):
    return prefix_0x(random.randbytes(length).hex())


def prefix_0x(hexstr: str):
    return hexstr if hexstr.startswith("0x") else "0x" + hexstr


def strip_0x(hexstr: str):
    return hexstr[2:] if hexstr.startswith("0x") else hexstr
