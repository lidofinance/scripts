from utils.tx_tracing import *
from utils.config import VOTING

_vote_item_group = GroupBy(
    contract_name="CallsScript",
    event_name="LogScriptCall",
    group_title="Vote item #",
    show_counter=True,
    color="magenta",
)

_service_item_group = GroupBy(
    contract_name="Voting",
    event_name="ScriptResult",
    group_title="Service events",
    show_counter=False,
    color="bright yellow",
)


def display_voting_call_trace(tx: TransactionReceipt) -> None:
    display_filtered_tx_call(
        tx,
        lambda trace_item: any(
            s in trace_item["fn"]
            for s in [
                "KernelProxy.",
                "Voting._executeVote",
                "EVMScriptRunner.getEVMScriptExecutor",
                "Initializable.",
                "TimeHelpers.",
                "AppStorage.",
                "ScriptHelpers.",
            ]
        ),
    )


def count_vote_items_by_events(tx: TransactionReceipt, voting_addr: str) -> int:
    events = tx_events_from_trace(tx)
    ev_dict = EventDict(events)

    calls_slice = ev_dict["LogScriptCall"]
    return sum(map(lambda x: x["src"] == voting_addr, calls_slice))


def display_voting_events(tx: TransactionReceipt) -> None:
    dict_events = EventDict(tx_events_from_trace(tx))
    groups = [_vote_item_group, _service_item_group]

    display_tx_events(dict_events, "Events registered during the vote execution", groups)


def group_voting_events(tx: TransactionReceipt) -> List[EventDict]:
    events = tx_events_from_trace(tx)

    def add_event_emitter(event):
        event['data'].append({'name': '_emitted_by', 'type': 'address', 'value': event['address'], 'decoded': True})
        return event
    
    # manually add event emitter address because it is dropped by EventDict class
    events = [add_event_emitter(e) for e in events]
    
    groups = [_vote_item_group, _service_item_group]

    grouped_events = group_tx_events(events, EventDict(events), groups)
    ret = [v for k, v in grouped_events if k == _vote_item_group]

    assert ret, (
        "Can't group voting events. Please check that `ETHERSCAN_TOKEN` env var is set "
        "and all of the required brownie flags (e.g. --network mainnet-fork -s) are present"
    )

    return ret


def group_voting_events_from_receipt(tx: TransactionReceipt) -> List[EventDict]:
    events = tx_events_from_receipt(tx)

    # Validate "service" Voting events are in the log
    assert len(events) >= 2, "Unexpected events count"
    assert events[-2]["address"] == VOTING and events[-2]["name"] == "ScriptResult", "Unexpected Voting service event"
    assert events[-1]["address"] == VOTING and events[-1]["name"] == "ExecuteVote", "Unexpected Voting service event"

    groups = []
    current_group = None

    for event in events[:-2]:
        is_start_of_new_group = event["name"] == "LogScriptCall" and event["address"] == VOTING

        if is_start_of_new_group:
            current_group = []
            groups.append(current_group)

        assert current_group != None, "Unexpected events chain"

        current_group.append(event)

    return [EventDict(group) for group in groups]
