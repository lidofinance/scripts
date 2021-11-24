#!/usr/bin/python3

from typing import Callable, Dict

from brownie.network.transaction import TransactionReceipt
from brownie.network.transaction import _step_internal, _step_external, _step_compare
from brownie.utils import color
from brownie.utils.output import build_tree

def tx_call_trace_filtered(tx: TransactionReceipt, filter_func: Callable[[Dict], bool] = lambda _: False) -> None:
        """
        Display the filtered sequence of contracts and methods called during
        the transaction. The format:
        Contract.functionName  [instruction]  start:stop  [gas used]
        * start:stop are index values for the `trace` member of this object,
          showing the points where the call begins and ends
        * for calls that include subcalls, gas use is displayed as
          [gas used in this frame / gas used in this frame + subcalls]
        * Calls displayed in red ended with a `REVERT` or `INVALID` instruction.

        Based on brownie.network.transaction.call_trace
        Arguments
        ---------
        filter_func : Callable[[Dict], bool]
            If filter_func returns `True` on current trace item, collapse it
        """

        trace = tx.trace
        key = _step_internal(
            trace[0], trace[-1], 0, len(trace), tx._get_trace_gas(0, len(tx.trace))
        )

        call_tree: List = [[key]]
        active_tree: List = [call_tree[0]]

        # (index, depth, jumpDepth) for relevent steps in the trace
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
                    not need_filtering, # don't expand filtered items
                )

            elif depth == last[1] and jump_depth > last[2]:
                # jumped into an internal function
                end = next(
                    (
                        x[0]
                        for x in trace_index[i + 1 :]
                        if x[1] < depth or (x[1] == depth and x[2] < jump_depth)
                    ),
                    len(trace),
                )

                total_gas, internal_gas = tx._get_trace_gas(idx, end)
                key = _step_internal(
                    trace[idx], trace[end - 1], idx, end, (total_gas, internal_gas)
                )

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
