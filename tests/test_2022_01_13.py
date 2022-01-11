"""
Tests for voting 27/12/2021.
"""

from collections import namedtuple

from scripts.vote_2022_01_13 import start_vote
from tx_tracing_helpers import *


dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

NodeOperatorAdd = namedtuple(
    'NodeOperatorAdd', ['name', 'id', 'address']
)
'''
 Node Operators Registry:
   Add node operator named Stakin with reward address
   `0xf6b0a1B771633DB40A3e21Cc49fD2FE35669eF46`
   Add node operator named ChainLayer with reward address
   `0xd5aC23b1adE91A054C4974264C9dbdDD0E52BB05`
   Add node operator named Simply Staking with reward address
   `0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd`
   Add node operator named BridgeTower with reward address
   `0x40C20da8d0214A7eF33a84e287992858dB744e6d`
   Add node operator named Stakely with reward address
   `0x77d2CF58aa4da90b3AFCd283646568e4383193BF`
   Add node operator named InfStones with reward address
   `0x60bC65e1ccA448F98578F8d9f9AB64c3BA70a4c3`
   Add node operator named HashQuark with reward address
   `0x065dAAb531e7Cd50f900D644E8caE8A208eEa4E9`
   Add node operator named ConsenSys Codefi with reward address
   `0x5Bc5ec5130f66f13d5C21ac6811A7e624ED3C7c6`
'''

NEW_NODE_OPERATORS = [
    # name, id, address
    NodeOperatorAdd(
        'Stakin', 14, '0xf6b0a1B771633DB40A3e21Cc49fD2FE35669eF46'
    ),
    NodeOperatorAdd(
        'ChainLayer', 15, '0xd5aC23b1adE91A054C4974264C9dbdDD0E52BB05'
    ),
    NodeOperatorAdd(
        'Simply Staking', 16, '0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd'
    ),
    NodeOperatorAdd(
        'BridgeTower', 17, '0x40C20da8d0214A7eF33a84e287992858dB744e6d'
    ),
    NodeOperatorAdd(
        'Stakely', 18, '0x77d2CF58aa4da90b3AFCd283646568e4383193BF'
    ),
    NodeOperatorAdd(
        'InfStones', 19, '0x60bC65e1ccA448F98578F8d9f9AB64c3BA70a4c3'
    ),
    NodeOperatorAdd(
        'HashQuark', 20, '0x065dAAb531e7Cd50f900D644E8caE8A208eEa4E9'
    ),
    NodeOperatorAdd(
        'ConsenSys Codefi', 21, '0x5Bc5ec5130f66f13d5C21ac6811A7e624ED3C7c6'
    ),
]

def test_2022_01_13(
    helpers, accounts, ldo_holder, dao_voting, node_operators_registry
):
    ##
    ## START VOTE
    ##
    vote_id, _ = start_vote({ 'from': ldo_holder }, silent=True)
    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    for node_operator in NEW_NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(
            node_operator.id, True
        )

        message = f'Failed on {node_operator.name}'
        assert no[0] is True, message
        assert no[1] == node_operator.name, message
        assert no[2] == node_operator.address, message
        assert no[3] == 0

    ### validate vote events
    # assert count_vote_items_by_events(tx) == 3, "Incorrect voting items count"

    # display_voting_events(tx)