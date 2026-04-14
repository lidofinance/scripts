"""
Vote 2026_04_08

=== 1. DG PROPOSAL ===
1.1. Deactivate Node Operator A41 (id = 32) in Curated Module 0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5
1.2. Change name to Stakin by The Tie for Node Operator Stakin (id = 14) in Curated Module 0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5
1.3. Change reward address to 0x3e97EC699191bEfc63EF4E4275204B03E7465f30 for Node Operator Stakin (id = 14) in Curated Module 0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5
1.4. Upgrade LazyOracle proxy 0x5DB427080200c235F2Ae8Cd17A7be87921f7AD6c implementation to 0x96c9a897D116ef660086d3aA67b3af653324aB37
1.5. Upgrade VaultHub proxy 0x1d201BE093d847f6446530Efb0E8Fb426d176709 implementation to 0x6330fE7756FBE8649adfb9A541d61C5edB8B4D70
1.6. Upgrade ZKSync L1ERC20Bridge proxy 0x41527B2d03844dB6b0945f25702cB958b6d55989 implementation to 0x43a66b32c9adca1a59b273e69b61da5197c21ccd
1.7. Call enableDeposits on ZKSync L1ERC20Bridge proxy 0x41527B2d03844dB6b0945f25702cB958b6d55989
1.8. Remove Chorus One member 0x285f8537e1daeedaf617e96c742f2cf36d63ccfb from Accounting Oracle HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.9. Remove Chorus One member 0x285f8537e1daeedaf617e96c742f2cf36d63ccfb from CSM Oracle HashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.10. Remove Chorus One member 0x285f8537e1daeedaf617e96c742f2cf36d63ccfb from VEB Oracle HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.11. Add new Chorus One member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 to Accounting Oracle HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.12. Add new Chorus One member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 to CSM Oracle HashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.13. Add new Chorus One member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 to VEB Oracle HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.14. Remove Stakefish member 0x946D3b081ed19173dC83Cd974fC69e1e760B7d78 from Accounting Oracle HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.15. Remove Stakefish member 0x946D3b081ed19173dC83Cd974fC69e1e760B7d78 from CSM Oracle HashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.16. Remove Stakefish member 0x946D3b081ed19173dC83Cd974fC69e1e760B7d78 from VEB Oracle HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.17. Add new Stakefish member 0x042a9e5acCfa17e28300F1b5967f20891E973922 to Accounting Oracle HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.18. Add new Stakefish member 0x042a9e5acCfa17e28300F1b5967f20891E973922 to CSM Oracle HashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.19. Add new Stakefish member 0x042a9e5acCfa17e28300F1b5967f20891E973922 to VEB Oracle HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.20. Set soft-mode target validators limit to 0 for Node Operator Chorus One (ID = 3) in Curated Module (MODULE_ID = 1) in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
1.21. Decrease limit from 1000 to 150 stETH per 12 months on Gas Supply AllowedRecipientsRegistry 0x49d1363016aA899bba09ae972a1BF200dDf8C55F
1.22. Set spent amount to 0 on Gas Supply AllowedRecipientsRegistry 0x49d1363016aA899bba09ae972a1BF200dDf8C55F
1.23. Raise CSM (MODULE_ID = 3) stake share limit from 750 BP to 850 BP and priority exit threshold from 900 BP to 1020 BP in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
1.24. Remove old Stakefish address 0xd4EF84b638B334699bcf5AF4B0410B8CCD71943f from Deposit Security Module 0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD and keep quorum size as 4
1.25. Add new Stakefish address 0x4B87F16B8d32cb5a859a4C48a88edB5adBe3498E to Deposit Security Module 0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD and keep quorum size as 4

=== NON-DG ITEMS ===
2. Remove old Simple DVT SubmitValidatorsExitRequestHashes factory 0xB7668B5485d0f826B86a75b0115e088bB9ee03eE from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
3. Remove old Curated Module SubmitValidatorsExitRequestHashes factory 0x8aa34dAaF0fC263203A15Bcfa0Ed926D466e59F3 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
4. Add new Simple DVT SubmitValidatorsExitRequestHashes factory 0x58A59dDC6Aea9b1D5743D024E15DfA4badB56E37 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: ValidatorsExitBusOracle.submitExitRequestsHash 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6eb1b19f57)
5. Add new Curated Module SubmitValidatorsExitRequestHashes factory 0x4F716AD3Cc7A3A5cdA2359e5B2c84335c171dCde to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: ValidatorsExitBusOracle.submitExitRequestsHash 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6eb1b19f57)
6. Remove old RegisterGroupsInOperatorGrid factory 0xE73842AEbEC99Dacf2aAEec61409fD01A033f478 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
7. Remove old RegisterTiersInOperatorGrid factory 0x5292A1284e4695B95C0840CF8ea25A818751C17F from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
8. Remove old AlterTiersInOperatorGrid factory 0x73f80240ad9363d5d3C5C3626953C351cA36Bfe9 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
9. Add new RegisterGroupsInOperatorGrid factory 0x17305dB55c908e84C58BbDCa57258A7D1f7eEa7c to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: operatorGrid.registerGroup, operatorGrid.registerTiers 0xc69685e89cefc327b43b7234ac646451b27c544de37a7c0bc69685e89cefc327b43b7234ac646451b27c544d552b91da)
10. Add new RegisterTiersInOperatorGrid factory 0x6b535F441F95046562406F4E2518D9AD7Db2dc0D to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: operatorGrid.registerTiers 0xc69685e89cefc327b43b7234ac646451b27c544d552b91da)
11. Add new AlterTiersInOperatorGrid factory 0x37d9B09EDA477a84E3913fCB4d032EFb0BF9B62E to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: operatorGrid.alterTiers 0xc69685e89cefc327b43b7234ac646451b27c544d54544bcb)

Vote passed & executed on Apr-13-2026 04:40:47 PM UTC, block #24872110.
"""

