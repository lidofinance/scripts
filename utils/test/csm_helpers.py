from brownie import ZERO_ADDRESS, chain

from utils.balance import set_balance_in_wei
from utils.test.easy_track_helpers import _encode_calldata
from utils.test.helpers import ETH
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.config import contracts, CSM_COMMITTEE_MS, EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY
from utils.test.merkle_tree import ICSTree



def csm_set_ics_tree_members(members):
    tree = ICSTree.new(members)
    calldata = _encode_calldata(["bytes32", "string"], [tree.root, "0xabc"])
    tx = contracts.easy_track.createMotion(EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY, calldata, {"from": CSM_COMMITTEE_MS})
    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()
    motions = contracts.easy_track.getMotions()
    contracts.easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": CSM_COMMITTEE_MS},
    )

    return tree



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
