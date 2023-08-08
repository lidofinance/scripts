from typing import List

#!/usr/bin/python3

# Check that all tx_events contained in reference_events (with proper ordering and occurrences count).
# Allow some of the reference_events skipped in the tx_events.
#
# Examples:
#
# tx_events: ['A', 'B', 'C'], reference_events: ['A', 'B', 'C'] => valid
# tx_events: ['A', 'B', 'D'], reference_events: ['A', 'B', 'C', 'D'] => valid
#
# tx_events: ['A', 'B', 'D'], reference_events: ['A', 'B', 'C'] => invalid // extra 'D' event
# tx_events: ['A', 'B', 'A', 'B'], reference_events: ['A', 'B'] => invalid // duplicated 'A', 'B' events chain
# tx_events: ['A', 'C', 'B'], reference_events: ['A', 'B', 'C'] => invalid // wrong order
def validate_events_chain(tx_events: List[str], reference_events: List[str]):
    for ev in tx_events:
        idx = next((reference_events.index(e) for e in reference_events if e == ev), len(reference_events))
        assert idx != len(reference_events), f"{ev} not found in the remaining {reference_events} events chain"
        reference_events = reference_events[idx + 1 :]