from typing import Dict, List, Tuple

from brownie import interface

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from utils.agent import agent_forward
from utils.dsm import encode_remove_guardian, encode_add_guardian
from utils.easy_track import add_evmscript_factory, remove_evmscript_factory, create_permissions
from utils.node_operators import (
    deactivate_node_operator,
    encode_set_node_operator_name,
    encode_set_node_operator_reward_address,
)
from utils.allowed_recipients_registry import set_limit_parameters, unsafe_set_spent_amount


# ============================== Addresses ===================================
STAKIN_REWARD_ADDRESS_NEW = "0x3e97EC699191bEfc63EF4E4275204B03E7465f30"

CURATED_MODULE = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
OPERATOR_GRID = "0xC69685E89Cefc327b43B7234AC646451B27c544d"
VEBO = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"

LAZY_ORACLE_PROXY = "0x5DB427080200c235F2Ae8Cd17A7be87921f7AD6c"
LAZY_ORACLE_IMPL_NEW = "0x96c9a897D116ef660086d3aA67b3af653324aB37"

VAULT_HUB_PROXY = "0x1d201BE093d847f6446530Efb0E8Fb426d176709"
VAULT_HUB_IMPL_NEW = "0x6330fE7756FBE8649adfb9A541d61C5edB8B4D70"

ZKSYNC_L1_ERC20_BRIDGE = "0x41527B2d03844dB6b0945f25702cB958b6d55989"
ZKSYNC_L1_ERC20_BRIDGE_IMPL_NEW = "0x43a66b32c9adca1a59b273e69b61da5197c21ccd"

CHORUS_ONE_ORACLE_MEMBER_OLD = "0x285f8537e1daeedaf617e96c742f2cf36d63ccfb"
CHORUS_ONE_ORACLE_MEMBER_NEW = "0x8dB977C13CAA938BC58464bFD622DF0570564b78"

STAKEFISH_ORACLE_MEMBER_OLD = "0x946D3b081ed19173dC83Cd974fC69e1e760B7d78"
STAKEFISH_ORACLE_MEMBER_NEW = "0x042a9e5acCfa17e28300F1b5967f20891E973922"

