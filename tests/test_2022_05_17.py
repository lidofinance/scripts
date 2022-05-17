"""
Tests for voting 10/05/2022.
"""
import pytest
from scripts.vote_2022_05_17 import start_vote
from tx_tracing_helpers import *
from event_validators.payout import Payout, validate_token_payout_event
from brownie import interface, chain, reverts

ldo_amount: int = 2_000_000 * 10 ** 18

lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'
dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'  # from
protocol_guild_address = '0xF29Ff96aaEa6C9A1fBa851f74737f3c069d4f1a9'  # to

# from https://protocol-guild.readthedocs.io/en/latest/3-smart-contract.html#split-contract
protocol_beneficiary = '0x84af3D5824F0390b9510440B6ABB5CC02BB68ea1'
split_main_address = '0x2ed6c4B5dA6378c7897AC67Ba9e43102Feb694EE';

# from https://protocol-guild.readthedocs.io/en/latest/3-smart-contract.html#pg-multisig
controller_address = '0xF6CBDd6Ea6EC3C4359e33de0Ac823701Cc56C6c4'

protocol_guild_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=protocol_guild_address,
    amount=ldo_amount
)

# from https://protocol-guild.readthedocs.io/en/latest/9-membership.html#addresses-and-weights
# sorted asc
guild_receipients = [
"0x0000006916a87b82333f4245046623b23794c65c",
"0x00a2d2d22f456125d64beda5a6f37273a13d9de0",
"0x00cDD7Fc085c86D000c0D54b3CA6fE83A8a806e5",
"0x00d3baf1080b1cfb5897225a21ecdcc25a1f4456",
"0x046Fb65722E7b2455012BFEBf6177F1D2e9738D9",
"0x05618d6EFFe2E522F07B1dB692d47A68bfD6fFEa",
"0x0760E844e6f368ce73F1eEB917d37Db19375De3B",
"0x0906Eb682C6d12EdBE5e0A43E60068E1A7F8bea3",
"0x0B916095200313900104bAcfc288462682C38700",
"0x10ab73AA48D686b7FD9ec9D50418a14DD23f6631",
"0x10c8597a5063A1648FfE13f54E996ba9bB3217B5",
"0x153afFb96Fcb60085Ee307996Bdd2df0183A3682",
"0x1de6938d9f9ebd43D0Cc56f0CeF1657D954c9A94",
"0x1ecaea79D739BC222D6dB2d6bf63F869a329a702",
"0x22D6637330aF1de97a1F67D03A73b99A1E6D2263",
"0x24113fFB07189D1e6E169025A424B58C29522972",
"0x299cB850bD75C07ef89978Bdc52e062Cc4fA0250",
"0x2A89178555a3e7d19218f28DF0B0Ec732E889e18",
"0x2bf7b04F143602692bBDc3EcbeA68C2c65278eee",
"0x2D56Cd519540bE541A3261E22e95d6507F5504Ca",
"0x2fb858991668840ce34F331402E0b3C66db078AF",
"0x3212974a4e53e5238f6ea193b36412db9ad61c26",
"0x35bc6a44AcFb79b5A47C1cbe2fD3C560a093a2B1",
"0x366A06CbA45BC45996A7B6a1B6F22e8c9283b6Ea",
"0x376D5C3a16E9d015e8C584bB2d278E25F0ccb27B",
"0x3B16821A5dBBFF86E4a88eA0621EC6be016cd79A",
"0x3d5D2AC4fEcF16bb1651A445d5B17f977A823546",
"0x3eD7bf997b7A91e9e8aB9eE2F7ce983bd37D6392",
"0x46cD90445349e64F895c403c23839e79eb4065e4",
"0x497f0D190C513f51eAC234628200a5E62271a7A5",
"0x49Aa00072a7BA8a5639C43Fe9F6536820E6F5d57",
"0x4B3105E9EC2B6069c1362388D429625a026f43e0",
"0x4Bfa4639Cc1f4554122aBB930Aa897CDAe90d13b",
"0x4d5083dd10f2a46f26f5583c6679f9f8d30ae850",
"0x50122A5509F628e901F9c0238F0168833753239b",
"0x50d5e44700c10873875b4E75C4c9396562D83bE1",
"0x57c5D54F7293CDE1FC129e4159cB07F48752ea61",
"0x5869C17c8934Ce9f674e88c7d4f8F94DCE193FCB",
"0x5973D1af5c13168bdC85c6e78309272815995Ffb",
"0x644177F8D79117c2b9C7596527642B3c2D05888E",
"0x6591e7D655f248f6930195385C36b8D5Af679B8B",
"0x65a63ceE206bFA6B2a3287479D28c8902B4055E9",
"0x661b81d462D80786c442774F452464A8C627a20E",
"0x6B29132ea388a308578c1d3Be068D0e4fc9915a2",
"0x6bb11EBDF00ebDFbe707005B506A24Fd57d5Bd66",
"0x6C1C4f642ab5611A46ee6F3ED95Bbf2E3Caf4D1c",
"0x6e22a5e30088c8389dc725bbead5f0675334299f",
"0x6f91b7e11d955897aa7394d5b4fc82559fab27b9",
"0x6fFd2248Ab7E80ef51D7Eb4CB60964C830125567",
"0x71c15691e243bE88220957C784053EF0E084440B",
"0x77b34f5E620e8Cfd1839b245beAADd27ae3A25FB",
"0x78ac9c2545850bEDbC076EB30ce7A6f0D74b395E",
"0x799681f9b9d7c55ed59f5a0f235cAb132Cde0a2B",
"0x7e59Df833869E2997d05e163D6004f3344A052FA",
"0x8360470F1793C91c953be453fcA52CC63dfCb367",
"0x84f678A3e7BA8Fc817c32Ff10884D6FB20976114",
"0x86F34D8b98171281AB8bFe65C7e2718E4f002e35",
"0x873a45B49289b868E81547c6226357E7117e6070",
"0x88dF07c605d13915B8E7D07dc8efD538dC0C5620",
"0x8cbf722adfbc071a12aae158a12a68397578017c",
"0x8ce466bD577396786C76Da8629314fcce5bE2A5f",
"0x925F5d6cCdB04F56fBa1cdcAd92E4eBb0d421411",
"0x92699d64C65c435D4a60E2ceEaEb931dB8B1cA09",
"0x974B9cb3c122561e3bf6234651E0b82B88Fb9015",
"0x975D1040E93316917BD67dD32a02e1929F8aF8D3",
"0x980a85ba6c2683e3509752dd3b4eB50165C0e65F",
"0x9b796F2de75772f1634D78A3AB23A03778D3702a",
"0x9Bee5b17Eb847744b6a81Ee935409739F91c722c",
"0x9d6d3b09F8AC8615805bd82e53B80D956F451CFa",
"0x9F60E4aF6020cc6a791B2d1Ce9902d25A72bA824",
"0xa1D76553266fA8Ed3D143794a462aaFAdfC34f74",
"0xa29576F07eAaD050AeACbc89AC0518B62fe2F88E",
"0xa87922d0074bCd82Ac82816633CcE68472548955",
"0xab8b3647EF7FF66D2f38ee5eaEf2b158c4eb52A2",
"0xAb96014a7c078f09418Cf899Bf197CadFf023C16",
"0xb721c2e6640D963e99b37B6437ABAF6914A25A5e",
"0xB7745Bde70e429bBd5Eb57dfa5ca70B84239477a",
"0xb7A593EC62dc447eef23ea0e0B4d5144ac75ABC5",
"0xbB3F2F946E8eE2912830e365cF241293636cb057",
"0xBc11295936Aa79d594139de1B2e12629414F3BDB",
"0xbC349D1BEeE33c61F0395d1667E70056B4C869B9",
"0xBFbeaB0896E29d0Db26ad60278d3Ab3C482BB199",
"0xC152fd31F285f6c0B3807070280595e7Ea713a7f",
"0xc66EFCcB88b3b7BdE6fC476d8cF139DD38075Ad7",
"0xC6cA7c3427AD6B7a06fbED6D18C394E540E31814",
"0xC9187b5C81d63b289811A4fcb9AC7ADb7103639e",
"0xCA186e78bf657d4C5694CA5CA448D3766d2b55Bb",
"0xCb8DC3beC7B659022aE0d3E9de17322F31e4AA7C",
"0xd20BebA9eFA30fB34aF93AF5c91C9a4d6854eAC4",
"0xD4a3030b5f5e8DD4860d370C17E8576aE9951a2D",
"0xdF6C53Df56f3992FC44195518A2d8B16306Af9ff",
"0xe019836A41CB707F79b991f60e241918097aC16e",
"0xe05875F287C028901798aC2Dc8C22Ba908b8eF36",
"0xe2A296b3d3AD4212b6030442e70419ff7B82FEE4",
"0xE35b6f8E759Ac242585E2F41Ac29A2baAf4c4e96",
"0xE4b99f9580B90d88C3e6dC3E0B853D8D3b0B8B55",
"0xe8FEE6186cbcF0790644D59f04cC5C085FBA68Bb",
"0xE9F19B6C72219f9B12C9c367405a90Ac9aFb2241",
"0xEB8E7c90014565EEd8126110630eFa2d9CD6eBE4",
"0xEd46bFFd4b8237a9c7E08f55F0B410544f989813",
"0xeFD79Dc8c08762156a2B204743e3fC9507f07f4E",
"0xf0443945aD3BE9645382FC2537317dA97FEfF3A9",
"0xf0869c68b91013bf214db68d503c65f9ba44097c",
"0xF23090AB5773200bE3dAD33f42C7Eb20a14C4a61",
"0xF51fc4c6Ab075482b61F5C1d4E72fADaFf8815F3",
"0xf5441a1b900a1D93e4c06CB9c3fDbA39F01469f0",
"0xf71E9C766Cdf169eDFbE2749490943C1DC6b8A55",
"0xF8843981e7846945960f53243cA2Fd42a579f719",
"0xfbbECa029104953F039537a111D07A6aC0549c3c",
"0xFBFd6Fa9F73Ac6A058E01259034C28001BEf8247",
"0xFf9977FB117a22254a8eB6c6CE8d3Dd671FA70DC"
]

