from brownie import accounts, interface, chain, reverts
from archive.scripts.upgrade_2024_08_20 import start_vote as start_vote_upgrade
from archive.scripts.revert_upgrade_2024_08_20 import start_vote as start_vote_downgrade
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, LDO_VOTE_EXECUTORS_FOR_TESTS, VOTING
from utils.mainnet_fork import chain_snapshot
from utils.test.tx_tracing_helpers import *
from utils.voting import create_vote, bake_vote_items
from utils.test.extra_data import VoterState

old_trp_voting_adapter_address = "0xCFda8aB0AE5F4Fa33506F9C51650B890E4871Cc1"

# Before simple delegation upgrade
old_voting_app = {
    "address": "0x72fb5253ad16307b9e773d2a78cac58e309d5ba4",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (3, 0, 0),
}

# After simple delegation upgrade
updated_voting_app = {
    "address": "0xf165148978Fa3cE74d76043f833463c340CFB704",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (4, 0, 0),
}

updated_trp_voting_adapter_address = "0x4b2AB543FA389Ca8528656282bF0011257071BED"

# After simple delegation downgrade
downgraded_voting_app = {
    "address": "0x72fb5253ad16307b9e773d2a78cac58e309d5ba4",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (5, 0, 0),
}


def create_dummy_vote(ldo_holder: str) -> int:
    vote_items = bake_vote_items(vote_desc_items=[], call_script_items=[])
    return create_vote(vote_items, {"from": ldo_holder}, cast_vote=False, executes_if_decided=False)[0]


