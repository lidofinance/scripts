# Ethereum Chain parameters
CHAIN_NETWORK_NAME = "holesky"
CHAIN_SLOTS_PER_EPOCH = 32
CHAIN_SECONDS_PER_SLOT = 12
CHAIN_GENESIS_TIME = 1695902400
CHAIN_DEPOSIT_CONTRACT = "0x4242424242424242424242424242424242424242"

# DAO
ARAGON_KERNEL = "0x3b03f75Ec541Ca11a223bB58621A3146246E1644"
LDO_TOKEN = "0x14ae7daeecdf57034f3E9db8564e46Dba8D97344"
ARAGON_KERNEL_IMPL = "0x34c0cbf9836FD945423bD3d2d72880da9d068E5F"

# Standard (or forked) Aragon apps
ACL = "0xfd1E42595CeC3E83239bf8dFc535250e7F48E0bC"
AGENT = "0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d"
FINANCE = "0xf0F281E5d7FBc54EAFcE0dA225CDbde04173AB16"
VOTING = "0xdA7d2573Df555002503F29aA4003e398d28cc00f"
TOKEN_MANAGER = "0xFaa1692c6eea8eeF534e7819749aD93a1420379A"
ACL_IMPL = "0xF1A087E055EA1C11ec3B540795Bd1A544e6dcbe9"
VOTING_IMPL = "0x994c92228803e8b2D0fb8a610AbCB47412EeF8eF"

# Our custom Aragon apps
LIDO = "0x3F1c547b21f65e10480dE3ad8E19fAAC46C95034"
LEGACY_ORACLE = "0x072f72BE3AcFE2c52715829F2CD9061A6C8fF019"
NODE_OPERATORS_REGISTRY = "0x595F64Ddc3856a3b5Ff4f4CC1d1fb4B46cFd2bAC"
# set address here after deploy
NODE_OPERATORS_REGISTRY_IMPL = "0x41646708A7EDbe22BD635Cb838Ff9C0CfA99A3bE"

# Aragon APM Repos
VOTING_REPO = "0x2997EA0D07D79038D83Cb04b3BB9A2Bc512E3fDA"
LIDO_REPO = "0xA37fb4C41e7D30af5172618a863BBB0f9042c604"
NODE_OPERATORS_REGISTRY_REPO = "0x4E8970d148CB38460bE9b6ddaab20aE2A74879AF"
LEGACY_ORACLE_REPO = "0xB3d74c319C0C792522705fFD3097f873eEc71764"

## LIDO_ARAGON_REPO_IMPL is common for Lido, NodeOperatorsRegistry, Oracle aragon apps
ARAGON_COMMON_REPO_IMPL = "0x8959360c48D601a6817BAf2449E5D00cC543FA3A"

# Other Aragon contracts
## For LIDO_EVM_SCRIPT_REGISTRY see Aragon Agent 0x853cc0D5917f49B57B8e9F89e491F5E18919093A
ARAGON_EVMSCRIPT_REGISTRY = "0xE1200ae048163B67D69Bc0492bF5FddC3a2899C0"
## See getEVMScriptExecutor(0x00000001) of any Aragon App or callsScript of LIDO_EASYTRACK_EVMSCRIPTEXECUTOR
ARAGON_CALLS_SCRIPT = "0xAa8B4F258a4817bfb0058b861447878168ddf7B0"

# Other (non-aragon) protocol contracts
WSTETH_TOKEN = "0x8d09a4502Cc8Cf1547aD300E066060D043f6982D"

EXECUTION_LAYER_REWARDS_VAULT = "0xE73a3602b99f1f913e72F8bdcBC235e206794Ac8"

WITHDRAWAL_VAULT = "0xF0179dEC45a37423EAD4FaD5fCb136197872EAd9"

# EasyTracks
EASYTRACK = "0x1763b9ED3586B08AE796c7787811a2E1bc16163a"

EASYTRACK_EVMSCRIPT_EXECUTOR = "0x2819B65021E13CEEB9AC33E77DB32c7e64e7520D"
EASYTRACK_INCREASE_NOP_STAKING_LIMIT_FACTORY = ""
EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER = "0xD76001b33b23452243E2FDa833B6e7B8E3D43198"
EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY = "0xeF5233A5bbF243149E35B353A73FFa8931FDA02b"
EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY = "0x5b4A9048176D5bA182ceec8e673D8aA6927A40D6"
EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY = "0x88d247cdf4ff4A4AAA8B3DD9dd22D1b89219FB3B"
EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY = "0x30Cb36DBb0596aD9Cf5159BD2c4B1456c18e47E8"
EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY = "0x4792BaC0a262200fA7d3b68e7622bFc1c2c3a72d"
EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY = "0x6Bfc576018C7f3D2a9180974E5c8e6CFa021f617"
EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY = "0xC91a676A69Eb49be9ECa1954fE6fc861AE07A9A2"
EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY = "0xb8C4728bc0826bA5864D02FA53148de7A44C2f7E"
EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY = "0x0"
EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY = "0x0"
EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY = "0x0"

# Multisigs
FINANCE_MULTISIG = ""

# Other
INSURANCE_FUND = ""
RELAY_ALLOWED_LIST = ""
CURVE_REWARDS_MANAGER = ""
BALANCER_REWARDS_MANAGER = ""
LIDO_V2_UPGRADE_TEMPLATE = ""

