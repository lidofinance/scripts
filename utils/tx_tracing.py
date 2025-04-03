#!/usr/bin/python3

from typing import Callable, Dict, Optional, List, Annotated, Tuple
from dataclasses import dataclass

from eth_event import StructLogError, decode_traceTransaction, decode_logs

from brownie.network.transaction import TransactionReceipt
from brownie.network.transaction import _step_internal, _step_external, _step_compare
from brownie.network.event import EventDict, _topics
from brownie.network import state
from brownie.convert.normalize import format_event
from brownie import web3

from brownie.utils import color
from brownie.utils.output import build_tree


@dataclass(eq=True, frozen=True)
class GroupBy:
    contract_name: str
    event_name: str
    group_title: str
    show_counter: bool
    color: str


def _align_intval_to(val: int, multiple: int) -> int:
    return val + (-val) % multiple


def _align_logdata_len(trace: List) -> List:
    for trace_item in trace:
        if not trace_item["op"].startswith("LOG"):
            continue

        try:
            length = int(trace_item["stack"][-2], 16)
            proper_length = _align_intval_to(length, 32)
            if proper_length > length:
                # overwrite logdata length
                trace_item["stack"][-2] = hex(proper_length)

                offset = int(trace_item["stack"][-1], 16)
                # determine memory word to expand
                memory_word_id = (offset + length) // 32
                # find the exact symbol position within the word
                internal_offset = 2 * ((offset + length) % 32)

                # expand the memory word in a factitious way
                memory_word = trace_item["memory"][memory_word_id]

                trace_item["memory"][memory_word_id] = (
                    memory_word[:internal_offset] + "00" * (proper_length - length) + memory_word[internal_offset:]
                )
        except KeyError:
            raise StructLogError("StructLog has no stack")
        except (IndexError, TypeError):
            raise StructLogError("Malformed stack")

    return trace


def _find_fist_index_of_event_with_different_from_first_event_address(events):
    first_event_address = events[0].address
    for idx in range(len(events)):
        e = events[idx]
        if e.address != first_event_address:
            return idx
    return len(events)


def tx_events_from_receipt(tx: TransactionReceipt) -> List:
    if not tx.status:
        raise "Tx has reverted status (set to 0)"

    result = web3.provider.make_request("eth_getTransactionReceipt", [tx.txid])
    events = decode_logs(result["result"]["logs"], _topics, allow_undecoded=True)
    return [format_event(i) for i in events]


def tx_events_from_trace(tx: TransactionReceipt) -> Optional[List]:
    """
    Parse and build events list from transaction receipt

    Arguments
    ---------
    tx : TransactionReceipt
        Transaction receipt provided by brownie
    """
    if not tx.status:
        raise "Tx has reverted status (set to 0)"

    # Parsing events from trace.
    # Brownie uses that way for the reverted transactions only.
    # Contracts resolution by addr works pretty well.
    print(f"Parsing events from tx trace...", end="")
    tx._get_trace()
    trace = tx._raw_trace

    if not trace:
        return None

    # Seems like Ganache sometimes provides correct data
    # but incorrect data length for the LOG traces.
    # Force the length to be aligned to a 32-bytes boundary
    trace = _align_logdata_len(trace)

    initial_address = str(tx.receiver or tx.contract_address)

    events = decode_traceTransaction(trace, _topics, allow_undecoded=True, initial_address=initial_address)
    print(f" Done")

    return [format_event(i) for i in events]


def resolve_contract(addr: str) -> str:
    """
    Resolve contract name by provided address

    Arguments
    ---------
    addr : str
        Contract address
    """
    contract = state._find_contract(addr)
    if not contract:
        return ""
    try:
        return contract.name()
    except Exception:
        return contract._name


def get_event_group(event, contract_name, groups: List[GroupBy]) -> Optional[GroupBy]:
    for g in groups:
        if g.contract_name == contract_name and g.event_name == event.name:
            return g
    return None


def group_tx_events(
    events: Optional[List], dict_events: EventDict, groups: List[GroupBy]
) -> List[Annotated[Tuple[GroupBy, EventDict], 2]]:
    """
    Group events with provided markers

    Arguments
    ---------
    events : Optional[List]
        Raw transaction events (logs)
    dict_events : EventDict
        Repacked transaction events (logs)
    groups: [GroupBy]
        Event grouping markers
    """
    evs = list(dict_events)
    all_evs = events
    ret = []

    prev_grp: Optional[GroupBy] = None
    group_start_index = 0
    group_stop_index = -1
    while evs:
        first_event = evs[0]
        idx = _find_fist_index_of_event_with_different_from_first_event_address(evs)
        contract_name = resolve_contract(first_event.address)
        if contract_name == "":
            print(f"WARNING: cannot resolve contract name at {first_event.address}")

        event_names = []
        for event in evs[:idx]:
            event_names.append(event.name)

        current_grp = get_event_group(first_event, contract_name, groups)
        if current_grp is not None:
            if group_stop_index >= group_start_index:
                ret.append((prev_grp, EventDict(all_evs[group_start_index : group_stop_index + 1])))
                group_start_index = group_stop_index + 1
            prev_grp = current_grp

        evs = evs[idx:]
        group_stop_index += idx

    ret.append((prev_grp, EventDict(all_evs[group_start_index : group_stop_index + 1])))

    return ret


