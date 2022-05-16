"""
Voting 17/05/2022.

1. Publishing new implementation in Lido app APM repo 0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1
2. Updating implementation of Lido app with the new one
3. Publishing new implementation in Node Operators Registry app APM repo 0x0D97E876ad14DB2b183CFeEB8aa1A5C788eB1831
4. Updating implementation of Node Operators Registry app with the new one
5. Publishing new implementation in Oracle app APM repo 0xF9339DE629973c60c4d2b76749c81E6F40960E3A
6. Updating implementation of Oracle app with new one
7. Call Oracle's finalizeUpgrade_v3() to update internal version counter
8. Create permission for SET_MEV_TX_FEE_VAULT_ROLE of Lido app
    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
9. Create permission for SET_MEV_TX_FEE_WITHDRAWAL_LIMIT_ROLE of Lido app
    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
10. Create permission for STAKING_RESUME_ROLE of Lido app
    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
11. Call Lido's setMevTxFeeVault() to connect deployed MevTxFeeVault #? need address
12. Set MevTxFee Withdrawal Limit to 2BP
13. Resume staking with rate limit roughly equal to 150,000 ETH per day

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
    'new_address': '0xC7B5aF82B05Eb3b64F12241B04B2cF14469E39F7', # TBA
    'content_uri': '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053',
    'id': '0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320',
    'version': (3, 0, 0),
    'mevtxfee_vault_address': '0xC7B5aF82B05Eb3b64F12241B04B2cF14469E39F7',  # TBA
    'mevtxfee_withdrawal_limit': 2,
    'max_staking_limit': 150_000 * 10**18,
    'staking_limit_increase': 150_000 * 10**18 * 13.5 // (24 * 60 * 60),  # 13.5s per block as a rough average
}

update_nos_app = {
    'new_address': '0xec3567ae258639a0FF5A02F7eAF4E4aE4416C5fe', # TBA
    'content_uri': '0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847',
    'id': '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d',
    'version': (3, 0, 0),
}

update_oracle_app = {
    'new_address': '0xADa6E33aa65590934870bFD204Fe8efe9c6Aa4bC', # TBA
    'content_uri': '0x697066733a516d514d64696979653134765966724a7753594250646e68656a446f62417877584b72524e45663438735370444d',
    'id': '0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93',
    'version': (3, 0, 0),
}

if network_name() in ("goerli", "goerli-fork"):
    update_lido_app['new_address'] = '0xb496DF40497Dd69c095470956b6A04cEF68fd50D'
    update_lido_app['mevtxfee_vault_address'] = '0x5bA8C245E8aED7b676F2c3B74aa0a3204cB53196'
    update_lido_app['content_uri'] = '0x697066733a516d626d5057357239484d64795541524e4a6a6a45374d4e714255477258617368776f577671525a686331743562'
    update_lido_app['id'] = '0x79ac01111b462384f1b7fba84a17b9ec1f5d2fddcfcb99487d71b443832556ea'
    update_lido_app['version'] = (8, 0, 0)

    update_oracle_app['new_address'] = '0xfD7e9d4Db932c576bFd8A596894698bDDdA29175'
    update_oracle_app['content_uri'] = '0x697066733a516d66414348396f5348465767563831446838525356636761564264686b5a7548685a5932695a76357379424a4b'
    update_oracle_app['id'] = '0xb2977cfc13b000b6807b9ae3cf4d938f4cc8ba98e1d68ad911c58924d6aa4f11'
    update_oracle_app['version'] = (4, 0, 0)

    update_nos_app['new_address'] = '0x779a5964BAC356142622Df28Ee1Ef99F27A1CD2d'
    update_nos_app['content_uri'] = '0x697066733a516d5145784a6b6f7967377857584a6a4c615943373555416d7347593153545934315954473377454b3771386464'
    update_nos_app['id'] = '0x57384c8fcaf2c1c2144974769a6ea4e5cf69090d47f5327f8fc93827f8c0001a'
    update_nos_app['version'] = (6, 0, 0)


def encode_finalize_oracle_upgrade():
    oracle: interface.LidoOracle = contracts.lido_oracle

    if network_name() in ("goerli", "goerli-fork"):
        # we already have an upgraded oracle on goerli, so just do something harmless
        return oracle.address, oracle.appId.encode_input()

    return oracle.address, oracle.finalizeUpgrade_v3.encode_input()


def encode_set_mevtxfee_vault(vault_address: str) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido

    return lido.address, lido.setMevTxFeeVault.encode_input(vault_address)


def encode_set_mevtxfee_withdrawal_limit(limit_bp: int) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido

    return lido.address, lido.setMevTxFeeWithdrawalLimit.encode_input(limit_bp)


def encode_resume_staking(max_limit: int, limit_increase_per_block: int) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido

    return lido.address, lido.resumeStaking.encode_input(max_limit, limit_increase_per_block)


def encode_permission_create_or_grant(permission_name: str) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido
    voting: interface.Voting = contracts.voting

    if network_name() in ("goerli", "goerli-fork"):
        return encode_permission_grant(lido, permission_name, voting)
    else:
        return encode_permission_create(voting, lido, permission_name, voting)


def inject_contracts(lido, nos, oracle, mev_vault):
    update_lido_app['new_address'] = lido
    update_lido_app['mevtxfee_vault_address'] = mev_vault
    update_nos_app['new_address'] = nos
    update_oracle_app['new_address'] = oracle


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
        # 8. Create permission for SET_MEV_TX_FEE_VAULT_ROLE of Lido app
        #    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        encode_permission_create_or_grant(permission_name='SET_MEV_TX_FEE_VAULT_ROLE'),
        # 9. Create permission for SET_MEV_TX_FEE_WITHDRAWAL_LIMIT_ROLE of Lido app
        #    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        encode_permission_create(entity=voting, target_app=lido, permission_name='SET_MEV_TX_FEE_WITHDRAWAL_LIMIT_ROLE',
                                 manager=voting),
        # 10. Create permission for STAKING_RESUME_ROLE of Lido app
        #    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        encode_permission_create(entity=voting, target_app=lido, permission_name='STAKING_RESUME_ROLE', manager=voting),

        # 11. Call Lido's setMevTxFeeVault() to connect deployed MevTxFeeVault
        encode_set_mevtxfee_vault(update_lido_app['mevtxfee_vault_address']),
        # 12. Set MevTxFee Withdrawal Limit to 2BP
        encode_set_mevtxfee_withdrawal_limit(update_lido_app['mevtxfee_withdrawal_limit']),
        # 13. Resume staking with rate limit roughly equal to 150,000 ETH per day
        encode_resume_staking(update_lido_app['max_staking_limit'], update_lido_app['staking_limit_increase'])
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Publish new implementation in Lido app APM repo;',
            '2) Updating implementation of Lido app with the new one;',
            '3) Publishing new implementation in Node Operators Registry app APM repo;',
            '4) Updating implementation of Node Operators Registry app with the new one;',
            '5) Publishing new implementation in Oracle app APM repo;'
            '6) Updating implementation of Oracle app with new one;',
            '7) Finalize Oracle upgrade to version 3;',
            '8) Create permission for SET_MEV_TX_FEE_VAULT_ROLE assigning it to Voting;',
            '9) Create permission for SET_MEV_TX_FEE_WITHDRAWAL_LIMIT_ROLE assigning it to Voting;',
            '10) Create permission for STAKING_RESUME_ROLE of Lido app assigning it to Voting;',
            '11) Call setMevTxFeeVault() to connect deployed MevTxFeeVault to Lido;',
            '12) Set MevTxFee Withdrawal Limit to 2BP;',
            '13) Resume staking with rate limit roughly equal to 150,000 ETH per day.'
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
