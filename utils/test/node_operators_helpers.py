from typing import Dict

NODE_OPERATOR_KEYS = [
    "active",
    "name",
    "rewardAddress",
    "stakingLimit",
    "stoppedValidators",
    "totalSigningKeys",
    "usedSigningKeys",
]

NODE_OPERATOR_SUMMARY_KEYS = [
    "isTargetLimitActive",
    "targetValidatorsCount",
    "stuckValidatorsCount",
    "refundedValidatorsCount",
    "stuckPenaltyEndTimestamp",
    "totalExitedValidators",
    "totalDepositedValidators",
    "depositableValidatorsCount",
]


def assert_node_operators(first: Dict[str, any], second: Dict[str, any], skip: [str] = []):
    assert_dict_values(first, second, NODE_OPERATOR_KEYS, skip)


def assert_summaries(first, second, skip=[]):
    assert_dict_values(first, second, NODE_OPERATOR_SUMMARY_KEYS, skip)


def assert_dict_values(first, second, keys, skip):
    for key in keys:
        if key in skip:
            continue
        assert first[key] == second[key], f'"{key}" values differ: "{first[key]}" != "{second[key]}"'
