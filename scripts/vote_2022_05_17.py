"""
Voting 17/05/2022.

1. Publishing new implementation in Lido app APM repo 0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1
2. Updating implementation of Lido app with the new one
3. Publishing new implementation in Node Operators Registry app APM repo 0x0D97E876ad14DB2b183CFeEB8aa1A5C788eB1831
4. Updating implementation of Node Operators Registry app with the new one
5. Publishing new implementation in Oracle app APM repo 0xF9339DE629973c60c4d2b76749c81E6F40960E3A
6. Updating implementation of Oracle app with new one
7. Call Oracle's finalizeUpgrade_v3() to update internal version counter
8. Create permission for SET_EL_REWARDS_VAULT_ROLE of Lido app
    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
9. Create permission for STAKING_CONTROL_ROLE of Lido app
    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
10. Set execution layer rewards vault to LidoExecutionLayerRewardsVault #? need address
11. Resume staking
12. Set staking limit rate to 150,000 ETH per day.

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.repo import (
    add_implementation_to_lido_app_repo,
    add_implementation_to_nos_app_repo,
    add_implementation_to_oracle_app_repo
)
from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts, network_name
)
from utils.permissions import encode_permission_create, encode_permission_grant
from utils.brownie_prelude import *

update_lido_app = {
    'new_address': None,  # TBA
    'content_uri': '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053',
    'id': '0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320',
    'version': (3, 0, 0),
    'execution_layer_rewards_vault_address': None,  # TBA
    'mevtxfee_withdrawal_limit': 2,
    'max_staking_limit': 150_000 * 10**18,
    'staking_limit_increase': 150_000 * 10**18 * 13.5 // (24 * 60 * 60),  # 13.5s per block as a rough average
}

update_nos_app = {
    'new_address': None,  # TBA
    'content_uri': '0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847',
    'id': '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d',
    'version': (3, 0, 0),
}

update_oracle_app = {
    'new_address': None,  # TBA
    'content_uri': '0x697066733a516d554d506669454b71354d786d387932475951504c756a47614a69577a31747665703557374564414767435238',
    'id': '0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93',
    'version': (3, 0, 0),
}

if network_name() in ("goerli", "goerli-fork"):
    update_lido_app['new_address'] = '0xb16876f11324Fbf02b9B294FBE307B3DB0C02DBB'
    update_lido_app['execution_layer_rewards_vault_address'] = '0x94750381bE1AbA0504C666ee1DB118F68f0780D4'
    update_lido_app['content_uri'] = '0x697066733a516d626d5057357239484d64795541524e4a6a6a45374d4e714255477258617368776f577671525a686331743562'
    update_lido_app['id'] = '0x79ac01111b462384f1b7fba84a17b9ec1f5d2fddcfcb99487d71b443832556ea'
    update_lido_app['version'] = (8, 0, 0)

    update_oracle_app['new_address'] = '0x7FDef26e3bBB8206135071A52e44f8460A243De5'
    update_oracle_app['content_uri'] = '0x697066733a516d66414348396f5348465767563831446838525356636761564264686b5a7548685a5932695a76357379424a4b'
    update_oracle_app['id'] = '0xb2977cfc13b000b6807b9ae3cf4d938f4cc8ba98e1d68ad911c58924d6aa4f11'
    update_oracle_app['version'] = (4, 0, 0)

    update_nos_app['new_address'] = '0xbb001978bD0d5b36D95c54025ac6a5822b2b1Aec'
    update_nos_app['content_uri'] = '0x697066733a516d5145784a6b6f7967377857584a6a4c615943373555416d7347593153545934315954473377454b3771386464'
    update_nos_app['id'] = '0x57384c8fcaf2c1c2144974769a6ea4e5cf69090d47f5327f8fc93827f8c0001a'
    update_nos_app['version'] = (6, 0, 0)


def encode_finalize_oracle_upgrade():
    oracle: interface.LidoOracle = contracts.lido_oracle

    if network_name() in ("goerli", "goerli-fork"):
        # we already have an upgraded oracle on goerli, so just do something harmless
        return oracle.address, oracle.appId.encode_input()

    return oracle.address, oracle.finalizeUpgrade_v3.encode_input()


def encode_set_elrewards_vault(vault_address: str) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido

    return lido.address, lido.setELRewardsVault.encode_input(vault_address)


def encode_set_elrewards_withdrawal_limit(limit_bp: int) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido

    return lido.address, lido.setELRewardsWithdrawalLimit.encode_input(limit_bp)


def encode_resume_staking() -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido

    return lido.address, lido.resumeStaking.encode_input()


def encode_set_staking_limit(max_limit: int, limit_increase_per_block: int) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido

    return lido.address, lido.setStakingLimit.encode_input(max_limit, limit_increase_per_block)


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    voting: interface.Voting = contracts.voting
    lido: interface.Lido = contracts.lido

    encoded_call_script = encode_call_script([
        # 1. Publishing new implementation in Lido app APM repo 0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1
        add_implementation_to_lido_app_repo(
            update_lido_app['version'],
            update_lido_app['new_address'],
            update_lido_app['content_uri']
        ),
        # 2. Updating implementation of Lido app with the new one
        update_app_implementation(
            update_lido_app['id'],
            update_lido_app['new_address']
        ),
        # 3. Publishing new implementation in Node Operators Registry app
        # APM repo 0x0D97E876ad14DB2b183CFeEB8aa1A5C788eB1831
        add_implementation_to_nos_app_repo(
            update_nos_app['version'],
            update_nos_app['new_address'],
            update_nos_app['content_uri']
        ),
        # 4. Updating implementation of Node Operators Registry app with the new one
        update_app_implementation(
            update_nos_app['id'],
            update_nos_app['new_address']
        ),
        # 5. Publishing new implementation in Oracle app APM repo 0xF9339DE629973c60c4d2b76749c81E6F40960E3A
        add_implementation_to_oracle_app_repo(
            update_oracle_app['version'],
            update_oracle_app['new_address'],
            update_oracle_app['content_uri']
        ),
        # 6. Updating implementation of Oracle app with new one
        update_app_implementation(
            update_oracle_app['id'],
            update_oracle_app['new_address']
        ),
        # 7. Finalize Oracle upgrade to version 3
        encode_finalize_oracle_upgrade(),
        # 8. Create permission for SET_EL_REWARDS_VAULT_ROLE of Lido app
        #    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        encode_permission_create(entity=voting, target_app=lido, permission_name='SET_EL_REWARDS_VAULT_ROLE',
                                 manager=voting),
        # 9. Create permission for STAKING_CONTROL_ROLE of Lido app
        #    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        encode_permission_create(entity=voting, target_app=lido, permission_name='STAKING_CONTROL_ROLE',
                                 manager=voting),

        # 10. Set execution layer rewards vault to LidoExecutionLayerRewardsVault
        encode_set_elrewards_vault(update_lido_app['execution_layer_rewards_vault_address']),
        # 11. Resume staking
        encode_resume_staking(),
        # 12. Set staking limit rate to 150,000 ETH per day.
        encode_set_staking_limit(update_lido_app['max_staking_limit'], update_lido_app['staking_limit_increase'])
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Publish new implementation in Lido app APM repo;',
            '2) Updating implementation of Lido app;',
            '3) Publishing new implementation in Node Operators Registry app APM repo;',
            '4) Updating implementation of Node Operators Registry app;',
            '5) Publishing new implementation in Oracle app APM repo;'
            '6) Updating implementation of Oracle app;',
            '7) Finalize Oracle upgrade to version 3;',
            '8) Create permission for SET_EL_REWARDS_VAULT_ROLE assigning it to Voting;',
            '9) Create permission for STAKING_CONTROL_ROLE of Lido app assigning it to Voting;',
            '10) Set execution layer rewards vault;',
            '11) Resume staking;',
            '12) Set staking limit rate to 150,000 ETH per day.',
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
