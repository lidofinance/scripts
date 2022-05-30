"""
Voting 31/05/2022.

1. Create role RESUME_ROLE and grant to Voting
2. Create role STAKING_PAUSE_ROLE and grant to Voting
3. Create role SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE and grant to Voting
4. Set Execution Layer rewards withdrawal limit to 2BP

5. Wrap stETH burner into the composite receiver
6. Attach composite receiver to lido oracle as beacon report callback
7. Revoke 'BURN_ROLE' permissions from Voting
8. Grant 'BURN_ROLE' constrained permissions to stETH burner

9. Create role MANAGE_PROTOCOL_CONTRACTS_ROLE and grant to Voting
10. Revoke SET_TREASURY from Voting
11. Revoke SET_INSURANCE_FUND from Voting
12. Revoke SET_ORACLE from Voting

"""

import time

from typing import (Dict, Tuple, Optional, List)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.agent import agent_forward

from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts, network_name,
    lido_dao_self_owned_steth_burner,
    lido_dao_composite_post_rebase_beacon_receiver,
    lido_dao_voting_address
)
from utils.permissions import encode_permission_create, encode_permission_grant_p, encode_permission_revoke
from utils.permission_parameters import Param, Op, ArgumentValue
# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


def get_burn_role_old_owner():
    if network_name() in ('goerli', 'goerli-fork'):
        return '0xf6a64DcB06Ef7eB1ee94aDfD7D10ACB44D9A9888'
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return lido_dao_voting_address
    else:
        assert False, f'Unsupported network "{network_name()}"'


def encode_set_elrewards_withdrawal_limit(limit_bp: int) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido
    return lido.address, lido.setELRewardsWithdrawalLimit.encode_input(limit_bp)


def encode_add_steth_burner_as_callback_to_composite_receiver() -> Tuple[str, str]:
    composite_receiver: interface.CompositePostRebaseBeaconReceiver = contracts.composite_post_rebase_beacon_receiver
    return (
        composite_receiver.address,
        composite_receiver.addCallback.encode_input(lido_dao_self_owned_steth_burner)
    )


def encode_attach_composite_receiver_to_oracle() -> Tuple[str, str]:
    oracle: interface.LidoOracle = contracts.lido_oracle
    return (
        oracle.address,
        oracle.setBeaconReportReceiver.encode_input(lido_dao_composite_post_rebase_beacon_receiver)
    )


def self_owned_burn_role_params() -> List[Param]:
    # Role params bytes taken from lido-dao, 25-vote-self-owned-steth-burner.js for reference:
    # 0x000100000000000000000000B280E33812c0B09353180e92e27b8AD399B07f26
    account_arg_index = 0
    return [
        Param(account_arg_index, Op.EQ, ArgumentValue(lido_dao_self_owned_steth_burner))
    ]



def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    voting: interface.Voting = contracts.voting
    lido: interface.Lido = contracts.lido

    encoded_call_script = encode_call_script([
        # 1. Create role RESUME_ROLE and grant to Voting 
        encode_permission_create(entity=voting, target_app=lido, permission_name='RESUME_ROLE',
                                 manager=voting),

        # 2. Create role STAKING_PAUSE_ROLE and grant to Voting
        encode_permission_create(entity=voting, target_app=lido, permission_name='STAKING_PAUSE_ROLE',
                                 manager=voting),

        # 3. Create role SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE and grant to Voting
        encode_permission_create(entity=voting, target_app=lido, permission_name='SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE',
                                 manager=voting),

        # 4. Set Execution Layer rewards withdrawal limit to 2BP
        encode_set_elrewards_withdrawal_limit(2),

        # 5. Wrap stETH burner into the composite receiver
        encode_add_steth_burner_as_callback_to_composite_receiver(),

        # 6. Attach composite receiver to lido oracle as beacon report callback
        encode_attach_composite_receiver_to_oracle(),

        # 7. Revoke 'BURN_ROLE' permissions from Voting
        encode_permission_revoke(target_app=lido, permission_name='BURN_ROLE',
                                 revoke_from=get_burn_role_old_owner()),

        # 8. Grant 'BURN_ROLE' constrained permissions to stETH burner
        encode_permission_grant_p(target_app=lido, permission_name='BURN_ROLE',
                                  grant_to=lido_dao_self_owned_steth_burner,
                                  params=self_owned_burn_role_params()),

        # 9. Create role MANAGE_PROTOCOL_CONTRACTS_ROLE and grant to Voting
        encode_permission_create(entity=voting, target_app=lido, permission_name='MANAGE_PROTOCOL_CONTRACTS_ROLE',
                                 manager=voting),

        # 10. Revoke SET_TREASURY from Voting
        encode_permission_revoke(target_app=lido, permission_name='SET_TREASURY',
                                 revoke_from=voting),

        # 11. Revoke SET_INSURANCE_FUND from Voting
        encode_permission_revoke(target_app=lido, permission_name='SET_INSURANCE_FUND',
                                 revoke_from=voting),

        # 12. Revoke SET_ORACLE from Voting
        encode_permission_revoke(target_app=lido, permission_name='SET_ORACLE',
                                 revoke_from=voting),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Create role RESUME_ROLE and grant to Voting; ',
            '2) Create role STAKING_PAUSE_ROLE and grant to Voting; ',
            '3) Create role SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE and grant to Voting; ',
            '4) Set Execution Layer rewards withdrawal limit to 2BP; ',
            '5) Wrap stETH burner into the composite receiver; ',
            '6) Attach composite receiver to lido oracle as beacon report callback; ',
            '7) Revoke BURN_ROLE permissions from Voting; ',
            '8) Grant BURN_ROLE constrained permissions to stETH burner; ',
            '9) Create role MANAGE_PROTOCOL_CONTRACTS_ROLE and grant to Voting; ',
            '10) Revoke SET_TREASURY from Voting; ',
            '11) Revoke SET_INSURANCE_FUND from Voting; ',
            '12) Revoke SET_ORACLE from Voting; ',
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    tx_params = {'from': get_deployer_account()}

    if get_is_live():
        tx_params['max_fee'] = '300 gwei'
        tx_params['priority_fee'] = '2 gwei'

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