# Auxiliary addresses
LDO_HOLDER_ADDRESS_FOR_TESTS = "0xcd1f9954330af39a74fd6e7b25781b4c24ee373f"
LDO_VOTE_EXECUTORS_FOR_TESTS = [
    "0xaa6bfbcd634ee744cb8fe522b29add23124593d3",
    "0xba59a84c6440e8cccfdb5448877e26f1a431fc8b",
    "0x1d835790d93a28fb30d998c0cb27426e5d2d7c8c",
]
# General network addresses
DAI_TOKEN = ""
USDT_TOKEN = ""
USDC_TOKEN = ""
WETH_TOKEN = ""


LIDO_LOCATOR = "0x28FAB2059C713A7F9D8c86Db49f9bb0e96Af1ef8"
LIDO_LOCATOR_IMPL = "0xa19a59aF0680F6D9676ABD77E1Ba7e4c205F55a0"
WITHDRAWAL_QUEUE = "0xc7cc160b58F8Bb0baC94b80847E2CF2800565C50"
ORACLE_DAEMON_CONFIG = "0xC01fC1F2787687Bc656EAc0356ba9Db6e6b7afb7"
ORACLE_REPORT_SANITY_CHECKER = "0x80D1B1fF6E84134404abA18A628347960c38ccA7"

BURNER = "0x4E46BD7147ccf666E1d73A3A456fC7a68de82eCA"
DEPOSIT_SECURITY_MODULE = "0x808DE3b26Be9438F12E9B45528955EA94C17f217"
DEPOSIT_SECURITY_MODULE_V2 = "0x045dd46212A178428c088573A7d102B9d89a022A"  # dsm address before SR V2 enact
ACCOUNTING_ORACLE = "0x4E97A3972ce8511D87F334dA17a2C332542a5246"
ACCOUNTING_ORACLE_IMPL = "0x748CE008ac6b15634ceD5a6083796f75695052a2"
VALIDATORS_EXIT_BUS_ORACLE = "0xffDDF7025410412deaa05E3E1cE68FE53208afcb"
EIP712_STETH = "0xE154732c5Eab277fd88a9fF6Bdff7805eD97BCB1"
STAKING_ROUTER = "0xd6EbF043D30A7fe46D1Db32BA90a0A51207FE229"
STAKING_ROUTER_IMPL = "0x9b5890E950E3Df487Bb64E0A6743cdE791139152"
WITHDRAWAL_VAULT_IMPL = "0xd517d9d04DA9B47dA23df91261bd3bF435BE964A"


# GateSeal
GATE_SEAL_FACTORY = "0x1134F7077055b0B3559BE52AfeF9aA22A0E1eEC2"
GATE_SEAL = "0x7f6FA688d4C12a2d51936680b241f3B0F0F9ca60"
GATE_SEAL_PAUSE_DURATION = 518400  # 6 days
GATE_SEAL_EXPIRY_TIMESTAMP = 1714521600  # 2024-05-01 00:00GMT
GATE_SEAL_COMMITTEE = "0x6165267E76D609465640bffc158aff7905D47B46"

# TRP
TRP_VESTING_ESCROW_FACTORY = "0x586f0b51d46ac8ac6058702d99cd066ae514e96b"
TRP_FACTORY_DEPLOY_BLOCK_NUMBER = 613282


NODE_OPERATORS_REGISTRY_ARAGON_APP_ID = "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d"
SIMPLE_DVT_ARAGON_APP_ID = "0xe1635b63b5f7b5e545f2a637558a4029dea7905361a2f0fc28c66e9136cf86a4"
SANDBOX_APP_ID = "0x85d2fceef13a6c14c43527594f79fb91a8ef8f15024a43486efac8df2b11e632"

SIMPLE_DVT = "0x11a93807078f8BB880c1BD0ee4C387537de4b4b6"
SIMPLE_DVT_IMPL = "0x41646708A7EDbe22BD635Cb838Ff9C0CfA99A3bE"  # same as for NOR
SIMPLE_DVT_REPO = "0x889dB59baf032E1dfD4fCA720e0833c24f1404C6"

SANDBOX = "0xD6C2ce3BB8bea2832496Ac8b5144819719f343AC"
SANDBOX_IMPL = "0x41646708A7EDbe22BD635Cb838Ff9C0CfA99A3bE"
SANDBOX_REPO = "0x00E75B5527a876B3F10C23436a0b896C626812d0"

SANDBOX_IMPL = "0x605A3AFadF35A8a8fa4f4Cd4fe34a09Bbcea7718"


CSM_ADDRESS = "0x4562c3e63c2e586cD1651B958C22F88135aCAd4f"
CS_ACCOUNTING_ADDRESS = "0xc093e53e8F4b55A223c18A2Da6fA00e60DD5EFE1"
CS_ORACLE_HASH_CONSENSUS_ADDRESS = "0xbF38618Ea09B503c1dED867156A0ea276Ca1AE37"
CS_EARLY_ADOPTION_ADDRESS = "0x71E92eA77C198a770d9f33A03277DbeB99989660"
CS_FEE_DISTRIBUTOR_ADDRESS = "0xD7ba648C8F72669C6aE649648B516ec03D07c8ED"
CS_FEE_ORACLE_ADDRESS = "0xaF57326C7d513085051b50912D51809ECC5d98Ee"
CS_GATE_SEAL_ADDRESS = "0x41F2677fae0222cF1f08Cd1c0AAa607B469654Ce"
CS_VERIFIER_ADDRESS = "0xc099dfd61f6e5420e0ca7e84d820daad17fc1d44"
CS_ORACLE_EPOCHS_PER_FRAME = 225 * 7  # 7 days
CS_VERIFIER_ADDRESS_OLD = "0x6FDAA094227CF8E1593f9fB9C1b867C1f846F916"
