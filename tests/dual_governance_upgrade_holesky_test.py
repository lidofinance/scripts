"""
Tests for voting 23/07/2024.
"""

from scripts.dual_governance_upgrade_holesky import start_vote, dual_governance_contracts
from utils.config import contracts
from utils.test.tx_tracing_helpers import *
from brownie.network.transaction import TransactionReceipt
from utils.config import contracts
from brownie.network.account import Account

try:
    from brownie import interface, chain
except ImportError:
    print(
        "You're probably running inside Brownie console. " "Please call:\n" "set_console_globals(interface=interface)"
    )

def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding, stranger: Account):
    dao_voting = contracts.voting
    timelock = interface.EmergencyProtectedTimelock(contracts.dual_governance.TIMELOCK())

    # Lido
    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.STAKING_CONTROL_ROLE()) == contracts.voting
    assert contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())

    # Allowed tokens registry
    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.agent)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.voting)

    # Agent
    assert not contracts.acl.hasPermission(contracts.dual_governance_admin_executor, contracts.agent, contracts.agent.RUN_SCRIPT_ROLE())
    assert contracts.acl.hasPermission(contracts.voting, contracts.agent, contracts.agent.RUN_SCRIPT_ROLE())

    # Reseal manager
    assert not contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), dual_governance_contracts["resealManager"])
    assert not contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.RESUME_ROLE(), dual_governance_contracts["resealManager"])

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Lido
    assert contracts.acl.getPermissionManager(contracts.lido, contracts.lido.STAKING_CONTROL_ROLE()) == contracts.agent
    assert not contracts.acl.hasPermission(contracts.voting, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())
    assert contracts.acl.hasPermission(contracts.agent, contracts.lido, contracts.lido.STAKING_CONTROL_ROLE())

    # # Allowed tokens registry
    assert contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.voting)
    assert not contracts.allowed_tokens_registry.hasRole(contracts.allowed_tokens_registry.DEFAULT_ADMIN_ROLE(), contracts.agent)

    # Agent
    assert contracts.acl.hasPermission(contracts.dual_governance_admin_executor, contracts.agent, contracts.agent.RUN_SCRIPT_ROLE())
    assert contracts.acl.hasPermission(contracts.voting, contracts.agent, contracts.agent.RUN_SCRIPT_ROLE())

    # Reseal manager
    assert contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), dual_governance_contracts["resealManager"])
    assert contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.RESUME_ROLE(), dual_governance_contracts["resealManager"])

    proposal_id = timelock.getProposalsCount()

    # while not contracts.dual_governance.canScheduleProposal(proposal_id):
    chain.sleep(60 * 24)

    contracts.dual_governance.scheduleProposal(proposal_id, {"from": stranger})

    # while not timelock.canExecute(proposal_id):
    chain.sleep(60 * 24)

    timelock.execute(proposal_id, {"from": stranger})
