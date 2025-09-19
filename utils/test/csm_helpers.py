from brownie import ZERO_ADDRESS

from utils.balance import set_balance_in_wei
from utils.test.helpers import ETH
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.config import contracts


def get_ics_members():
    """Few ICS members from mainnet list"""
    return ((
                "0xf4c1b69a65f3fdbafcae0786c5fb02dad3e0f353",
                [
                    "0x5f1fbf1cda5a3dd4d863cd96f6513c24f4f5973e9de0d4524ba5c65bdbff09c6",
                    "0x459f8832de04e639e148bfdf73d008f9496bc5473b76c76fcb2681dd2806b34f",
                    "0x38b9c0886c7f5a0115688d538e14318a22856470d265c03778b63e775bfce55a",
                    "0x007c11b18270c5b5ec10e821b3b2763fd7b28f889b11ec0ae297ab3c55ab0dba",
                    "0x5cb1b7f8a3505a0d36cb64886bfd5d48e28e62d2ff0fd52aa12d3f5933fe1916",
                    "0x429e5ae3d28582cb7efcebca05bae5430e9915f8f5bef58c79563938479fa791",
                    "0x31003203efa870c41458f35927908e17c10f24b615b0e6af863d01c0d8ea3065",
                    "0xbe5b3c65dec940f408d96c86777263868e45fa74b9848871c1f508bde4d731e1"
                ]
            ), ("0x9b4064c9d9801f062f377512e61bd19484e7f365",
                [
                    "0x3dca0828b389d4a4f72eb381ac3edd6f96f51a04b0446db2e7a77892b61ba7c7",
                    "0x8f5af01242e34310a430415a1bda6ad42ea09b7ed487de5b38c2626d7acb08b1",
                    "0x2ae5c4b9c69f91edb90caf2594e595e01758c58ae9719311cd3d5d41a32f0b66",
                    "0x1f7e8e488cf08018ea5796a648b39f2218f1aad23223dcd6c3733cf775950dff",
                    "0xdbc36608e64ffee165ab914565b18e83b526b81771c46fc4689e7579c426a567",
                    "0xf676e62b1ca138f69927c196ec23e6f43e4e430e2865637fa5db83cc26670372",
                    "0x31003203efa870c41458f35927908e17c10f24b615b0e6af863d01c0d8ea3065",
                    "0xbe5b3c65dec940f408d96c86777263868e45fa74b9848871c1f508bde4d731e1"
                ]
                ), ("0xb8f8e5751b2c5bad790ff0d2f5574ab38246272e",
                    [
                        "0x96441bf0ea1e2d069560e692ff9b5baec46e83a364ffe3203c5b16d91bc0321f",
                        "0x5e7c84656af7b03dc12353898f2cafda93166fc9c85aec6d797e7410a38390b2",
                        "0x90efa708c8677e4589f86f98d788a2b6096b1202358cabc31558ccc716bab269",
                        "0x1392ec14e24fb65c06527743cafc6c408653a312511fbeb4f7a385ee62cbb201",
                        "0xc656eee8bb516c8ef59fa3c73f68276c87aa2e707b1394cfe0d0d2151a60ecb8",
                        "0x994eb932575dc2f3b0a55262fcdfd0108cdf5573228a2fdac5c82bc689cbb90d",
                        "0xc878b4f250b6b2616245fe079be412dac4605b48aede5ac8f695fe219931051d",
                        "0xf0e2720fdd888df5369e9aa081347d97603fadbd22f5a1978b08fbaa7c13e6f7"
                    ]
                    ), (
                "0x88792bee0d8a4c46acb7a2d8bfbef7e3a678639e",
                [
                    "0x955c8105dfeed6dd47fccc580e67b00090043c2e0fe00dd9269adaf1864ac073",
                    "0xfb254edbb3d5dc888dd77e1779146b94268fb5964d0dc9f71815fad8da58612c",
                    "0x90efa708c8677e4589f86f98d788a2b6096b1202358cabc31558ccc716bab269",
                    "0x1392ec14e24fb65c06527743cafc6c408653a312511fbeb4f7a385ee62cbb201",
                    "0xc656eee8bb516c8ef59fa3c73f68276c87aa2e707b1394cfe0d0d2151a60ecb8",
                    "0x994eb932575dc2f3b0a55262fcdfd0108cdf5573228a2fdac5c82bc689cbb90d",
                    "0xc878b4f250b6b2616245fe079be412dac4605b48aede5ac8f695fe219931051d",
                    "0xf0e2720fdd888df5369e9aa081347d97603fadbd22f5a1978b08fbaa7c13e6f7"
                ]
            ), (
                "0x1ea60eaa2883173e2f8d6b7b025fce33ebc08738",
                [
                    "0xd5d55039d3530cc365d80d5bdb249c6a21024ecd2d0f3629ab256da3030e5f4a",
                    "0xad535120c80dea856727178e9ffc03a549ae69c71fa8fd69e7da87500d94ed5e",
                    "0x18c929c35a4632f9aea2684bba2fb918a1a32035c2c2aa1c50d7d48ab6f84960",
                    "0x1eae092568547d900432cc755ab381fedac95d4847e6de94bbdec79ca7706b47",
                    "0xe8c3fe7bc103e7c4da1d5a7d2bafbc6e9d1b1d42cbdb8b75bc9136701e18dd4d",
                    "0xd456f32b3f050d9204e43c123bb5a81c01c482ea56c9a0249ad60e36c64468af",
                    "0xbf3f96fd42d14dc9db9126b57923d8845d8434c7e64dcf9a1a23f17afec30aad",
                    "0xf0e2720fdd888df5369e9aa081347d97603fadbd22f5a1978b08fbaa7c13e6f7"
                ]
            ))


