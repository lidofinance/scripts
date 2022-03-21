from brownie import interface
import pytest
from utils.config import (ldo_token_address)
from scripts.vote_2021_08_26_nor_ops_1m_nft_lego_ssv import (start_vote)

NODE_OPERATORS = [
    {
        "id": 0,
        "limit": 4400
    },
    {
        "id": 2,
        "limit": 4500
    },
    {
        "id": 3,
        "limit": 5000
    },
    {
        "id": 5,
        "limit": 5000
    },
    {
        "id": 6,
        "limit": 2900
    },
    {
        "id": 7,
        "limit": 3000
    },
    {
        "id": 8,
        "limit": 5000
    },
]

NEW_NODE_OPERATORS = [
    {
        "id": 9,
        "name": "RockX",
        "address": "0x258cB32B1875168858E57Bb31482054e008d344e",
    },
    {
        "id": 10,
        "name": "Figment",
        "address": "0xfE78617EC612ac67bCc9CC145d376400f15a82cb",
    },
    {
        "id": 11,
        "name": "Allnodes",
        "address": "0xd8d93E91EA5F24D0E2a328BC242055D40f00bE1A",
    },
    {
        "id": 12,
        "name": "Anyblock Analytics",
        "address": "0x8b90ac446d4360332129e92F857a9d536DB9d7c2",
    }
]


@pytest.fixture(scope='module')
def rarible(interface):
    return interface.MintableToken('0x60f80121c31a0d46b5279700f9df786054aa5ee5')


@pytest.fixture(scope='module')
def agent(accounts):
    return accounts.at('0x3e40d73eb977dc6a537af587d48316fee66e9c8c', force=True)


def test_vote(ldo_holder, helpers, accounts, dao_voting, node_operators_registry, rarible, agent):
    ldo = interface.ERC20(ldo_token_address)

    blox_address = '0xb35096b074fdb9bBac63E3AdaE0Bbde512B2E6b6'
    obol_address = '0xC62188bDB24d2685AEd8fa491E33eFBa47Db63C2'
    blox_ldo_balance_before = ldo.balanceOf(blox_address)
    obol_ldo_balance_before = ldo.balanceOf(obol_address)

    lego_address = '0x12a43b049A7D330cB8aEAB5113032D18AE9a9030'

    (vote_id, _) = start_vote({"from": ldo_holder}, silent=True)
    print(f'Vote {vote_id} created')
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting)
    print(f'Vote {vote_id} executed')

    blox_ldo_balance_after = ldo.balanceOf(blox_address)
    obol_ldo_balance_after = ldo.balanceOf(obol_address)

    assert blox_ldo_balance_after - blox_ldo_balance_before == 16_640 * 10 ** 18
    assert obol_ldo_balance_after - obol_ldo_balance_before == 16_640 * 10 ** 18

    assert ldo.balanceOf(lego_address) == 240_000 * 10 ** 18

    assert rarible.ownerOf(1225266) == '0x90102a92e8E40561f88be66611E5437FEb339e79'

    for node_operator in NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(node_operator["id"], True)
        assert node_operator["limit"] == no[3]

    assert node_operators_registry.getNodeOperatorsCount() == 13

    for node_operator in NEW_NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(node_operator["id"], True)
        assert no[0] == True
        assert no[1] == node_operator["name"]
        assert no[2] == node_operator["address"]
        assert no[3] == 0
