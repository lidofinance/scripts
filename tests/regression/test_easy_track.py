from eth_abi.abi import encode_single
from brownie import accounts, chain, interface  # type: ignore
from utils.config import contracts, LIDO_EASYTRACK_INCREASE_NOP_STAKING_LIMIT_FACTORY

NODE_OPERATOR_ID = 0


def _encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()


def test_increase_nop_staking_limit(
    stranger,
):
    factory = interface.IncreaseNodeOperatorStakingLimit(LIDO_EASYTRACK_INCREASE_NOP_STAKING_LIMIT_FACTORY)
    node_operator = contracts.node_operators_registry.getNodeOperator(NODE_OPERATOR_ID, False)
    trusted_caller = accounts.at(node_operator["rewardAddress"], force=True)
    new_staking_limit = node_operator["totalVettedValidators"] + 1

    motions_before = contracts.easy_track.getMotions()

    if node_operator["totalAddedValidators"] < new_staking_limit:
        contracts.node_operators_registry.addSigningKeys(
            NODE_OPERATOR_ID,
            1,
            "0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000aa0101",
            "0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a1",
            {"from": contracts.voting},
        )

    calldata = _encode_calldata("(uint256,uint256)", [NODE_OPERATOR_ID, new_staking_limit])

    tx = contracts.easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    assert len(contracts.easy_track.getMotions()) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    motions = contracts.easy_track.getMotions()

    contracts.easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    updated_node_operator = contracts.node_operators_registry.getNodeOperator(NODE_OPERATOR_ID, False)

    assert updated_node_operator["totalVettedValidators"] == new_staking_limit