def display_tx_events(events: EventDict, title: str, groups: List[GroupBy]) -> None:
    """
    Display tx events registered during the transaction.
    Output data has a tree layout, the root node has 'title' text.

    Note: inspired by brownie.network.transaction{.call_trace, .info} methods
    Arguments
    ---------
    events : EventDict
        Transaction events (logs)
    title: str
        Tree root node text
    groups: [GroupBy]
        Event grouping markers
    """
    events = list(events)
    call_tree: List = [[f'{color("bright cyan")}{title}{color}']]
    active_tree: List = [call_tree[0]]
    counters = {}

    while events:
        first_event = events[0]
        idx = _find_fist_index_of_event_with_different_from_first_event_address(events)

        contract_name = resolve_contract(first_event.address)
        if contract_name:
            sub_tree: List = [f"{contract_name} ({first_event.address})"]
        else:
            print(f"WARNING: cannot resolve contract name at {first_event.address}")
            sub_tree = [f"{first_event.address}"]

        event_names = []
        for event in events[:idx]:
            sub_tree.append([event.name, *(f"{k}: {v}" for k, v in event.items())])
            event_names.append(event.name)

        current_grp = get_event_group(first_event, contract_name, groups)

        if current_grp is not None:
            if len(active_tree) > 1:
                active_tree.pop()

            counter_str = ""
            if current_grp.show_counter:
                if current_grp.group_title not in counters:
                    counters[current_grp.group_title] = 0
                counters[current_grp.group_title] += 1
                counter_str = counters[current_grp.group_title]
            active_tree[-1].append([f"{color(current_grp.color)}{current_grp.group_title}{counter_str}{color}"])
            active_tree.append(active_tree[-1][-1])

        active_tree[-1].append(sub_tree)

        events = events[idx:]

    event_tree = build_tree(call_tree, multiline_pad=0, pad_depth=[0, 1])
    result = f"{event_tree}"
    print(f"{result}")


def display_filtered_tx_call(tx: TransactionReceipt, filter_func: Callable[[Dict], bool] = lambda _: False) -> None:
    """
    Display the filtered sequence of contracts and methods called during
    the transaction. The format:
    Contract.functionName  [instruction]  start:stop  [gas used]
    * start:stop are index values for the `trace` member of this object,
      showing the points where the call begins and ends
    * for calls that include subcalls, gas use is displayed as
      [gas used in this frame / gas used in this frame + subcalls]
    * Calls displayed in red ended with a `REVERT` or `INVALID` instruction.

    Note: based on brownie.network.transaction.call_trace
    Arguments
    ---------
    filter_func : Callable[[Dict], bool]
        If filter_func returns `True` on current trace item, collapse it
    """
    trace = tx.trace
    key = _step_internal(trace[0], trace[-1], 0, len(trace), tx._get_trace_gas(0, len(tx.trace)))
    call_tree: List = [[key]]
    active_tree: List = [call_tree[0]]
    # (index, depth, jumpDepth) for relevant steps in the trace
    trace_index = [(0, 0, 0)] + [
        (i, trace[i]["depth"], trace[i]["jumpDepth"])
        for i in range(1, len(trace))
        if not _step_compare(trace[i], trace[i - 1])
    ]
    subcalls = tx.subcalls[::-1]
    # track filter state
    is_filter_active = False
    filter_index = trace_index[0]
    for i, (idx, depth, jump_depth) in enumerate(trace_index[1:], start=1):
        last = trace_index[i - 1]
        # check for the filter reset
        if is_filter_active:
            if depth < filter_index[1]:
                last = filter_index
                is_filter_active = False
            elif depth == filter_index[1] and jump_depth < filter_index[2]:
                last = filter_index
                is_filter_active = False
        if depth == last[1] and jump_depth < last[2]:
            # returning from an internal function, reduce tree by one
            if not is_filter_active:
                active_tree.pop()
            continue
        elif depth < last[1]:
            # returning from an external call, return tree by jumpDepth of the previous depth
            if not is_filter_active:
                active_tree = active_tree[: -(last[2] + 1)]
            continue
        need_filtering = filter_func(trace[idx])
        if depth > last[1]:
            # called to a new contract
            end = next((x[0] for x in trace_index[i + 1 :] if x[1] < depth), len(trace))
            total_gas, internal_gas = tx._get_trace_gas(idx, end)
            key = _step_external(
                trace[idx],
                trace[end - 1],
                idx,
                end,
                (total_gas, internal_gas),
                subcalls.pop(),
                not need_filtering,  # don't expand filtered items
            )
        elif depth == last[1] and jump_depth > last[2]:
            # jumped into an internal function
            end = next(
                (x[0] for x in trace_index[i + 1 :] if x[1] < depth or (x[1] == depth and x[2] < jump_depth)),
                len(trace),
            )
            total_gas, internal_gas = tx._get_trace_gas(idx, end)
            key = _step_internal(trace[idx], trace[end - 1], idx, end, (total_gas, internal_gas))
        # show [collapsed] remark for the filtered tree node
        if need_filtering:
            key += f"{color('magenta')} [collapsed]{color}"
        if not is_filter_active:
            active_tree[-1].append([key])
            active_tree.append(active_tree[-1][-1])
            if need_filtering:
                is_filter_active = True
                filter_index = trace_index[i]
    print(
        f"Call trace for '{color('bright blue')}{tx.txid}{color}':\n"
        f"Initial call cost  [{color('bright yellow')}{tx._call_cost} gas{color}]"
    )
    print(build_tree(call_tree).rstrip())