HASH_CONSENSUS_FOR_AO = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
CS_HASH_CONSENSUS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"
HASH_CONSENSUS_FOR_VEBO = "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"

DEPOSIT_SECURITY_MODULE = "0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD"

STAKEFISH_DSM_GUARDIAN_OLD = "0xd4EF84b638B334699bcf5AF4B0410B8CCD71943f"
STAKEFISH_DSM_GUARDIAN_NEW = "0x4B87F16B8d32cb5a859a4C48a88edB5adBe3498E"
DSM_QUORUM_SIZE = 4

GAS_SUPPLY_ALLOWED_RECIPIENTS_REGISTRY = "0x49d1363016aA899bba09ae972a1BF200dDf8C55F"

OLD_SDVT_SUBMIT_EXIT_HASHES_FACTORY = "0xB7668B5485d0f826B86a75b0115e088bB9ee03eE"
OLD_CURATED_SUBMIT_EXIT_HASHES_FACTORY = "0x8aa34dAaF0fC263203A15Bcfa0Ed926D466e59F3"
NEW_SDVT_SUBMIT_EXIT_HASHES_FACTORY = "0x58A59dDC6Aea9b1D5743D024E15DfA4badB56E37"
NEW_CURATED_SUBMIT_EXIT_HASHES_FACTORY = "0x4F716AD3Cc7A3A5cdA2359e5B2c84335c171dCde"

OLD_REGISTER_GROUPS_FACTORY = "0xE73842AEbEC99Dacf2aAEec61409fD01A033f478"
OLD_REGISTER_TIERS_FACTORY = "0x5292A1284e4695B95C0840CF8ea25A818751C17F"
OLD_ALTER_TIERS_FACTORY = "0x73f80240ad9363d5d3C5C3626953C351cA36Bfe9"
NEW_REGISTER_GROUPS_FACTORY = "0x17305dB55c908e84C58BbDCa57258A7D1f7eEa7c"
NEW_REGISTER_TIERS_FACTORY = "0x6b535F441F95046562406F4E2518D9AD7Db2dc0D"
NEW_ALTER_TIERS_FACTORY = "0x37d9B09EDA477a84E3913fCB4d032EFb0BF9B62E"

# ============================== Constants ===================================
A41_NO_ID = 32
STAKIN_NO_ID = 14
STAKIN_NAME_NEW = "Stakin by The Tie"

CHORUS_ONE_NO_ID = 3
CURATED_MODULE_ID = 1
NO_TARGET_LIMIT_SOFT_MODE = 1
CHORUS_ONE_NEW_TARGET_LIMIT = 0

GAS_SUPPLY_NEW_LIMIT = 150 * 10**18
GAS_SUPPLY_PERIOD_DURATION_MONTHS = 12

CSM_MODULE_ID = 3
CSM_STAKE_SHARE_LIMIT_NEW = 850
CSM_PRIORITY_EXIT_SHARE_THRESHOLD_NEW = 1020
CSM_MODULE_FEE_BP = 600
CSM_TREASURY_FEE_BP = 400
CSM_MAX_DEPOSITS_PER_BLOCK = 30
CSM_MIN_DEPOSIT_BLOCK_DISTANCE = 25

AO_HASH_CONSENSUS_QUORUM = 5
CS_HASH_CONSENSUS_QUORUM = 5
VEBO_HASH_CONSENSUS_QUORUM = 5

# Function names for permissions
OPERATOR_GRID_REGISTER_GROUP = "registerGroup"
OPERATOR_GRID_REGISTER_TIERS = "registerTiers"
OPERATOR_GRID_ALTER_TIERS = "alterTiers"
SUBMIT_EXIT_REQUESTS = "submitExitRequestsHash"

