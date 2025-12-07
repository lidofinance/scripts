import pytest
import brownie
import tests.utils_test_2025_12_10_lidov3 as lidov3

@pytest.fixture(autouse=True)
def isolation():
    brownie.chain.reset()

def test_vote_v1_dg1(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):

    lidov3.enact_and_test_voting(helpers, accounts, ldo_holder, vote_ids_from_env,
        194, 6,
    )

    lidov3.enact_and_test_dg(stranger, 6)