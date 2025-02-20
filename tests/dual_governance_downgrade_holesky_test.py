from scripts.dual_governance_downgrade_holesky import start_vote
from utils.config import contracts
from utils.test.tx_tracing_helpers import *
from brownie.network.transaction import TransactionReceipt
from utils.config import contracts
from brownie.network.account import Account

DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x3Cc908B004422fd66FdB40Be062Bf9B0bd5BDbed"
RESEAL_MANAGER = "0x517C93bb27aD463FE3AD8f15DaFDAD56EC0bEeC3"

def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding, stranger: Account):
    dao_voting = contracts.voting

    # Lido
    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.STAKING_CONTROL_ROLE()) == contracts.agent
    assert not contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())
    assert contracts.acl.hasPermission(contracts.agent, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())

    # Reseal manager
    assert contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), RESEAL_MANAGER)
    assert contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.RESUME_ROLE(), RESEAL_MANAGER)

    # Allowed tokens registry
    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.voting)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.agent)

    # Agent
    assert contracts.acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, contracts.agent, contracts.agent.RUN_SCRIPT_ROLE())
    assert contracts.acl.hasPermission(contracts.voting, contracts.agent, contracts.agent.RUN_SCRIPT_ROLE())

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Lido
    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.STAKING_CONTROL_ROLE()) == contracts.voting
    assert contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())

    # Reseal manager
    assert not contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), RESEAL_MANAGER)
    assert not contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.RESUME_ROLE(), RESEAL_MANAGER)

    # Allowed tokens registry
    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.agent)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.voting)

    # Agent
    assert not contracts.acl.hasPermission(DUAL_GOVERNANCE_ADMIN_EXECUTOR, contracts.agent, contracts.agent.RUN_SCRIPT_ROLE())
    assert contracts.acl.hasPermission(contracts.voting, contracts.agent, contracts.agent.RUN_SCRIPT_ROLE())