# ============================= IPFS Description ==================================
IPFS_DESCRIPTION = """
1. **Deactivate Node Operator A41**, [as requested on the forum](https://research.lido.fi/t/a41-node-operator-intention-to-wind-down-operations-request-for-dao-vote/10954/5). Item 1.1.
2. **Change name and reward address for Node Operator Stakin**, [as per Snapshot decision](https://snapshot.org/#/s:lido-snapshot.eth/proposal/0x60d9126fed2a492a22ef53942a16a7a8a7ec3a576ffc2b2367ebcec8eb6baa30). Items 1.2, 1.3.
3. **Upgrade Lazy Oracle**, [as proposed on the forum](https://research.lido.fi/t/lido-v3-design-implementation-proposal/10665/23). Audit & deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20v3%20Security%20Audit%20Report%2003-26.pdf). Item 1.4.
4. **Upgrade Vault Hub**, [as proposed on the forum](https://research.lido.fi/t/security-bulletin-batched-immunefi-reported-weakness-disclosure-march-2026-funds-not-at-risk/11342/4). Audit & deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20v3%20Security%20Audit%20Report%2003-26.pdf). Item 1.5.
5. **Upgrade and re-enable ZKSync Bridge**, [as proposed on the forum](https://research.lido.fi/t/security-bulletin-batched-immunefi-reported-weakness-disclosure-march-2026-funds-not-at-risk/11342/2). Audit & deployment verification: [Cantina](https://github.com/lidofinance/audits/blob/main/L2/zkSync-2026-03-05-Cantina-PR-85-fix-report.pdf). Items 1.6, 1.7.
6. **Rotate address for Oracle Set member Chorus One**, [as requested on the forum](https://research.lido.fi/t/expansion-of-lidos-ethereum-oracle-set/2836/80). Items 1.8–1.13.
7. **Rotate address for Oracle Set member Stakefish**, [as requested on the forum](https://research.lido.fi/t/expansion-of-lidos-ethereum-oracle-set/2836/81). Items 1.14–1.19.
8. **Set Node Operator Chorus One soft target validators limit to 0**, [as requested on the forum](https://research.lido.fi/t/chorus-one-joins-bitwise/11250/3). Item 1.20.
9. **Decrease Gas Supply Easy Track limit from 1000 to 150 stETH per year and reset spent amount for the 2026 period**, [as proposed on the forum](https://research.lido.fi/t/nominate-the-gas-supply-committee-as-a-supervisor-for-gas-expenditure/4724/14). Items 1.21, 1.22.
10. **Raise Community Staking Module stake share limit to 8.5% and priority exit threshold to 10.2%**, [as per Snapshot decision](https://snapshot.org/#/s:lido-snapshot.eth/proposal/0xc3f92bcdf8926cfa7528ca6a979c0fdce1e4d0cfaaa72dd6410a76a2e1e55766). Details in the [forum post](https://research.lido.fi/t/community-staking-module/5917/201). Item 1.23.
11. **Rotate Deposit Security Committee address for Stakefish**, [as requested on the forum](https://research.lido.fi/t/stakefish-is-updating-the-address-for-council-daemon/11394). Items 1.24, 1.25.
12. **Upgrade Curated and SDVT Staking Modules Easy Track factories for validator exit request hashes submission**, [as proposed on the forum](https://research.lido.fi/t/security-bulletin-batched-immunefi-reported-weakness-disclosure-march-2026-funds-not-at-risk/11342/3). Audit & deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20Easy%20Track%20Security%20Audit%20Report%2003-26.pdf). Items 2-5.
13. **Upgrade stVaults Easy Track factories to register groups and register & alter tiers in Operator Grid**, [as proposed on the forum](https://research.lido.fi/t/stvaults-committee-proposal/10608/15). Audit & deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20Easy%20Track%20stVaults%20Security%20Audit%20Report%2003-26.pdf). Items 6-11.
"""


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    dsm = interface.DepositSecurityModule(DEPOSIT_SECURITY_MODULE)
    no_registry = interface.NodeOperatorsRegistry(CURATED_MODULE)
    hash_consensus_for_accounting_oracle = interface.HashConsensus(HASH_CONSENSUS_FOR_AO)
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    hash_consensus_for_vebo = interface.HashConsensus(HASH_CONSENSUS_FOR_VEBO)
    lazy_oracle_proxy = interface.OssifiableProxy(LAZY_ORACLE_PROXY)
    vault_hub_proxy = interface.OssifiableProxy(VAULT_HUB_PROXY)
    zksync_bridge_proxy = interface.OssifiableProxy(ZKSYNC_L1_ERC20_BRIDGE)
    zksync_bridge = interface.ZkSyncL1ERC20Bridge(ZKSYNC_L1_ERC20_BRIDGE)

    return [
        # 1.1. Deactivate Node Operator A41 (id = 32) in Curated Module 0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5
        agent_forward([deactivate_node_operator(A41_NO_ID)]),
        # 1.2. Change name to Stakin by The Tie for Node Operator Stakin (id = 14) in Curated Module 0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5
        agent_forward([encode_set_node_operator_name(STAKIN_NO_ID, STAKIN_NAME_NEW, no_registry)]),
        # 1.3. Change reward address to 0x3e97EC699191bEfc63EF4E4275204B03E7465f30 for Node Operator Stakin (id = 14) in Curated Module 0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5
        agent_forward([encode_set_node_operator_reward_address(STAKIN_NO_ID, STAKIN_REWARD_ADDRESS_NEW, no_registry)]),
        # 1.4. Upgrade LazyOracle proxy 0x5DB427080200c235F2Ae8Cd17A7be87921f7AD6c implementation to 0x96c9a897D116ef660086d3aA67b3af653324aB37
        agent_forward(
            [
                (
                    lazy_oracle_proxy.address,
                    lazy_oracle_proxy.proxy__upgradeTo.encode_input(LAZY_ORACLE_IMPL_NEW),
                )
            ]
        ),
        # 1.5. Upgrade VaultHub proxy 0x1d201BE093d847f6446530Efb0E8Fb426d176709 implementation to 0x6330fE7756FBE8649adfb9A541d61C5edB8B4D70
        agent_forward(
            [
                (
                    vault_hub_proxy.address,
                    vault_hub_proxy.proxy__upgradeTo.encode_input(VAULT_HUB_IMPL_NEW),
                )
            ]
        ),
        # 1.6. Upgrade ZKSync L1ERC20Bridge proxy 0x41527B2d03844dB6b0945f25702cB958b6d55989 implementation to 0x43a66b32c9adca1a59b273e69b61da5197c21ccd
        agent_forward(
            [
                (
                    zksync_bridge_proxy.address,
                    zksync_bridge_proxy.proxy__upgradeTo.encode_input(ZKSYNC_L1_ERC20_BRIDGE_IMPL_NEW),
                )
            ]
        ),
        # 1.7. Call enableDeposits on ZKSync L1ERC20Bridge proxy 0x41527B2d03844dB6b0945f25702cB958b6d55989
        agent_forward([(zksync_bridge.address, zksync_bridge.enableDeposits.encode_input())]),
        # 1.8. Remove Chorus One member 0x285f8537e1daeedaf617e96c742f2cf36d63ccfb from Accounting Oracle HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
        agent_forward(
            [
                (
                    hash_consensus_for_accounting_oracle.address,
                    hash_consensus_for_accounting_oracle.removeMember.encode_input(
                        CHORUS_ONE_ORACLE_MEMBER_OLD, AO_HASH_CONSENSUS_QUORUM
                    ),
                )
            ]
        ),
        # 1.9. Remove Chorus One member 0x285f8537e1daeedaf617e96c742f2cf36d63ccfb from CSM Oracle HashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
        agent_forward(
            [
                (
                    cs_hash_consensus.address,
                    cs_hash_consensus.removeMember.encode_input(CHORUS_ONE_ORACLE_MEMBER_OLD, CS_HASH_CONSENSUS_QUORUM),
                )
            ]
        ),
        # 1.10. Remove Chorus One member 0x285f8537e1daeedaf617e96c742f2cf36d63ccfb from VEB Oracle HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
        agent_forward(
            [
                (
                    hash_consensus_for_vebo.address,
                    hash_consensus_for_vebo.removeMember.encode_input(
                        CHORUS_ONE_ORACLE_MEMBER_OLD, VEBO_HASH_CONSENSUS_QUORUM
                    ),
                )
            ]
        ),
        # 1.11. Add new Chorus One member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 to Accounting Oracle HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
        agent_forward(
            [
                (
                    hash_consensus_for_accounting_oracle.address,
                    hash_consensus_for_accounting_oracle.addMember.encode_input(
                        CHORUS_ONE_ORACLE_MEMBER_NEW, AO_HASH_CONSENSUS_QUORUM
                    ),
                )
            ]
        ),
        # 1.12. Add new Chorus One member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 to CSM Oracle HashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
        agent_forward(
            [
                (
                    cs_hash_consensus.address,
                    cs_hash_consensus.addMember.encode_input(CHORUS_ONE_ORACLE_MEMBER_NEW, CS_HASH_CONSENSUS_QUORUM),
                )
            ]
        ),
        # 1.13. Add new Chorus One member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 to VEB Oracle HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
        agent_forward(
            [
                (
                    hash_consensus_for_vebo.address,
                    hash_consensus_for_vebo.addMember.encode_input(
                        CHORUS_ONE_ORACLE_MEMBER_NEW, VEBO_HASH_CONSENSUS_QUORUM
                    ),
                )
            ]
        ),
        # 1.14. Remove Stakefish member 0x946D3b081ed19173dC83Cd974fC69e1e760B7d78 from Accounting Oracle HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
        agent_forward(
            [
                (
                    hash_consensus_for_accounting_oracle.address,
                    hash_consensus_for_accounting_oracle.removeMember.encode_input(
                        STAKEFISH_ORACLE_MEMBER_OLD, AO_HASH_CONSENSUS_QUORUM
                    ),
                )
            ]
        ),
        # 1.15. Remove Stakefish member 0x946D3b081ed19173dC83Cd974fC69e1e760B7d78 from CSM Oracle HashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
        agent_forward(
            [
                (
                    cs_hash_consensus.address,
                    cs_hash_consensus.removeMember.encode_input(STAKEFISH_ORACLE_MEMBER_OLD, CS_HASH_CONSENSUS_QUORUM),
                )
            ]
        ),
        # 1.16. Remove Stakefish member 0x946D3b081ed19173dC83Cd974fC69e1e760B7d78 from VEB Oracle HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
        agent_forward(
            [
                (
                    hash_consensus_for_vebo.address,
                    hash_consensus_for_vebo.removeMember.encode_input(
                        STAKEFISH_ORACLE_MEMBER_OLD, VEBO_HASH_CONSENSUS_QUORUM
                    ),
                )
            ]
        ),
        # 1.17. Add new Stakefish member 0x042a9e5acCfa17e28300F1b5967f20891E973922 to Accounting Oracle HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
        agent_forward(
            [
                (
                    hash_consensus_for_accounting_oracle.address,
                    hash_consensus_for_accounting_oracle.addMember.encode_input(
                        STAKEFISH_ORACLE_MEMBER_NEW, AO_HASH_CONSENSUS_QUORUM
                    ),
                )
            ]
        ),
        # 1.18. Add new Stakefish member 0x042a9e5acCfa17e28300F1b5967f20891E973922 to CSM Oracle HashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
        agent_forward(
            [
                (
                    cs_hash_consensus.address,
                    cs_hash_consensus.addMember.encode_input(STAKEFISH_ORACLE_MEMBER_NEW, CS_HASH_CONSENSUS_QUORUM),
                )
            ]
        ),
        # 1.19. Add new Stakefish member 0x042a9e5acCfa17e28300F1b5967f20891E973922 to VEB Oracle HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
        agent_forward(
            [
                (
                    hash_consensus_for_vebo.address,
                    hash_consensus_for_vebo.addMember.encode_input(
                        STAKEFISH_ORACLE_MEMBER_NEW, VEBO_HASH_CONSENSUS_QUORUM
                    ),
                )
            ]
        ),
        # 1.20. Set soft-mode target validators limit to 0 for Node Operator Chorus One (ID = 3) in Curated Module (MODULE_ID = 1) in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
        agent_forward(
            [
                (
                    staking_router.address,
                    staking_router.updateTargetValidatorsLimits.encode_input(
                        CURATED_MODULE_ID, CHORUS_ONE_NO_ID, NO_TARGET_LIMIT_SOFT_MODE, CHORUS_ONE_NEW_TARGET_LIMIT
                    ),
                )
            ]
        ),
        # 1.21. Decrease limit from 1000 to 150 stETH per 12 months on Gas Supply AllowedRecipientsRegistry 0x49d1363016aA899bba09ae972a1BF200dDf8C55F
        agent_forward(
            [
                set_limit_parameters(
                    limit=GAS_SUPPLY_NEW_LIMIT,
                    period_duration_months=GAS_SUPPLY_PERIOD_DURATION_MONTHS,
                    registry_address=GAS_SUPPLY_ALLOWED_RECIPIENTS_REGISTRY,
                ),
            ]
        ),
        # 1.22. Set spent amount to 0 on Gas Supply AllowedRecipientsRegistry 0x49d1363016aA899bba09ae972a1BF200dDf8C55F
        agent_forward(
            [
                unsafe_set_spent_amount(spent_amount=0, registry_address=GAS_SUPPLY_ALLOWED_RECIPIENTS_REGISTRY),
            ]
        ),
        # 1.23. Raise CSM (MODULE_ID = 3) stake share limit from 750 BP to 850 BP and priority exit threshold from 900 BP to 1020 BP in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
        agent_forward(
            [
                (
                    staking_router.address,
                    staking_router.updateStakingModule.encode_input(
                        CSM_MODULE_ID,
                        CSM_STAKE_SHARE_LIMIT_NEW,
                        CSM_PRIORITY_EXIT_SHARE_THRESHOLD_NEW,
                        CSM_MODULE_FEE_BP,
                        CSM_TREASURY_FEE_BP,
                        CSM_MAX_DEPOSITS_PER_BLOCK,
                        CSM_MIN_DEPOSIT_BLOCK_DISTANCE,
                    ),
                )
            ]
        ),
        # 1.24. Remove old Stakefish address 0xd4EF84b638B334699bcf5AF4B0410B8CCD71943f from Deposit Security Module 0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD and keep quorum size as 4
        agent_forward(
            [
                encode_remove_guardian(
                    dsm=dsm, guardian_address=STAKEFISH_DSM_GUARDIAN_OLD, quorum_size=DSM_QUORUM_SIZE
                ),
            ]
        ),
        # 1.25. Add new Stakefish address 0x4B87F16B8d32cb5a859a4C48a88edB5adBe3498E to Deposit Security Module 0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD and keep quorum size as 4
        agent_forward(
            [
                encode_add_guardian(dsm=dsm, guardian_address=STAKEFISH_DSM_GUARDIAN_NEW, quorum_size=DSM_QUORUM_SIZE),
            ]
        ),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    validators_exit_bus_oracle = interface.ValidatorsExitBusOracle(VEBO)
    dg_items = get_dg_items()

    dg_call_script = submit_proposals(
        [
            (
                dg_items,
                "Deactivate A41, change name and reward address for Stakin, upgrade Lazy Oracle, Vault Hub and ZKSync Bridge, rotate addresses for Chorus One and Stakefish oracle set members, set Chorus One target validators limit, decrease Gas Supply ET limit and reset spent amount, raise CSM stake share limit and priority exit threshold, rotate DSC address for Stakefish",
            )
        ]
    )

    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to deactivate A41, change name and reward address for Stakin, upgrade Lazy Oracle, Vault Hub and ZKSync Bridge, rotate addresses for Chorus One and Stakefish oracle set members, set Chorus One target validators limit, decrease Gas Supply ET limit and reset spent amount, raise CSM stake share limit and priority exit threshold, rotate DSC address for Stakefish",
            dg_call_script[0],
        ),
        (
            "2. Remove old Simple DVT SubmitValidatorsExitRequestHashes factory 0xB7668B5485d0f826B86a75b0115e088bB9ee03eE from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory(OLD_SDVT_SUBMIT_EXIT_HASHES_FACTORY),
        ),
        (
            "3. Remove old Curated Module SubmitValidatorsExitRequestHashes factory 0x8aa34dAaF0fC263203A15Bcfa0Ed926D466e59F3 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory(OLD_CURATED_SUBMIT_EXIT_HASHES_FACTORY),
        ),
        (
            "4. Add new Simple DVT SubmitValidatorsExitRequestHashes factory 0x58A59dDC6Aea9b1D5743D024E15DfA4badB56E37 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: ValidatorsExitBusOracle.submitExitRequestsHash 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6eb1b19f57)",
            add_evmscript_factory(
                NEW_SDVT_SUBMIT_EXIT_HASHES_FACTORY,
                create_permissions(validators_exit_bus_oracle, SUBMIT_EXIT_REQUESTS),
            ),
        ),
        (
            "5. Add new Curated Module SubmitValidatorsExitRequestHashes factory 0x4F716AD3Cc7A3A5cdA2359e5B2c84335c171dCde to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: ValidatorsExitBusOracle.submitExitRequestsHash 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6eb1b19f57)",
            add_evmscript_factory(
                NEW_CURATED_SUBMIT_EXIT_HASHES_FACTORY,
                create_permissions(validators_exit_bus_oracle, SUBMIT_EXIT_REQUESTS),
            ),
        ),
        (
            "6. Remove old RegisterGroupsInOperatorGrid factory 0xE73842AEbEC99Dacf2aAEec61409fD01A033f478 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory(OLD_REGISTER_GROUPS_FACTORY),
        ),
        (
            "7. Remove old RegisterTiersInOperatorGrid factory 0x5292A1284e4695B95C0840CF8ea25A818751C17F from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory(OLD_REGISTER_TIERS_FACTORY),
        ),
        (
            "8. Remove old AlterTiersInOperatorGrid factory 0x73f80240ad9363d5d3C5C3626953C351cA36Bfe9 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory(OLD_ALTER_TIERS_FACTORY),
        ),
        (
            "9. Add new RegisterGroupsInOperatorGrid factory 0x17305dB55c908e84C58BbDCa57258A7D1f7eEa7c to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: operatorGrid.registerGroup, operatorGrid.registerTiers 0xc69685e89cefc327b43b7234ac646451b27c544de37a7c0bc69685e89cefc327b43b7234ac646451b27c544d552b91da)",
            add_evmscript_factory(
                NEW_REGISTER_GROUPS_FACTORY,
                create_permissions(operator_grid, OPERATOR_GRID_REGISTER_GROUP)
                + create_permissions(operator_grid, OPERATOR_GRID_REGISTER_TIERS)[2:],
            ),
        ),
        (
            "10. Add new RegisterTiersInOperatorGrid factory 0x6b535F441F95046562406F4E2518D9AD7Db2dc0D to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: operatorGrid.registerTiers 0xc69685e89cefc327b43b7234ac646451b27c544d552b91da)",
            add_evmscript_factory(
                NEW_REGISTER_TIERS_FACTORY,
                create_permissions(operator_grid, OPERATOR_GRID_REGISTER_TIERS),
            ),
        ),
        (
            "11. Add new AlterTiersInOperatorGrid factory 0x37d9B09EDA477a84E3913fCB4d032EFb0BF9B62E to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: operatorGrid.alterTiers 0xc69685e89cefc327b43b7234ac646451b27c544d54544bcb)",
            add_evmscript_factory(
                NEW_ALTER_TIERS_FACTORY,
                create_permissions(operator_grid, OPERATOR_GRID_ALTER_TIERS),
            ),
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