guild_percents = [
12001,
12523,
5367,
9961,
4733,
11732,
6197,
5367,
6450,
10277,
6197,
5934,
12265,
10277,
5060,
10882,
13507,
5657,
6694,
4000,
5657,
12776,
9467,
11455,
12901,
13147,
5060,
12901,
8945,
14424,
8391,
11173,
4733,
6929,
6197,
11028,
12776,
4733,
12901,
7798,
16783,
9122,
5657,
11028,
3578,
13024,
10432,
6694,
12776,
10584,
6325,
5657,
9961,
12001,
4733,
6450,
11867,
11173,
9296,
13388,
5060,
8391,
9467,
16397,
5060,
5657,
4382,
16783,
9296,
12901,
8198,
9634,
11732,
4000,
12265,
7798,
5657,
9961,
13742,
13268,
7590,
13507,
7376,
5367,
8764,
3578,
12523,
6929,
11173,
10277,
13742,
13388,
9634,
5367,
7156,
9296,
3347,
15699,
5060,
5060,
5934,
6197,
5657,
3795,
13147,
12001,
12901,
8013,
4382,
5367,
9122,
]

def waitBlock(seconds):
    chain.sleep(seconds)
    chain.mine()

@pytest.fixture(scope='module')
def unknown_person(accounts):
    return accounts.at('0x98ec059dc3adfbdd63429454aeb0c990fba4a128', force=True)


