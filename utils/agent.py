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
    return (AGENT, agent.forward.encode_input(encode_call_script(call_script)))


def dual_governance_agent_forward(
    call_script: Sequence[Tuple[str, str]],
    description: Optional[str] = "",
) -> Tuple[str, str]:

    ## TODO: move up the scope when mainnet configuration for DG is updated
    from utils.config import DUAL_GOVERNANCE

    dual_governance = contracts.dual_governance
    (agent_address, agent_calldata) = agent_forward(call_script)
    return (
        contracts.dual_governance.address,
        dual_governance.submitProposal.encode_input([(agent_address, 0, agent_calldata)], description),
    )


def agent_execute(target: str, value: str, data: str) -> Tuple[str, str]:
    agent = contracts.agent
    return (AGENT, agent.execute.encode_input(target, value, data))
