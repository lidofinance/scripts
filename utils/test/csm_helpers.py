from brownie import ZERO_ADDRESS

from utils.balance import set_balance_in_wei
from utils.test.helpers import ETH
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.config import contracts

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


def get_ea_members():
    """Each ea member from different source"""
    return ((
                "0x113e5bA177D3021E4515e847bc4779B074AA0813", [  # good performer
                    "0xb3f1d62e731a0ac46f103f3423265baaae773036410890c1ee4bc4ba4a5b6806",
                    "0xdd218546f8029d89f8bb325d50e9a272543ac9642e88d60c6d5b0f1d11db14ea",
                    "0x82a14915d66df3004c15749f90a53606faaa8adcf890ef9159974a470df16a1f",
                    "0x9f7ee78a4e733ab2715190ae5481a1456b81b3d5b65a05cd070bcf95fe7a7c92",
                    "0x68431bdd53ada7d0fcbc0eeae8a7e0f614cbd3da6b54b16214bfedc9e42ea753",
                    "0x2006bffe956465add92037dd50b5001f7bfdc9ed531fb40b9bbcdff3586ffb63",
                    "0xbf0015b0b477df4cd5a81eda856a20d65f1a631f033eeb4d630fbebf962a8310",
                    "0x03c02b7b15ef3c91ae99e86c4c3b1eee48c776e38ffff1a99dcbe4f78942679f",
                    "0xacbd1f9b565d87a3156b972c1a860a71b5365992f503821166f2c11f591748ec",
                    "0x8ac7d39a7d9d96d17f5b42f8ef026c44ebb17bd62c995f12e3124b5ca4bfc5e7",
                    "0x582edbfcd0fb5f0a95caca952bdb943a8cd008c4d114c586e4e03c839bc7c7cd",
                    "0x772f2c70f39b9a6848799e13c16fe05bdfd1eded3c2b588834bf751b79a9fce5",
                    "0x3f53e44db24145c061bbbf7d1df796a0ab059b7125c9c2cacf7064bc3904c9d1",
                    "0x617a04e701d0b1c8e0e96c278ba4caf00e2d787e4287e52fcc4b5f248d89c2b3"
                ]),
            ("0x6D08b74BD14b2D6Deb468BA31D578a002D0AdDE8", [  # Galxe point holder
                "0x6184b17c37f752a58be2c14d26abf9220efff1349fb5c561d9b688b798237d13",
                "0xe2d16f320a6de8ef9c8fdca825bad92bb3df1da7995b035d4c0ce2a68cbd3e2a",
                "0x35f55c85e9331c8767bf00735389eebc9ba335f52922809cc9cf8d8487646d27",
                "0x6442dd1037d0faced9476b99c7f93987326845cd36114be02abebf734759e8a9",
                "0xc7f4e2bc84d3a89a6046c9feae416160dad7b28a6209b1e3dff004a3d2b4d0de",
                "0xc69995256422fbd2478a7bb8201c777383493e4c1a2fc6a45620341d8108103d",
                "0xd703c9506f78ffe85059902bf94a1da7d0efa195424ee10d436af20867700d7c",
                "0xfa6b80e968a2f48fc65a45e6763f5a0d470f7640f75edf648d001cb46acefe3c",
                "0x9950a0f220017fcd05a338574cbc289a3c00de804ca8d10867a177afd673c347",
                "0x83389a6b368766d86b6d57720596f25ff3aeccd4ad21a3b683dbbd231755a2df",
                "0x2980e52feb24b69169c73a9618107b58ae5bea120649a045aba137b07e822172",
                "0xdbaa84b6f34f08ec11a23797a3497898e75dec4e99bf42d63e7cbfee0dee67d6",
                "0xc4556dc19f0330ccc6c929b09a965e05c360d32a5c71c3f64b4123fda973b8dd",
                "0x617a04e701d0b1c8e0e96c278ba4caf00e2d787e4287e52fcc4b5f248d89c2b3"
            ]),
            ("0xe95fb9768cef2893445bc02e7056dead0c32fe6a", [  # dappnode buyer
                "0x6fdf504e61ce21367058bc13a34c21f94a4320e29b75c632aa371dd228f2595e",
                "0xeeda87c6ce2ef88e9748f7987a64a7147a93be2297f62f44c75f38e5c5756111",
                "0x852b5fdd3cf28c632af3270443231205b4d5fa8186b6e241e4f8d3414bfbb540",
                "0xa4d359ba49c62fe93c99b49ac4453cf544252e6bf1a42fababa321bb23850163",
                "0x8a9297667d1dbe4f17916ff6bc052e58790a3df7703b22baac3f4d224c06a444",
                "0x696335ac8a25acf05c2b7b85bd97e0473219f8fff3bc89f49601ba6084f54e51",
                "0x6aa7a7a69448a2170b3dc9f6f6227cd0926dd71962e4c15e63448a984369c7a4",
                "0x5f87b1e6bfecfd3440114bd9829647532aad1328699af183aeb490d1406003cd",
                "0x9d117f35be949e6db5e479949f91cb0710ea3e85be2a58deed5a0b4c05763fe3",
                "0x70d5df1f59c0f5fd1667e832f91b8e389adc70f69a520a9f9ca333861bdb27e2",
                "0x398e90a61a92850edce556da82fbb16b5f520bcf3fb3c1a5d7cdc6a1baf4883c",
                "0xdbaa84b6f34f08ec11a23797a3497898e75dec4e99bf42d63e7cbfee0dee67d6",
                "0xc4556dc19f0330ccc6c929b09a965e05c360d32a5c71c3f64b4123fda973b8dd",
                "0x617a04e701d0b1c8e0e96c278ba4caf00e2d787e4287e52fcc4b5f248d89c2b3"
            ]),
            ("0x024813b4972428003c725ea756348dcd79b826e6", [  # obol teche credentials
                "0xfc49117ff5d49126e2ed0ee2a6229678604428fc175670aaf6dfcacfba55c414",
                "0xa9011da71acb5f3c61c0cc80f5c8b89f916345efb9c149ead010aac852dfbac3",
                "0xa0af25f19dde818bb362aae34d967c6d141cfe4b2666a9aeef5fb03cf705ab1b",
                "0xb8a34c5bdc302c3944e1f1919f304aa25168e0db81b7e2b67c6afe8a7fa8cc46",
                "0x6c209589c3c08d2b8441263874648617f70ebfd255d513840aa191284b5815a9",
                "0x45493cc5f6e07014c06f4fe700bc91cedbe7947bdae3d3bdf960ae67abab3adf",
                "0xa6df3cbb3e9113c1c429e842c8999b3597d1b6b55c9c979c2703e995b0f762c6",
                "0x9e70b4cb13a9517ad1a4fe4920b02abd9eeab2236b9a541e20beaee5557ad7fd",
                "0x0a9dc8737db2646bbfc1539e073b563f203e9bfed2aabacfcd03d9d16e8f9739",
                "0x2f362f8032842941fe910be787723b082ab7a21effb5cd38022b36c75a103013",
                "0x6a5e8cf1bacfe83bee183d9ed803f679d8714103a8106301ad9e355f7790e901",
                "0xd001326ce1fa4bfc303be10f953c87ad779c22268ea03d357da5d8e26659e50b",
                "0xd597d21fed5e65b2a6de1c6fe70dfdb2df43ab5495a5c0a01c915e60c14c6edb",
                "0xf99292f2fccc3f4fa8cef73512bd5f21a46214d922dfed8e8a65f763c13dfb72"
            ]),
            ("0xe3a2417f8eaafb93a93dc896724e20d0bc1a1feb", [  # rated
                "0x2faac9fec99b1a1d464422f5cc64c153514da1d3a438362ef7f1aaa5f585cf65",
                "0xf17a0bdf45def725c1ad7bf6c457d4c749705f02ff4282c6739e54dc8965340b",
                "0xa0530504a2c0e61ab5de781f0ee4467097595b7a9815b9b2371e33daf920e25c",
                "0x1d95475075f06c85ba13b81f01891bde5cf0af4df6f2693b15586884b4a3fac7",
                "0x4a8ebe10d4e6f7bb1cadf1e54b58471a6933a62fd7fd6b4750c645f87347c8bd",
                "0x96f7f6c9f3b8c3c45392e1598c4ee9ff2aa0eb655bb428c3977e939a8c2cacf5",
                "0x404ba635ed5cce8cbc77c4b0eb581c8383e52a7be1507d9fbb053d86fe132fd4",
                "0xa680f8f19b75770eee3435719f5731dccd057b968fabd81b40528a9b689a7b6c",
                "0x78fe6adcb23cf69e7533e4a3d0558fdc6f0bf13384e85c7679b6d054b05b34ed",
                "0xbab879d3c26f5d5e3816a4ce99f35a6ac8139c8df8053608bea4a76951b17e0d",
                "0x15b1fc08779715ad26f61b07d0665a82f118104391b56863bd54e6bbe3ec0ff0",
                "0xbe7a61521ebadab96f18fdce4dbcfed777f7799c1a02400052ee9dd838ff1ad4",
                "0x5894e79a333e76f3e367a65aaad4cc2ca21650c4a532ce89b28009b0d35ca075",
                "0xd597d21fed5e65b2a6de1c6fe70dfdb2df43ab5495a5c0a01c915e60c14c6edb",
                "0xf99292f2fccc3f4fa8cef73512bd5f21a46214d922dfed8e8a65f763c13dfb72"
            ]),
            ("0x61ad82d4466437d4cc250a0ceffbcbd7e07b8f96", [  # stake cat
                "0xc863e03646d118cf51af3581cacc457f166134a78b3f4253b219e7f694becc50",
                "0x52b3bb9a9105a40e8270cd7e6687f3b010213bd9297748d90b7f90dad779defd",
                "0x82e0aec8e35aa0c9b8732a77dc5470b13f3d9d36870acec8568ce73807674a15",
                "0x096a86c63fccf92230d8d445d7df591d20f9d71ed5c77141e4bb85a47acbb2e3",
                "0x4b875dfece281e9d8ab00c0b8544fa7431dc99661c44e0e6cbaad66f942e5c62",
                "0x0590fd2e84b7f5a152881a0d17a6fe0732be6ffd020ada4e91693f8e94696cd8",
                "0x1f99300883319c93920319ed5159329a98f2efc356165d9587c316abd6d4cbac",
                "0x516c84f2139897f30531bd6e08f3372c0a06bdccd9f17ce91bd2565c79b1afca",
                "0x5b698237e78d7b2ef3227a5bc652d030bba9bfa8f21aec555eee0b4f65a24b40",
                "0x0a125fd7e859f5e8a67214923c80caaa3e48da3ea985ab0d346ed36a0a92989a",
                "0xefb4a879db517af0fb7e4f0731a12d8360bc6a155fcfc7546ace79b55cdafa52",
                "0xd2af30f01b69d3f2d1d94e5b401418ffa90b566b1450d7b3310a097701ac694a",
                "0x769a53742322902c2080251b628f262577d620d70831c142a59b77910c464a63",
                "0xf99292f2fccc3f4fa8cef73512bd5f21a46214d922dfed8e8a65f763c13dfb72"])
    )


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


def csm_add_ics_node_operator(csm, vetted_gate, accounting, node_operator, proof, keys_count=5, curve_id=0):
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
        csm_add_node_operator(contracts.csm, contracts.cs_permissionless_gate, contracts.cs_accounting, node_operator, keys_count=keys_count)
        added_operators_count += 1
    return csm_node_operators_before, added_operators_count

