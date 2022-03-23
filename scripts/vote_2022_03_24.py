"""
Voting 24/03/2022.

1. Add AddRewardProgram 0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51 factory to Easy Track
2. Add RemoveRewardProgram 0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C factory to Easy Track
3. Add TopUpRewardPrograms 0x54058ee0E0c87Ad813C002262cD75B98A7F59218 factory to Easy Track
4. Send 350,000 LDO to 0x3A043ce95876683768D3D3FB80057be2ee3f2814 for Hyperelliptic & RockX
   team for Lido-on-Avalanache comps
5. Pass ownership of the 1inch rewarder 0xf5436129Cf9d8fa2a1cb6e591347155276550635
   to TokensRecoverer 0x...
6. Recover LDO funds from the 1inch rewarder 0xf5436129cf9d8fa2a1cb6e591347155276550635
   to DAO Agent

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie import RewardsManagerTokensRecoverer
from brownie.network.transaction import TransactionReceipt

from utils.agent import agent_forward
from utils.finance import make_ldo_payout
from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.config import get_deployer_account, contracts, get_is_live
from utils.easy_track import add_evmscript_factory, create_permissions

from utils.brownie_prelude import *

def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    finance = contracts.finance
    ldo_token = contracts.ldo_token

    reward_programs_registry = interface.RewardProgramsRegistry('0xfCaD241D9D2A2766979A2de208E8210eDf7b7D4F')
    rewards_manager = interface.RewardsManager('0xf5436129Cf9d8fa2a1cb6e591347155276550635')
    tokens_recoverer = RewardsManagerTokensRecoverer.at('0x1bdfFe0EBef3FEAdF2723D3330727D73f538959C')

    encoded_call_script = encode_call_script([
        # 1. Add AddRewardProgram 0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51 factory to Easy Track
        add_evmscript_factory(
            factory='0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51',
            permissions=create_permissions(reward_programs_registry, 'addRewardProgram')
        ),
        # 2. Add RemoveRewardProgram 0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C factory to Easy Track
        add_evmscript_factory(
            factory='0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C',
            permissions=create_permissions(reward_programs_registry, 'removeRewardProgram')
        ),
        # 3. Add TopUpRewardPrograms 0x54058ee0E0c87Ad813C002262cD75B98A7F59218 factory to Easy Track
        add_evmscript_factory(
            factory='0x54058ee0E0c87Ad813C002262cD75B98A7F59218',
            permissions=create_permissions(finance, 'newImmediatePayment')
        ),
        # 4. Send 350,000 LDO to 0x3A043ce95876683768D3D3FB80057be2ee3f2814 for Hyperelliptic & RockX team for Lido-on-Avalanache comps
        make_ldo_payout(
            target_address='0x3A043ce95876683768D3D3FB80057be2ee3f2814',
            ldo_in_wei=350_000 * (10 ** 18),
            reference="Hyperelliptic & RockX team for Lido-on-Avalanache comps"
        ),
        # 5. Pass ownership of the 1inch rewarder 0xf5436129Cf9d8fa2a1cb6e591347155276550635
        # to the TokensRecoverer 0x...
        agent_forward([
             (
                 rewards_manager.address,
                 rewards_manager.transfer_ownership.encode_input(tokens_recoverer.address)
             )
        ]),
        # 6. Recover LDO funds from 1inch reward contract 0xf5436129cf9d8fa2a1cb6e591347155276550635
        # to DAO Agent
        (
            tokens_recoverer.address,
            tokens_recoverer.recover.encode_input(
                rewards_manager.address,
                ldo_token.address,
                50_000 * 10 ** 18
            )
        )
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1. Add AddRewardProgram 0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51 factory to Easy Track;'
            '2. Add RemoveRewardProgram 0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C factory to Easy Track;'
            '3. Add TopUpRewardPrograms 0x54058ee0E0c87Ad813C002262cD75B98A7F59218 factory to Easy Track;'
            '4. Send 350,000 LDO to 0x3A043ce95876683768D3D3FB80057be2ee3f2814 for Hyperelliptic & RockX team;'
            '5. Pass ownership of the 1inch rewarder 0xf5436129Cf9d8fa2a1cb6e591347155276550635 to TokensRecoverer;'
            '6. Recover LDO funds from the 1inch rewarder 0xf5436129cf9d8fa2a1cb6e591347155276550635 to DAO Agent.'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )

def main():
    tx_params = { 'from': get_deployer_account() }
    if get_is_live():
        tx_params['max_fee'] = '300 gwei'
        tx_params['priority_fee'] = '2 gwei'

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