"""
Test LDO transfer from Lido Agent via Voting
"""
def test_transfer_ldo_tokens(
    helpers, accounts, ldo_holder, dao_voting,
    ldo_token,
    vote_id_from_env, bypass_events_decoding
):
    dao_agent_balance_before = ldo_token.balanceOf(dao_agent_address)
    protocol_guild_balance_before = ldo_token.balanceOf(protocol_guild_address)

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    dao_agent_balance_after = ldo_token.balanceOf(dao_agent_address)
    protocol_guild_balance_after = ldo_token.balanceOf(protocol_guild_address)

    assert protocol_guild_balance_after == protocol_guild_balance_before + ldo_amount, "Incorrect LDO amount"
    assert dao_agent_balance_after == dao_agent_balance_before - ldo_amount, "Incorrect LDO amount"

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_token_payout_event(evs[0], protocol_guild_payout)


"""
Test Protocol Guild defaults params
"""
def test_protocol_guild_vesting_params():
    vesting_module = interface.VestingModule(protocol_guild_address)

    vesting_period = vesting_module.vestingPeriod()
    assert vesting_period == 60*60*24*365, "Incorrect Vesting period"

    vesting_streams_count = vesting_module.numVestingStreams()
    assert vesting_streams_count == 4, "Incorrect Vesting nums"

    beneficiary = vesting_module.beneficiary()
    assert beneficiary == protocol_beneficiary, "Invalid beneficiary address"

    split_main_module = interface.SplitMain(split_main_address)
    controller = split_main_module.getController(beneficiary)
    assert controller == controller_address, "Invalid controller address"

