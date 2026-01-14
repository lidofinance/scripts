"""
Vote 2026_01_20

TODO: a list of items

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

from brownie import interface

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from utils.easy_track import remove_evmscript_factory, add_evmscript_factory, create_permissions

from utils.permissions import encode_oz_revoke_role, encode_oz_grant_role, encode_permission_grant, encode_permission_revoke
from utils.agent import agent_forward

# ============================== Addresses ===================================

# DAO addresses
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"

# Lido addresses
LIDO = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
OPERATOR_GRID = "0xC69685E89Cefc327b43B7234AC646451B27c544d"
VAULT_HUB = "0x1d201BE093d847f6446530Efb0E8Fb426d176709"
CS_HASH_CONSENSUS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"
TWO_PHASE_FRAME_CONFIG_UPDATE = "0xb2B4DB1491cbe949ae85EfF01E0d3ee239f110C1"
PREDEPOSIT_GUARANTEE = "0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3"
PREDEPOSIT_GUARANTEE_NEW_IMPL = "0xE78717192C45736DF0E4be55c0219Ee7f9aDdd0D"

# Old Easy Track factories
ST_VAULTS_COMMITTEE = "0x18A1065c81b0Cc356F1b1C843ddd5E14e4AefffF"
OLD_VAULTS_ADAPTER = "0xe2DE6d2DefF15588a71849c0429101F8ca9FB14D"
OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0xa29173C7BCf39dA48D5E404146A652d7464aee14"
OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0x194A46DA1947E98c9D79af13E06Cfbee0D8610cC"
OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0x8Bdc726a3147D8187820391D7c6F9F942606aEe6"
OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x93F1DEE4473Ee9F42c8257C201e33a6Da30E5d67"
OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0x1dF50522A1D868C12bF71747Bb6F24A18Fe6d32C"
OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6C968cD89CA358fbAf57B18e77a8973Fa869a6aA"
OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0x5C3bDFa3E7f312d8cf72F56F2b797b026f6B471c"

# New Easy Track factories
VAULTS_ADAPTER = "0x28F9Ac198C4E0FA6A9Ad2c2f97CB38F1A3120f27"
ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0x73f80240ad9363d5d3C5C3626953C351cA36Bfe9"
REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0xE73842AEbEC99Dacf2aAEec61409fD01A033f478"
UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0xf23559De8ab37fF7a154384B0822dA867Cfa7Eac"
SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x6a4f33F05E7412A11100353724Bb6a152Cf0D305"
SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0xaf35A63a4114B7481589fDD9FDB3e35Fd65fAed7"
FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6F5c0A5a824773E8f8285bC5aA59ea0Aab2A6400"
UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0xDfA0bc38113B6d53c2881573FD764CEEFf468610"

# CSM module parameters
CSM_MODULE_ID = 3
CSM_MODULE_NEW_TARGET_SHARE_BP = 750  # increase from 500 BP to 750 BP (7.5%)
CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 900  # increase from 625 BP to 900 BP (9%)
CSM_MODULE_MODULE_FEE_BP = 600 # Unchanged
CSM_MODULE_TREASURY_FEE_BP = 400 # Unchanged
CSM_MODULE_MAX_DEPOSITS_PER_BLOCK = 30 # Unchanged
CSM_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25 # Unchanged

# Lido max external ratio
MAX_EXTERNAL_RATIO_BP = 3000  # 30%


# ============================= Description ==================================
# TODO <a description for IPFS (will appear in the voting description on vote.lido.fi)>
IPFS_DESCRIPTION = ""


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    lido = interface.Lido(LIDO)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    vault_hub = interface.VaultHub(VAULT_HUB)
    vaults_adapter = interface.IVaultsAdapter(VAULTS_ADAPTER)
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    predeposit_guarantee_proxy = interface.OssifiableProxy(PREDEPOSIT_GUARANTEE)
    predeposit_guarantee = interface.PredepositGuarantee(PREDEPOSIT_GUARANTEE)

    dg_items = [
        # ======================== EasyTrack ========================
        # 1.1. Revoke `vaults.OperatorsGrid.Registry` role `a495a3428837724c7f7648cda02eb83c9c4c778c8688d6f254c7f3f80c154d55` on OperatorGrid `0xC69685E89Cefc327b43B7234AC646451B27c544d` from old VaultsAdapter `0xe2DE6d2DefF15588a71849c0429101F8ca9FB14D`
        agent_forward([
            encode_oz_revoke_role(operator_grid, "vaults.OperatorsGrid.Registry", OLD_VAULTS_ADAPTER)
        ]),

        # 1.2. Grant `vaults.OperatorsGrid.Registry` role `a495a3428837724c7f7648cda02eb83c9c4c778c8688d6f254c7f3f80c154d55` on OperatorGrid `0xC69685E89Cefc327b43B7234AC646451B27c544d` to new VaultsAdapter `0x28F9Ac198C4E0FA6A9Ad2c2f97CB38F1A3120f27`
        agent_forward([
            encode_oz_grant_role(operator_grid, "vaults.OperatorsGrid.Registry", VAULTS_ADAPTER)
        ]),

        # 1.3. Revoke `vaults.VaultHub.ValidatorExitRole` role `2159c5943234d9f3a7225b9a743ea06e4a0d0ba5ed82889e867759a8a9eb7883` on VaultHub `0x1d201BE093d847f6446530Efb0E8Fb426d176709` from old VaultsAdapter `0xe2DE6d2DefF15588a71849c0429101F8ca9FB14D`
        agent_forward([
            encode_oz_revoke_role(vault_hub, "vaults.VaultHub.ValidatorExitRole", OLD_VAULTS_ADAPTER)
        ]),

        # 1.4. Grant `vaults.VaultHub.ValidatorExitRole` role `2159c5943234d9f3a7225b9a743ea06e4a0d0ba5ed82889e867759a8a9eb7883` on VaultHub `0x1d201BE093d847f6446530Efb0E8Fb426d176709` to new VaultsAdapter `0x28F9Ac198C4E0FA6A9Ad2c2f97CB38F1A3120f27`
        agent_forward([
            encode_oz_grant_role(vault_hub, "vaults.VaultHub.ValidatorExitRole", VAULTS_ADAPTER)
        ]),

        # 1.5. Revoke `vaults.VaultHub.BadDebtMasterRole` role `a85bab4b576ca359fa6ae02ab8744b5c85c7e7ed4d7e0bca7b5b64580ac5d17d` on VaultHub `0x1d201BE093d847f6446530Efb0E8Fb426d176709` from old VaultsAdapter `0xe2DE6d2DefF15588a71849c0429101F8ca9FB14D`
        agent_forward([
            encode_oz_revoke_role(vault_hub, "vaults.VaultHub.BadDebtMasterRole", OLD_VAULTS_ADAPTER)
        ]),

        # 1.6. Grant `vaults.VaultHub.BadDebtMasterRole` role `a85bab4b576ca359fa6ae02ab8744b5c85c7e7ed4d7e0bca7b5b64580ac5d17d` on VaultHub `0x1d201BE093d847f6446530Efb0E8Fb426d176709` to new VaultsAdapter `0x28F9Ac198C4E0FA6A9Ad2c2f97CB38F1A3120f27`
        agent_forward([
            encode_oz_grant_role(vault_hub, "vaults.VaultHub.BadDebtMasterRole", VAULTS_ADAPTER)
        ]),

        # ======================== PDG ========================
        # 1.7. Update PredepositGuarantee proxy `0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3` implementation to `0xE78717192C45736DF0E4be55c0219Ee7f9aDdd0D`
        agent_forward([
            (
                predeposit_guarantee_proxy.address,
                predeposit_guarantee_proxy.proxy__upgradeTo.encode_input(PREDEPOSIT_GUARANTEE_NEW_IMPL),
            )
        ]),

        # 1.8. Temporarily grant `PausableUntilWithRoles.ResumeRole` `a79a6aede309e0d48bf2ef0f71355c06ad317956d4c0da2deb0dc47cc34f826c` on PredepositGuarantee `0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3` to Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
        agent_forward([
            encode_oz_grant_role(predeposit_guarantee, "PausableUntilWithRoles.ResumeRole", AGENT)
        ]),

        # 1.9. Unpause PredepositGuarantee `0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3`
        agent_forward([
            (
                predeposit_guarantee_proxy.address,
                predeposit_guarantee.resume.encode_input(),
            )
        ]),

        # 1.10. Revoke `PausableUntilWithRoles.ResumeRole` `a79a6aede309e0d48bf2ef0f71355c06ad317956d4c0da2deb0dc47cc34f826c` on PredepositGuarantee `0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3` from Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
        agent_forward([
            encode_oz_revoke_role(predeposit_guarantee, "PausableUntilWithRoles.ResumeRole", AGENT)
        ]),

        # ======================== Lido ========================
        # 1.11. Temporarily grant `STAKING_CONTROL_ROLE` `a42eee1333c0758ba72be38e728b6dadb32ea767de5b4ddbaea1dae85b1b051f` on Lido `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84` to Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
        agent_forward([
            encode_permission_grant(lido, "STAKING_CONTROL_ROLE", AGENT)
        ]),

        # 1.12. Set max external ratio to `30%` on Lido `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84`
        agent_forward([
            (
                lido.address,
                lido.setMaxExternalRatioBP.encode_input(MAX_EXTERNAL_RATIO_BP),
            )
        ]),

        # 1.13. Revoke `STAKING_CONTROL_ROLE` a42eee1333c0758ba72be38e728b6dadb32ea767de5b4ddbaea1dae85b1b051f on Lido `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84` from Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`
        agent_forward([
            encode_permission_revoke(lido, "STAKING_CONTROL_ROLE", AGENT)
        ]),

        # ======================== CSM ========================
        # 1.14. Raise CSM (MODULE_ID = `3`) stake share limit from `500 BP` to `750 BP` and priority exit threshold from `625 BP` to `900 BP`
        agent_forward([
            (
                staking_router.address,
                staking_router.updateStakingModule.encode_input(
                    CSM_MODULE_ID,
                    CSM_MODULE_NEW_TARGET_SHARE_BP,
                    CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
                    CSM_MODULE_MODULE_FEE_BP,
                    CSM_MODULE_TREASURY_FEE_BP,
                    CSM_MODULE_MAX_DEPOSITS_PER_BLOCK,
                    CSM_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                ),
            ),
        ]),

        # 1.15. Grant `MANAGE_FRAME_CONFIG_ROLE` `921f40f434e049d23969cbe68d9cf3ac1013fbe8945da07963af6f3142de6afe` on CS HashConsensus `0x71093efF8D8599b5fA340D665Ad60fA7C80688e4` to TwoPhaseFrameConfigUpdate contract `0xb2B4DB1491cbe949ae85EfF01E0d3ee239f110C1`
        agent_forward([
            encode_oz_grant_role(
                contract=cs_hash_consensus,
                role_name="MANAGE_FRAME_CONFIG_ROLE",
                grant_to=TWO_PHASE_FRAME_CONFIG_UPDATE,
            )
        ]),
    ]

    dg_call_script = submit_proposals([
        (dg_items, "Activate Lido V3 Phase 2, raise CSM stake share limit to 7.5% and priority exit threshold from 9%, grant MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus to TwoPhaseFrameConfigUpdate contract")
    ])

    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to activate Lido V3 Phase 2, raise CSM stake share limit to 7.5% and priority exit threshold from 9%, grant MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus to TwoPhaseFrameConfigUpdate contract",
            dg_call_script[0]
        ),
        (
            "2. Remove old `ALTER_TIERS_IN_OPERATOR_GRID_FACTORY` `0xa29173C7BCf39dA48D5E404146A652d7464aee14` from Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea`",
            remove_evmscript_factory(OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "3. Add new `ALTER_TIERS_IN_OPERATOR_GRID_FACTORY` `0x73f80240ad9363d5d3C5C3626953C351cA36Bfe9` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` (permissions: operatorGrid.alterTiers `0xc69685e89cefc327b43b7234ac646451b27c544d54544bcb`)",
            add_evmscript_factory(ALTER_TIERS_IN_OPERATOR_GRID_FACTORY, create_permissions(operator_grid, "alterTiers"))
        ),
        (
            "4. Remove old `REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY` `0x194A46DA1947E98c9D79af13E06Cfbee0D8610cC` from Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea`",
            remove_evmscript_factory(OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "5. Add new `REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY` `0xE73842AEbEC99Dacf2aAEec61409fD01A033f478` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` (permissions: operatorGrid.registerGroup, operatorGrid.registerTiers `0xc69685e89cefc327b43b7234ac646451b27c544de37a7c0bc69685e89cefc327b43b7234ac646451b27c544d552b91da`)",
            add_evmscript_factory(
                REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY,
                create_permissions(operator_grid, "registerGroup") + create_permissions(operator_grid, "registerTiers")[2:]
            )
        ),
        (
            "6. Remove old `UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY` `0x8Bdc726a3147D8187820391D7c6F9F942606aEe6` from Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea`",
            remove_evmscript_factory(OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "7. Add new `UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY` `0xf23559De8ab37fF7a154384B0822dA867Cfa7Eac` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` (permissions: operatorGrid.updateGroupShareLimit `0xc69685e89cefc327b43b7234ac646451b27c544de52b6085`)",
            add_evmscript_factory(UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY, create_permissions(operator_grid, "updateGroupShareLimit"))
        ),
        (
            "8. Remove old `SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY` `0x93F1DEE4473Ee9F42c8257C201e33a6Da30E5d67` from Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea`",
            remove_evmscript_factory(OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "9. Add new `SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY` `0x6a4f33F05E7412A11100353724Bb6a152Cf0D305` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` (permissions: vaults_adapter.setVaultJailStatus `0x28f9ac198c4e0fa6a9ad2c2f97cb38f1a3120f27285f591c`)",
            add_evmscript_factory(SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY, create_permissions(vaults_adapter, "setVaultJailStatus"))
        ),
        (
            "10. Remove old `SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY` `0x1dF50522A1D868C12bF71747Bb6F24A18Fe6d32C` from Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea`",
            remove_evmscript_factory(OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY)
        ),
        (
            "11. Add new `SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY` `0xaf35A63a4114B7481589fDD9FDB3e35Fd65fAed7` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` (permissions: vaults_adapter.socializeBadDebt `0x28f9ac198c4e0fa6a9ad2c2f97cb38f1a3120f2796c4d514`)",
            add_evmscript_factory(SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY, create_permissions(vaults_adapter, "socializeBadDebt"))
        ),
        (
            "12. Remove old `FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY` `0x6C968cD89CA358fbAf57B18e77a8973Fa869a6aA` from Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea`",
            remove_evmscript_factory(OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY)
        ),
        (
            "13. Add new `FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY` `0x6F5c0A5a824773E8f8285bC5aA59ea0Aab2A6400` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` (permissions: vaults_adapter.forceValidatorExit `0x28f9ac198c4e0fa6a9ad2c2f97cb38f1a3120f2733eb1f1a`)",
            add_evmscript_factory(FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY, create_permissions(vaults_adapter, "forceValidatorExit"))
        ),
        (
            "14. Remove old `UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY` `0x5C3bDFa3E7f312d8cf72F56F2b797b026f6B471c` from Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea`",
            remove_evmscript_factory(OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "15. Add new `UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY` `0xDfA0bc38113B6d53c2881573FD764CEEFf468610` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` (permissions: vaults_adapter.updateVaultFees `0x28f9ac198c4e0fa6a9ad2c2f97cb38f1a3120f27ed7139a7`)",
            add_evmscript_factory(UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY, create_permissions(vaults_adapter, "updateVaultFees"))
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
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
