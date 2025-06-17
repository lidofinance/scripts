from utils.agent import agent_forward
from utils.voting import create_vote, bake_vote_items
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, ARAGON_CALLS_SCRIPT, GATE_SEAL_FACTORY
from utils.test.tx_tracing_helpers import group_voting_events_from_receipt, group_voting_events
from utils.evm_script import encode_call_script
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.allowed_recipients_registry import create_top_up_allowed_recipient_permission
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)


def test_empty_voting(helpers, accounts):
    vote_id, _ = create_vote(bake_vote_items([], []), tx_params={"from": LDO_HOLDER_ADDRESS_FOR_TESTS})
    vote_execute_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    events_from_receipt = group_voting_events_from_receipt(vote_execute_tx)

    assert len(events_from_receipt) == 0


def test_voting_with_empty_agent_forward(helpers, accounts):
    vote_id, _ = create_vote(
        bake_vote_items(["1. Item with empty aragon forward"], [agent_forward([])]),
        tx_params={"from": LDO_HOLDER_ADDRESS_FOR_TESTS},
    )
    vote_execute_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    events_from_receipt = group_voting_events_from_receipt(vote_execute_tx)

    assert len(events_from_receipt) == 1
    assert len(events_from_receipt[0]["LogScriptCall"]) == 1
    assert len(events_from_receipt[0]["ScriptResult"]) == 1

    log_script_call_event = events_from_receipt[0]["LogScriptCall"]
    assert log_script_call_event["sender"] == vote_execute_tx.sender
    assert log_script_call_event["src"] == contracts.voting
    assert log_script_call_event["dst"] == contracts.agent

    script_result_event = events_from_receipt[0]["ScriptResult"]
    assert script_result_event["executor"] == ARAGON_CALLS_SCRIPT
    assert script_result_event["script"] == "0x00000001"
    assert script_result_event["input"] == "0x00"
    assert script_result_event["returnData"] == "0x00"


def test_calls_without_events(accounts, helpers):
    vote_desc_items, call_script_items = zip(
        (
            "View method without events from Voting",
            (contracts.ldo_token.address, contracts.ldo_token.totalSupply.encode_input()),
        ),
        (
            "View method without events forward to Agent",
            agent_forward([(contracts.voting.address, contracts.voting.isForwarder.encode_input())]),
        ),
    )
    vote_id, _ = create_vote(
        bake_vote_items(list(vote_desc_items), list(call_script_items)),
        tx_params={"from": LDO_HOLDER_ADDRESS_FOR_TESTS},
    )
    vote_execute_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    events_from_receipt = group_voting_events_from_receipt(vote_execute_tx)

    assert len(events_from_receipt) == 2

    # first item of the vote, even though view method doesn't emit any event, service LogScriptCall
    # event was emitted with correct params

    assert len(events_from_receipt[0]) == 1
    assert len(events_from_receipt[0]["LogScriptCall"]) == 1

    voting_log_script_call_event = events_from_receipt[0]["LogScriptCall"]
    assert voting_log_script_call_event["sender"] == vote_execute_tx.sender
    assert voting_log_script_call_event["src"] == contracts.voting
    assert voting_log_script_call_event["dst"] == contracts.ldo_token

    # second item of the vote, beside LogScriptCall from Voting contract it also includes
    # LogScriptCall and ScriptResult events from forward() call to Agent

    assert len(events_from_receipt[1]) == 3
    assert len(events_from_receipt[1]["LogScriptCall"]) == 2
    assert len(events_from_receipt[1]["ScriptResult"]) == 1

    voting_log_script_call_event = events_from_receipt[1]["LogScriptCall"][0]
    assert voting_log_script_call_event["sender"] == vote_execute_tx.sender
    assert voting_log_script_call_event["src"] == contracts.voting
    assert voting_log_script_call_event["dst"] == contracts.agent

    agent_log_script_call_event = events_from_receipt[1]["LogScriptCall"][1]
    assert agent_log_script_call_event["sender"] == contracts.voting
    assert agent_log_script_call_event["src"] == contracts.agent
    assert agent_log_script_call_event["dst"] == contracts.voting

    agent_script_result_event = events_from_receipt[1]["ScriptResult"]
    assert agent_script_result_event["executor"] == ARAGON_CALLS_SCRIPT
    assert agent_script_result_event["script"] == encode_call_script(
        [(contracts.voting.address, contracts.voting.isForwarder.encode_input())]
    )
    assert agent_script_result_event["input"] == "0x00"
    assert agent_script_result_event["returnData"] == "0x00"


