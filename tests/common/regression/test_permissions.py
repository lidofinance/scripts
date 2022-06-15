"""
Tests for permissions setup
"""
import pytest

from brownie import interface, convert, web3
from event_validators.permission import Permission, PermissionP
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def operator(accounts, dao_voting):
    return accounts.at(dao_voting.address, force=True)


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(vote_id_from_env, helpers, accounts, dao_voting):
    if vote_id_from_env:
        helpers.execute_vote(
            vote_id=vote_id_from_env, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
        )

    start_and_execute_votes(dao_voting, helpers)

@pytest.fixture(scope="module")
def permission_pause_role(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='PAUSE_ROLE'))
    )

@pytest.fixture(scope="module")
def permission_resume_role(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='RESUME_ROLE'))
    )


@pytest.fixture(scope="module")
def permission_staking_pause_role(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='STAKING_PAUSE_ROLE'))
    )

@pytest.fixture(scope="module", autouse=True)
def permission_staking_control_role(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='STAKING_CONTROL_ROLE'))
    )

@pytest.fixture(scope="module")
def permission_set_el_rewards_withdraw_limit_role(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE'))
    )

@pytest.fixture(scope="module")
def permission_set_el_rewards_vault_role(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='SET_EL_REWARDS_VAULT_ROLE'))
    )

@pytest.fixture(scope="module")
def permission_set_treasury(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='SET_TREASURY'))
    )

@pytest.fixture(scope="module")
def permission_set_insurance_fund(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='SET_INSURANCE_FUND'))
    )

@pytest.fixture(scope="module")
def permission_set_oracle(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='SET_ORACLE'))
    )

@pytest.fixture(scope="module")
def permission_manage_protocol_contracts(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='MANAGE_PROTOCOL_CONTRACTS_ROLE'))
    )

@pytest.fixture(scope="module")
def permission_old_deposit_role(lido):
    return Permission(
        entity=interface.DepositSecurityModule('0xDb149235B6F40dC08810AA69869783Be101790e7'),
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='DEPOSIT_ROLE'))
    )

@pytest.fixture(scope="module")
def permission_new_deposit_role(lido):
    return Permission(
        entity=interface.DepositSecurityModule('0x710B3303fB508a84F10793c1106e32bE873C24cd'),
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='DEPOSIT_ROLE'))
    )

@pytest.fixture(scope="module")
def permission_manage_fee(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='MANAGE_FEE'))
    )

@pytest.fixture(scope="module")
def permission_burn_role_voting_old(dao_voting, lido):
    return Permission(
        entity=dao_voting,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='BURN_ROLE'))
    )

@pytest.fixture(scope="module")
def permission_burn_role_burner_new(self_owned_steth_burner, lido):
    return PermissionP(
        entity=self_owned_steth_burner,
        app=lido,  # Lido
        role=convert.to_uint(web3.keccak(text='BURN_ROLE')),
        params=['0x000100000000000000000000B280E33812c0B09353180e92e27b8AD399B07f26']
    )


def test_permissions_after_vote(
    acl,
    permission_pause_role,
    permission_resume_role,
    permission_staking_control_role,
    permission_staking_pause_role,
    permission_set_el_rewards_vault_role,
    permission_set_el_rewards_withdraw_limit_role,
    permission_set_oracle,
    permission_set_treasury,
    permission_set_insurance_fund,
    permission_manage_protocol_contracts,
    permission_old_deposit_role,
    permission_new_deposit_role,
    permission_manage_fee,
    permission_burn_role_voting_old,
    permission_burn_role_burner_new
):
    assert acl.hasPermission(*permission_pause_role)
    assert acl.hasPermission(*permission_resume_role)
    assert acl.hasPermission(*permission_staking_control_role)
    assert acl.hasPermission(*permission_staking_pause_role)
    assert acl.hasPermission(*permission_set_el_rewards_vault_role)
    assert acl.hasPermission(*permission_set_el_rewards_withdraw_limit_role)
    assert not acl.hasPermission(*permission_set_oracle)
    assert not acl.hasPermission(*permission_set_treasury)
    assert not acl.hasPermission(*permission_set_insurance_fund)
    assert acl.hasPermission(*permission_manage_protocol_contracts)
    assert acl.hasPermission(*permission_old_deposit_role)
    assert not acl.hasPermission(*permission_new_deposit_role)
    assert acl.hasPermission(*permission_manage_fee)
    assert not acl.hasPermission(*permission_burn_role_voting_old)
    assert acl.hasPermission['address,address,bytes32,uint[]'](*permission_burn_role_burner_new)
