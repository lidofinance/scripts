# Use this config as addressbook only
chain_network = "goerli"
# DAO
lido_dao_kernel = "0x1dD91b354Ebd706aB3Ac7c727455C7BAA164945A"
ldo_token_address = "0x56340274fB5a72af1A3C6609061c451De7961Bd4"
# Standard (or forked) Aragon apps
lido_dao_acl_address = "0xb3cf58412a00282934d3c3e73f49347567516e98"
lido_dao_agent_address = "0x4333218072D5d7008546737786663c38B4D561A4"
lido_dao_finance_address = "0x75c7b1D23f1cad7Fb4D60281d7069E46440BC179"
lido_dao_voting_address = "0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db"
lido_dao_token_manager_address = "0xDfe76d11b365f5e0023343A367f0b311701B3bc1"
# Our custom Aragon apps
lido_dao_node_operators_registry = "0x9D4AF1Ee19Dad8857db3a45B0374c81c8A1C6320"
lido_dao_steth_address = "0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F"
lido_dao_legacy_oracle = "0x24d8451BC07e7aF4Ba94F69aCDD9ad3c6579D9FB"
# Aragon APM Repos
lido_dao_voting_repo = "0x14de4f901cE0B81F4EfcA594ad7b70935C276806"
lido_dao_lido_repo = "0xe9ede497d2417fd980d8b5338232666641b9b9ac"
lido_dao_node_operators_registry_repo = "0x5f867429616b380f1ca7a7283ff18c53a0033073"
lido_dao_legacy_oracle_repo = "0x9234e37Adeb44022A078557D9943b72AB89bF36a"

lido_dao_deposit_security_module_address_old = "0x7DC1C1ff64078f73C98338e2f17D1996ffBb2eDe"
lido_dao_deposit_security_module_address = "0xC8a75E7196b11aE2DEbC39a2F8583f852E5BB7c3"

# Needed only for the tests development. Before the voting start the LidoLocator
# proxy is to be set to the implementation
lido_dao_lido_locator_implementation = "0x6D5b7439c166A1BDc5c8DB547c1a871c082CE22C"
lido_dao_accounting_oracle_implementation = "0x49cc40EE660BfD5f46423f04891502410d32E965"

# Needed temporary only for Shapella upgrade
deployer_eoa = "0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1"
dummy_implementation_address = ""

lido_dao_lido_locator = "0x1eDf09b5023DC86737b59dE68a8130De878984f5"
lido_dao_burner = "0x20c61C07C2E2FAb04BF5b4E12ce45a459a18f3B1"
lido_dao_execution_layer_rewards_vault = "0x94750381bE1AbA0504C666ee1DB118F68f0780D4"
lido_dao_hash_consensus_for_accounting_oracle = "0x8d87A8BCF8d4e542fd396D1c50223301c164417b"
lido_dao_accounting_oracle = "0x76f358A842defa0E179a8970767CFf668Fc134d6"
lido_dao_hash_consensus_for_validators_exit_bus_oracle = "0x8374B4aC337D7e367Ea1eF54bB29880C3f036A51"
lido_dao_validators_exit_bus_oracle = "0xb75A55EFab5A8f5224Ae93B34B25741EDd3da98b"
lido_dao_oracle_report_sanity_checker = "0x0F3475f755FA356f1356ABC80B4aE4a786d8aae5"
lido_dao_withdrawal_queue = "0xCF117961421cA9e546cD7f50bC73abCdB3039533"
gate_seal = "0x75A77AE52d88999D0b12C6e5fABB1C1ef7E92638"
lido_dao_eip712_steth = "0xB4300103FfD326f77FfB3CA54248099Fb29C3b9e"
lido_dao_withdrawal_vault = "0xdc62f9e8C34be08501Cdef4EBDE0a280f576D762"
lido_dao_withdrawal_vault_implementation = "0x297Eb629655C8c488Eb26442cF4dfC8A7Cc32fFb"
lido_dao_staking_router = "0xa3Dbd317E53D363176359E10948BA0b1c0A4c820"
oracle_daemon_config = "0xad55833Dec7ab353B47691e58779Bd979d459388"
shapella_upgrade_template_address = "0xD2fEf3d3544ddf64028784aC3f166413A2A61393"

lido_easytrack = "0xAf072C8D368E4DD4A9d4fF6A76693887d6ae92Af"
lido_easytrack_evmscriptexecutor = "0x3c9AcA237b838c59612d79198685e7f20C7fE783"
lido_easytrack_increase_nop_staking_limit_factory = "0xE033673D83a8a60500BcE02aBd9007ffAB587714"

lido_insurance_fund_address = "0x2FAe4D2D86Efb17249F24C9fb70855d4c58585A5"
lido_relay_allowed_list = "0xeabE95AC5f3D64aE16AcBB668Ed0efcd81B721Bc"

ldo_holder_address_for_tests = "0x709abe1880E3B7A813A297B68a1cdB8976025550"
ldo_vote_executors_for_tests = [
    "0x319d5370715D24A1225817009BB23e676aE741D3",
    "0x4333218072d5d7008546737786663c38b4d561a4",
    "0xfda7e01b2718c511bf016030010572e833c7ae6a",
]

dai_token_address = "0x11fE4B6AE13d2a6055C8D9cF65c55bac32B5d844"

weth_token_address = "0xb4fbf271143f4fbf7b91a5ded31805e42b2208d6"

oracle_committee = [
    "0xfdA7E01B2718C511bF016030010572e833C7aE6A",
    "0xD3b1e36A372Ca250eefF61f90E833Ca070559970",
    "0x1a13648EE85386cC101d2D7762e2848372068Bc3",
    "0x3fF28f2EDE8358E288798afC23Ee299a503aD5C9",
    "0x4c75FA734a39f3a21C57e583c1c29942F021C6B7",
    "0xCFd533f909741B78a564e399F64C83B783c27597",
    "0x81E411f1BFDa43493D7994F82fb61A415F6b8Fd4",
    "0xb29dD2f6672C0DFF2d2f173087739A42877A5172",
    "0x3799bDA7B884D33F79CEC926af21160dc47fbe05",
]

guardians = [
    "0x3dc4cF780F2599B528F37dedB34449Fb65Ef7d4A",
    "0x96fD3D127Abd0D77724D49B7bdDECdc89f684bB6",
    "0x79A132BE0c25cED09e745629D47cf05e531bb2bb",
    "0x43464Fe06c18848a2E2e913194D64c1970f4326a",
    "0xD15B778e954b02d44f343c2fC7b54D4B08d9b1be",
    "0xf060ab3d5dCfdC6a0DFd5ca0645ac569b8f105CA",
    "0xC34D33b95D7D6DF2255D6051ddB12F8bd7AEF64c",
    "0xdA1A296F9Df18D04e0aEfcfF658B80B3EF824ec9",
    "0x25F76608A3FbC9C75840E070e3c285ce1732F834",
]

wsteth_token_address = "0x6320cd32aa674d2898a68ec82e869385fc5f7e2f"
deposit_contract = "0xff50ed3d0ec03aC01D4C79aAd74928BFF48a7b2b"

# Used if env variable PARSE_EVENTS_FROM_LOCAL_ABI is set
# Needed to enable events checking if ABI from Etherscan not available for any reason
contract_address_mapping = {}
