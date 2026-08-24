"""
Voting: EDF/DSM v5 upgrade on Hoodi.

1. Submit the EDF/DSM v5 upgrade to Dual Governance
# ===== Oracle committees: rotate members from EOA hot keys to EDF DelegationContracts =====
# Committees (in order): HashConsensus for AccountingOracle, HashConsensus for
# ValidatorsExitBusOracle, CSHashConsensus for CSFeeOracle, HashConsensus for
# Curated Module FeeOracle. Members (in order): Instadapp, Caliber, Chorus One,
# Chainlayer, P2P, Staking Facilities, Stakefish, bloXroute, MatrixedLink, Lido.
1.1-1.80. For each committee, for each member: remove the old member EOA and add its
          EDF DelegationContract, keeping quorum 6
# ===== DSM v5 =====
1.81. Upgrade LidoLocator implementation (points to the new DepositSecurityModule v5)
1.82. Revoke STAKING_MODULE_UNVETTING_ROLE on StakingRouter from the old DepositSecurityModule
1.83. Grant STAKING_MODULE_UNVETTING_ROLE on StakingRouter to the new DepositSecurityModule v5
1.84. Revoke TOP_UP_ROLE on TopUpGateway from the old depositor bot EOA
1.85. Grant TOP_UP_ROLE on TopUpGateway to the depositor bot DelegationContract

The new DSM v5 is deployed with the guardian set already moved to DelegationContracts:
Stakely replaces Kiln, and the extra Lido dev team guardian is removed.
"""

from typing import Dict, List, NamedTuple, Tuple

from brownie import interface, web3

