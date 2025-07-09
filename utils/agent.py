from utils.config import network_name, contracts, AGENT
from utils.evm_script import (
    encode_call_script,
)
from typing import (
    Tuple,
    Optional,
    Sequence,
)


def agent_forward(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    agent = contracts.agent
    print(f"Forwarding call script to agent: {call_script}")
    return (AGENT, agent.forward.encode_input(encode_call_script(call_script)))

def extract_as_dg_admin_call(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    print(f"Extracting call script for dual governance admin: {call_script}")
    return (call_script[0][0], call_script[0][1])

def dual_governance_agent_forward(
    call_script: Sequence[Tuple],
    description: Optional[str] = "",
) -> Tuple[str, str]:
    dual_governance = contracts.dual_governance
    forwarded = []

    for _call in call_script:
        if len(_call) > 2 and _call[2] == True:
            forwarded.append(extract_as_dg_admin_call([_call]))
        else:
            forwarded.append(agent_forward([_call]))

    print(f"Forwarding call script to dual governance: {forwarded}")
    return (
        contracts.dual_governance.address,
        dual_governance.submitProposal.encode_input([(_call[0], 0, _call[1]) for _call in forwarded], description),
    )


def agent_execute(target: str, value: str, data: str) -> Tuple[str, str]:
    agent = contracts.agent
    return (AGENT, agent.execute.encode_input(target, value, data))
