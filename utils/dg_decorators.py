from typing import List, Optional, Sequence, Tuple, Dict
from utils.config import contracts, AGENT
from utils.agent import agent_forward
from utils.evm_script import encode_call_script

# ──────────────────────────────────────────────────────────────────────────
#  Constructors
# ──────────────────────────────────────────────────────────────────────────

def agent_forward(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    agent = contracts.agent
    print(f"Forwarding call script to agent: {call_script}")
    return (AGENT, agent.forward.encode_input(encode_call_script(call_script)))

def extract_as_dg_admin_call(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    print(f"Extracting call script for dual governance admin: {call_script}")
    return (call_script[0][0], call_script[0][1])

def _make_item(kind: str, address: str, data: str) -> Dict[str, str]:
    return {"type": kind, "address": address, "data": data}


def forward_agent(address: str, data: str) -> Dict[str, str]:
    return _make_item("agent", address, data)


def forward_dg_admin(address: str, data: str) -> Dict[str, str]:
    return _make_item("dg_admin", address, data)


def forward_voting(address: str, data: str) -> Dict[str, str]:
    return _make_item("voting", address, data)


# ──────────────────────────────────────────────────────────────────────────
#  Aggregator + order validation
# ──────────────────────────────────────────────────────────────────────────


def aggregate(
    entries: List[Tuple[str, Dict[str, str]]]
) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Checks the order rule and separates descriptions and scripts.

    Rule: `forward_voting` block(s) must be either before all other
    calls or after all other calls.
    """
    desc: List[str] = []
    scripts: List[Dict[str, str]] = []
    kinds: List[str] = []
    for d, s in entries:
        desc.append(d)
        scripts.append(s)
        kinds.append(s["type"])

    first_non_vote = next((i for i, k in enumerate(kinds) if k != "voting"), len(kinds))
    last_non_vote = (
        len(kinds) - 1 - next((i for i, k in enumerate(reversed(kinds)) if k != "voting"), len(kinds))
    )

    if any(k == "voting" for k in kinds[first_non_vote : last_non_vote + 1]):
        raise ValueError(
            "`forward_voting` calls can appear only before all other calls or after them"
        )

    return desc, scripts


# ──────────────────────────────────────────────────────────────────────────
#  Splitter for execution
# ──────────────────────────────────────────────────────────────────────────


def split_agent_dg_vs_voting(
    descriptions: List[str], scripts: List[Dict[str, str]]
) -> Tuple[List[Tuple[str, Dict[str, str]]], List[Dict[str, str]]]:
    """
    Forms two arrays:

    1) a list of tuples ``(description, script)`` for calls to
       `forward_agent` and `forward_dg_admin`;
    2) a list of scripts for `forward_voting`.
    """
    agent_dg: List[Tuple[str, Dict[str, str]]] = []
    voting: List[Dict[str, str]] = []

    for d, s in zip(descriptions, scripts):
        if s["type"] == "voting":
            voting.append((d, s))
        else:
            agent_dg.append((d, s))

    return agent_dg, voting


# ──────────────────────────────────────────────────────────────────────────
#  Combined processing
# ──────────────────────────────────────────────────────────────────────────


def process_voting_items(
    entries: List[Tuple[str, Dict[str, str]]]
) -> dict:
    """
    Combines `aggregate` and `split_agent_dg_vs_voting`.
    """

    desc, scripts = aggregate(entries)

    dg_items, voting_items = split_agent_dg_vs_voting(desc, scripts)

    dg_desc = "\n".join(d for d, s in dg_items)
    call_script_items = [s for d, s in dg_items]
    dg_vote = dual_governance_agent_forward(call_script_items, dg_desc)
    voting_items = {desc: (meta["address"], meta["data"]) for desc, meta in voting_items}

    vote_items = {dg_desc: dg_vote, **voting_items}
    return vote_items


def dual_governance_agent_forward(
    call_script: Sequence[Dict[str, str]],
    description: Optional[str] = "",
) -> Tuple[str, str]:
    dual_governance = contracts.dual_governance

    proposal_actions = []
    for s in call_script:
        print(f"Processing script item: {s}")
        if s["type"] == "dg_admin":
            addr, data = s["address"], s["data"]
            proposal_actions.append((addr, 0, data))
        else:  # 'agent'
            call = [(s["address"], s["data"])]
            result = agent_forward(call)
            addr, data = result[0], result[1]
            proposal_actions.append((addr, 0, data))

    print(f"Forwarding call script to dual governance: {proposal_actions}")
    return (
        contracts.dual_governance.address,
        dual_governance.submitProposal.encode_input(proposal_actions, description),
    )