from utils.agent import agent_forward
from utils.config import (
    AGENT,
    LIDO_LOCATOR,
    STAKING_ROUTER,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.dual_governance import submit_proposals
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.voting import bake_vote_items, confirm_vote_script, create_vote


# ============================== Addresses ===================================
# EDF contracts are deployed from lidofinance/core PR #1921 (branch feat/edf);

# DSM v5, https://github.com/lidofinance/core/blob/3deade5e5f1320cb1869e5990a8372b3feab31ba/deployed-hoodi.json#L510
NEW_DEPOSIT_SECURITY_MODULE = "0x8E63F0aF403ffd3Cbd5dB18b4ee632314ab49B51"
# https://github.com/lidofinance/core/blob/3deade5e5f1320cb1869e5990a8372b3feab31ba/deployed-hoodi.json#L685
NEW_LIDO_LOCATOR_IMPLEMENTATION = "0x546d76dd8D4BC0c6a26Cb71a39De5d78E222Cbf8"

# DSM v4, https://github.com/lidofinance/core/blob/26d59952672cbd5725dc5d1a7bd8948bd8762c2c/deployed-hoodi.json#L453
# (replaced by DSM v5 in deployed-hoodi.json after the EDF deploy)
OLD_DEPOSIT_SECURITY_MODULE = "0xf738F86009Ec704880c9Aa175fc5869F020FEe4e"
# https://github.com/lidofinance/core/blob/3deade5e5f1320cb1869e5990a8372b3feab31ba/scripts/upgrade/upgrade-params-hoodi.toml#L145
TOP_UP_GATEWAY = "0x10DBEb3367876826d00D21718D1d893e0fbD2956"
# Also the delegate of the depositor bot DelegationContract,
# https://github.com/lidofinance/core/blob/3deade5e5f1320cb1869e5990a8372b3feab31ba/deployed-hoodi.json#L496
DEPOSITOR_BOT_OLD_EOA = "0x9b186cE78Ddd6fF098b4a533Dd17a139e1FFeD76"
# https://github.com/lidofinance/core/blob/3deade5e5f1320cb1869e5990a8372b3feab31ba/deployed-hoodi.json#L494
DEPOSITOR_BOT_DELEGATION_CONTRACT = "0x25636798f6E716b2e6b7dEA8ED52a45271768D7A"

STAKING_MODULE_UNVETTING_ROLE = web3.keccak(text="STAKING_MODULE_UNVETTING_ROLE").hex()
TOP_UP_ROLE = web3.keccak(text="TOP_UP_ROLE").hex()

ORACLE_COMMITTEE_QUORUM = 6

NEW_DSM_GUARDIAN_QUORUM = 2
# Guardians of the new DSM v5 (EDF DelegationContracts); the new DSM is deployed
# with this set, the vote only switches the protocol to it
NEW_DSM_GUARDIANS = [
    "0x56a1B0b5074818D568D6608dc07353e81b4b53ec",  # Lido dev team
    "0x89e1bEBAf6857312bCDc313B93F29aB9cA98000f",  # P2P
    "0x901789EA029B3c7CEa47019d6Df3C5973212976D",  # Staking Facilities
    "0xa66FDd65Cfc78964A62b5Ec50E5b0Afd0e52D610",  # Blockscape
    "0x4EEC6BEd8d5E45f0a6a99F067bC5F6370f2f7221",  # Stake.fish
    "0x03224cFc446F3166c83E875095e872DD1E098076",  # Stakely (replaces Kiln)
]


class OracleCommittee(NamedTuple):
    name: str
    consensus_contract: str


class OracleMemberMapping(NamedTuple):
    name: str
    old_member: str
    delegation_contract: str


# Committee order is fixed by the EDF upgrade manifest:
# accounting-oracle, validators-exit-bus-oracle, csm-fee-oracle, curated-module-fee-oracle
ORACLE_COMMITTEES: List[OracleCommittee] = [
    OracleCommittee("HashConsensus for AccountingOracle",         "0x32EC59a78abaca3f91527aeB2008925D5AaC1eFC"),
    OracleCommittee("HashConsensus for ValidatorsExitBusOracle",  "0x30308CD8844fb2DB3ec4D056F1d475a802DCA07c"),
    OracleCommittee("CSHashConsensus for CSFeeOracle",            "0x54f74a10e4397dDeF85C4854d9dfcA129D72C637"),
    OracleCommittee("HashConsensus for Curated Module FeeOracle", "0x920883908A78c1554f682006a8aB32E62Be09F33"),
]

# Member order is fixed by the EDF upgrade manifest (oracle-member-01..10);
# the same mapping is applied to every committee.
# DelegationContract addresses source: the EDF migration tracker (confirmed by
# each operator).
ORACLE_MEMBER_MAPPINGS: List[OracleMemberMapping] = [
    OracleMemberMapping("Instadapp",          "0x43C45C2455C49eed320F463fF4f1Ece3D2BF5aE2", "0xe768fF17be4799D64649E9B8a58ee66Eb628FA93"),
    OracleMemberMapping("Caliber",            "0x948A62cc0414979dc7aa9364BA5b96ECb29f8736", "0x9F81976E461B82cfe3CAec06De8eFA8aD5543408"),
    OracleMemberMapping("Chorus One",         "0x1932f53B1457a5987791a40Ba91f71c5Efd5788F", "0x9950477b8D8154ef44745612832464C3c2155F79"),
    OracleMemberMapping("Chainlayer",         "0xf7aE520e99ed3C41180B5E12681d31Aa7302E4e5", "0xC51fE2B136a24D6eC8368C858Ae5211dc2FE0e0B"),
    OracleMemberMapping("P2P",                "0x99B2B75F490fFC9A29E4E1f5987BE8e30E690aDF", "0x43c97fEfeF1e41D6429814e2a3Ad37aA096d633e"),
    OracleMemberMapping("Staking Facilities", "0x219743f1911d84B32599BdC2Df21fC8Dba6F81a2", "0xc19a08e427351F51DA7A82136aF66d8F01931738"),
    OracleMemberMapping("Stakefish",          "0xD3b1e36A372Ca250eefF61f90E833Ca070559970", "0x9d7bFAa500b5DeC4FBab2257dfbC0cB3D5c1Fbc8"),
    OracleMemberMapping("bloXroute",          "0x4c75FA734a39f3a21C57e583c1c29942F021C6B7", "0x443e31892Ffd51f6f0Fef6DAE4ac2e2795f311Bf"),
    OracleMemberMapping("MatrixedLink",       "0xfe43A8B0b481Ae9fB1862d31826532047d2d538c", "0x89E9FCB24CC82e9A449A69f3932C70ca2FA07E1D"),
    OracleMemberMapping("Lido",               "0xcA80ee7313A315879f326105134F938676Cfd7a9", "0xAFca4694c06720Ad03037db3760a920320037217"),
]


# ============================= Description ==================================
DG_PROPOSAL_METADATA = (
    "Upgrade the protocol to EDF/DSM v5: rotate oracle committee members to "
    "Execution Delegation Framework delegation contracts, upgrade LidoLocator "
    "and switch to the new DepositSecurityModule v5"
)
DG_SUBMISSION_DESCRIPTION = "1. Submit the EDF/DSM v5 upgrade to Dual Governance"
IPFS_DESCRIPTION = """
Upgrade the Lido protocol on Hoodi to the Execution Delegation Framework (EDF) and DepositSecurityModule v5 (LIP-37).

1. Rotate all members of the four oracle committees (HashConsensus contracts for AccountingOracle, ValidatorsExitBusOracle, CSFeeOracle and Curated Module FeeOracle) from EOA hot keys to per-operator EDF DelegationContracts, keeping quorum 6. Items 1.1-1.80.
2. Upgrade the LidoLocator implementation so it points to the new DepositSecurityModule v5. The new DSM is deployed with the guardian set already moved to DelegationContracts: Stakely replaces Kiln, and the extra Lido dev team guardian is removed. Item 1.81.
3. Move STAKING_MODULE_UNVETTING_ROLE on StakingRouter from the old DepositSecurityModule to the new DepositSecurityModule v5. Items 1.82-1.83.
4. Move TOP_UP_ROLE on TopUpGateway from the old depositor bot EOA to the depositor bot DelegationContract. Items 1.84-1.85.
"""


# ============================ Pre-flight checks =============================
def _is_placeholder_address(value: str) -> bool:
    normalized = str(value).strip().lower()
    return normalized in ("", "0x0000000000000000000000000000000000000000") or normalized.startswith("todo")


def _require_configured_addresses() -> None:
    missing = []
    for name, value in [
        ("NEW_DEPOSIT_SECURITY_MODULE", NEW_DEPOSIT_SECURITY_MODULE),
        ("NEW_LIDO_LOCATOR_IMPLEMENTATION", NEW_LIDO_LOCATOR_IMPLEMENTATION),
    ]:
        if _is_placeholder_address(value):
            missing.append(name)

    for mapping in ORACLE_MEMBER_MAPPINGS:
        if _is_placeholder_address(mapping.delegation_contract):
            missing.append(f"DelegationContract for oracle member {mapping.name}")

    if missing:
        raise ValueError(
            "The following addresses are not configured yet, set them at the top of "
            f"scripts/vote_edf_hoodi.py first: {', '.join(missing)}"
        )


def _assert_no_duplicates() -> None:
    old_members = [m.old_member.lower() for m in ORACLE_MEMBER_MAPPINGS]
    new_members = [m.delegation_contract.lower() for m in ORACLE_MEMBER_MAPPINGS]
    consensus_contracts = [c.consensus_contract.lower() for c in ORACLE_COMMITTEES]
    assert len(set(old_members)) == len(old_members), "Duplicate old oracle members"
    assert len(set(new_members)) == len(new_members), "Duplicate oracle delegation contracts"
    assert len(set(consensus_contracts)) == len(consensus_contracts), "Duplicate consensus contracts"
    assert not set(old_members) & set(new_members), "Old and new oracle member sets intersect"


def _assert_committee_matches_chain(committee: OracleCommittee) -> None:
    consensus = interface.HashConsensus(committee.consensus_contract)

    quorum = consensus.getQuorum()
    assert quorum == ORACLE_COMMITTEE_QUORUM, (
        f"Quorum mismatch on {committee.name} {committee.consensus_contract}: "
        f"expected {ORACLE_COMMITTEE_QUORUM}, got {quorum}"
    )

    members = [str(m).lower() for m in consensus.getMembers()[0]]
    assert len(members) == len(ORACLE_MEMBER_MAPPINGS), (
        f"Members count mismatch on {committee.name}: "
        f"expected {len(ORACLE_MEMBER_MAPPINGS)}, got {len(members)}"
    )

    for mapping in ORACLE_MEMBER_MAPPINGS:
        assert mapping.old_member.lower() in members, (
            f"{mapping.name} old member {mapping.old_member} is not a member of {committee.name}"
        )
        assert mapping.delegation_contract.lower() not in members, (
            f"{mapping.name} DelegationContract {mapping.delegation_contract} "
            f"is already a member of {committee.name}"
        )


def _assert_state_before_vote() -> None:
    _assert_no_duplicates()
    for committee in ORACLE_COMMITTEES:
        _assert_committee_matches_chain(committee)

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    assert staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE), (
        "Old DSM does not hold STAKING_MODULE_UNVETTING_ROLE"
    )
    assert not staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE), (
        "New DSM already holds STAKING_MODULE_UNVETTING_ROLE"
    )

    locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    assert str(locator_proxy.proxy__getImplementation()).lower() != NEW_LIDO_LOCATOR_IMPLEMENTATION.lower(), (
        "LidoLocator already points to the new implementation"
    )

    top_up_gateway = interface.TopUpGateway(TOP_UP_GATEWAY)
    assert top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_OLD_EOA), (
        "Old depositor bot EOA does not hold TOP_UP_ROLE"
    )
    assert not top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_DELEGATION_CONTRACT), (
        "Depositor bot DelegationContract already holds TOP_UP_ROLE"
    )

    # The vote does not change DSM guardians, so verify the new DSM is deployed
    # with the expected guardian set, owner and protocol links before switching
    # the protocol to it
    old_dsm = interface.DepositSecurityModule(OLD_DEPOSIT_SECURITY_MODULE)
    new_dsm = interface.DepositSecurityModule(NEW_DEPOSIT_SECURITY_MODULE)
    assert new_dsm.VERSION() == 5, "New DSM version is not 5"
    assert str(new_dsm.getOwner()).lower() == AGENT.lower(), "New DSM owner is not the Agent"
    assert str(new_dsm.STAKING_ROUTER()).lower() == STAKING_ROUTER.lower(), "New DSM staking router mismatch"
    assert str(new_dsm.DEPOSIT_CONTRACT()).lower() == str(old_dsm.DEPOSIT_CONTRACT()).lower(), (
        "New DSM deposit contract mismatch"
    )
    assert not new_dsm.isDepositsPaused(), "New DSM deposits are paused"
    assert new_dsm.getGuardianQuorum() == NEW_DSM_GUARDIAN_QUORUM, "New DSM guardian quorum mismatch"
    new_dsm_guardians = {str(g).lower() for g in new_dsm.getGuardians()}
    assert new_dsm_guardians == {g.lower() for g in NEW_DSM_GUARDIANS}, "New DSM guardian set mismatch"