"""
- Test create vesting
- Test vested amount after 1 minute
- Test realized tokens from unknown address
- Test for incorrect recipient list
- Test for incorrect distribution fee
- Test distribute ERC20 tokens from unknown address
- Test recipients withdrawals +-10 WEI
- Test for 2 claim in a row for one holder
- Test for 1 wei on contract balance after distribution (protocol feature)
"""
def test_protocol_vesting(
    helpers, accounts, ldo_holder, dao_voting, unknown_person,
    ldo_token,
    vote_id_from_env
):
    protocol_guild_balance_before = ldo_token.balanceOf(protocol_guild_address)
    assert protocol_guild_balance_before == 0

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    vesting_module = interface.VestingModule(protocol_guild_address)

    waitBlock(60*60)
    create_timestamp_before = chain.time()
    vesting_module.createVestingStreams([ldo_token], {"from": unknown_person})
    create_timestamp_after = chain.time()

    vesting_streams_count = vesting_module.numVestingStreams()
    assert vesting_streams_count == 4 + 1, "Incorrect Vesting nums"

    ### Create vesting stream
    vestingId = vesting_streams_count - 1
    stream = vesting_module.vestingStream(vestingId)

    assert stream[0] == ldo_token, "Incorrect token"
    assert stream[1] >=create_timestamp_before, "Incorrect timestamp"
    assert stream[1] <=create_timestamp_after, "Incorrect timestamp"
    assert stream[2] == ldo_amount, "Incorrect total amount of tokens for vesting"
    assert stream[3] == 0, "Incorrect released amount of tokens"

    protocol_beneficiar_balance_before = ldo_token.balanceOf(protocol_beneficiary)
    assert protocol_beneficiar_balance_before == 0, "Incorrect token amount of beneficiary"

    ### Release vesting
    waitBlock(60)
    vesting_module.releaseFromVesting([vestingId], {"from": unknown_person})

    #vestedTokensPerSec = int(ldo_amount / (60 * 60 * 24 * 365))

    stream = vesting_module.vestingStream(vestingId)
    released_tokens = stream[3]

    assert released_tokens >= 3805175038051750560
    assert released_tokens < 4122272957889396440

    protocol_beneficiar_balance_after = ldo_token.balanceOf(protocol_beneficiary)
    assert released_tokens == protocol_beneficiar_balance_after, "Incorrect token amount of beneficiary"

    split_main_module = interface.SplitMain(split_main_address)

    distributor_fee = 0
    distributor_address = unknown_person

    ## check incorrect receipients list
    with reverts():
        split_main_module.distributeERC20(
            protocol_beneficiary,
            lido_dao_token,
            [unknown_person],
            guild_percents,
            distributor_fee,
            distributor_address,
            { "from": unknown_person})

    ## check incorrect fee
    distributor_fee_incorrect = 10
    with reverts():
        split_main_module.distributeERC20(
            protocol_beneficiary,
            lido_dao_token,
            [unknown_person],
            guild_percents,
            distributor_fee_incorrect,
            distributor_address,
            { "from": unknown_person})

    ## Distibute tokens after vesting release
    split_main_module.distributeERC20(protocol_beneficiary,
        lido_dao_token,
        guild_receipients,
        guild_percents,
        distributor_fee,
        distributor_address,
        { "from": unknown_person})

    ## Holders withdrawals
    ##
    for i in range(10):
        holder_balance_before = ldo_token.balanceOf(guild_receipients[i])
        assert holder_balance_before == 0, "Invalid holder amount"

        split_main_module.withdraw(guild_receipients[i], 0, [lido_dao_token], { "from": unknown_person})
        holder_balance_after = ldo_token.balanceOf(guild_receipients[i])

        expected_balance = int(released_tokens * guild_percents[i] / 10000 / 100)
        assert holder_balance_after >= expected_balance-10, "Invalid holder balance "
        assert holder_balance_after < expected_balance+10, "Invalid holder balance "


    ## check the 2 claims in a row
    holder_index = 50
    holder_balance_before = ldo_token.balanceOf(guild_receipients[holder_index])

    split_main_module.withdraw(guild_receipients[holder_index], 0, [lido_dao_token], { "from": unknown_person})
    split_main_module.withdraw(guild_receipients[holder_index], 0, [lido_dao_token], { "from": unknown_person})

    holder_balance_after = ldo_token.balanceOf(guild_receipients[holder_index])
    expected_balance = int(released_tokens * guild_percents[holder_index] / 10000 / 100)
    assert holder_balance_after >= holder_balance_before + expected_balance-10, "Invalid holder balance "
    assert holder_balance_after < holder_balance_before + expected_balance+10, "Invalid holder balance "

    ##
    ## from the code https://etherscan.io/address/0x2ed6c4b5da6378c7897ac67ba9e43102feb694ee#code
    ## they leave 1 for gas efficiency
    ##
    beneficiar_balance_after_distibute = ldo_token.balanceOf(protocol_beneficiary)
    assert beneficiar_balance_after_distibute - 1 == 0, "Invalid beneficiar balance after"