def csm_add_node_operator(csm, permissionless_gate, accounting, node_operator, keys_count=5, curve_id=0):
    pubkeys_batch = random_pubkeys_batch(keys_count)
    signatures_batch = random_signatures_batch(keys_count)

    value = accounting.getBondAmountByKeysCount(keys_count, curve_id)
    set_balance_in_wei(node_operator, value + ETH(10))

    permissionless_gate.addNodeOperatorETH(
        keys_count,
        pubkeys_batch,
        signatures_batch,
        (ZERO_ADDRESS, ZERO_ADDRESS, False),
        ZERO_ADDRESS,
        {"from": node_operator, "value": value}
    )

    return csm.getNodeOperatorsCount() - 1


def csm_add_ics_node_operator(csm, vetted_gate, accounting, node_operator, proof, keys_count=5, curve_id=2):
    pubkeys_batch = random_pubkeys_batch(keys_count)
    signatures_batch = random_signatures_batch(keys_count)

    value = accounting.getBondAmountByKeysCount(keys_count, curve_id)
    set_balance_in_wei(node_operator, value + ETH(10))

    vetted_gate.addNodeOperatorETH(
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
    set_balance_in_wei(manager_address, accounting.getRequiredBondForNextKeys(no_id, keys_count) + ETH(1))

    keys_batch = 100
    remaining_keys = keys_count
    while remaining_keys > 0:
        keys_batch = min(keys_batch, remaining_keys)
        pubkeys_batch = random_pubkeys_batch(keys_batch)
        signatures_batch = random_signatures_batch(keys_batch)
        value = accounting.getRequiredBondForNextKeys(no_id, keys_count)
        address = csm.getNodeOperator(no_id)["managerAddress"]
        csm.addValidatorKeysETH(address, no_id, keys_batch, pubkeys_batch, signatures_batch, {
            "from": address,
            "value": value
        })
        remaining_keys -= keys_batch


def fill_csm_operators_with_keys(target_operators_count, keys_count):
    csm_node_operators_before = contracts.csm.getNodeOperatorsCount()
    added_operators_count = 0
    for no_id in range(0, min(csm_node_operators_before, target_operators_count)):
        depositable_keys = contracts.csm.getNodeOperator(no_id)["depositableValidatorsCount"]
        if depositable_keys < keys_count:
            csm_upload_keys(contracts.csm, contracts.cs_accounting, no_id, keys_count - depositable_keys)
            assert contracts.csm.getNodeOperator(no_id)["depositableValidatorsCount"] == keys_count
    while csm_node_operators_before + added_operators_count < target_operators_count:
        node_operator = f"0xbb{str(added_operators_count).zfill(38)}"
        csm_add_node_operator(contracts.csm, contracts.cs_permissionless_gate, contracts.cs_accounting, node_operator,
                              keys_count=keys_count)
        added_operators_count += 1
    return csm_node_operators_before, added_operators_count
