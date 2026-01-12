"""
Vote 2026_01_21

# TODO <a list of vote items synced with Notion Omnibus checklist>

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

from utils.permissions import encode_oz_revoke_role, encode_oz_grant_role
from utils.agent import agent_forward

# ============================== Addresses ===================================

# DAO addresses
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"

# Lido addresses
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
OPERATOR_GRID = "0xC69685E89Cefc327b43B7234AC646451B27c544d"
VAULT_HUB = "0x1d201BE093d847f6446530Efb0E8Fb426d176709"
CS_HASH_CONSENSUS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"
TWO_PHASE_FRAME_CONFIG_UPDATE = "0xb2B4DB1491cbe949ae85EfF01E0d3ee239f110C1"
PREDEPOSIT_GUARANTEE = "0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3"
PREDEPOSIT_GUARANTEE_NEW_IMPL = "0x85cBc70D06CfD02D176c7e8474636cF9fCa414eA"  # TODO update address after deployment

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
VAULTS_ADAPTER = "0xe2DE6d2DefF15588a71849c0429101F8ca9FB14D" # TODO update address after deployment
ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0xa29173C7BCf39dA48D5E404146A652d7464aee14" # TODO update address after deployment
REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0x194A46DA1947E98c9D79af13E06Cfbee0D8610cC" # TODO update address after deployment
UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0x8Bdc726a3147D8187820391D7c6F9F942606aEe6" # TODO update address after deployment
SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x93F1DEE4473Ee9F42c8257C201e33a6Da30E5d67" # TODO update address after deployment
SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0x1dF50522A1D868C12bF71747Bb6F24A18Fe6d32C" # TODO update address after deployment
FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6C968cD89CA358fbAf57B18e77a8973Fa869a6aA" # TODO update address after deployment
UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0x5C3bDFa3E7f312d8cf72F56F2b797b026f6B471c" # TODO update address after deployment

# CSM module parameters
CSM_MODULE_ID = 3
CSM_MODULE_NEW_TARGET_SHARE_BP = 750  # increase from 500 BP to 750 BP (7.5%)
CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 900  # increase from 625 BP to 900 BP (9%)
CSM_MODULE_MODULE_FEE_BP = 600 # Unchanged
CSM_MODULE_TREASURY_FEE_BP = 400 # Unchanged
CSM_MODULE_MAX_DEPOSITS_PER_BLOCK = 30 # Unchanged
CSM_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25 # Unchanged


# ============================= Description ==================================
# TODO <a description for IPFS (will appear in the voting description on vote.lido.fi)>
IPFS_DESCRIPTION = ""


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    vault_hub = interface.VaultHub(VAULT_HUB)
    vaults_adapter = interface.IVaultsAdapter(VAULTS_ADAPTER)
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    predeposit_guarantee_proxy = interface.OssifiableProxy(PREDEPOSIT_GUARANTEE)
    predeposit_guarantee = interface.PredepositGuarantee(PREDEPOSIT_GUARANTEE)

    dg_items = [
        # 1.1. Revoke REGISTRY_ROLE on OperatorGrid from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(operator_grid, "vaults.OperatorsGrid.Registry", OLD_VAULTS_ADAPTER)
        ]),

        # 1.2. Grant REGISTRY_ROLE on OperatorGrid to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(operator_grid, "vaults.OperatorsGrid.Registry", VAULTS_ADAPTER)
        ]),

        # 1.3. Revoke VALIDATOR_EXIT_ROLE on VaultHub from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(vault_hub, "vaults.VaultHub.ValidatorExitRole", OLD_VAULTS_ADAPTER)
        ]),

        # 1.4. Grant VALIDATOR_EXIT_ROLE on VaultHub to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(vault_hub, "vaults.VaultHub.ValidatorExitRole", VAULTS_ADAPTER)
        ]),

        # 1.5. Revoke BAD_DEBT_MASTER_ROLE on VaultHub from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(vault_hub, "vaults.VaultHub.BadDebtMasterRole", OLD_VAULTS_ADAPTER)
        ]),

        # 1.6. Grant BAD_DEBT_MASTER_ROLE on VaultHub to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(vault_hub, "vaults.VaultHub.BadDebtMasterRole", VAULTS_ADAPTER)
        ]),

        # 1.7. Raise CSM (MODULE_ID = 3) stake share limit from 500 BP to 750 BP and priority exit threshold from 625 BP to 900 BP
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

        # 1.8. Grant MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus to TwoPhaseFrameConfigUpdate
        agent_forward([
            encode_oz_grant_role(
                contract=cs_hash_consensus,
                role_name="MANAGE_FRAME_CONFIG_ROLE",
                grant_to=TWO_PHASE_FRAME_CONFIG_UPDATE,
            )
        ]),

        # 1.9. Update PredepositGuarantee implementation
        agent_forward([
            (
                predeposit_guarantee_proxy.address,
                predeposit_guarantee_proxy.proxy__upgradeTo.encode_input(PREDEPOSIT_GUARANTEE_NEW_IMPL),
            )
        ]),

        # 1.10. Grant RESUME_ROLE on PredepositGuarantee to Agent
        agent_forward([
            encode_oz_grant_role(predeposit_guarantee, "PausableUntilWithRoles.ResumeRole", AGENT)
        ]),

        # 1.11. Unpause PredepositGuarantee
        agent_forward([
            (
                predeposit_guarantee_proxy.address,
                predeposit_guarantee.resume.encode_input(),
            )
        ]),

        # 1.12. Revoke RESUME_ROLE on PredepositGuarantee from Agent
        agent_forward([
            encode_oz_revoke_role(predeposit_guarantee, "PausableUntilWithRoles.ResumeRole", AGENT)
        ]),
    ]

    dg_call_script = submit_proposals([
        (dg_items, "TODO DG proposal description")
    ])

    vote_desc_items, call_script_items = zip(
        (
            "TODO 1. DG submission description",
            dg_call_script[0]
        ),
        (
            "2. Remove old ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory from Easy Track",
            remove_evmscript_factory(OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "3. Add new ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory to Easy Track",
            add_evmscript_factory(ALTER_TIERS_IN_OPERATOR_GRID_FACTORY, create_permissions(operator_grid, "alterTiers"))
        ),
        (
            "4. Remove old REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory from Easy Track",
            remove_evmscript_factory(OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "5. Add new REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory to Easy Track",
            add_evmscript_factory(
                REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY,
                create_permissions(operator_grid, "registerGroup") + create_permissions(operator_grid, "registerTiers")[2:]
            )
        ),
        (
            "6. Remove old UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY factory from Easy Track",
            remove_evmscript_factory(OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "7. Add new UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY factory to Easy Track",
            add_evmscript_factory(UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY, create_permissions(operator_grid, "updateGroupShareLimit"))
        ),
        (
            "8. Remove old SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory from Easy Track",
            remove_evmscript_factory(OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "9. Add new SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory to Easy Track",
            add_evmscript_factory(SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY, create_permissions(vaults_adapter, "setVaultJailStatus"))
        ),
        (
            "10. Remove old SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY factory from Easy Track",
            remove_evmscript_factory(OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY)
        ),
        (
            "11. Add new SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY factory to Easy Track",
            add_evmscript_factory(SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY, create_permissions(vaults_adapter, "socializeBadDebt"))
        ),
        (
            "12. Remove old FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY factory from Easy Track",
            remove_evmscript_factory(OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY)
        ),
        (
            "13. Add new FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY factory to Easy Track",
            add_evmscript_factory(FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY, create_permissions(vaults_adapter, "forceValidatorExit"))
        ),
        (
            "14. Remove old UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY factory from Easy Track",
            remove_evmscript_factory(OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY)
        ),
        (
            "15. Add new UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY factory to Easy Track",
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
