from brownie import ZERO_ADDRESS

from utils.balance import set_balance_in_wei
from utils.test.helpers import ETH
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch


def get_ea_member():
    """
    Random address and proof for EA member
    """
    address = "0x00200f4e638e81ebe172daa18c9193a33a50bbbd"
    proof = [
        "0x6afd64d1f8e5feed98652d45b758fcbff17eea77665d51f0e531d692a5054756",
        "0x52e265b49b47b47690ed87febf862cd32a651b9ab187cad973bc9b77749bb219",
        "0x35e699543254ce0682e153798e663901c7b14a637c6823def95687ce98c3bfd2",
        "0x90c4d893c062e47126e1fb88c62d7f1addb6787d7681c8b4783e77848fd94ce3",
        "0xcc571b6d9faf0a49b61d00cb56d518a9ac9bc61b9ef63c7b6376a3ead99bd455",
        "0x190eb8e475726914932a14a9f62b854636a9dcb6323c4d97ac6630fcd29dc33c",
        "0x4ac93583eb5d1fb5546b438eac0a489b07b0d62910c4bab3e7b41f0042831d48",
        "0xcdc54828056fbe5307ece8e4138766177cd9568ffd68564b37d3deaaf112bb6c",
        "0x4d63ec7d0dcc7a38ac4984b6ea8fad8255dfd6419c6c66684e49676d3112e062",
        "0x5c39f6b822174cc0267fa29cb2c74340b837859bbc95beca29997689334b4895",
        "0x2980e52feb24b69169c73a9618107b58ae5bea120649a045aba137b07e822172",
        "0xdbaa84b6f34f08ec11a23797a3497898e75dec4e99bf42d63e7cbfee0dee67d6",
        "0xc4556dc19f0330ccc6c929b09a965e05c360d32a5c71c3f64b4123fda973b8dd",
        "0x617a04e701d0b1c8e0e96c278ba4caf00e2d787e4287e52fcc4b5f248d89c2b3"
    ]
    return address, proof


def csm_add_node_operator(csm, accounting, node_operator, proof, keys_count=5, curve_id=0):
    pubkeys_batch = random_pubkeys_batch(keys_count)
    signatures_batch = random_signatures_batch(keys_count)

    value = accounting.getBondAmountByKeysCount['uint256,uint256'](keys_count, curve_id)
    set_balance_in_wei(node_operator, value + ETH(1))

    csm.addNodeOperatorETH(
        keys_count,
        pubkeys_batch,
        signatures_batch,
        (ZERO_ADDRESS, ZERO_ADDRESS, False),
        proof,
        ZERO_ADDRESS,
        {"from": node_operator, "value": value}
    )

    return csm.getNodeOperatorsCount() - 1


def csm_upload_keys(csm, accounting, no_id, keys_count=5):
    manager_address = csm.getNodeOperator(no_id)["managerAddress"]
    pubkeys_batch = random_pubkeys_batch(keys_count)
    signatures_batch = random_signatures_batch(keys_count)
    csm.addValidatorKeysETH(no_id, keys_count, pubkeys_batch, signatures_batch,
                            {"from": manager_address, "value": accounting.getRequiredBondForNextKeys(no_id, keys_count)}
                            )
