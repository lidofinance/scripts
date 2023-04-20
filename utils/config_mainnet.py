chain_network = "mainnet"
# DAO
lido_dao_kernel = "0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc"
ldo_token_address = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"
# Standard (or forked) Aragon apps
lido_dao_acl_address = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
lido_dao_agent_address = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
lido_dao_finance_address = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"
lido_dao_voting_address = "0x2e59A20f205bB85a89C53f1936454680651E618e"
lido_dao_token_manager_address = "0xf73a1260d222f447210581DDf212D915c09a3249"
# Our custom Aragon apps
lido_dao_node_operators_registry = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
lido_dao_steth_address = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
lido_dao_legacy_oracle = "0x442af784A788A5bd6F42A01Ebe9F287a871243fb"
# Aragon APM Repos
lido_dao_voting_repo = "0x4Ee3118E3858E8D7164A634825BfE0F73d99C792"
lido_dao_lido_repo = "0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1"
lido_dao_node_operators_registry_repo = "0x0D97E876ad14DB2b183CFeEB8aa1A5C788eB1831"
lido_dao_legacy_oracle_repo = "0xF9339DE629973c60c4d2b76749c81E6F40960E3A"

curve_rewards_manager_address = "0x753D5167C31fBEB5b49624314d74A957Eb271709"
balancer_rewards_manager = "0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8"

lido_easytrack = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
lido_easytrack_evmscriptexecutor = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
lido_easytrack_increase_nop_staking_limit_factory = "0xFeBd8FAC16De88206d4b18764e826AF38546AfE0"

lido_insurance_fund_address = "0x8B3f33234ABD88493c0Cd28De33D583B70beDe35"
lido_relay_allowed_list = "0xF95f069F9AD107938F6ba802a3da87892298610E"

lido_dao_execution_layer_rewards_vault = "0x388C818CA8B9251b393131C08a736A67ccB19297"

# Multisigs
finance_multisig_address = "0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb"

ldo_holder_address_for_tests = "0x9bb75183646e2a0dc855498bacd72b769ae6ced3"
ldo_vote_executors_for_tests = [
    "0x3e40d73eb977dc6a537af587d48316fee66e9c8c",
    "0xb8d83908aab38a159f3da47a59d84db8e1838712",
    "0xa2dfc431297aee387c05beef507e5335e684fbcd",
]

dai_token_address = "0x6b175474e89094c44da98b954eedeac495271d0f"
weth_token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

#
# New entires for the Shapella Upgrade
#

# Existed contracts
lido_dao_voting_implementation_address = "0x72fb5253AD16307B9E773d2A78CaC58E309d5Ba4"
lido_dao_kernel_implementation = "0x2b33CF282f867A7FF693A66e11B0FcC5552e4425"
lido_dao_calls_script = "0x5cEb19e1890f677c3676d5ecDF7c501eBA01A054"
lido_dao_acl_implementation_address = "0x9f3b9198911054B122fDb865f8A5Ac516201c339"
lido_dao_legacy_oracle_implementation_v1 = "0x1430194905301504e8830ce4B0b0df7187E84AbD"
lido_dao_steth_implementation_address_v1 = "0x47EbaB13B806773ec2A2d16873e2dF770D130b50"
lido_dao_node_operators_registry_implementation_v1 = "0x5d39ABaa161e622B99D45616afC8B837E9F19a25"
wsteth_token_address = "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0"
deposit_contract = "0x00000000219ab540356cBB839Cbe05303d7705Fa"
lido_dao_withdrawal_vault = "0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f"

# Existed values from chain
oracle_committee = (
    "0x140Bd8FbDc884f48dA7cb1c09bE8A2fAdfea776E",
    "0x1d0813bf088BE3047d827D98524fBf779Bc25F00",
    "0x404335BcE530400a5814375E7Ec1FB55fAff3eA2",
    "0x946D3b081ed19173dC83Cd974fC69e1e760B7d78",
    "0x007DE4a5F7bc37E2F26c0cb2E8A95006EE9B89b5",
    "0xEC4BfbAF681eb505B94E4a7849877DC6c600Ca3A",
    "0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8",
    "0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d",
    "0xA7410857ABbf75043d61ea54e07D57A6EB6EF186",
)

guardians = [
    "0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1",
    "0x7912Fa976BcDe9c2cf728e213e892AD7588E6AaF",
    "0x14D5d5B71E048d2D75a39FfC5B407e3a3AB6F314",
    "0xf82D88217C249297C6037BA77CE34b3d8a90ab43",
    "0xa56b128Ea2Ea237052b0fA2a96a387C0E43157d8",
    "0xd4EF84b638B334699bcf5AF4B0410B8CCD71943f",
]

# New: EOA
deployer_eoa = "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1"

# New contracts (deployed mainnet)
# TODO: add LidoLocator proxy here