"""
- Test for the end of vesting in 1 year
- Test for update recipients list via updateSplit method signed with controller (multisig) address and withdrawal of funds
"""
def test_protocol_update_scripts(
    helpers, accounts, ldo_holder, dao_voting, unknown_person,
    ldo_token,
    vote_id_from_env
):
    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    vesting_module = interface.VestingModule(protocol_guild_address)

    waitBlock(60*60)
    create_timestamp = chain.time()
    vesting_module.createVestingStreams([ldo_token], {"from": unknown_person})

    vesting_streams_count = vesting_module.numVestingStreams()
    assert vesting_streams_count == 4 + 1, "Incorrect Vesting nums"

    ### Create vesting stream
    vestingId = vesting_streams_count - 1
    stream = vesting_module.vestingStream(vestingId)

    assert stream[0] == ldo_token, "Incorrect token"
    assert stream[1] == create_timestamp, "Incorrect timestamp"
    assert stream[2] == ldo_amount, "Incorrect total amount of tokens for vesting"
    assert stream[3] == 0, "Incorrect released amount of tokens"

    waitBlock(60 * 60 * 24 * 365 + 10)
    vesting_module.releaseFromVesting([vestingId], {"from": unknown_person})

    multisig = accounts.at('0xF6CBDd6Ea6EC3C4359e33de0Ac823701Cc56C6c4', force=True)

    h1 = '0x0000006916a87b82333f4245046623b23794C65C'
    h2 = '0x0B916095200313900104bAcfc288462682C38700'

    #minimum 2 accounts
    accs = [h1, h2]
    perc = [500000, 500000]
    fee = 0

    #change split
    split_main_module = interface.SplitMain(split_main_address)
    split_main_module.updateSplit(protocol_beneficiary, accs, perc, fee, {"from": multisig})

    beneficiar_balance_after_distibute = ldo_token.balanceOf(protocol_beneficiary)
    assert beneficiar_balance_after_distibute == 2_000_000 * 10**18


    distributor_fee = 0
    distributor_address = unknown_person

    # distibute tokens to new holders
    split_main_module.distributeERC20(
        protocol_beneficiary,
        lido_dao_token,
        accs,
        perc,
        distributor_fee,
        distributor_address,
        { "from": unknown_person})

    split_main_module.withdraw(h1, 0, [lido_dao_token], { "from": unknown_person})
    h1_balance_after = ldo_token.balanceOf(h1)

    split_main_module.withdraw(h2, 0, [lido_dao_token], { "from": unknown_person})
    h2_balance_after = ldo_token.balanceOf(h2)

    assert h1_balance_after >= 999_999 * 10**18
    assert h2_balance_after >= 999_999 * 10**18


