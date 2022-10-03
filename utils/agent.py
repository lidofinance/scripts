from utils.config import contracts
from utils.config import lido_dao_agent_address
from utils.evm_script import (
    encode_call_script,
)
from typing import (
    Tuple,
    Sequence,
)


def agent_forward(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    agent = contracts.agent
    return (
        lido_dao_agent_address,
        agent.forward.encode_input(
            encode_call_script(call_script)
        )
    )


def agent_exacute(target: str, value_in_wei: int, call_data: str):
    agent = contracts.agent
    return (
        lido_dao_agent_address,
        agent.execute.encode_input(
            target,
            value_in_wei,
            call_data
        )
    )
