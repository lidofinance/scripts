from brownie import chain, accounts, interface
from utils.config import (
    contracts,
    EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER,
    EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
)
from utils.test.easy_track_helpers import _encode_calldata
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch

MIN_OP_KEYS_CNT = 10
MIN_OPS_CNT = 3


def get_operator_name(n: int):
    return f"Name {n}"


def get_operator_address(id: int):
    return f"0x111{id:037x}"


def get_managers_address(id: int):
    return f"0x222{id:037x}"


def fill_simple_dvt_ops(stranger, min_ops_cnt=MIN_OPS_CNT):
    node_operators_count_before = contracts.simple_dvt.getNodeOperatorsCount()
    cnt = 0
    input_params = []
    while node_operators_count_before + cnt < min_ops_cnt:
        op_id = node_operators_count_before + cnt
        input_params.append((get_operator_name(op_id), get_operator_address(op_id), get_managers_address(op_id)))
        cnt += 1

    (node_operators_count_before, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt, stranger, input_params
    )
    assert node_operator_count_after == node_operators_count_before + cnt
    assert contracts.simple_dvt.getNodeOperatorsCount() >= min_ops_cnt


def fill_simple_dvt_ops_keys(stranger, min_ops_cnt=MIN_OPS_CNT, min_keys_cnt=MIN_OP_KEYS_CNT):
    fill_simple_dvt_ops(stranger, min_ops_cnt)
    for no_id in range(0, min_ops_cnt):
        unused_keys_count = contracts.simple_dvt.getUnusedSigningKeyCount(no_id)

        if unused_keys_count < min_keys_cnt:
            simple_dvt_add_keys(contracts.simple_dvt, no_id, min_keys_cnt - unused_keys_count)

        assert contracts.simple_dvt.getUnusedSigningKeyCount(no_id) >= min_keys_cnt


def fill_simple_dvt_ops_vetted_keys(stranger, min_ops_cnt=MIN_OPS_CNT, min_keys_cnt=MIN_OP_KEYS_CNT):
    fill_simple_dvt_ops_keys(stranger, min_ops_cnt, min_keys_cnt)
    factory = interface.SetVettedValidatorsLimits(EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    input_params = []
    for no_id in range(0, min_ops_cnt):
        no = contracts.simple_dvt.getNodeOperator(no_id, False)

        if no["totalVettedValidators"] < no["totalAddedValidators"]:
            input_params.append((no_id, no["totalAddedValidators"]))

    if len(input_params) > 0:
        calldata = _encode_calldata("((uint256,uint256)[])", [input_params])

        motions_before = contracts.easy_track.getMotions()

        tx = contracts.easy_track.createMotion(factory, calldata, {"from": trusted_caller})
        motions = contracts.easy_track.getMotions()

        assert len(motions) == len(motions_before) + 1

        chain.sleep(60 * 60 * 24 * 3)
        chain.mine()

        contracts.easy_track.enactMotion(
            motions[-1][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

    for no_id in range(0, min_ops_cnt):
        no = contracts.simple_dvt.getNodeOperator(no_id, False)

        assert no["totalVettedValidators"] == no["totalAddedValidators"]


def simple_dvt_vet_keys(operator_id, stranger):
    factory = interface.SetVettedValidatorsLimits(EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    simple_dvt, easy_track = contracts.simple_dvt, contracts.easy_track

    operator = simple_dvt.getNodeOperator(operator_id, False)

    if operator["totalVettedValidators"] == operator["totalAddedValidators"]:
        return

    calldata = _encode_calldata("((uint256,uint256)[])", [[(operator_id, operator["totalAddedValidators"])]])
    motions_before = easy_track.getMotions()

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})
    motions = easy_track.getMotions()

    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    operator = simple_dvt.getNodeOperator(operator_id, False)
    assert operator["totalVettedValidators"] == operator["totalAddedValidators"]


def simple_dvt_add_node_operators(simple_dvt, stranger, input_params=[]):
    factory = interface.AddNodeOperators(EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    node_operators_count_before = simple_dvt.getNodeOperatorsCount()

    # input_params = [
    #     (OPERATOR_NAMES[0], REWARD_ADDRESSES[0], MANAGERS[0]),
    #     (OPERATOR_NAMES[1], REWARD_ADDRESSES[1], MANAGERS[1]),
    # ]
    if len(input_params) > 0:
        calldata = _encode_calldata(
            "(uint256,(string,address,address)[])",
            [
                node_operators_count_before,
                input_params,
            ],
        )
        motions_before = contracts.easy_track.getMotions()

        tx = contracts.easy_track.createMotion(factory, calldata, {"from": trusted_caller})

        motions = contracts.easy_track.getMotions()
        assert len(motions) == len(motions_before) + 1

        chain.sleep(60 * 60 * 24 * 3)
        chain.mine()

        contracts.easy_track.enactMotion(
            motions[-1][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

    return (node_operators_count_before, simple_dvt.getNodeOperatorsCount())


def simple_dvt_add_keys(simple_dvt, node_operator_id, keys_count=1):
    pubkeys_batch = random_pubkeys_batch(keys_count)
    signatures_batch = random_signatures_batch(keys_count)

    total_signing_keys_count_before = simple_dvt.getTotalSigningKeyCount(node_operator_id)
    unused_signing_keys_count_before = simple_dvt.getUnusedSigningKeyCount(node_operator_id)
    node_operator_before = simple_dvt.getNodeOperator(node_operator_id, True)

    tx = simple_dvt.addSigningKeys(
        node_operator_id,
        keys_count,
        pubkeys_batch,
        signatures_batch,
        {"from": node_operator_before["rewardAddress"]},
    )

    total_signing_keys_count_after = simple_dvt.getTotalSigningKeyCount(node_operator_id)
    unused_signing_keys_count_after = simple_dvt.getUnusedSigningKeyCount(node_operator_id)

    assert total_signing_keys_count_after == total_signing_keys_count_before + keys_count
    assert unused_signing_keys_count_after == unused_signing_keys_count_before + keys_count