# ================================ Main ======================================
def get_edf_upgrade_calls() -> List[Tuple[str, str]]:
    """Return the raw upgrade calls in the order of EDFUpgradeVoteScript._getVoteItems
    (without the EDFUpgradeTemplate startUpgrade/finishUpgrade calls)."""
    _require_configured_addresses()
    _assert_state_before_vote()

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    top_up_gateway = interface.TopUpGateway(TOP_UP_GATEWAY)

    calls: List[Tuple[str, str]] = []

    # 1.1-1.80. Rotate oracle committee members
    for committee in ORACLE_COMMITTEES:
        consensus = interface.HashConsensus(committee.consensus_contract)
        for mapping in ORACLE_MEMBER_MAPPINGS:
            calls.append(
                (
                    consensus.address,
                    consensus.removeMember.encode_input(mapping.old_member, ORACLE_COMMITTEE_QUORUM),
                )
            )
            calls.append(
                (
                    consensus.address,
                    consensus.addMember.encode_input(mapping.delegation_contract, ORACLE_COMMITTEE_QUORUM),
                )
            )

    # 1.81. Upgrade LidoLocator implementation
    calls.append(
        (locator_proxy.address, locator_proxy.proxy__upgradeTo.encode_input(NEW_LIDO_LOCATOR_IMPLEMENTATION))
    )

    # 1.82. Revoke STAKING_MODULE_UNVETTING_ROLE from the old DSM
    calls.append(
        (
            staking_router.address,
            staking_router.revokeRole.encode_input(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE),
        )
    )

    # 1.83. Grant STAKING_MODULE_UNVETTING_ROLE to the new DSM
    calls.append(
        (
            staking_router.address,
            staking_router.grantRole.encode_input(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE),
        )
    )

    # 1.84. Revoke TOP_UP_ROLE from the old depositor bot EOA
    calls.append(
        (
            top_up_gateway.address,
            top_up_gateway.revokeRole.encode_input(TOP_UP_ROLE, DEPOSITOR_BOT_OLD_EOA),
        )
    )

    # 1.85. Grant TOP_UP_ROLE to the depositor bot DelegationContract
    calls.append(
        (
            top_up_gateway.address,
            top_up_gateway.grantRole.encode_input(TOP_UP_ROLE, DEPOSITOR_BOT_DELEGATION_CONTRACT),
        )
    )

    expected_count = 2 * len(ORACLE_COMMITTEES) * len(ORACLE_MEMBER_MAPPINGS) + 5
    assert len(calls) == expected_count, f"Expected {expected_count} upgrade calls, got {len(calls)}"

    return calls


def get_dg_items() -> List[Tuple[str, str]]:
    # The whole upgrade is forwarded by the Agent in a single call
    return [agent_forward(get_edf_upgrade_calls())]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    dg_call_script = submit_proposals([(get_dg_items(), DG_PROPOSAL_METADATA)])

    vote_desc_items = [DG_SUBMISSION_DESCRIPTION]
    call_script_items = [dg_call_script[0]]

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent
        else upload_vote_ipfs_description(IPFS_DESCRIPTION)
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
