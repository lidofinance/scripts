import pytest
import brownie
import tests.utils_test_2025_12_15_lidov3 as lidov3
import tests.utils_test_2025_12_15_operations as ops

@pytest.fixture(autouse=True)
def isolation():
    brownie.chain.reset()

def test_vote_dg1_dg2(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):

    lidov3.enact_and_test_dg(stranger, 6)

    ops.enact_and_test_dg(stranger, 7)

def test_vote_dg2_dg1(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):

    ops.enact_and_test_dg(stranger, 7)

    lidov3.enact_and_test_dg(stranger, 6)