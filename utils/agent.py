from utils.config import contracts
from utils.config import AGENT
from utils.evm_script import (
    encode_call_script,
)
from typing import (
    Tuple,
    Sequence,
)


def agent_forward(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    agent = contracts.agent
    return (AGENT, agent.forward.encode_input(encode_call_script(call_script)))


def agent_execute(target: str, value: str, data: str) -> Tuple[str, str]:
    agent = contracts.agent
    return (AGENT, agent.execute.encode_input(target, value, data))
