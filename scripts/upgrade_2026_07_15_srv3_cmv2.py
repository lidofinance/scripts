"""
Vote 2026_07_15

1. Submit Dual Governance proposal with `1` call to Dual Governance `0xc1db28b3301331277e307fdcff8de28242a4486e`

I. Start Upgrade
1.1. Execute `startUpgrade()` on Upgrade Template `0xd92b6303ba39297cb69a3a17a88b47586a6af14c`

II. Core
1.2. Upgrade Lido Locator `0xc1d0b3de6792bf6b4b37eccdcc24e45978cfd2eb` to implementation `0x0360002bf51DCae1c0267aE0AFDaBacAF7De686b`
1.3. Upgrade Staking Router `0xfddf38947afb03c621c71b06c9c70bce73f12999` to implementation `0xDD76927045435C7605cf6f5F978cfb8CABDb5F80` with setup calldata `0x8ee1c0a8000000000000000000000000000000000000000000000000000002e90edd0000` and force call `false`
1.4. Upgrade AccountingOracle `0x852ded011285fe67063a08005c71a85690503cee` to implementation `0xe4f03D1107d1905B6F2A28FCb6Af221E0CE19136` with setup calldata `0x9d005ce70000000000000000000000000000000000000000000000000000000000000006` and force call `false`
1.5. Upgrade ValidatorsExitBusOracle `0x0de4ea0184c2ad0baca7183356aea5b8d5bf5c6e` to implementation `0x2C3386b39db89eef0F362A3BE0C05a6811E809E3` with setup calldata `0x560cf78100000000000000000000000000000000000000000000000000000000000002580000000000000000000000000000000000000000000000000000000000057800000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000005` and force call `false`
1.6. Upgrade Accounting `0x23ed611be0e1a820978875c0122f92260804cddf` to implementation `0x3aa937Ac2ab89CDd363EdC6b5A4d4A42dF5bc043`
1.7. Upgrade Withdrawal Vault `0xb9d7934878b5fb9610b3fe8a5e441e8fad7e293f` to implementation `0xfB4521BD151BFB45DB6045D2d07e58e0f597e340` with setup calldata `0x6d395b7e`
1.8. Grant APP_MANAGER_ROLE `0xb6d92708f3d4817afc106147d969e229ced5c46e65e0a5002a0d391287762bd0` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` for Lido DAO (Kernel) `0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc` on Aragon ACL `0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb`
1.9. Set app in APP_BASES_NAMESPACE `0xf1f3eb40f5bc1ad1344716ced8b8a0431d840b5783aea1fd01786bc26f35ac0f` and ID `0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320` to new Lido implementation `0x028271E30a695c0527A0C50cA30603feD004cDb0` on Lido DAO (Kernel) `0xb8ffc3cd6e7cf5a098a1c92f48009765b24088dc`
1.10. Revoke APP_MANAGER_ROLE `0xb6d92708f3d4817afc106147d969e229ced5c46e65e0a5002a0d391287762bd0` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` for Lido DAO (Kernel) `0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc` on Aragon ACL `0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb`
1.11. Create BUFFER_RESERVE_MANAGER_ROLE `0x33969636f1fbf3d7d062d4de4a08e7bd3c46606ec28b3a4398d2665be559b921` for Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` on Lido and stETH token `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84` with manager Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` through Aragon ACL `0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb`
1.12. Finalize stETH upgrade v4 with deposits reserve target `1500000000000000000000` on Lido and stETH token `0xae7ab96520de3a18e5e111b5eaab095312d7fe84`
1.13. Grant STAKING_MODULE_SHARE_MANAGE_ROLE `0x43bf0e13900cfaa1b03ed5681dc143266597e29a1d6f9cbd84114f0ac21cd208` to EVMScriptExecutor `0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977` on Staking Router `0xfddf38947afb03c621c71b06c9c70bce73f12999`
1.14. Revoke STAKING_MODULE_UNVETTING_ROLE `0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57` from old Deposit Security Module `0xfFA96D84dEF2EA035c7AB153D8B991128e3d72fD` on Staking Router `0xfddf38947afb03c621c71b06c9c70bce73f12999`
1.15. Grant STAKING_MODULE_UNVETTING_ROLE `0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57` to new Deposit Security Module `0xF573E9E3de1f86B085417ab294f56E7920B4e9Be` on Staking Router `0xfddf38947afb03c621c71b06c9c70bce73f12999`
1.16. Grant TW_EXIT_LIMIT_MANAGER_ROLE `0x03c30da9b9e4d4789ac88a294d39a63058ca4a498804c2aa823e381df59d0cf4` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` on Triggerable Withdrawals Gateway `0xdc00116a0d3e064427da2600449cfd2566b3037b`
1.17. Set exit request limit to max `250`, exits per frame `1`, and frame duration `240` seconds on Triggerable Withdrawals Gateway `0xdc00116a0d3e064427da2600449cfd2566b3037b`
1.18. Register Consolidation Gateway `0x17be979344f2c2cC806229a532D92f8742C10462` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CircuitBreaker Committee `0x8772E3a2D86B9347A2688f9bc1808A6d8917760C`
1.19. Register Top Up Gateway `0x3FC2C71579D80790Aaa3fc7Be8B66ac39dC57374` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CircuitBreaker Committee `0x8772E3a2D86B9347A2688f9bc1808A6d8917760C`

III. CSM
1.20. Upgrade CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f` to implementation `0x63992a86f009fcC796a8369feEfB68880aef4e3a` with setup calldata `0x3b5312dc`
1.21. Upgrade ParametersRegistry `0x9d28ad303c90df524ba960d7a2dac56dcc31e428` to implementation `0x107d287F178cD54792614d7D63C47D8242240BeD` with setup calldata `0x3b5312dc`
1.22. Upgrade FeeOracle `0x4d4074628678bd302921c20573eea1ed38ddf7fb` to implementation `0xecE6e0Cde61078F76b66Ef0C338a6875E5D01F79` with setup calldata `0x5334b5ef0000000000000000000000000000000000000000000000000000000000000004`
1.23. Upgrade VettedGate (Identified Community Stakers Gate) `0xb314d4a76c457c93150d308787939063f4cc67e0` to implementation `0x66ADb8b3F58d3DFdF6bAdB595E41f19e947E5c14`
1.24. Upgrade CSM Accounting `0x4d72bff1beac69925f8bd12526a39baab069e5da` to implementation `0xe768572cc5aE5C698345C59288d871a949Ea8bd3` with setup calldata `0x3b5312dc`
1.25. Upgrade FeeDistributor `0xd99cc66fec647e68294c6477b40fc7e0f6f618d0` to implementation `0x936da7cDB7eed1084d294E23eA1d7Ad72DCcfE0E` with setup calldata `0x3b5312dc`
1.26. Upgrade ExitPenalties `0x06cd61045f958a209a0f8d746e103ecc625f4193` to implementation `0xA5b9e96E951089E629Ab0834AEaF242a81394EA0`
1.27. Upgrade ValidatorStrikes `0xaa328816027f2d32b9f56d190bc9fa4a5c07637f` to implementation `0xd25E7C3923d2e68c325980b0e15eD20d62B2691F`
1.28. Set ejector to new CSM Ejector `0x610B517D380f287c239C93F8eF6FfBd567AA4bA5` on ValidatorStrikes `0xaa328816027f2d32b9f56d190bc9fa4a5c07637f`
1.29. Revoke REPORT_EL_REWARDS_STEALING_PENALTY_ROLE `0x59911a6aa08a72fe3824aec4500dc42335c6d0702b6d5c5c72ceb265a0de9302` from CSM Committee `0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.30. Grant REPORT_GENERAL_DELAYED_PENALTY_ROLE `0xa2c92d51d5647473735e9dfd5e2edf65bcf2fc2c139c95cbed53c19dc227c0b5` to CSM Committee `0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.31. Revoke SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE `0xe85fdec10fe0f93d0792364051df7c3d73e37c17b3a954bffe593960e3cd3012` from EVMScriptExecutor `0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.32. Grant SETTLE_GENERAL_DELAYED_PENALTY_ROLE `0xe4c6f42648e5067520394b287613558d8b8a48bc7a320523da96c04d46253bda` to EVMScriptExecutor `0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.33. Revoke VERIFIER_ROLE `0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09` from old CSM Verifier `0xdC5FE1782B6943f318E05230d688713a560063DC` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.34. Grant VERIFIER_ROLE `0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09` to new CSM Verifier `0xfce7aB839e55de77730716D05b3553e45ab3A5Ba` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.35. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE `0xb169cb0459e6d91326174ff566a2fcc3c7bb31ef3d4d83bec1d5679c611ab094` to new CSM Verifier `0xfce7aB839e55de77730716D05b3553e45ab3A5Ba` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.36. Grant REPORT_SLASHED_WITHDRAWN_VALIDATORS_ROLE `0x2dba60a7b2c6bc437f1868d48dc8e53a95d71e78cef88de0aff6d952ecff8daa` to EVMScriptExecutor `0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.37. Revoke CREATE_NODE_OPERATOR_ROLE `0xc72a21b38830f4d6418a239e17db78b945cc7cfee674bac97fd596eaf0438478` from old PermissionlessGate `0xcF33a38111d0B1246A3F38a838fb41D626B454f0` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.38. Grant CREATE_NODE_OPERATOR_ROLE `0xc72a21b38830f4d6418a239e17db78b945cc7cfee674bac97fd596eaf0438478` to new PermissionlessGate `0xb8cd8F059Ad7a5dB8CAfDe34aAb007317F7156C8` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.39. Revoke START_REFERRAL_SEASON_ROLE `0xc0bd4bb446c4ce6fd2289aa78c8ea233de3ad2b870bc787b2ba154e19c271f12` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` on VettedGate (Identified Community Stakers Gate) `0xb314d4a76c457c93150d308787939063f4cc67e0`
1.40. Revoke END_REFERRAL_SEASON_ROLE `0x4a1304957825c6a76938ccf907b92b9b872c8348083e23dae57e7e6111105d0c` from CSM Committee `0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f` on VettedGate (Identified Community Stakers Gate) `0xb314d4a76c457c93150d308787939063f4cc67e0`
1.41. Set name `Identified Community Stakers Gate` on VettedGate (Identified Community Stakers Gate) `0xb314d4a76c457c93150d308787939063f4cc67e0`
1.42. Register old CSM Verifier `0xdC5FE1782B6943f318E05230d688713a560063DC` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser `0x0000000000000000000000000000000000000000`
1.43. Register old CSM Ejector `0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser `0x0000000000000000000000000000000000000000`
1.44. Register new CSM Verifier `0xfce7aB839e55de77730716D05b3553e45ab3A5Ba` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CSM Committee `0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f`
1.45. Register new CSM Ejector `0x610B517D380f287c239C93F8eF6FfBd567AA4bA5` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CSM Committee `0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f`
1.46. Register VettedGate (Identified DVT Cluster Gate) `0xa12760721A72A7199aB38059DA6690b9Cd4ed7B8` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CSM Committee `0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f`
1.47. Grant CREATE_NODE_OPERATOR_ROLE `0xc72a21b38830f4d6418a239e17db78b945cc7cfee674bac97fd596eaf0438478` to VettedGate (Identified DVT Cluster Gate) `0xa12760721A72A7199aB38059DA6690b9Cd4ed7B8` on CSModule `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f`
1.48. Grant SET_BOND_CURVE_ROLE `0x645c9e6d2a86805cb5a28b1e4751c0dab493df7cf935070ce405489ba1a7bf72` to VettedGate (Identified DVT Cluster Gate) `0xa12760721A72A7199aB38059DA6690b9Cd4ed7B8` on CSM Accounting `0x4d72bff1beac69925f8bd12526a39baab069e5da`
1.49. Grant MANAGE_BOND_CURVES_ROLE `0xd35e4a788498271198ec69c34f1dc762a1eee8200c111f598da1b3dde946783d` to Identified DVT Cluster Curve Setup `0x711985E069f4d702e0457C0dACAde3D3894Ce4E3` on CSM Accounting `0x4d72bff1beac69925f8bd12526a39baab069e5da`
1.50. Grant MANAGE_CURVE_PARAMETERS_ROLE `0x2ea86fa86b8394b93915254c102ea62e584d45bf5fd06dbc4e2efaddacd2d925` to Identified DVT Cluster Curve Setup `0x711985E069f4d702e0457C0dACAde3D3894Ce4E3` on ParametersRegistry `0x9d28ad303c90df524ba960d7a2dac56dcc31e428`
1.51. Execute `execute()` on Identified DVT Cluster Curve Setup `0x711985e069f4d702e0457c0dacade3d3894ce4e3`
1.52. Grant MANAGE_GENERAL_PENALTIES_AND_CHARGES_ROLE `0x00b6097bf7ad894f88f786cd383df3190b971af96510047737d0cb2e9bd25558` to CSM Committee `0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f` on ParametersRegistry `0x9d28ad303c90df524ba960d7a2dac56dcc31e428`
1.53. Revoke REQUEST_BURN_SHARES_ROLE `0x4be29e0e4eb91f98f709d98803cba271592782e293b84a625e025cbb40197ba8` from CSM Accounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` on Burner `0xe76c52750019b80b43e36df30bf4060eb73f573a`
1.54. Grant REQUEST_BURN_MY_STETH_ROLE `0x28186f938b759084eea36948ef1cd8b40ec8790a98d5f1a09b70879fe054e5cc` to CSM Accounting `0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da` on Burner `0xe76c52750019b80b43e36df30bf4060eb73f573a`
1.55. Revoke ADD_FULL_WITHDRAWAL_REQUEST_ROLE `0x15fac8ba7fe8dd5344b88c1915452ce66976f270d1cd793c3b0ab579cecd33c0` from old CSM Ejector `0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C` on Triggerable Withdrawals Gateway `0xdc00116a0d3e064427da2600449cfd2566b3037b`
1.56. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE `0x15fac8ba7fe8dd5344b88c1915452ce66976f270d1cd793c3b0ab579cecd33c0` to new CSM Ejector `0x610B517D380f287c239C93F8eF6FfBd567AA4bA5` on Triggerable Withdrawals Gateway `0xdc00116a0d3e064427da2600449cfd2566b3037b`

IV. Curated Module
1.57. Add staking module `curated-onchain-v2` with module CuratedModule `0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1`, stake share limit `10000`, priority exit share threshold `10000`, staking module fee `400`, treasury fee `600`, max deposits per block `100`, min deposit block distance `75`, and withdrawal credentials type `2` on Staking Router `0xfddf38947afb03c621c71b06c9c70bce73f12999`
1.58. Grant REQUEST_BURN_MY_STETH_ROLE `0x28186f938b759084eea36948ef1cd8b40ec8790a98d5f1a09b70879fe054e5cc` to Curated Accounting `0x2F91e3A8C5d6593bf4F8403fCfeCcd62dF59f6F6` on Burner `0xe76c52750019b80b43e36df30bf4060eb73f573a`
1.59. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE `0x15fac8ba7fe8dd5344b88c1915452ce66976f270d1cd793c3b0ab579cecd33c0` to Curated Ejector `0xe181A377A2d2BDE9A83f1474BC3DB7A412de091E` on Triggerable Withdrawals Gateway `0xdc00116a0d3e064427da2600449cfd2566b3037b`
1.60. Grant RESUME_ROLE `0x2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7` to Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` on CuratedModule `0xda5f930ce326eb5205085d66c72a4e79d60cb8c1`
1.61. Execute `resume()` on CuratedModule `0xda5f930ce326eb5205085d66c72a4e79d60cb8c1`
1.62. Revoke RESUME_ROLE `0x2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7` from Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` on CuratedModule `0xda5f930ce326eb5205085d66c72a4e79d60cb8c1`
1.63. Update initial epoch to `467564` on HashConsensus `0x902d64c93f6595339aa46105627a085591051afb`
1.64. Register CuratedModule `0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CMC Committee `0x2570e0b22AD904501dfB0d49575991ACB801dD91`
1.65. Register Curated Accounting `0x2F91e3A8C5d6593bf4F8403fCfeCcd62dF59f6F6` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CMC Committee `0x2570e0b22AD904501dfB0d49575991ACB801dD91`
1.66. Register Curated FeeOracle `0x8EeFCdbD984c30E472BcbF545783D051CB5114e5` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CMC Committee `0x2570e0b22AD904501dfB0d49575991ACB801dD91`
1.67. Register Curated Verifier `0xC392F457960f1B13Ebaf1aa6C065479dD507E1E3` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CMC Committee `0x2570e0b22AD904501dfB0d49575991ACB801dD91`
1.68. Register Curated Ejector `0xe181A377A2d2BDE9A83f1474BC3DB7A412de091E` on CircuitBreaker `0x6019cb557978296ba3c08a7b73225c0975dfb2f7` with pauser CMC Committee `0x2570e0b22AD904501dfB0d49575991ACB801dD91`

V. Finish Upgrade
1.69. Execute `finishUpgrade()` on Upgrade Template `0xd92b6303ba39297cb69a3a17a88b47586a6af14c`

VI. EasyTrack
2. Remove EVM script factory CSMSettleElStealingPenalty `0xF6B6E7997338C48Ea3a8BCfa4BB64a315fDa76f4` from EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
3. Remove EVM script factory CSMSetVettedGateTree `0xBc5642bDD6F2a54b01A75605aAe9143525D97308` from EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
4. Add EVM script factory UpdateStakingModuleShareLimits `0x0C6703F1d8D9DdfB6c6e5F57b4f7432a6500D6D8` with permissions `0x0c6703f1d8d9ddfb6c6e5f57b4f7432a6500d6d85adcee90fddf38947afb03c621c71b06c9c70bce73f1299913976a06` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
5. Add EVM script factory AllowConsolidationPair `0x29e23B1EF0c9fffAc8330F9abaCebDDD827E4b5C` with permissions `0x9dc70b5a4f4f5e4af9058c983d560564f031f1d7b4ecbe1a` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
6. Add EVM script factory SetMerkleGateTree `0xf3ec30B86c3dC1b8a1C754D885F9bE3160e15B4c` with permissions `0xf3ec30b86c3dc1b8a1c754d885f9be3160e15b4c672c809eb314d4a76c457c93150d308787939063f4cc67e0ed4b1869a12760721a72a7199ab38059da6690b9cd4ed7b8ed4b1869` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
7. Add EVM script factory ReportWithdrawalsForSlashedValidators `0xE330516a03bDdEBA4209b5591112f1aa3dd90F0A` with permissions `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f4412f7aa` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
8. Add EVM script factory SettleGeneralDelayedPenalty `0xB71755bE764abB4Ce26cb4dADf056Be57fB8880F` with permissions `0xda7de2ecddfccc6c3af10108db212acbbf9ea83f187d9f92` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
9. Add EVM script factory SetMerkleGateTree `0xa121667D1780a1D54EAEd67AE17ee13d0f872D60` with permissions `0xa121667d1780a1d54eaed67ae17ee13d0f872d60672c809e6093efa6b5e2ff3be54d1c895c9dea932805c49fed4b18698c002c6ee10cf8adb78d1f9eb2e134fdaf8a7c1aed4b1869207798e6fd1aa7ee8a63782a64c959cd6727b78ced4b1869ef273ca4a21ba7b414ae3c9f9b443038cb133f72ed4b18693bbbb175f7f07954de00052b20e1c5572223f24ded4b186986a8d4e0db5938d21d98047544668fccb1a9adc8ed4b1869773933f9db8964a17d62fb808f2ec7a2de4247cced4b1869` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
10. Add EVM script factory ReportWithdrawalsForSlashedValidators `0x71862Abd99819597670007bb992A7a7562fE50f2` with permissions `0xda5f930ce326eb5205085d66c72a4e79d60cb8c14412f7aa` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
11. Add EVM script factory SettleGeneralDelayedPenalty `0xfffEFC16231eDC6Dc9C93e364ff4D4E3f787f416` with permissions `0xda5f930ce326eb5205085d66c72a4e79d60cb8c1187d9f92` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`
12. Add EVM script factory CreateOrUpdateOperatorGroup `0x2fC78638b77381e9D040163Bd6EB1cac967bDBdF` with permissions `0x2fc78638b77381e9d040163bd6eb1cac967bdbdfc4e88725a64b339eebd3dc3de848298b6a140955932901d852d13274` on EasyTrack `0xf0211b7660680b49de1a7e9f25c65660f0a13fea`

Vote passed & executed on [TBA] +UTC, block [TBA]

"""

