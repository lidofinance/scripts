from utils.tx_tracing import *

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
    groups = [_vote_item_group, _service_item_group]

    grouped_events = group_tx_events(events, EventDict(events), groups)
    ret = [v for k, v in grouped_events if k == _vote_item_group]

    assert ret, (
        "Can't group voting events. Please check that `ETHERSCAN_TOKEN` env var is set "
        "and all of the required brownie flags (e.g. --network mainnet-fork -s) are present"
    )

    return ret
