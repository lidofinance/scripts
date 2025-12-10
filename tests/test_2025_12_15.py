import tests.utils_test_2025_12_15_operations as ops


def test_vote_v2_dg2(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):

    ops.enact_and_test_voting(helpers, accounts, ldo_holder, vote_ids_from_env, stranger,
        194, 6,
    )

    ops.enact_and_test_dg(stranger, 6)