def test_multiple_events_happy_path(accounts, helpers, interface, chain):
    seconds_per_day = 24 * 60 * 60
    seal_duration = 7 * seconds_per_day
    expiry_timestamp = chain.time() + 30 * seconds_per_day

    # brownie checks that address contain code during permissions build, so use agent contract as stub
    registry_stub_address = contracts.agent.address
    new_evm_script_factory_stub = accounts[-1]

    gate_seal_factory = interface.GateSealFactory(GATE_SEAL_FACTORY)

    vote_desc_items, call_script_items = zip(
        (
            "Add EVMScriptFactory from Voting",
            add_evmscript_factory(
                factory=new_evm_script_factory_stub,
                permissions=create_top_up_allowed_recipient_permission(registry_address=registry_stub_address),
            ),
        ),
        (
            "Deploy Gate Seal through Agent forwarding",
            agent_forward(
                [
                    (
                        gate_seal_factory.address,
                        gate_seal_factory.create_gate_seal.encode_input(
                            contracts.agent.address,
                            seal_duration,
                            [contracts.withdrawal_queue],
                            expiry_timestamp,
                        ),
                    )
                ]
            ),
        ),
    )

    vote_id, _ = create_vote(
        bake_vote_items(list(vote_desc_items), list(call_script_items)),
        tx_params={"from": LDO_HOLDER_ADDRESS_FOR_TESTS},
    )
    vote_execute_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    events_from_receipt = group_voting_events_from_receipt(vote_execute_tx)

    assert len(events_from_receipt) == 2

    assert len(events_from_receipt[0]["LogScriptCall"]) == 1
    assert len(events_from_receipt[0]["EVMScriptFactoryAdded"]) == 1

    validate_evmscript_factory_added_event(
        events_from_receipt[0],
        EVMScriptFactoryAdded(
            factory_addr=new_evm_script_factory_stub,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(interface.AllowedRecipientRegistry(registry_stub_address), "updateSpentAmount")[2:],
        ),
    )

    assert len(events_from_receipt[1]["LogScriptCall"]) == 2
    assert len(events_from_receipt[1]["GateSealCreated"]) == 1
    assert len(events_from_receipt[1]["ScriptResult"]) == 1

    voting_log_script_call_event = events_from_receipt[1]["LogScriptCall"][0]
    assert voting_log_script_call_event["sender"] == vote_execute_tx.sender
    assert voting_log_script_call_event["src"] == contracts.voting
    assert voting_log_script_call_event["dst"] == contracts.agent

    agent_log_script_call_event = events_from_receipt[1]["LogScriptCall"][1]
    assert agent_log_script_call_event["sender"] == contracts.voting
    assert agent_log_script_call_event["src"] == contracts.agent
    assert agent_log_script_call_event["dst"] == gate_seal_factory

    agent_script_result_event = events_from_receipt[1]["ScriptResult"]
    assert agent_script_result_event["executor"] == ARAGON_CALLS_SCRIPT
    assert agent_script_result_event["script"] == encode_call_script(
        [
            (
                gate_seal_factory.address,
                gate_seal_factory.create_gate_seal.encode_input(
                    contracts.agent.address,
                    seal_duration,
                    [contracts.withdrawal_queue],
                    expiry_timestamp,
                ),
            )
        ]
    )
    assert agent_script_result_event["input"] == "0x00"
    assert agent_script_result_event["returnData"] == "0x00"

    # Additionally check that events from trace produce same result

    events_from_trace = group_voting_events(vote_execute_tx)
    assert str(events_from_receipt) == str(events_from_trace)