"""
- Test for update distribution fee (max 10%) from multisig
"""
def test_protocol_update_fee(
    helpers, accounts, ldo_holder, dao_voting, unknown_person,
    ldo_token,
    vote_id_from_env,
):
    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    vesting_module = interface.VestingModule(protocol_guild_address)

    waitBlock(60*60)
    create_timestamp = chain.time()
    vesting_module.createVestingStreams([ldo_token], {"from": unknown_person})

    vesting_streams_count = vesting_module.numVestingStreams()
    assert vesting_streams_count == 4 + 1, "Incorrect Vesting nums"

    ### Create vesting stream
    vestingId = vesting_streams_count - 1
    stream = vesting_module.vestingStream(vestingId)

    assert stream[0] == ldo_token, "Incorrect token"
    assert stream[1] == create_timestamp, "Incorrect timestamp"
    assert stream[2] == ldo_amount, "Incorrect total amount of tokens for vesting"
    assert stream[3] == 0, "Incorrect released amount of tokens"

    waitBlock(60 * 60 * 24 * 365 + 10)
    vesting_module.releaseFromVesting([vestingId], {"from": unknown_person})

    multisig = accounts.at('0xF6CBDd6Ea6EC3C4359e33de0Ac823701Cc56C6c4', force=True)

    h6 = '0x4Bfa4639Cc1f4554122aBB930Aa897CDAe90d13b'

    #  MAX_DISTRIBUTOR_FEE = 1e5;
    distributor_fee = 100_000
    distributor_fee_incorrect = 500_000

    #change split
    split_main_module = interface.SplitMain(split_main_address)

    with reverts():
        split_main_module.updateSplit(protocol_beneficiary, guild_receipients, guild_percents, distributor_fee_incorrect, {"from": multisig})

    split_main_module.updateSplit(protocol_beneficiary, guild_receipients, guild_percents, distributor_fee, {"from": multisig})

    beneficiar_balance_after_distibute = ldo_token.balanceOf(protocol_beneficiary)
    assert beneficiar_balance_after_distibute == 2_000_000 * 10**18

    distributor_address = h6

    # distibute tokens to new holders
    split_main_module.distributeERC20(
        protocol_beneficiary,
        lido_dao_token,
        guild_receipients,
        guild_percents,
        distributor_fee,
        distributor_address,
        { "from": unknown_person})

    h1_balance_after = ldo_token.balanceOf(h6)
    print(h1_balance_after)

    split_main_module.withdraw(h6, 0, [lido_dao_token], { "from": unknown_person})
    h6_balance_after = ldo_token.balanceOf(h6)
    assert h6_balance_after >= 200_000 * 10**18
    assert h6_balance_after < 210_000 * 10**18

