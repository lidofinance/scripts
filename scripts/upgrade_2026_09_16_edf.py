"""
Vote 2026_09_16

1. Submit a Dual Governance proposal containing a single Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c forward call to Dual Governance 0xC1db28B3301331277e307FDCfF8DE28242A4486E

I. EDF: rotate the oracle committee members from EOA hot keys to DelegationContracts (LIP-37), keeping quorum 5
1.1. Remove Instadapp oracle member 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.2. Add Instadapp DelegationContract 0xE75A431A98487DC69A14Bdd13d858E3238e9C1b3 to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.3. Remove Caliber oracle member 0x4118DAD7f348A4063bD15786c299De2f3B1333F3 from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.4. Add Caliber DelegationContract 0xc77d0Bf3AA4778E36a89CDC8bbc9c34d8060637d to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.5. Remove Staking Facilities oracle member 0x404335BcE530400a5814375E7Ec1FB55fAff3eA2 from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.6. Add Staking Facilities DelegationContract 0xc7442d4d8F3FfEa0fA4a18Ad3062c8137cE21749 to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.7. Remove Chorus One oracle member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.8. Add Chorus One DelegationContract 0x56B3eA8016Da18C6E8CD8135492d242F0dE0DBBC to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.9. Remove P2P oracle member 0x007DE4a5F7bc37E2F26c0cb2E8A95006EE9B89b5 from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.10. Add P2P DelegationContract 0x4E3F2DEeb59eB9a205D82D17647b3e56422e0FEe to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.11. Remove ChainLayer oracle member 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.12. Add ChainLayer DelegationContract 0xd524101C3c40f71Fce7B9312D299603880a06Bdb to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.13. Remove bloXroute oracle member 0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8 from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.14. Add bloXroute DelegationContract 0x99Cd2EF33040879D40BBC77Df81863D97f13C64d to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.15. Remove MatrixedLink oracle member 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.16. Add MatrixedLink DelegationContract 0xC4f2704273598d51A0ec76A31C12553ec8f5A891 to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.17. Remove Stakefish oracle member 0x042a9e5acCfa17e28300F1b5967f20891E973922 from HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.18. Add Stakefish DelegationContract 0x5e8Ed9f10307eD6FA793A347e4D0f407D00B9C6f to HashConsensus for AccountingOracle 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288
1.19. Remove Instadapp oracle member 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.20. Add Instadapp DelegationContract 0xE75A431A98487DC69A14Bdd13d858E3238e9C1b3 to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.21. Remove Caliber oracle member 0x4118DAD7f348A4063bD15786c299De2f3B1333F3 from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.22. Add Caliber DelegationContract 0xc77d0Bf3AA4778E36a89CDC8bbc9c34d8060637d to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.23. Remove Staking Facilities oracle member 0x404335BcE530400a5814375E7Ec1FB55fAff3eA2 from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.24. Add Staking Facilities DelegationContract 0xc7442d4d8F3FfEa0fA4a18Ad3062c8137cE21749 to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.25. Remove Chorus One oracle member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.26. Add Chorus One DelegationContract 0x56B3eA8016Da18C6E8CD8135492d242F0dE0DBBC to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.27. Remove P2P oracle member 0x007DE4a5F7bc37E2F26c0cb2E8A95006EE9B89b5 from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.28. Add P2P DelegationContract 0x4E3F2DEeb59eB9a205D82D17647b3e56422e0FEe to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.29. Remove ChainLayer oracle member 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.30. Add ChainLayer DelegationContract 0xd524101C3c40f71Fce7B9312D299603880a06Bdb to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.31. Remove bloXroute oracle member 0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8 from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.32. Add bloXroute DelegationContract 0x99Cd2EF33040879D40BBC77Df81863D97f13C64d to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.33. Remove MatrixedLink oracle member 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.34. Add MatrixedLink DelegationContract 0xC4f2704273598d51A0ec76A31C12553ec8f5A891 to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.35. Remove Stakefish oracle member 0x042a9e5acCfa17e28300F1b5967f20891E973922 from HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.36. Add Stakefish DelegationContract 0x5e8Ed9f10307eD6FA793A347e4D0f407D00B9C6f to HashConsensus for ValidatorsExitBusOracle 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
1.37. Remove Instadapp oracle member 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.38. Add Instadapp DelegationContract 0xE75A431A98487DC69A14Bdd13d858E3238e9C1b3 to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.39. Remove Caliber oracle member 0x4118DAD7f348A4063bD15786c299De2f3B1333F3 from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.40. Add Caliber DelegationContract 0xc77d0Bf3AA4778E36a89CDC8bbc9c34d8060637d to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.41. Remove Staking Facilities oracle member 0x404335BcE530400a5814375E7Ec1FB55fAff3eA2 from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.42. Add Staking Facilities DelegationContract 0xc7442d4d8F3FfEa0fA4a18Ad3062c8137cE21749 to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.43. Remove Chorus One oracle member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.44. Add Chorus One DelegationContract 0x56B3eA8016Da18C6E8CD8135492d242F0dE0DBBC to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.45. Remove P2P oracle member 0x007DE4a5F7bc37E2F26c0cb2E8A95006EE9B89b5 from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.46. Add P2P DelegationContract 0x4E3F2DEeb59eB9a205D82D17647b3e56422e0FEe to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.47. Remove ChainLayer oracle member 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.48. Add ChainLayer DelegationContract 0xd524101C3c40f71Fce7B9312D299603880a06Bdb to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.49. Remove bloXroute oracle member 0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8 from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.50. Add bloXroute DelegationContract 0x99Cd2EF33040879D40BBC77Df81863D97f13C64d to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.51. Remove MatrixedLink oracle member 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.52. Add MatrixedLink DelegationContract 0xC4f2704273598d51A0ec76A31C12553ec8f5A891 to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.53. Remove Stakefish oracle member 0x042a9e5acCfa17e28300F1b5967f20891E973922 from CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.54. Add Stakefish DelegationContract 0x5e8Ed9f10307eD6FA793A347e4D0f407D00B9C6f to CSHashConsensus for CSFeeOracle 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4
1.55. Remove Instadapp oracle member 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.56. Add Instadapp DelegationContract 0xE75A431A98487DC69A14Bdd13d858E3238e9C1b3 to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.57. Remove Caliber oracle member 0x4118DAD7f348A4063bD15786c299De2f3B1333F3 from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.58. Add Caliber DelegationContract 0xc77d0Bf3AA4778E36a89CDC8bbc9c34d8060637d to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.59. Remove Staking Facilities oracle member 0x404335BcE530400a5814375E7Ec1FB55fAff3eA2 from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.60. Add Staking Facilities DelegationContract 0xc7442d4d8F3FfEa0fA4a18Ad3062c8137cE21749 to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.61. Remove Chorus One oracle member 0x8dB977C13CAA938BC58464bFD622DF0570564b78 from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.62. Add Chorus One DelegationContract 0x56B3eA8016Da18C6E8CD8135492d242F0dE0DBBC to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.63. Remove P2P oracle member 0x007DE4a5F7bc37E2F26c0cb2E8A95006EE9B89b5 from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.64. Add P2P DelegationContract 0x4E3F2DEeb59eB9a205D82D17647b3e56422e0FEe to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.65. Remove ChainLayer oracle member 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.66. Add ChainLayer DelegationContract 0xd524101C3c40f71Fce7B9312D299603880a06Bdb to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.67. Remove bloXroute oracle member 0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8 from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.68. Add bloXroute DelegationContract 0x99Cd2EF33040879D40BBC77Df81863D97f13C64d to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.69. Remove MatrixedLink oracle member 0xe57B3792aDCc5da47EF4fF588883F0ee0c9835C9 from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.70. Add MatrixedLink DelegationContract 0xC4f2704273598d51A0ec76A31C12553ec8f5A891 to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.71. Remove Stakefish oracle member 0x042a9e5acCfa17e28300F1b5967f20891E973922 from HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb
1.72. Add Stakefish DelegationContract 0x5e8Ed9f10307eD6FA793A347e4D0f407D00B9C6f to HashConsensus for Curated Module FeeOracle 0x902D64c93F6595339aA46105627a085591051aFb

II. DSM v5
1.73. Upgrade Lido Locator 0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb to implementation 0x60E09F1791F1168d0450E4F100616B4a3F95119C
1.74. Revoke STAKING_MODULE_UNVETTING_ROLE 0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57 from DepositSecurityModule v4 0xF573E9E3de1f86B085417ab294f56E7920B4e9Be on StakingRouter 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
1.75. Grant STAKING_MODULE_UNVETTING_ROLE 0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57 to DepositSecurityModule v5 0x39BB5d491e98A44D1bfe8047A737a81E296a63E0 on StakingRouter 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
1.76. Revoke TOP_UP_ROLE 0x5e4bd437d29fad01c10cdcfff414f0d6b0e84b96d2dade88d780d45b5630696b from the depositor bot 0xF82aC5937A20dC862F9bc0668779031E06000f17 on TopUpGateway 0x3FC2C71579D80790Aaa3fc7Be8B66ac39dC57374
1.77. Grant TOP_UP_ROLE 0x5e4bd437d29fad01c10cdcfff414f0d6b0e84b96d2dade88d780d45b5630696b to the depositor bot DelegationContract 0x6Aa249bA53A3abcaC52F91146583B3eE2Ee4C7F5 on TopUpGateway 0x3FC2C71579D80790Aaa3fc7Be8B66ac39dC57374

III. Easy Track factory for deposit reserve target management by CMC
1.78. Grant BUFFER_RESERVE_MANAGER_ROLE 0x33969636f1fbf3d7d062d4de4a08e7bd3c46606ec28b3a4398d2665be559b921 to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Lido 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84
2. Add SetDepositsReserveTarget EVM script factory 0x62E9Dc68BDCBC46362f40e0bb9c154C9a42E62b0 with setDepositsReserveTarget permission on Lido 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84 to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea

The new DSM v5 is deployed with the guardian set already moved to DelegationContracts:
Stakely replaces Kiln, the guardian quorum stays 4.

TODO (after vote) Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from brownie import interface, web3

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    ACL,
    AGENT,
    EASYTRACK,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    LIDO,
    LIDO_LOCATOR,
    STAKING_ROUTER,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals

from utils.agent import agent_forward
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.permissions import encode_permission_grant


# ============================== Addresses ===================================
# EDF contracts are deployed from lidofinance/core branch feat/edf, commit e4d0404,
# https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/25
# Deploy state: deployed-mainnet.json; the DelegationContracts are announced by
# their operators in the same thread

# DSM v5, https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L482
NEW_DEPOSIT_SECURITY_MODULE = "0x39BB5d491e98A44D1bfe8047A737a81E296a63E0"
# https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L623
NEW_LIDO_LOCATOR_IMPLEMENTATION = "0x60E09F1791F1168d0450E4F100616B4a3F95119C"

# DSM v4 (SRv3), the current LidoLocator.depositSecurityModule(), https://docs.lido.fi/deployed-contracts/#core-protocol
OLD_DEPOSIT_SECURITY_MODULE = "0xF573E9E3de1f86B085417ab294f56E7920B4e9Be"
# TopUpGateway proxy, https://docs.lido.fi/deployed-contracts/#core-protocol
TOP_UP_GATEWAY = "0x3FC2C71579D80790Aaa3fc7Be8B66ac39dC57374"
# The sole TOP_UP_ROLE holder, the depositor bot, https://docs.lido.fi/deployed-contracts/#bots
DEPOSITOR_BOT_OLD_EOA = "0xF82aC5937A20dC862F9bc0668779031E06000f17"

# EDF DelegationFactory, https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/10
DELEGATION_FACTORY = "0xD990770eB2B4b6062EDdB06892fF179C693b46e6"
# https://github.com/lidofinance/core/blob/e4d0404c85b043b1b9fb1dd42d85c2535a7f30d8/deployed-mainnet.json#L361
DELEGATION_FACTORY_RUNTIME_CODE_HASH = "0x0898ad72098301345c44103c8aca22cd8a0a02a339bffe222c6487ec25ff3591"

# https://research.lido.fi/t/proposal-add-easy-track-factory-for-deposit-reserve-target-management-by-cmc/11827/6
SET_DEPOSITS_RESERVE_TARGET_FACTORY = "0x62E9Dc68BDCBC46362f40e0bb9c154C9a42E62b0"
# https://research.lido.fi/t/proposal-add-easy-track-factory-for-deposit-reserve-target-management-by-cmc/11827
SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER = "0x2570e0b22AD904501dfB0d49575991ACB801dD91"
# https://research.lido.fi/t/proposal-add-easy-track-factory-for-deposit-reserve-target-management-by-cmc/11827
SET_DEPOSITS_RESERVE_TARGET_MAX = 9600 * 10**18


DELEGATION_CONTRACT_COOLDOWN = 172800  # 2 days


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


# Committee order: accounting-oracle, validators-exit-bus-oracle, csm-fee-oracle, curated-module-fee-oracle.
# AccountingOracle and ValidatorsExitBusOracle: https://docs.lido.fi/deployed-contracts/#oracle-contracts
# CSFeeOracle: https://docs.lido.fi/deployed-contracts/#community-staking-module
# Curated Module FeeOracle: https://docs.lido.fi/deployed-contracts/#curated-module-v2
ORACLE_COMMITTEES: List[OracleCommittee] = [
    OracleCommittee(name="HashConsensus for AccountingOracle", consensus_contract="0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"),
    OracleCommittee(name="HashConsensus for ValidatorsExitBusOracle", consensus_contract="0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"),
    OracleCommittee(name="CSHashConsensus for CSFeeOracle", consensus_contract="0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"),
    OracleCommittee(name="HashConsensus for Curated Module FeeOracle", consensus_contract="0x902D64c93F6595339aA46105627a085591051aFb"),
]

ORACLE_MEMBER_MAPPINGS: List[OracleMemberMapping] = [
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

# DSM guardians: the old DSM v4 holds the EOA hot keys (DSM_GUARDIANS in configs/config_mainnet.py),
# the new DSM v5 is deployed with the EDF DelegationContracts, the vote only switches
# the protocol to it. Stakely takes the seat of Kiln.
DSM_GUARDIAN_MAPPINGS: List[DsmGuardianMapping] = [
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

ALL_DELEGATION_CONTRACTS: List[DelegationContract] = (
    [m.delegation_contract for m in ORACLE_MEMBER_MAPPINGS]
    + [m.delegation_contract for m in DSM_GUARDIAN_MAPPINGS]
    + [DEPOSITOR_BOT_DELEGATION_CONTRACT]
)


# ============================== Constants ===================================
STAKING_MODULE_UNVETTING_ROLE = web3.keccak(text="STAKING_MODULE_UNVETTING_ROLE").hex()
TOP_UP_ROLE = web3.keccak(text="TOP_UP_ROLE").hex()
BUFFER_RESERVE_MANAGER_ROLE = "BUFFER_RESERVE_MANAGER_ROLE"
# IERC1271.isValidSignature.selector
ERC1271_INTERFACE_ID = "0x1626ba7e"

# The current on-chain quorum of every committee (ORACLE_QUORUM in configs/config_mainnet.py),
# kept by the rotation
ORACLE_COMMITTEE_QUORUM = 5

# The current on-chain guardian quorum (DSM_GUARDIAN_QUORUM in configs/config_mainnet.py);
# the new DSM is deployed with the same quorum, https://research.lido.fi/t/lip-37-execution-delegation-framework-edf/11746/25
DSM_GUARDIAN_QUORUM = 4

DG_PROPOSAL_METADATA = (
    "Upgrade the protocol to EDF/DSM v5 (LIP-37): rotate oracle committee members to "
    "Execution Delegation Framework delegation contracts, upgrade LidoLocator "
    "and switch to the new DepositSecurityModule v5"
)


# ============================= IPFS Description ==================================
IPFS_DESCRIPTION = """
Upgrade the Lido protocol to the Execution Delegation Framework (EDF) and DepositSecurityModule v5 (LIP-37).

