from brownie import ZERO_ADDRESS

from utils.balance import set_balance_in_wei
from utils.test.helpers import ETH
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch


def get_ea_member():
    """
    Random address and proof for EA member
    """
    address = "0x00200f4e638e81ebe172daa18c9193a33a50bbbd"
    proof = ["0x6afc021ded39a008e9e7c646cd70b0e0425b8c0cc2decc102d45a09a9cadc3b4",
             "0x9fb8ad314dcef15562b7a930e037068f77bb860156199862df2957017d68b59b",
             "0xa70999dbf9fb0843abbcfbc67498e195527ac129b43994dfaccdde3479893bed",
             "0xe529a4c4315a65bc576d6cb030bb0f6957084d18fb108d8bb2d2b9ac05b17d66",
             "0xc94fe8c075792d6610715e8adbc53fafd06aeddaeb4fcb45867d8ab92685bbe6",
             "0xb2cc15dba514f0df05e7243a48aa47b1a5455f5a4291398c0edacca5f0aca2fc",
             "0x7c4efc55c91a8f3b6064dcdb0622d9815dc31998fc6f9069a6ba0188512f1144",
             "0xcb497013c0ad8e40663b8318967dcbc1cfbb38132a5bb36a6def0bf1352b3733",
             "0xab3d7faaf4662097e8a953ee63af9e71078a4224c4c69425b6c53404aa14459f",
             "0x9e1485ad05559cc88dc80939a490c03bbdb7aa81c01b259023c7cdc73884dabc",
             "0x6206a54be4267fcced2b6c60e90b9f1974933b4655444a56ae993d4727bacde4",
             "0x60aaa2f08de8edbe2b9edfb201c5ed962cbbd8ce1d096013549fc4de2dc330d6",
             "0xd88ad1a0d41adf346661f16fad68e45102a5f7730122af03c81bdc90a6b473d7",
             "0x9abd3efc8d538c4714dae174a75caaa1414c9a9155e8cea71e977822978807df"]
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
