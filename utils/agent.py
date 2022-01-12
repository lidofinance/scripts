from typing import Tuple
from utils.config import contracts
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
