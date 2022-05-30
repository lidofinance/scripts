"""
Voting 31/05/2022.

TODO: rename grant to 

1. Create role RESUME_ROLE and grant to Voting
2. Create role STAKING_PAUSE_ROLE and grant to Voting
3. Create role SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE and grant to Voting
4. Set Execution Layer rewards withdrawal limit to 2BP

5. x Revoke DEPOSIT_ROLE from old DepositSecurityModule 0xDb149235B6F40dC08810AA69869783Be101790e7
6. x Grant DEPOSIT_ROLE to new DepositSecurityModule 0x710B3303fB508a84F10793c1106e32bE873C24cd
7. x Set lastDepositBlock of DepositSecurityModule to ???

8. Wrap stETH burner into the composite receiver
9. Attach composite receiver to lido oracle as beacon report callback
10. Revoke 'BURN_ROLE' permissions from Voting
11. Grant 'BURN_ROLE' constrained permissions to stETH burner

12. Create role MANAGE_PROTOCOL_CONTRACTS_ROLE and grant to Voting
13. Revoke SET_TREASURY from Voting
14. Revoke SET_INSURANCE_FUND from Voting
15. Revoke SET_ORACLE from Voting

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


def get_proposed_deposit_security_module_address():
    if network_name() in ('goerli', 'goerli-fork'):
        return '0x7DC1C1ff64078f73C98338e2f17D1996ffBb2eDe'
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return '0x710B3303fB508a84F10793c1106e32bE873C24cd'
    else:
        assert False, f'Unsupported network "{network_name()}"'


def get_last_deposit_block():
    if network_name() in ('goerli', 'goerli-fork'):
        return 123
    elif network_name() in ('mainnet', 'mainnet-fork'):
        assert False, 'TODO'
    else:
        assert False, f'Unsupported network "{network_name()}"'


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


def encode_set_last_deposit_block(last_deposit_block: int) -> Tuple[str, str]:
    deposit_security_module: interface.DepositSecurityModule = contracts.deposit_security_module
    return agent_forward([(
        deposit_security_module.address,
        deposit_security_module.setLastDepositBlock.encode_input(last_deposit_block)
    )])


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

    # proposed_deposit_security_module_address = get_proposed_deposit_security_module_address()
    # last_deposit_block = get_last_deposit_block()

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

        # # 5. Revoke DEPOSIT_ROLE from the old DepositSecurityModule
        # encode_permission_revoke(target_app=lido, permission_name='DEPOSIT_ROLE',
        #                          revoke_from=lido_dao_deposit_security_module_address),

        # # 6. Grant DEPOSIT_ROLE to the new DepositSecurityModule
        # encode_permission_grant(target_app=lido, permission_name='DEPOSIT_ROLE',
        #                         grant_to=proposed_deposit_security_module_address),

        # # TODO: fix
        # # 7. Set lastDepositBlock of DepositSecurityModule to ???
        # encode_set_last_deposit_block(last_deposit_block),

        # 8. Wrap stETH burner into the composite receiver
        encode_add_steth_burner_as_callback_to_composite_receiver(),

        # 9. Attach composite receiver to lido oracle as beacon report callback
        encode_attach_composite_receiver_to_oracle(),

        # 10. Revoke 'BURN_ROLE' permissions from Voting
        encode_permission_revoke(target_app=lido, permission_name='BURN_ROLE',
                                 revoke_from=get_burn_role_old_owner()),

        # 11. Grant 'BURN_ROLE' constrained permissions to stETH burner
        encode_permission_grant_p(target_app=lido, permission_name='BURN_ROLE',
                                  grant_to=lido_dao_self_owned_steth_burner,
                                  params=self_owned_burn_role_params()),

        # 12. Create role MANAGE_PROTOCOL_CONTRACTS_ROLE and grant to Voting
        encode_permission_create(entity=voting, target_app=lido, permission_name='MANAGE_PROTOCOL_CONTRACTS_ROLE',
                                 manager=voting),

        # 13. Revoke SET_TREASURY from Voting
        encode_permission_revoke(target_app=lido, permission_name='SET_TREASURY',
                                 revoke_from=voting),

        # 14. Revoke SET_INSURANCE_FUND from Voting
        encode_permission_revoke(target_app=lido, permission_name='SET_INSURANCE_FUND',
                                 revoke_from=voting),

        # 15. Revoke SET_ORACLE from Voting
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
            '5) x Revoke DEPOSIT_ROLE from the old DepositSecurityModule; ',
            '6) x Grant DEPOSIT_ROLE to the new DepositSecurityModule; ',
            '7) x Set lastDepositBlock of DepositSecurityModule to ???; ',
            '8) Wrap stETH burner into the composite receiver; ',
            '9) Attach composite receiver to lido oracle as beacon report callback; ',
            '10) Revoke BURN_ROLE permissions from Voting; ',
            '11) Grant BURN_ROLE constrained permissions to stETH burner; ',
            '12) Create role MANAGE_PROTOCOL_CONTRACTS_ROLE and grant to Voting; ',
            '13) Revoke SET_TREASURY from Voting; ',
            '14) Revoke SET_INSURANCE_FUND from Voting; ',
            '15) Revoke SET_ORACLE from Voting; ',
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