# New contracts (yet deployed in preliminary steps)
lido_dao_lido_locator = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
gate_seal = "0xD59f8Bc37BAead58cbCfD99b03997655A13f56d9"
shapella_upgrade_template_address = "0xF9a393Baab3C575c2B31166636082AB58a3dae62"
lido_dao_steth_implementation_address = "0xAb3bcE27F31Ca36AAc6c6ec2bF3e79569105ec2c"
lido_dao_node_operators_registry_implementation = "0x9cBbA6CDA09C7dadA8343C4076c21eE06CCa4836"
lido_dao_legacy_oracle_implementation = "0xcA3cE6bf0CB2bbaC5dF3874232AE3F5b67C6b146"
dummy_implementation_address = "0xE2f969983c8859E986d6e19892EDBd1eea7371D2"
lido_dao_deposit_security_module_address_old = "0x710B3303fB508a84F10793c1106e32bE873C24cd"
lido_dao_deposit_security_module_address = "0xe44E11BBb629Dc23e72e6eAC4e538AaCb66A0c88"
lido_dao_lido_locator_implementation = "0x7948f9cf80D99DDb7C7258Eb23a693E9dFBc97EC"
lido_dao_burner = "0xFc810b3F9acc7ee0C3820B5f7a9bb0ee88C3cBd2"
lido_dao_hash_consensus_for_accounting_oracle = "0x379EBeeD117c96380034c6a6234321e4e64fCa0B"
lido_dao_accounting_oracle = "0x9FE21EeCC385a1FeE057E58427Bfb9588E249231"
lido_dao_accounting_oracle_implementation = "0x115065ad19aDae715576b926CF6e26067F64e741"
lido_dao_hash_consensus_for_validators_exit_bus_oracle = "0x2330b9F113784a58d74c7DB49366e9FB792DeABf"
lido_dao_validators_exit_bus_oracle = "0x6e7Da71eF6E0Aaa85E59554C1FAe44128fA649Ed"
lido_dao_validators_exit_bus_oracle_implementation = "0xfdfad30ae5e5c9Dc4fb51aC35AB60674FcBdefB3"
lido_dao_oracle_report_sanity_checker = "0x499A11A07ebe21685953583B6DA9f237E792aEE3"
lido_dao_withdrawal_queue = "0xFb4E291D12734af4300B89585A16dF932160b840"
lido_dao_withdrawal_queue_implementation = "0x5EfF11Cb6bD446370FC3ce46019F2b501ba06c2D"
lido_dao_eip712_steth = "0x8dF3c29C96fd4c4d496954646B8B6a48dFFcA83F"
lido_dao_withdrawal_vault_implementation = "0x654f166BA493551899212917d8eAa30CE977b794"
lido_dao_withdrawal_vault_implementation_v1 = "0xe681faB8851484B57F32143FD78548f25fD59980"
lido_dao_withdrawal_vault_stub_implementation = "0xe681faB8851484B57F32143FD78548f25fD59980"
lido_dao_staking_router = "0x5A2a6cB5e0f57A30085A9411f7F5f07be8ad1Ec7"
lido_dao_staking_router_implementation = "0x4384fB5DcaC0576B93e36b8af6CdfEB739888894"
oracle_daemon_config = "0xbA3981771AB991960028B2F83ae83664Fd003F61"

# Used if env variable PARSE_EVENTS_FROM_LOCAL_ABI is set
# Needed to enable events checking if ABI from Etherscan not available for any reason
contract_address_mapping = {
    "AccountingOracle": [lido_dao_accounting_oracle, lido_dao_accounting_oracle_implementation],
    "ACL": [lido_dao_acl_implementation_address],
    "Burner": [lido_dao_burner],
    "CallsScript": [lido_dao_calls_script],
    "DepositSecurityModule": [lido_dao_deposit_security_module_address],
    "EIP712StETH": [lido_dao_eip712_steth],
    "HashConsensus": [
        lido_dao_hash_consensus_for_accounting_oracle,
        lido_dao_hash_consensus_for_validators_exit_bus_oracle,
    ],
    "LegacyOracle": [lido_dao_legacy_oracle, lido_dao_legacy_oracle_implementation],
    "Lido": [lido_dao_steth_address, lido_dao_steth_implementation_address],
    "LidoLocator": [lido_dao_lido_locator],
    "LidoExecutionLayerRewardsVault": [lido_dao_execution_layer_rewards_vault],
    "Kernel": [lido_dao_kernel_implementation],
    "NodeOperatorsRegistry": [lido_dao_node_operators_registry, lido_dao_node_operators_registry_implementation],
    "OracleDaemonConfig": [oracle_daemon_config],
    "OracleReportSanityChecker": [lido_dao_oracle_report_sanity_checker],
    "Repo": ["0xa8A358E9bbB9fF60D4B89CBE5b2FE88f98b51B9D"],
    "StakingRouter": [lido_dao_staking_router, lido_dao_staking_router_implementation],
    "ValidatorsExitBusOracle": [
        lido_dao_validators_exit_bus_oracle,
        lido_dao_validators_exit_bus_oracle_implementation,
    ],
    "Voting": [lido_dao_voting_implementation_address],
    "WithdrawalQueueERC721": [lido_dao_withdrawal_queue, lido_dao_withdrawal_queue_implementation],
    "WithdrawalVault": [lido_dao_withdrawal_vault, lido_dao_withdrawal_vault_implementation],
}