from typing import Dict, List, Optional, Tuple

from brownie import interface

from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.dual_governance import submit_proposals
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

# SRv3/CMv2 upgrade omnibus (UpgradeVoteScript) — the vote script reads its items
# from this contract. Synced from core/deployed-mainnet.json.
UPGRADE_VOTE_SCRIPT = "0xE6530830A2cf90773cB232748b2c674c27b6E0CA"

# ============================= Description ==================================
DG_PROPOSAL_METADATA = "Activate Staking Router v3, Community Staking Module v3 and Curated Module v2"
DG_SUBMISSION_DESCRIPTION = "1. Submit a Dual Governance proposal to activate Staking Router v3, Community Staking Module v3 and Curated Module v2"
IPFS_DESCRIPTION = """
# Staking Router v3, Community Staking Module v3 and Curated Module v2

Upgrade the [Staking Router to v3 (SRv3)](https://research.lido.fi/t/staking-router-v3-design-implementation-proposal-lip-35/11621) to enable balance-based accounting and support for 0x02 validators, upgrade the [Community Staking Module to v3 (CSMv3)](https://github.com/lidofinance/lido-improvement-proposals/blob/develop/LIPS/lip-33.md#motivation) and add the [Curated Module v2 (CMv2)](https://research.lido.fi/t/future-of-the-curated-module-cmv2-landscape/10929) to the Staking Router. The changes follow the DAO-approved Snapshot proposals [LIP-35 (SRv3)](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x8fdec5d2cb70f8a266c4f5a269051fcfa985fab0f66cbe747702719d7433f606) and [LIP-33 (CMv2 and CSMv3)](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x7b07bc31f0b38b69a117473031bc126becc70b9fa37246b53d9fe5a841c814f5).

Audits & deployment verification:
- SRv3: [Certora](https://github.com/lidofinance/audits/blob/main/Certora%20Staking%20Router%20v3%20Audit%20Report%2007-2026.pdf), [Statemind](https://github.com/lidofinance/audits/blob/main/Statemind%20Staking%20Router%20v3%20Audit%20Report%2007-2026.pdf)
- CSMv3 & CMv2: [Certora](https://github.com/lidofinance/audits/blob/main/Certora%20Lido%20CSM%20v3%20and%20CM%20v2%20Audit%20Report%20-%2006-2026.pdf), [Statemind](https://github.com/lidofinance/audits/blob/main/Statemind%20Lido%20CSM%20v3%20and%20CM%20v2%20Audit%20Report%2006-2026.pdf)
- Upgrade voting contracts: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Staking%20Router%20v3%20Upgrade%20Audit%20Report%2007-2026.pdf)
- Easy Track factories: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20Easy%20Track%20Factories%20(SRv3%20CSMv3%20CMv2)%20Security%20Audit%20Report%2007-2026.pdf)
- Off-chain Oracle: [Composable Security](https://github.com/lidofinance/audits/blob/main/Composable%20Security%20Lido%20Oracle%20V8_0_2%20Security%20Consultation%20Report.pdf)

[Dual Governance Items](https://research.lido.fi/t/future-of-the-curated-module-cmv2-landscape/10929/33#p-25898-part-2-dual-governance-items-69-items-subject-to-dg-veto-period-3)

* Lock the upgrade window and record initial protocol state. Item 1.1.
* Upgrade Lido Core contracts to enable SRv3, reassign roles and permissions, set Triggerable Withdrawals Gateway (TWG) exit limits, and register CircuitBreaker Committee as the pauser for the new Consolidation Gateway and TopUp Gateway sealables. Items 1.2 - 1.19.
* Upgrade CSM contracts to v3, reassign roles and permissions, enable Identified DVT Cluster type, and register [CSM Committee](https://docs.lido.fi/multisigs/committees/#29-community-staking-module-committee) as the pauser for the CSM sealables. Items 1.20 - 1.56.
* Add CMv2 to the Staking Router, assign roles and permissions, and register [CM Committee](https://docs.lido.fi/multisigs/committees/#220-curated-module-committee-cmc) as the pauser for the CMv2 sealables. Items 1.57 - 1.68.
* Finalize the upgrade and perform final assertions. Item 1.69.

[Voting Items](https://research.lido.fi/t/future-of-the-curated-module-cmv2-landscape/10929/33#p-25898-part-1-voting-items-11-items-execute-immediately-2)

- Remove deprecated CSM Easy Track factories: CSMSettleElStealingPenalty and CSMSetVettedGateTree. Items 2 - 3.
- Add 9 Easy Track factories supporting CSMv3, CMv2, and consolidation operations. Items 4 - 12.
"""


