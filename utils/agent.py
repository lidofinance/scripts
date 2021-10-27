from typing import Tuple
from utils.config import (
    lido_dao_agent_address,
)
from utils.evm_script import (
    encode_call_script,
)
from typing import (
    Tuple,
    Sequence,
)

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )

def agent_forward(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    agent = interface.Agent(lido_dao_agent_address)
    return (
        lido_dao_agent_address,
        agent.forward.encode_input(
            encode_call_script(call_script)
        )
    )
