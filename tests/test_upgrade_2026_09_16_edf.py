from brownie import chain, interface, web3, accounts, convert, reverts
from brownie.network.event import EventDict
from brownie.network.transaction import TransactionReceipt
from dataclasses import dataclass
from eth_abi import encode as encode_abi
import pytest

from utils.test.tx_tracing_helpers import (
    add_event_emitter,
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events,
)
from utils.tx_tracing import tx_events_from_receipt
from utils.evm_script import encode_call_script
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.easy_track import (
    EVMScriptFactoryAdded,
    validate_evmscript_factory_added_event,
)
from utils.test.event_validators.hash_consensus import (
    validate_hash_consensus_member_added,
    validate_hash_consensus_member_removed,
)
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.proxy import validate_proxy_upgrade_event
from utils.easy_track import create_permissions

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
import scripts.upgrade_2026_09_16_edf as vote_script
from scripts.upgrade_2026_09_16_edf import (
    start_vote,
    get_vote_items,
    get_dg_items,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
# Addresses are hardcoded here on purpose, independently from the vote script,
# as a cross-check of the vote script data.
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"

# Filled independently from scripts/upgrade_2026_09_16_edf.py (do not copy-paste from
# the script) - the fixture cross-checks both copies against each other
# EDF core contracts, https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/25
# DSM v5, https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L482
NEW_DEPOSIT_SECURITY_MODULE = "0x39BB5d491e98A44D1bfe8047A737a81E296a63E0"
# https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L623
NEW_LIDO_LOCATOR_IMPLEMENTATION = "0x60E09F1791F1168d0450E4F100616B4a3F95119C"

LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
# DSM v4 and TopUpGateway, https://docs.lido.fi/deployed-contracts/#core-protocol
OLD_DEPOSIT_SECURITY_MODULE = "0xF573E9E3de1f86B085417ab294f56E7920B4e9Be"
TOP_UP_GATEWAY = "0x3FC2C71579D80790Aaa3fc7Be8B66ac39dC57374"
# The sole TOP_UP_ROLE holder, the depositor bot, https://docs.lido.fi/deployed-contracts/#bots
DEPOSITOR_BOT_OLD_EOA = "0xF82aC5937A20dC862F9bc0668779031E06000f17"

# EDF DelegationFactory, https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/10
DELEGATION_FACTORY = "0xD990770eB2B4b6062EDdB06892fF179C693b46e6"
# https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L361
DELEGATION_FACTORY_RUNTIME_CODE_HASH = "0x0898ad72098301345c44103c8aca22cd8a0a02a339bffe222c6487ec25ff3591"

ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
LIDO = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
EASYTRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
EASYTRACK_EVMSCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
# Easy Track factory for deposit reserve target management by CMC, https://research.lido.fi/t/proposal-add-easy-track-factory-for-deposit-reserve-target-management-by-cmc/11827/6
SET_DEPOSITS_RESERVE_TARGET_FACTORY = "0x62E9Dc68BDCBC46362f40e0bb9c154C9a42E62b0"
# The CMC multisig (5/9) and the factory cap, https://research.lido.fi/t/proposal-add-easy-track-factory-for-deposit-reserve-target-management-by-cmc/11827
SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER = "0x2570e0b22AD904501dfB0d49575991ACB801dD91"
SET_DEPOSITS_RESERVE_TARGET_MAX = 9600 * 10**18

STAKING_MODULE_UNVETTING_ROLE = web3.keccak(text="STAKING_MODULE_UNVETTING_ROLE").hex()
TOP_UP_ROLE = web3.keccak(text="TOP_UP_ROLE").hex()
BUFFER_RESERVE_MANAGER_ROLE = web3.keccak(text="BUFFER_RESERVE_MANAGER_ROLE")
ERC1271_INTERFACE_ID = "0x1626ba7e"

ORACLE_COMMITTEE_QUORUM = 5
OLD_DSM_VERSION = 4
NEW_DSM_VERSION = 5
DSM_GUARDIAN_QUORUM = 4
DELEGATION_CONTRACT_COOLDOWN = 172800


@dataclass(frozen=True)
class DelegationContract:
    name: str
    address: str
    owner: str
    delegate: str
    cooldown: int
    runtime_code_hash: str


@dataclass(frozen=True)
class OracleCommittee:
    name: str
    consensus_contract: str


@dataclass(frozen=True)
class OracleMemberMapping:
    name: str
    old_member: str
    delegation_contract: DelegationContract


@dataclass(frozen=True)
class DsmGuardianMapping:
    name: str
    old_guardian: str
    delegation_contract: DelegationContract


# AccountingOracle and ValidatorsExitBusOracle: https://docs.lido.fi/deployed-contracts/#oracle-contracts
# CSFeeOracle: https://docs.lido.fi/deployed-contracts/#community-staking-module
# Curated Module FeeOracle: https://docs.lido.fi/deployed-contracts/#curated-module-v2
ORACLE_COMMITTEES = [
    OracleCommittee(name="HashConsensus for AccountingOracle", consensus_contract="0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"),
    OracleCommittee(name="HashConsensus for ValidatorsExitBusOracle", consensus_contract="0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"),
    OracleCommittee(name="CSHashConsensus for CSFeeOracle", consensus_contract="0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"),
    OracleCommittee(name="HashConsensus for Curated Module FeeOracle", consensus_contract="0x902D64c93F6595339aA46105627a085591051aFb"),
]

# Old members are the current committee members (ORACLE_COMMITTEE in configs/config_mainnet.py),
# DelegationContracts are announced by the operators on the forum
ORACLE_MEMBER_MAPPINGS = [
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/20
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L414-L420
    OracleMemberMapping(
        name="Instadapp",
        old_member="0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12",
        delegation_contract=DelegationContract(
            name="Instadapp oracle",
            address="0xE75A431A98487DC69A14Bdd13d858E3238e9C1b3",
            owner="0x772E9D0387671Ce641f17FD1fCFB3a9cE8ED05fB",
            delegate="0x5595033F304217aFDB8ffB35E42C22B72184730b",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0xfa9e481ba85fd64689081b8512c6cd5d8be5f4a9e0583c966a0b40c51feeb3d3",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/18
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L421-L427
    OracleMemberMapping(
        name="Caliber",
        old_member="0x4118DAD7f348A4063bD15786c299De2f3B1333F3",
        delegation_contract=DelegationContract(
            name="Caliber oracle",
            address="0xc77d0Bf3AA4778E36a89CDC8bbc9c34d8060637d",
            owner="0x84225B558e224dc6C38f4eda1d3591fE6b5E34aa",
            delegate="0x82A821E8a2585D1AC8f346BE7Da6995490d21Ca6",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0xb8b55cfe3617fd6a463c1e3d25b30cb722ba1f472aff4fd9784f4cae8559253e",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/13
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L428-L434
    OracleMemberMapping(
        name="Staking Facilities",
        old_member="0x404335BcE530400a5814375E7Ec1FB55fAff3eA2",
        delegation_contract=DelegationContract(
            name="Staking Facilities oracle",
            address="0xc7442d4d8F3FfEa0fA4a18Ad3062c8137cE21749",
            owner="0x035AcCF7E230f32028a1134134A035dda567C86e",
            delegate="0x7abC999C7E1f22a7E12b2A1024bC17676FE18b4b",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x66db96aa7e7e8a80298ef9cd30a114a20a6704e3ccf4885e4e89105eb839dbf3",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/22
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L435-L441
    OracleMemberMapping(
        name="Chorus One",
        old_member="0x8dB977C13CAA938BC58464bFD622DF0570564b78",
        delegation_contract=DelegationContract(
            name="Chorus One oracle",
            address="0x56B3eA8016Da18C6E8CD8135492d242F0dE0DBBC",
            owner="0x6057526Da2Dc9Bd23a3C6F1b15C74De2D7593378",
            delegate="0x5416CAAb6f37BF81cb2dc7ce0a363AfB9DD92d57",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x91c0c609df951e9a9e17b16c09a98fbf20f048a5f0775805b4bb319c076ba932",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/17
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L442-L448
    OracleMemberMapping(
        name="P2P",
        old_member="0x007DE4a5F7bc37E2F26c0cb2E8A95006EE9B89b5",
        delegation_contract=DelegationContract(
            name="P2P oracle",
            address="0x4E3F2DEeb59eB9a205D82D17647b3e56422e0FEe",
            owner="0x1E8518cd5835B6775F902e1451a3Dd7b02EB3e8A",
            delegate="0x565F04cB319EC2295E1fcbBbe5F708687FFcCE75",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x4a75c94b356c64241dea7252089f7bb3a557b44a6a615c17db7cb25eae827e5c",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/14
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L449-L455
    OracleMemberMapping(
        name="ChainLayer",
        old_member="0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf",
        delegation_contract=DelegationContract(
            name="ChainLayer oracle",
            address="0xd524101C3c40f71Fce7B9312D299603880a06Bdb",
            owner="0x48D10eaec45e330003E62115e56d2A05F29eca70",
            delegate="0x4D3aD7E8e591d389B612Fc063f53837E284d3F86",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0xaae023229e81acfdbb4675175a0bc9f945704a9217f5530b8fd8ec22dcce9fbd",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/23
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L456-L462
    OracleMemberMapping(
        name="bloXroute",
        old_member="0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8",
        delegation_contract=DelegationContract(
            name="bloXroute oracle",
            address="0x99Cd2EF33040879D40BBC77Df81863D97f13C64d",
            owner="0x9462A9FfF5646d0b6517D8eac49de49277e89dB9",
            delegate="0x375ABa35EA2011Af97b51bd395494C827d1C39BD",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0xe56a914a089d78f7734cb896e29f532819ac2e8a63bd1a111df997297fe7426a",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/19
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L463-L469
    OracleMemberMapping(
        name="MatrixedLink",
        old_member="0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9",
        delegation_contract=DelegationContract(
            name="MatrixedLink oracle",
            address="0xC4f2704273598d51A0ec76A31C12553ec8f5A891",
            owner="0x60D78785B763374bd552F5cE270da77781C6066C",
            delegate="0xC10258969442c7957351A0ddc8194D2685B2a2c2",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x2bbbaab03b813645a5da96cee20f10449dd26e88f12f4072e43c7621144eb0cb",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/15
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L470-L476
    OracleMemberMapping(
        name="Stakefish",
        old_member="0x042a9e5acCfa17e28300F1b5967f20891E973922",
        delegation_contract=DelegationContract(
            name="Stakefish oracle",
            address="0x5e8Ed9f10307eD6FA793A347e4D0f407D00B9C6f",
            owner="0x3F7c24Cc2C91E8BEb20498E61b51a696ffb2AbA5",
            delegate="0x2aE828F10DfeE5b4c42f6E61D3d30033D4520753",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x5eb9788f7b86ec4f846121b1a7374250807579aaef19b2a129d8cf76cdb3e8f6",
        ),
    ),
]

# Old DSM v4 guardians (EOA hot keys, DSM_GUARDIANS in configs/config_mainnet.py) and the
# DelegationContracts of the new DSM v5 announced by the operators on the forum;
# Stakely takes the seat of Kiln
DSM_GUARDIAN_MAPPINGS = [
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/21
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L365-L371
    DsmGuardianMapping(
        name="Lido dev team",
        old_guardian="0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1",
        delegation_contract=DelegationContract(
            name="Lido dev team guardian",
            address="0x915F0Fa50E1af761B113b41c79ab33Bf4734C36E",
            owner="0x2E6e175F57D7a18b3CA5490844034600FC18EF83",
            delegate="0x5ecf14e7a3831D44e2F7d4542Ba98C6c96E47420",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x46a3f2e13ebb9ff53d4ae49f460c52fcf1213793c6fa60849f6fd595cc90db09",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/16
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L372-L378
    DsmGuardianMapping(
        name="P2P",
        old_guardian="0xa56b128Ea2Ea237052b0fA2a96a387C0E43157d8",
        delegation_contract=DelegationContract(
            name="P2P guardian",
            address="0xe387Ba1d5C9f6306eCe9ac949C7fB6233dD5411E",
            owner="0x1E8518cd5835B6775F902e1451a3Dd7b02EB3e8A",
            delegate="0xAEbd3E0c29111C02166FB2d560f7158a6ccE6841",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x4a75c94b356c64241dea7252089f7bb3a557b44a6a615c17db7cb25eae827e5c",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/13
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L379-L385
    DsmGuardianMapping(
        name="Staking Facilities",
        old_guardian="0xf82D88217C249297C6037BA77CE34b3d8a90ab43",
        delegation_contract=DelegationContract(
            name="Staking Facilities guardian",
            address="0x35506190Ca6df385aA6Bc4a970646dd4f49426c1",
            owner="0x3d49967d09637B83E465Cc32b1C5d968e3d34eA8",
            delegate="0x06d6c4F26354aA1426c0Abd79A5f18A5d5fF684f",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x9127ec398c753b1ac3565b4b1c79d61ec35eb37856d15281a270adb128bda876",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/11
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L386-L392
    DsmGuardianMapping(
        name="Blockscape",
        old_guardian="0x7912Fa976BcDe9c2cf728e213e892AD7588E6AaF",
        delegation_contract=DelegationContract(
            name="Blockscape guardian",
            address="0xDc1579636686C082fc3b00B9EB25259A110D0C44",
            owner="0xFcBC1BB96b3F521fe7BFD1E2E309eC032F078fDE",
            delegate="0x6aF45f506fD171994D26d014Fc079137532Db219",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0x1df72bae32352508f084c3818b72905aece6fb426e44ed6a549b7ffbb551b63d",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/15
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L393-L399
    DsmGuardianMapping(
        name="Stake.fish",
        old_guardian="0x4B87F16B8d32cb5a859a4C48a88edB5adBe3498E",
        delegation_contract=DelegationContract(
            name="Stake.fish guardian",
            address="0x031E597BcF680f1f2293b119b4b2B14096B15497",
            owner="0xaB61339Cb8A5BBED2dEaC4D2c6E71B912919aBdB",
            delegate="0xA4512893C5B8BCD8E7AE1cAa56b8402951720D14",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0xe4bab4398f923579cc5e6cc6a57dc803d31fd402dc0ae772c26c996d8ee0e259",
        ),
    ),
    # https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/12
    # https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L400-L406
    DsmGuardianMapping(
        name="Stakely (replaces Kiln)",
        old_guardian="0x6d22aE126eB2c37F67a1391B37FF4f2863e61389",  # Kiln (replaced by Stakely)
        delegation_contract=DelegationContract(
            name="Stakely guardian (replaces Kiln)",
            address="0x6A22d74a816662078f2371A7138E7614874cd61d",
            owner="0xce0F8F5019856D79840F9463b5D05c44c7d9B791",
            delegate="0xc04c1979e37e53FD21E40bd089D311EEfFdb4E00",
            cooldown=DELEGATION_CONTRACT_COOLDOWN,
            runtime_code_hash="0xa3a98836267e83dca0cd885e4487e2caea164622512fe0ab4879341b22399cea",
        ),
    ),
]

# https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/24
# https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L407-L413
DEPOSITOR_BOT_DELEGATION_CONTRACT = DelegationContract(
    name="Depositor bot",
    address="0x6Aa249bA53A3abcaC52F91146583B3eE2Ee4C7F5",
    owner="0x2E6e175F57D7a18b3CA5490844034600FC18EF83",
    delegate="0x2df4013EF30b09100A027192E700114cD0D13900",
    cooldown=DELEGATION_CONTRACT_COOLDOWN,
    runtime_code_hash="0x46a3f2e13ebb9ff53d4ae49f460c52fcf1213793c6fa60849f6fd595cc90db09",
)

ALL_DELEGATION_CONTRACTS = (
    [m.delegation_contract for m in ORACLE_MEMBER_MAPPINGS]
    + [m.delegation_contract for m in DSM_GUARDIAN_MAPPINGS]
    + [DEPOSITOR_BOT_DELEGATION_CONTRACT]
)


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = 205
# The next DG proposal id, timelock.getProposalsCount() + 1 at the time of writing
EXPECTED_DG_PROPOSAL_ID = 14
EXPECTED_VOTE_EVENTS_COUNT = 2
# 4 committees * 9 members * 2 (remove + add) + locator upgrade
# + unvetting role revoke + grant + top-up role revoke + grant
# + buffer reserve manager role grant, all inside a single Agent.forward
EXPECTED_DG_EVENTS_FROM_AGENT = 78
EXPECTED_DG_EVENTS_COUNT = 1
IPFS_DESCRIPTION_HASH = "bafkreigymggpsrbc7fi53wqqls4thoczvvgpz6ohzlqax2ljeg2f5o74wi"
DG_PROPOSAL_METADATA = (
    "Adopt the Execution Delegation Framework (LIP-37): reassign the Oracle committee member addresses, "
    "the DSM guardian seats, and the depositor bot to DelegationContracts, switch to the redeployed "
    "DepositSecurityModule, and update the related protocol permissions, including the buffer-reserve "
    "manager role used to adjust the Deposit Reserve Target via Easy Track."
)


# ============================================================================
# ================================ Helpers ===================================
# ============================================================================
def _event_list(events: EventDict, name: str):
    return [event_item for event_item in events if event_item.name == name]


def _single_event(events: EventDict, name: str):
    items = _event_list(events, name)
    assert len(items) == 1, f"Expected exactly one {name} event, got {len(items)}"
    return items[0]


def _normalize_role(role_value) -> str:
    if isinstance(role_value, bytes):
        return role_value.hex().replace("0x", "")

    if hasattr(role_value, "hex") and callable(role_value.hex):
        return role_value.hex().replace("0x", "")

    return str(role_value).replace("0x", "")


def _strip_hex_prefix(value: str) -> str:
    return str(value).lower().replace("0x", "")


def _assert_emitted_by(event_item, emitted_by: str) -> None:
    assert convert.to_address(event_item["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}, got {event_item['_emitted_by']}"


def _raw_event_values(raw_event: dict) -> dict:
    return {item["name"]: item["value"] for item in raw_event["data"]}


def _locator_addresses(locator) -> dict:
    """Snapshot every zero-arg address getter the current locator implementation responds to."""
    addresses = {}
    for entry in locator.abi:
        if entry.get("type") != "function" or entry.get("inputs") or entry.get("stateMutability") != "view":
            continue
        outputs = entry.get("outputs") or []
        if len(outputs) != 1 or outputs[0].get("type") != "address":
            continue
        try:
            addresses[entry["name"]] = str(getattr(locator, entry["name"])())
        except Exception:
            continue
    return addresses


def _assert_delegation_contract(contract: DelegationContract) -> None:
    """The same checks as EDFUpgradeTemplate._validateFactoryAndDelegationContracts in lidofinance/core:
    the contract is the DelegationFactory deployment recorded in deployed-mainnet.json
    (the runtime code hash reflects the immutable owner and cooldown; the delegate is
    mutable by the owner and is checked on-chain), it is live and it supports ERC-1271
    so it can sign oracle reports and DSM messages."""
    code = web3.eth.get_code(contract.address)
    assert len(code) > 0, f"{contract.name}: no code at {contract.address}"
    assert _strip_hex_prefix(web3.keccak(code).hex()) == _strip_hex_prefix(contract.runtime_code_hash), (
        f"{contract.name}: runtime code hash mismatch"
    )

    delegation = interface.DelegationContract(contract.address)
    assert convert.to_address(delegation.owner()) == convert.to_address(contract.owner), f"{contract.name}: owner"
    assert convert.to_address(delegation.getDelegate()) == convert.to_address(contract.delegate), (
        f"{contract.name}: delegate"
    )
    assert delegation.getCooldown() == contract.cooldown, f"{contract.name}: cooldown"
    assert not delegation.isTerminated(), f"{contract.name}: terminated"
    assert delegation.supportsInterface(ERC1271_INTERFACE_ID), f"{contract.name}: no ERC-1271 support"


def _assert_all_delegation_contracts() -> None:
    factory_code = web3.eth.get_code(DELEGATION_FACTORY)
    assert _strip_hex_prefix(web3.keccak(factory_code).hex()) == _strip_hex_prefix(
        DELEGATION_FACTORY_RUNTIME_CODE_HASH
    ), "DelegationFactory runtime code hash mismatch"
    for contract in ALL_DELEGATION_CONTRACTS:
        _assert_delegation_contract(contract)


def _group_agent_dg_events_from_receipt(receipt: TransactionReceipt, timelock: str, agent: str) -> list[EventDict]:
    """Group DG proposal events by the Agent's inner call script items (single Agent.forward)."""
    events = tx_events_from_receipt(receipt)

    assert len(events) >= 1, "Unexpected events count"
    assert (
        convert.to_address(events[-1]["address"]) == convert.to_address(timelock)
        and events[-1]["name"] == "ProposalExecuted"
    ), "Unexpected Dual Governance service event"

    groups = []
    current_group = None

    for event in events[:-1]:
        event_values = _raw_event_values(event) if event["name"] == "LogScriptCall" else {}
        is_start_of_new_group = event["name"] == "LogScriptCall" and convert.to_address(
            event_values["src"]
        ) == convert.to_address(agent)

        if is_start_of_new_group:
            current_group = []
            groups.append(current_group)

        assert current_group is not None, "Unexpected DG events chain"
        current_group.append(add_event_emitter(event))

    return [EventDict(group) for group in groups]


def _assert_test_data_matches_script() -> None:
    """The test constants are an independent copy of the vote data, both copies must agree."""
    # Cross-check the deploy data against the vote script copies
    assert NEW_DEPOSIT_SECURITY_MODULE.lower() == vote_script.NEW_DEPOSIT_SECURITY_MODULE.lower()
    assert NEW_LIDO_LOCATOR_IMPLEMENTATION.lower() == vote_script.NEW_LIDO_LOCATOR_IMPLEMENTATION.lower()
    assert OLD_DEPOSIT_SECURITY_MODULE.lower() == vote_script.OLD_DEPOSIT_SECURITY_MODULE.lower()
    assert TOP_UP_GATEWAY.lower() == vote_script.TOP_UP_GATEWAY.lower()
    assert DEPOSITOR_BOT_OLD_EOA.lower() == vote_script.DEPOSITOR_BOT_OLD_EOA.lower()
    assert DELEGATION_FACTORY.lower() == vote_script.DELEGATION_FACTORY.lower()
    assert SET_DEPOSITS_RESERVE_TARGET_FACTORY.lower() == vote_script.SET_DEPOSITS_RESERVE_TARGET_FACTORY.lower()
    assert (
        SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER.lower()
        == vote_script.SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER.lower()
    )
    assert ORACLE_COMMITTEE_QUORUM == vote_script.ORACLE_COMMITTEE_QUORUM
    assert DSM_GUARDIAN_QUORUM == vote_script.DSM_GUARDIAN_QUORUM

    assert len(ORACLE_COMMITTEES) == len(vote_script.ORACLE_COMMITTEES)
    for test_committee, script_committee in zip(ORACLE_COMMITTEES, vote_script.ORACLE_COMMITTEES):
        assert test_committee.consensus_contract.lower() == script_committee.consensus_contract.lower()

    assert len(ORACLE_MEMBER_MAPPINGS) == len(vote_script.ORACLE_MEMBER_MAPPINGS)
    for test_mapping, script_mapping in zip(ORACLE_MEMBER_MAPPINGS, vote_script.ORACLE_MEMBER_MAPPINGS):
        assert test_mapping.old_member.lower() == script_mapping.old_member.lower()
        assert test_mapping.delegation_contract.address.lower() == script_mapping.delegation_contract.address.lower()

    assert len(DSM_GUARDIAN_MAPPINGS) == len(vote_script.DSM_GUARDIAN_MAPPINGS)
    for test_mapping, script_mapping in zip(DSM_GUARDIAN_MAPPINGS, vote_script.DSM_GUARDIAN_MAPPINGS):
        assert test_mapping.old_guardian.lower() == script_mapping.old_guardian.lower()
        assert test_mapping.delegation_contract.address.lower() == script_mapping.delegation_contract.address.lower()
    assert len(ALL_DELEGATION_CONTRACTS) == len(vote_script.ALL_DELEGATION_CONTRACTS)
    for test_contract, script_contract in zip(ALL_DELEGATION_CONTRACTS, vote_script.ALL_DELEGATION_CONTRACTS):
        assert test_contract.address.lower() == script_contract.address.lower()
        assert test_contract.owner.lower() == script_contract.owner.lower()
        assert test_contract.delegate.lower() == script_contract.delegate.lower()
        assert test_contract.cooldown == script_contract.cooldown
        assert _strip_hex_prefix(test_contract.runtime_code_hash) == _strip_hex_prefix(script_contract.runtime_code_hash)


# ============================================================================
# =========================== Event validators ===============================
# ============================================================================
# ============================================================================
# =============================== Fixtures ===================================
# ============================================================================
@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    dg_items = get_dg_items()

    # Convert each dg_item to the expected format
    proposal_calls = []
    for dg_item in dg_items:
        target, data = dg_item  # agent_forward returns (target, data)
        proposal_calls.append({
            "target": target,
            "value": 0,
            "data": data
        })

    return proposal_calls


# ============================================================================
# ================================= Test =====================================
# ============================================================================
def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

    new_dsm = interface.DepositSecurityModule(NEW_DEPOSIT_SECURITY_MODULE)
    old_dsm = interface.DepositSecurityModule(OLD_DEPOSIT_SECURITY_MODULE)
    locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    top_up_gateway = interface.TopUpGateway(TOP_UP_GATEWAY)
    acl = interface.ACL(ACL)
    easy_track = interface.EasyTrack(EASYTRACK)

    _assert_test_data_matches_script()
    # Every DelegationContract the vote relies on must be the factory deployment
    # from the manifest, before and after the upgrade
    _assert_all_delegation_contracts()


    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        if EXPECTED_VOTE_ID is not None:
            assert vote_id == EXPECTED_VOTE_ID
    elif EXPECTED_VOTE_ID is not None and voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
    onchain_script = voting.getVote(vote_id)["script"]
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()


    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        # Acceptance tests (before voting state)
        assert not acl.hasPermission(EASYTRACK_EVMSCRIPT_EXECUTOR, LIDO, BUFFER_RESERVE_MANAGER_ROLE)
        assert SET_DEPOSITS_RESERVE_TARGET_FACTORY not in easy_track.getEVMScriptFactories()


        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        # Acceptance tests (after voting state)
        assert SET_DEPOSITS_RESERVE_TARGET_FACTORY in easy_track.getEVMScriptFactories()


        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            # 1. Submit a Dual Governance proposal to adopt the Execution Delegation Framework (LIP-37)
            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata=DG_PROPOSAL_METADATA,
                proposal_calls=dual_governance_proposal_calls,
            )

        # 2. Add SetDepositsReserveTarget EVM script factory to EasyTrack
        validate_evmscript_factory_added_event(
            vote_events[1],
            EVMScriptFactoryAdded(
                factory_addr=SET_DEPOSITS_RESERVE_TARGET_FACTORY,
                permissions=create_permissions(interface.Lido(LIDO), "setDepositsReserveTarget"),
            ),
            emitted_by=EASYTRACK,
        )


    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        locator_addresses_before = None
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================

            # Acceptance tests (before DG state)
            for committee in ORACLE_COMMITTEES:
                consensus = interface.HashConsensus(committee.consensus_contract)
                assert consensus.getQuorum() == ORACLE_COMMITTEE_QUORUM
                members = [str(m).lower() for m in consensus.getMembers()[0]]
                assert len(members) == len(ORACLE_MEMBER_MAPPINGS)
                for mapping in ORACLE_MEMBER_MAPPINGS:
                    assert mapping.old_member.lower() in members
                    assert mapping.delegation_contract.address.lower() not in members

            # The roles are moved from their only holders
            assert staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE)
            assert not staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE)
            assert staking_router.getRoleMemberCount(STAKING_MODULE_UNVETTING_ROLE) == 1
            assert top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_OLD_EOA)
            assert not top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_DELEGATION_CONTRACT.address)
            assert top_up_gateway.getRoleMemberCount(TOP_UP_ROLE) == 1

            assert str(locator_proxy.proxy__getImplementation()).lower() != NEW_LIDO_LOCATOR_IMPLEMENTATION.lower()

            # Snapshot the full locator address registry - the upgrade must change
            # only the depositSecurityModule entry
            locator_addresses_before = _locator_addresses(interface.LidoLocator(LIDO_LOCATOR))
            assert locator_addresses_before["depositSecurityModule"].lower() == OLD_DEPOSIT_SECURITY_MODULE.lower()

            # Old DSM v4 holds the EOA guardian set
            assert old_dsm.VERSION() == OLD_DSM_VERSION
            assert old_dsm.getGuardianQuorum() == DSM_GUARDIAN_QUORUM
            old_dsm_guardians = {str(g).lower() for g in old_dsm.getGuardians()}
            assert old_dsm_guardians == {m.old_guardian.lower() for m in DSM_GUARDIAN_MAPPINGS}

            # New DSM v5 is deployed with the DelegationContract guardian set
            assert new_dsm.VERSION() == NEW_DSM_VERSION
            assert convert.to_address(new_dsm.getOwner()) == convert.to_address(AGENT)
            assert convert.to_address(new_dsm.STAKING_ROUTER()) == convert.to_address(STAKING_ROUTER)
            assert convert.to_address(new_dsm.DEPOSIT_CONTRACT()) == convert.to_address(old_dsm.DEPOSIT_CONTRACT())
            assert not new_dsm.isDepositsPaused()
            assert new_dsm.getPauseIntentValidityPeriodBlocks() == old_dsm.getPauseIntentValidityPeriodBlocks()
            assert new_dsm.getMaxOperatorsPerUnvetting() == old_dsm.getMaxOperatorsPerUnvetting()
            assert new_dsm.getGuardianQuorum() == DSM_GUARDIAN_QUORUM
            new_dsm_guardians = {str(g).lower() for g in new_dsm.getGuardians()}
            assert new_dsm_guardians == {m.delegation_contract.address.lower() for m in DSM_GUARDIAN_MAPPINGS}



            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)

                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT


                # The whole upgrade is a single Agent.forward, validate its inner calls one by one
                agent_events = _group_agent_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    agent=AGENT,
                )
                assert len(agent_events) == EXPECTED_DG_EVENTS_FROM_AGENT

                event_index = 0

                # 1.1-1.72. Rotate oracle committee members
                for committee in ORACLE_COMMITTEES:
                    for mapping in ORACLE_MEMBER_MAPPINGS:
                        validate_hash_consensus_member_removed(
                            agent_events[event_index],
                            member=mapping.old_member,
                            new_quorum=ORACLE_COMMITTEE_QUORUM,
                            new_total_members=len(ORACLE_MEMBER_MAPPINGS) - 1,
                            emitted_by=committee.consensus_contract,
                        )
                        event_index += 1

                        validate_hash_consensus_member_added(
                            agent_events[event_index],
                            member=mapping.delegation_contract.address,
                            new_quorum=ORACLE_COMMITTEE_QUORUM,
                            new_total_members=len(ORACLE_MEMBER_MAPPINGS),
                            emitted_by=committee.consensus_contract,
                        )
                        event_index += 1

                # 1.73. Upgrade LidoLocator implementation
                validate_proxy_upgrade_event(
                    agent_events[event_index],
                    NEW_LIDO_LOCATOR_IMPLEMENTATION,
                    emitted_by=LIDO_LOCATOR,
                )
                event_index += 1

                # 1.74. Revoke STAKING_MODULE_UNVETTING_ROLE from the old DSM
                validate_revoke_role_event(
                    agent_events[event_index],
                    role=STAKING_MODULE_UNVETTING_ROLE,
                    revoke_from=OLD_DEPOSIT_SECURITY_MODULE,
                    sender=AGENT,
                    emitted_by=STAKING_ROUTER,
                )
                event_index += 1

                # 1.75. Grant STAKING_MODULE_UNVETTING_ROLE to the new DSM
                validate_grant_role_event(
                    agent_events[event_index],
                    role=STAKING_MODULE_UNVETTING_ROLE,
                    grant_to=NEW_DEPOSIT_SECURITY_MODULE,
                    sender=AGENT,
                    emitted_by=STAKING_ROUTER,
                )
                event_index += 1

                # 1.76. Revoke TOP_UP_ROLE from the old depositor bot EOA
                validate_revoke_role_event(
                    agent_events[event_index],
                    role=TOP_UP_ROLE,
                    revoke_from=DEPOSITOR_BOT_OLD_EOA,
                    sender=AGENT,
                    emitted_by=TOP_UP_GATEWAY,
                )
                event_index += 1

                # 1.77. Grant TOP_UP_ROLE to the depositor bot DelegationContract
                validate_grant_role_event(
                    agent_events[event_index],
                    role=TOP_UP_ROLE,
                    grant_to=DEPOSITOR_BOT_DELEGATION_CONTRACT.address,
                    sender=AGENT,
                    emitted_by=TOP_UP_GATEWAY,
                )
                event_index += 1

                # 1.78. Grant BUFFER_RESERVE_MANAGER_ROLE to the Easy Track EVMScriptExecutor
                # (the last inner call group also carries the Agent.forward service events)
                validate_events_chain(
                    [e.name for e in agent_events[event_index]],
                    ["LogScriptCall", "SetPermission", "ScriptResult", "Executed"],
                )
                set_permission_event = _single_event(agent_events[event_index], "SetPermission")
                assert convert.to_address(set_permission_event["entity"]) == convert.to_address(
                    EASYTRACK_EVMSCRIPT_EXECUTOR
                )
                assert convert.to_address(set_permission_event["app"]) == convert.to_address(LIDO)
                assert _normalize_role(set_permission_event["role"]) == BUFFER_RESERVE_MANAGER_ROLE.hex().replace("0x", "")
                assert set_permission_event["allowed"] is True
                _assert_emitted_by(set_permission_event, ACL)
                event_index += 1
                assert event_index == EXPECTED_DG_EVENTS_FROM_AGENT


        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================
        assert timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["executed"]

        # Acceptance tests (after DG state)
        for committee in ORACLE_COMMITTEES:
            consensus = interface.HashConsensus(committee.consensus_contract)
            assert consensus.getQuorum() == ORACLE_COMMITTEE_QUORUM
            members = [str(m).lower() for m in consensus.getMembers()[0]]
            assert len(members) == len(ORACLE_MEMBER_MAPPINGS)
            for mapping in ORACLE_MEMBER_MAPPINGS:
                assert mapping.old_member.lower() not in members
                assert mapping.delegation_contract.address.lower() in members

        assert str(locator_proxy.proxy__getImplementation()).lower() == NEW_LIDO_LOCATOR_IMPLEMENTATION.lower()
        assert (
            str(interface.LidoLocator(LIDO_LOCATOR).depositSecurityModule()).lower()
            == NEW_DEPOSIT_SECURITY_MODULE.lower()
        )

        # Every locator entry except depositSecurityModule must stay unchanged
        if locator_addresses_before is not None:
            locator = interface.LidoLocator(LIDO_LOCATOR)
            for name, before_value in locator_addresses_before.items():
                after_value = str(getattr(locator, name)())
                if name == "depositSecurityModule":
                    assert after_value.lower() == NEW_DEPOSIT_SECURITY_MODULE.lower()
                else:
                    assert after_value == before_value, f"Locator entry {name} changed unexpectedly"

        # The new holders are the only holders
        assert not staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE)
        assert staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE)
        assert staking_router.getRoleMemberCount(STAKING_MODULE_UNVETTING_ROLE) == 1
        assert not top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_OLD_EOA)
        assert top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_DELEGATION_CONTRACT.address)
        assert top_up_gateway.getRoleMemberCount(TOP_UP_ROLE) == 1

        assert new_dsm.VERSION() == NEW_DSM_VERSION
        assert convert.to_address(new_dsm.getOwner()) == convert.to_address(AGENT)
        assert new_dsm.getGuardianQuorum() == DSM_GUARDIAN_QUORUM
        assert {str(g).lower() for g in new_dsm.getGuardians()} == {m.delegation_contract.address.lower() for m in DSM_GUARDIAN_MAPPINGS}

        # The DelegationContracts are untouched by the upgrade
        _assert_all_delegation_contracts()

        # Scenario tests (after DG state)
        # Easy Track factory for deposit reserve target management
        acl = interface.ACL(ACL)
        easy_track = interface.EasyTrack(EASYTRACK)
        factory = interface.SetDepositsReserveTarget(SET_DEPOSITS_RESERVE_TARGET_FACTORY)
        lido = interface.Lido(LIDO)

        assert acl.hasPermission(EASYTRACK_EVMSCRIPT_EXECUTOR, LIDO, BUFFER_RESERVE_MANAGER_ROLE)
        assert SET_DEPOSITS_RESERVE_TARGET_FACTORY in easy_track.getEVMScriptFactories()
        assert easy_track.evmScriptFactoryPermissions(SET_DEPOSITS_RESERVE_TARGET_FACTORY) == create_permissions(
            lido, "setDepositsReserveTarget"
        )
        assert convert.to_address(factory.trustedCaller()) == convert.to_address(
            SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER
        )
        assert convert.to_address(factory.lido()) == convert.to_address(LIDO)
        assert factory.MAX_DEPOSITS_RESERVE_TARGET() == SET_DEPOSITS_RESERVE_TARGET_MAX

        # Happy path: the granted role lets the EVMScriptExecutor move the target,
        # and the factory builds a script for exactly that call
        chain.snapshot()
        try:
            new_target = lido.getDepositsReserveTarget() + 10**18
            assert new_target <= SET_DEPOSITS_RESERVE_TARGET_MAX

            # the factory builds a script for the new target and guards its limits
            call_data = encode_abi(["uint256"], [new_target])
            assert factory.decodeEVMScriptCallData(call_data) == new_target

            # the produced script must be exactly one call to Lido.setDepositsReserveTarget(new_target)
            expected_script = encode_call_script([(LIDO, lido.setDepositsReserveTarget.encode_input(new_target))])
            produced_script = factory.createEVMScript(SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER, call_data)
            assert str(produced_script).lower() == expected_script.lower()

            with reverts("CALLER_IS_FORBIDDEN"):
                factory.createEVMScript(stranger, call_data)

            with reverts("DEPOSITS_RESERVE_TARGET_TOO_HIGH"):
                factory.createEVMScript(
                    SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER,
                    encode_abi(["uint256"], [SET_DEPOSITS_RESERVE_TARGET_MAX + 1]),
                )

            # the granted role lets the EVMScriptExecutor apply the new target
            executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
            lido.setDepositsReserveTarget(new_target, {"from": executor})
            assert lido.getDepositsReserveTarget() == new_target

            with reverts("SAME_DEPOSITS_RESERVE_TARGET"):
                factory.createEVMScript(SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER, call_data)
        finally:
            chain.revert()