def test_voting_delegation_reverse_upgrade(helpers, delegate1, delegate2, ldo_holder):
    with chain_snapshot():
        # Voting App before
        voting_proxy = interface.AppProxyUpgradeable(VOTING)
        voting_app_from_repo = contracts.voting_app_repo.getLatest()
        assert voting_app_from_repo[0] == old_voting_app["version"]
        assert voting_app_from_repo[1] == old_voting_app["address"]
        assert voting_proxy.implementation() == old_voting_app["address"]

        # START UPGRADE VOTE
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote_upgrade(tx_params, silent=True)
        helpers.execute_vote(accounts, vote_id, contracts.voting)

        # Voting App after upgrade, before downgrade
        voting_app_from_repo = contracts.voting_app_repo.getLatest()
        assert voting_app_from_repo[0] == updated_voting_app["version"]
        assert voting_app_from_repo[1] == updated_voting_app["address"]
        assert voting_proxy.implementation() == updated_voting_app["address"]

        # TRP Voting Adapter after upgrade, before downgrade
        trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
        assert trp_voting_adapter_address == updated_trp_voting_adapter_address

        voters = LDO_VOTE_EXECUTORS_FOR_TESTS + [LDO_HOLDER_ADDRESS_FOR_TESTS]
        contracts.voting.assignDelegate(delegate1, {"from": accounts.at(voters[0], force=True)})
        assert contracts.voting.getDelegate(voters[0]) == delegate1
        contracts.voting.assignDelegate(delegate1, {"from": accounts.at(voters[1], force=True)})
        assert contracts.voting.getDelegate(voters[1]) == delegate1
        contracts.voting.assignDelegate(delegate2, {"from": accounts.at(voters[2], force=True)})
        assert contracts.voting.getDelegate(voters[2]) == delegate2

        # Start dummy vote and vote for it during main phase
        dummy_vote_id = create_dummy_vote(ldo_holder)
        vote = contracts.voting.getVote(dummy_vote_id)
        assert vote["yea"] == 0
        assert vote["nay"] == 0
        assert contracts.voting.getVotePhase(dummy_vote_id) == 0  # Main phase
        contracts.voting.attemptVoteFor(dummy_vote_id, True, voters[0], {"from": delegate1})
        contracts.voting.vote(dummy_vote_id, True, False, {"from": accounts.at(voters[1], force=True)})
        contracts.voting.attemptVoteFor(dummy_vote_id, True, voters[2], {"from": delegate2})
        contracts.voting.vote(dummy_vote_id, True, False, {"from": accounts.at(voters[3], force=True)})

        # Fast-forward to the objection phase
        chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
        chain.mine()
        assert contracts.voting.getVotePhase(dummy_vote_id) == 1  # Objection phase

        # Vote during the objection phase
        contracts.voting.assignDelegate(delegate2, {"from": accounts.at(voters[0], force=True)})
        contracts.voting.attemptVoteFor(dummy_vote_id, False, voters[0], {"from": delegate2})

        # Check vote state
        assert contracts.voting.getVoterState(dummy_vote_id, voters[0]) == VoterState.DelegateNay.value
        assert contracts.voting.getVoterState(dummy_vote_id, voters[1]) == VoterState.Yea.value
        assert contracts.voting.getVoterState(dummy_vote_id, voters[2]) == VoterState.DelegateYea.value
        assert contracts.voting.getVoterState(dummy_vote_id, voters[3]) == VoterState.Yea.value
        vote = contracts.voting.getVote(dummy_vote_id)
        assert vote["yea"] == sum([contracts.ldo_token.balanceOf(v) for v in voters[1:]])
        assert vote["nay"] == contracts.ldo_token.balanceOf(voters[0])

        # Execute the vote
        chain.sleep(contracts.voting.objectionPhaseTime())
        chain.mine()
        assert contracts.voting.getVotePhase(dummy_vote_id) == 2  # Closed phase
        execute_tx = contracts.voting.executeVote(dummy_vote_id, {"from": ldo_holder})
        assert execute_tx.events["ExecuteVote"]["voteId"] == dummy_vote_id

        # START DOWNGRADE VOTE
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote_downgrade(tx_params, silent=True)
        helpers.execute_vote(accounts, vote_id, contracts.voting)

        # Voting App after downgrade
        voting_app_from_repo = contracts.voting_app_repo.getLatest()
        assert voting_app_from_repo[0] == downgraded_voting_app["version"]
        assert voting_app_from_repo[1] == downgraded_voting_app["address"]
        assert voting_proxy.implementation() == downgraded_voting_app["address"]

        # TRP Voting Adapter after downgrade
        trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
        assert trp_voting_adapter_address == old_trp_voting_adapter_address

        # Check that assignDelegate call is not possible now
        with reverts():
            contracts.voting.assignDelegate(delegate1, {"from": accounts.at(voters[2], force=True)})

        # Check dummy vote state again
        vote_object = contracts.voting.getVote(dummy_vote_id)
        print("vote_object", vote_object)
        with reverts():
            contracts.voting.getVoterState(dummy_vote_id, voters[0])  # DelegateNay
        assert contracts.voting.getVoterState(dummy_vote_id, voters[1]) == VoterState.Yea.value
        with reverts():
            contracts.voting.getVoterState(dummy_vote_id, voters[2])  # DelegateYea
        assert contracts.voting.getVoterState(dummy_vote_id, voters[3]) == VoterState.Yea.value
        vote = contracts.voting.getVote(dummy_vote_id)
        assert vote["yea"] == sum([contracts.ldo_token.balanceOf(v) for v in voters[1:]])
        assert vote["nay"] == contracts.ldo_token.balanceOf(voters[0])

        # Check that dummy vote is closed and can not be executed
        assert contracts.voting.getVotePhase(dummy_vote_id) == 2  # Closed phase
        with reverts("VOTING_CAN_NOT_EXECUTE"):
            contracts.voting.executeVote(dummy_vote_id, {"from": ldo_holder})

        # Check that it's not possible to vote
        with reverts():
            contracts.voting.attemptVoteFor(dummy_vote_id, True, voters[0], {"from": delegate1})
        with reverts("VOTING_CAN_NOT_VOTE"):
            contracts.voting.vote(dummy_vote_id, True, False, {"from": accounts.at(voters[1], force=True)})

        # Start new dummy vote
        dummy_vote_id = create_dummy_vote(ldo_holder)

        # Ensure that delegate can not vote
        with reverts():
            contracts.voting.attemptVoteFor(dummy_vote_id, True, voters[0], {"from": delegate1})
        # Vote for new dummy vote during main phase
        for voter in voters:
            contracts.voting.vote(dummy_vote_id, True, False, {"from": accounts.at(voter, force=True)})

        # Vote for new dummy vote during objection phase
        chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
        chain.mine()
        assert contracts.voting.getVotePhase(dummy_vote_id) == 1  # Objection phase
        contracts.voting.vote(dummy_vote_id, False, False, {"from": accounts.at(voters[0], force=True)})

        # Execute new dummy vote
        chain.sleep(contracts.voting.objectionPhaseTime())
        chain.mine()
        assert contracts.voting.getVotePhase(dummy_vote_id) == 2  # Closed phase
        execute_tx = contracts.voting.executeVote(dummy_vote_id, {"from": ldo_holder})
        assert execute_tx.events["ExecuteVote"]["voteId"] == dummy_vote_id
