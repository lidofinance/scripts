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
deployer_eoa = "0xBC862d4beE4E1cd82B9e8519b4375c3457fc6A5a"

# New contracts (deployed mainnet)
# TODO: add LidoLocator proxy here

# New contracts (yet deployed in preliminary steps)
lido_dao_lido_locator = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
gate_seal = "0x1aD5cb2955940F998081c1eF5f5F00875431aA90"
gate_seal_factory_address = "0x6C82877cAC5a7A739f16Ca0A89c0A328B8764A24"
shapella_upgrade_template_address = "0xc205B6c6bA5660E2A6e67A367eE65f83073C2f7D"
lido_dao_steth_implementation_address = "0x11638262f6d34D807aE469166f0368c8Dc2a5689"
lido_dao_node_operators_registry_implementation = "0x8e409ad726C887890d8129530B352A6fDf0e25Ad"
lido_dao_legacy_oracle_implementation = "0x599E51510719e94525eF406d4519949eca4242ac"
dummy_implementation_address = "0xf10Aa372B5FB8bCFCec860C145770C399fcc1eF4"
lido_dao_deposit_security_module_address_old = "0x710B3303fB508a84F10793c1106e32bE873C24cd"
lido_dao_deposit_security_module_address = "0xae39af54e982D3e343b248Ace96fa6B7a0E6FB2c"
lido_dao_lido_locator_implementation = "0x2d15B9620875A6d613B45739E8d23D50Dad0f688"
lido_dao_burner = "0x73C53b124D5200CA4BA9Ea696786e74cA78060A1"
lido_dao_hash_consensus_for_accounting_oracle = "0x289029fDA5E5155f581E276E66c7f367b3D433c0"
lido_dao_accounting_oracle = "0x3751203ccb564F30bf413DabEBbA957cD45F311A"
lido_dao_accounting_oracle_implementation = "0x41d3219AA3AF7CDA24B3B24ebCf415DB59d69662"
lido_dao_hash_consensus_for_validators_exit_bus_oracle = "0x08aFd6e128423fE661432b2A4872F53C98Da11Bf"
lido_dao_validators_exit_bus_oracle = "0x110406b2714A48741417a8B78B5D9c291652dc59"
lido_dao_validators_exit_bus_oracle_implementation = "0x6f2FBD3b7E76E7A17345Adb0F828840c963b382D"
lido_dao_oracle_report_sanity_checker = "0xAB58bA6bb1d30e48d4f5439A77D9B38bc53B7Ec0"
lido_dao_withdrawal_queue = "0x0E4FCfa76d83A6974269Ebe29AEbC61f827B2D05"
lido_dao_withdrawal_queue_implementation = "0x851f572d3382Ff19ec1f0E04E65B625E32bF21CB"
lido_dao_eip712_steth = "0xE5FCaDa1cE2E3DE88C2e79b8299740b8551E4649"
lido_dao_withdrawal_vault_implementation = "0xd457411A7B8e36aedC5c1080c6793414fa163793"
lido_dao_withdrawal_vault_implementation_v1 = "0xe681faB8851484B57F32143FD78548f25fD59980"
lido_dao_withdrawal_vault_stub_implementation = "0xe681faB8851484B57F32143FD78548f25fD59980"
lido_dao_staking_router = "0x7F17B9C7BaC5769A354E2133963553996FB1a0eC"
lido_dao_staking_router_implementation = "0xF28459782bD32200d1475b0163e86216F35b9315"
oracle_daemon_config = "0xA3821b42f1c1D587CaDd3deF3Dd4BD252Bb11Ac9"

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
