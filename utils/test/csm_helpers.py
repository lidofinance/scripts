from brownie import ZERO_ADDRESS

from utils.balance import set_balance_in_wei
from utils.test.helpers import ETH
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch


def get_ea_member():
    """
    Random address and proof for EA member
    """
    address = "0x00200f4e638e81ebe172daa18c9193a33a50bbbd"
    proof = ["0x6afb48863bdb84141ef424715c70cd61e5d629a293038b2e55b2aaa330955435",
             "0xf2cbc3e761642defc881539fb26fd2f349c87ac9baa031572693d4b47286d521",
             "0x526c3d791066e220842b26d606a332cc22d088eb0d1431c43d6c5a8503417f4e",
             "0x25f371f22e592b9541b1fe8c3e2a599b3db0b11e9b027bffe525dc48b6971bf5",
             "0xffaad8403c4681c00ce2a7d6c82f2f4343ec7ef0efd9dd1959e37a55c71949bc",
             "0xf86d0c08277b41ad7d4b9640be4c1e6b0e2eed1fd4bfc084c300086cb638b933",
             "0x3c66b0db484c5bd7351114a5e7fb073604fd8772254ad3ef02432918a7b65f2c",
             "0x47d2ab6d81d882809ffb9df212c126fbbb5fe01c0849cb42d8101fe0f5b5ea1c",
             "0x62373951ea824814af660ae6276d03fec5e734f9ea8e9fe662e600b19fd58dea",
             "0x812242ec081e8ebf25e682ff968a40dbf0786caa89ba18958d7f91f7e981e415",
             "0x1b3e4aade81953dbfc7df20d22852a95c255bf0bcf5f186115f9f439b29f4845",
             "0x2db100e320128d95cf46a003497bc5dcf25cdc62a1e66a89f0fa7c79b1a858ad",
             "0x03d33582f7cac74515d95d4ab3711d95ce9814df7351a1a46223d3bb4c3fdd44",
             "0x566d2db5a4091a4c3152e2e3ba7a26d44b9f09515d4d8e587cf7f8aea77e38f0",
             "0xd415d9673b0b81ccf04e5ed1317f6a2ec5c94bc3c8d14e5d302225ad9b99b137"]
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