def get_dg_items(upgrade_vote_script: Optional[str] = None) -> List[Tuple[str, str]]:
    vote_script_address = (upgrade_vote_script or UPGRADE_VOTE_SCRIPT).strip()
    omnibus = interface.UpgradeVoteScript(vote_script_address)
    dg_items: List[Tuple[str, str]] = []

    for _, call_script in omnibus.getVoteItems():
        dg_items.append((call_script[0], call_script[1].hex()))

    return dg_items


def get_vote_items(
    upgrade_vote_script: Optional[str] = None,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    vote_script_address = (upgrade_vote_script or UPGRADE_VOTE_SCRIPT).strip()
    omnibus = interface.UpgradeVoteScript(vote_script_address)

    vote_desc_items: List[str] = []
    call_script_items: List[Tuple[str, str]] = []

    dg_items = get_dg_items(upgrade_vote_script)

    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_METADATA)])
    vote_desc_items.append(DG_SUBMISSION_DESCRIPTION)
    call_script_items.append(dg_call_script[0])

    voting_items = omnibus.getVotingVoteItems()
    for desc, call_script in voting_items:
        vote_desc_items.append(desc)
        call_script_items.append((call_script[0], call_script[1].hex()))

    return vote_desc_items, call_script_items


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
    upgrade_vote_script: Optional[str] = None,
):
    vote_desc_items, call_script_items = get_vote_items(
        upgrade_vote_script=upgrade_vote_script,
    )
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))
    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    vote_script_address = (upgrade_vote_script or UPGRADE_VOTE_SCRIPT).strip()
    assert interface.UpgradeVoteScript(vote_script_address).isValidVoteScript(
        vote_id,
        DG_PROPOSAL_METADATA,
    )

    return vote_id, tx


def main(upgrade_vote_script: Optional[str] = None):
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(
        tx_params=tx_params,
        silent=False,
        upgrade_vote_script=upgrade_vote_script,
    )
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def post_vote_on_fork():
    if get_is_live():
        raise Exception("This hook is for local testing only.")

    print("Rebuilding CSM total withdrawn validators after vote...")
    contracts.csm.rebuildTotalWithdrawnValidators({"from": get_deployer_account(), "silent": True})
    print("[ok] CSM total withdrawn validators rebuilt")


def start_and_execute_vote_on_fork_manual(upgrade_vote_script: Optional[str] = None):
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(
        tx_params=tx_params,
        silent=True,
        upgrade_vote_script=upgrade_vote_script,
    )
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(
        int(vote_id),
        step_by_step=True,
    )
    post_vote_on_fork()