1. Rotate all members of the four oracle committees (HashConsensus contracts for AccountingOracle, ValidatorsExitBusOracle, CSFeeOracle and Curated Module FeeOracle) from EOA hot keys to per-operator EDF DelegationContracts, keeping quorum 5. Items 1.1-1.72.
2. Upgrade the LidoLocator implementation so it points to the new DepositSecurityModule v5. The new DSM is deployed with the guardian set already moved to DelegationContracts: Stakely replaces Kiln, the guardian quorum stays 4. Item 1.73.
3. Move STAKING_MODULE_UNVETTING_ROLE on StakingRouter from the old DepositSecurityModule to the new DepositSecurityModule v5. Items 1.74-1.75.
4. Move TOP_UP_ROLE on TopUpGateway from the old depositor bot EOA to the depositor bot DelegationContract. Items 1.76-1.77.
5. Enable deposit reserve target management by CMC via Easy Track: grant BUFFER_RESERVE_MANAGER_ROLE on Lido to the Easy Track EVMScriptExecutor and add the SetDepositsReserveTarget factory, limited to Lido.setDepositsReserveTarget(uint256). Item 1.78 and item 2.
"""


# ============================ Pre-flight checks =============================
def _assert_no_duplicates() -> None:
    old_members = [m.old_member.lower() for m in ORACLE_MEMBER_MAPPINGS]
    new_members = [m.delegation_contract.address.lower() for m in ORACLE_MEMBER_MAPPINGS]
    consensus_contracts = [c.consensus_contract.lower() for c in ORACLE_COMMITTEES]
    delegation_contracts = [c.address.lower() for c in ALL_DELEGATION_CONTRACTS]
    assert len(set(old_members)) == len(old_members), "Duplicate old oracle members"
    assert len(set(new_members)) == len(new_members), "Duplicate oracle delegation contracts"
    assert len(set(consensus_contracts)) == len(consensus_contracts), "Duplicate consensus contracts"
    assert len(set(delegation_contracts)) == len(delegation_contracts), "Duplicate delegation contracts"
    assert not set(old_members) & set(new_members), "Old and new oracle member sets intersect"

    old_guardians = [m.old_guardian.lower() for m in DSM_GUARDIAN_MAPPINGS]
    new_guardians = [m.delegation_contract.address.lower() for m in DSM_GUARDIAN_MAPPINGS]
    assert len(set(old_guardians)) == len(old_guardians), "Duplicate old DSM guardians"
    assert not set(old_guardians) & set(new_guardians), "Old and new DSM guardian sets intersect"
    assert len(old_guardians) == len(new_guardians), "Old and new DSM guardian counts differ"


def _strip_hex_prefix(value: str) -> str:
    return str(value).lower().replace("0x", "")


def _code_hash(address: str) -> str:
    code = web3.eth.get_code(address)
    assert len(code) > 0, f"No code at {address}"
    return _strip_hex_prefix(web3.keccak(code).hex())


def _assert_delegation_contract_matches_manifest(contract: DelegationContract) -> None:
    """Mirror EDFUpgradeTemplate._validateFactoryAndDelegationContracts from lidofinance/core:
    the contract must be the factory deployment recorded in deployed-mainnet.json
    (the runtime code hash reflects the immutable owner and cooldown; the delegate
    is mutable by the owner and is checked on-chain)."""
    assert _code_hash(contract.address) == _strip_hex_prefix(contract.runtime_code_hash), (
        f"{contract.name} DelegationContract {contract.address} runtime code hash mismatch"
    )

    delegation = interface.DelegationContract(contract.address)
    assert str(delegation.owner()).lower() == contract.owner.lower(), (
        f"{contract.name} DelegationContract owner mismatch"
    )
    assert str(delegation.getDelegate()).lower() == contract.delegate.lower(), (
        f"{contract.name} DelegationContract delegate mismatch"
    )
    assert delegation.getCooldown() == contract.cooldown, f"{contract.name} DelegationContract cooldown mismatch"
    assert not delegation.isTerminated(), f"{contract.name} DelegationContract is terminated"
    assert delegation.supportsInterface(ERC1271_INTERFACE_ID), (
        f"{contract.name} DelegationContract does not support ERC-1271"
    )


def _assert_delegation_contracts() -> None:
    assert _code_hash(DELEGATION_FACTORY) == _strip_hex_prefix(DELEGATION_FACTORY_RUNTIME_CODE_HASH), (
        "DelegationFactory runtime code hash mismatch"
    )
    for contract in ALL_DELEGATION_CONTRACTS:
        _assert_delegation_contract_matches_manifest(contract)


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
        assert mapping.delegation_contract.address.lower() not in members, (
            f"{mapping.name} DelegationContract {mapping.delegation_contract.address} "
            f"is already a member of {committee.name}"
        )


def _locator_address_getters(locator) -> List[str]:
    """Names of the zero-arg address getters of the locator implementation ABI."""
    names = []
    for entry in locator.abi:
        if entry.get("type") != "function" or entry.get("inputs") or entry.get("stateMutability") != "view":
            continue
        outputs = entry.get("outputs") or []
        if len(outputs) == 1 and outputs[0].get("type") == "address":
            names.append(entry["name"])
    return names


def _assert_state_before_vote() -> None:
    _assert_no_duplicates()
    _assert_delegation_contracts()
    for committee in ORACLE_COMMITTEES:
        _assert_committee_matches_chain(committee)

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    assert staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE), (
        "Old DSM does not hold STAKING_MODULE_UNVETTING_ROLE"
    )
    assert not staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE), (
        "New DSM already holds STAKING_MODULE_UNVETTING_ROLE"
    )
    # the old DSM must be the only holder, so after the swap the new DSM is the only one
    assert staking_router.getRoleMemberCount(STAKING_MODULE_UNVETTING_ROLE) == 1, (
        "Unexpected extra STAKING_MODULE_UNVETTING_ROLE holders"
    )

    locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    assert str(locator_proxy.proxy__getImplementation()).lower() != NEW_LIDO_LOCATOR_IMPLEMENTATION.lower(), (
        "LidoLocator already points to the new implementation"
    )
    locator = interface.LidoLocator(LIDO_LOCATOR)
    assert str(locator.depositSecurityModule()).lower() == OLD_DEPOSIT_SECURITY_MODULE.lower(), (
        "LidoLocator does not point to the old DSM"
    )
    # the new implementation must differ from the current one only by the DSM entry
    new_locator = interface.LidoLocator(NEW_LIDO_LOCATOR_IMPLEMENTATION)
    assert str(new_locator.depositSecurityModule()).lower() == NEW_DEPOSIT_SECURITY_MODULE.lower(), (
        "New LidoLocator implementation does not point to the new DSM"
    )
    for getter in _locator_address_getters(locator):
        if getter == "depositSecurityModule":
            continue
        assert str(getattr(locator, getter)()) == str(getattr(new_locator, getter)()), (
            f"New LidoLocator implementation changes the {getter} entry"
        )

    top_up_gateway = interface.TopUpGateway(TOP_UP_GATEWAY)
    assert top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_OLD_EOA), (
        "Old depositor bot EOA does not hold TOP_UP_ROLE"
    )
    assert not top_up_gateway.hasRole(TOP_UP_ROLE, DEPOSITOR_BOT_DELEGATION_CONTRACT.address), (
        "Depositor bot DelegationContract already holds TOP_UP_ROLE"
    )
    # the old depositor bot EOA must be the only holder, so after the swap the
    # DelegationContract is the only one
    assert top_up_gateway.getRoleMemberCount(TOP_UP_ROLE) == 1, "Unexpected extra TOP_UP_ROLE holders"

    # The vote does not change DSM guardians, so verify the new DSM is deployed
    # with the expected guardian set, owner and protocol links before switching
    # the protocol to it
    old_dsm = interface.DepositSecurityModule(OLD_DEPOSIT_SECURITY_MODULE)
    new_dsm = interface.DepositSecurityModule(NEW_DEPOSIT_SECURITY_MODULE)
    assert old_dsm.VERSION() == 4, "Old DSM version is not 4"
    assert new_dsm.VERSION() == 5, "New DSM version is not 5"
    assert str(new_dsm.getOwner()).lower() == AGENT.lower(), "New DSM owner is not the Agent"
    assert str(new_dsm.STAKING_ROUTER()).lower() == STAKING_ROUTER.lower(), "New DSM staking router mismatch"
    assert str(new_dsm.DEPOSIT_CONTRACT()).lower() == str(old_dsm.DEPOSIT_CONTRACT()).lower(), (
        "New DSM deposit contract mismatch"
    )
    assert not new_dsm.isDepositsPaused(), "New DSM deposits are paused"
    assert new_dsm.getPauseIntentValidityPeriodBlocks() == old_dsm.getPauseIntentValidityPeriodBlocks(), (
        "Pause intent validity period differs between the old and the new DSM"
    )
    assert new_dsm.getMaxOperatorsPerUnvetting() == old_dsm.getMaxOperatorsPerUnvetting(), (
        "Max operators per unvetting differs between the old and the new DSM"
    )
    assert new_dsm.getGuardianQuorum() == DSM_GUARDIAN_QUORUM, "New DSM guardian quorum mismatch"
    # the upgrade replaces the guardian set but must keep the same threshold
    assert new_dsm.getGuardianQuorum() == old_dsm.getGuardianQuorum(), (
        "Guardian quorum differs between the old and the new DSM"
    )
    old_dsm_guardians = {str(g).lower() for g in old_dsm.getGuardians()}
    assert old_dsm_guardians == {m.old_guardian.lower() for m in DSM_GUARDIAN_MAPPINGS}, "Old DSM guardian set mismatch"
    new_dsm_guardians = {str(g).lower() for g in new_dsm.getGuardians()}
    assert new_dsm_guardians == {m.delegation_contract.address.lower() for m in DSM_GUARDIAN_MAPPINGS}, "New DSM guardian set mismatch"

    # Easy Track factory for deposit reserve target management
    acl = interface.ACL(ACL)
    buffer_reserve_manager_role = web3.keccak(text=BUFFER_RESERVE_MANAGER_ROLE)
    # the Agent grants the role from inside the DG proposal, so it must be its manager
    assert str(acl.getPermissionManager(LIDO, buffer_reserve_manager_role)).lower() == AGENT.lower(), (
        "Agent is not the manager of BUFFER_RESERVE_MANAGER_ROLE on Lido"
    )
    assert not acl.hasPermission(
        EASYTRACK_EVMSCRIPT_EXECUTOR, LIDO, buffer_reserve_manager_role
    ), "EVMScriptExecutor already holds BUFFER_RESERVE_MANAGER_ROLE"

    easy_track = interface.EasyTrack(EASYTRACK)
    registered_factories = {str(f).lower() for f in easy_track.getEVMScriptFactories()}
    assert SET_DEPOSITS_RESERVE_TARGET_FACTORY.lower() not in registered_factories, (
        "SetDepositsReserveTarget factory is already registered in Easy Track"
    )

    factory = interface.SetDepositsReserveTarget(SET_DEPOSITS_RESERVE_TARGET_FACTORY)
    assert str(factory.trustedCaller()).lower() == SET_DEPOSITS_RESERVE_TARGET_TRUSTED_CALLER.lower(), (
        "SetDepositsReserveTarget factory trusted caller mismatch"
    )
    assert str(factory.lido()).lower() == LIDO.lower(), "SetDepositsReserveTarget factory targets another Lido"
    assert factory.MAX_DEPOSITS_RESERVE_TARGET() == SET_DEPOSITS_RESERVE_TARGET_MAX, (
        "SetDepositsReserveTarget factory cap mismatch"
    )


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    top_up_gateway = interface.TopUpGateway(TOP_UP_GATEWAY)
    lido = interface.Lido(LIDO)

    # 1.1 - 1.72. For each committee, for each member: remove the old member EOA and add
    # its DelegationContract, keeping the quorum (same order as EDFUpgradeVoteScript in core)
    oracle_rotation_calls: List[Tuple[str, str]] = []
    for committee in ORACLE_COMMITTEES:
        consensus = interface.HashConsensus(committee.consensus_contract)
        for mapping in ORACLE_MEMBER_MAPPINGS:
            oracle_rotation_calls.append(
                (
                    consensus.address,
                    consensus.removeMember.encode_input(mapping.old_member, ORACLE_COMMITTEE_QUORUM),
                )
            )
            oracle_rotation_calls.append(
                (
                    consensus.address,
                    consensus.addMember.encode_input(mapping.delegation_contract.address, ORACLE_COMMITTEE_QUORUM),
                )
            )

    calls: List[Tuple[str, str]] = [
        *oracle_rotation_calls,
        # 1.73. Upgrade Lido Locator 0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb to implementation 0x60E09F1791F1168d0450E4F100616B4a3F95119C
        (
            locator_proxy.address,
            locator_proxy.proxy__upgradeTo.encode_input(NEW_LIDO_LOCATOR_IMPLEMENTATION),
        ),
        # 1.74. Revoke STAKING_MODULE_UNVETTING_ROLE 0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57 from DepositSecurityModule v4 0xF573E9E3de1f86B085417ab294f56E7920B4e9Be on StakingRouter 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
        (
            staking_router.address,
            staking_router.revokeRole.encode_input(STAKING_MODULE_UNVETTING_ROLE, OLD_DEPOSIT_SECURITY_MODULE),
        ),
        # 1.75. Grant STAKING_MODULE_UNVETTING_ROLE 0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57 to DepositSecurityModule v5 0x39BB5d491e98A44D1bfe8047A737a81E296a63E0 on StakingRouter 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
        (
            staking_router.address,
            staking_router.grantRole.encode_input(STAKING_MODULE_UNVETTING_ROLE, NEW_DEPOSIT_SECURITY_MODULE),
        ),
        # 1.76. Revoke TOP_UP_ROLE 0x5e4bd437d29fad01c10cdcfff414f0d6b0e84b96d2dade88d780d45b5630696b from the depositor bot 0xF82aC5937A20dC862F9bc0668779031E06000f17 on TopUpGateway 0x3FC2C71579D80790Aaa3fc7Be8B66ac39dC57374
        (
            top_up_gateway.address,
            top_up_gateway.revokeRole.encode_input(TOP_UP_ROLE, DEPOSITOR_BOT_OLD_EOA),
        ),
        # 1.77. Grant TOP_UP_ROLE 0x5e4bd437d29fad01c10cdcfff414f0d6b0e84b96d2dade88d780d45b5630696b to the depositor bot DelegationContract 0x6Aa249bA53A3abcaC52F91146583B3eE2Ee4C7F5 on TopUpGateway 0x3FC2C71579D80790Aaa3fc7Be8B66ac39dC57374
        (
            top_up_gateway.address,
            top_up_gateway.grantRole.encode_input(TOP_UP_ROLE, DEPOSITOR_BOT_DELEGATION_CONTRACT.address),
        ),
        # 1.78. Grant BUFFER_RESERVE_MANAGER_ROLE 0x33969636f1fbf3d7d062d4de4a08e7bd3c46606ec28b3a4398d2665be559b921 to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 on Lido 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84
        encode_permission_grant(
            target_app=lido,
            permission_name=BUFFER_RESERVE_MANAGER_ROLE,
            grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
        ),
    ]

    expected_count = 2 * len(ORACLE_COMMITTEES) * len(ORACLE_MEMBER_MAPPINGS) + 6
    assert len(calls) == expected_count, f"Expected {expected_count} upgrade calls, got {len(calls)}"

    # The whole upgrade is applied atomically in a single Agent.forward
    return [agent_forward(calls)]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    lido = interface.Lido(LIDO)

    dg_items = get_dg_items()
    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_METADATA)])

    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to upgrade the protocol to EDF/DSM v5 (LIP-37): "
            "rotate the oracle committee members to DelegationContracts, upgrade Lido Locator "
            "to the implementation with DepositSecurityModule v5 and move the DSM and depositor bot roles",
            dg_call_script[0],
        ),
        (
            # Easy Track admin is Voting, so the factory is registered by the vote directly
            "2. Add SetDepositsReserveTarget EVM script factory 0x62E9Dc68BDCBC46362f40e0bb9c154C9a42E62b0 "
            "with setDepositsReserveTarget permission on Lido 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84 "
            "to EasyTrack 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            add_evmscript_factory(
                factory=SET_DEPOSITS_RESERVE_TARGET_FACTORY,
                permissions=create_permissions(lido, "setDepositsReserveTarget"),
            ),
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    _assert_state_before_vote()

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
