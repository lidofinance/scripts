"""
Tests for voting 17/05/2022.
"""
from scripts.vote_2022_05_17 import start_vote
from tx_tracing_helpers import *
from event_validators.payout import Payout, validate_token_payout_event
from brownie import interface, chain, reverts
from utils.splits_config import guild_recipients, guild_percents

ldo_amount: int = 2_000_000 * 10 ** 18

steth_address = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
depositor_multisig_address = '0x5181d5D56Af4f823b96FE05f062D7a09761a5a53'
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

fund_payout = Payout(
    token_addr=steth_address,
    from_addr=dao_agent_address,
    to_addr=depositor_multisig_address,
    amount=235.8 * (10 ** 18)
)



def waitSecondsAndMine(seconds):
    chain.sleep(seconds)
    chain.mine()

def steth_balance_checker(lhs_value: int, rhs_value: int):
    assert (lhs_value + 9) // 10 == (rhs_value + 9) // 10

"""
Test Voting
"""
def test_transfer_ldo_tokens(
    helpers, accounts, ldo_holder, dao_voting, lido,
    ldo_token,
    vote_id_from_env, bypass_events_decoding
):
    dao_agent_balance_before = ldo_token.balanceOf(dao_agent_address)
    protocol_guild_balance_before = ldo_token.balanceOf(protocol_guild_address)
    depositor_multisig_balance_before = lido.balanceOf(depositor_multisig_address)
    dao_balance_before = lido.balanceOf(dao_agent_address)

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    dao_agent_balance_after = ldo_token.balanceOf(dao_agent_address)
    protocol_guild_balance_after = ldo_token.balanceOf(protocol_guild_address)
    depositor_multisig_balance_after = lido.balanceOf(depositor_multisig_address)
    dao_balance_after = lido.balanceOf(dao_agent_address)

    assert protocol_guild_balance_after == protocol_guild_balance_before + ldo_amount, "Incorrect LDO amount"
    assert dao_agent_balance_after == dao_agent_balance_before - ldo_amount, "Incorrect LDO amount"

    steth_balance_checker(depositor_multisig_balance_after - depositor_multisig_balance_before, fund_payout.amount)
    steth_balance_checker(dao_balance_before - dao_balance_after, fund_payout.amount)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 2, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_token_payout_event(evs[0], protocol_guild_payout)

    # asserts on vote item 2
    validate_token_payout_event(evs[1], fund_payout)


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
def test_protocol_guild_vesting(
    helpers, accounts, ldo_holder, dao_voting, unknown_person,
    ldo_token,
    vote_id_from_env
):
    protocol_guild_balance_before = ldo_token.balanceOf(protocol_guild_address)
    assert protocol_guild_balance_before == 0

    vesting_module = interface.VestingModule(protocol_guild_address)

    vesting_streams_before = vesting_module.numVestingStreams()

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    waitSecondsAndMine(60*60)
    create_timestamp_before = chain.time()
    vesting_module.createVestingStreams([ldo_token], {"from": unknown_person})
    create_timestamp_after = chain.time()

    vesting_streams_count = vesting_module.numVestingStreams()
    assert vesting_streams_count == vesting_streams_before + 1, "Incorrect Vesting nums"

    ### Create vesting stream
    vestingId = vesting_streams_count - 1
    stream = vesting_module.vestingStream(vestingId)

    assert stream[0] == ldo_token, "Incorrect token"
    assert stream[1] >= create_timestamp_before, "Incorrect timestamp"
    assert stream[1] <= create_timestamp_after, "Incorrect timestamp"
    assert stream[2] == ldo_amount, "Incorrect total amount of tokens for vesting"
    assert stream[3] == 0, "Incorrect released amount of tokens"

    protocol_beneficiary_balance_before = ldo_token.balanceOf(protocol_beneficiary)
    assert protocol_beneficiary_balance_before == 0, "Incorrect token amount of beneficiary"

    ### Release vesting
    waitSecondsAndMine(60)
    vesting_module.releaseFromVesting([vestingId], {"from": unknown_person})

    vestedTokensPerSec = int(ldo_amount / (60 * 60 * 24 * 365))
    now = chain.time()
    min_time = (now - stream[1])-5
    max_time = (now - stream[1])+5
    min_expected_released_tokens = min_time * vestedTokensPerSec
    max_expected_released_tokens = max_time * vestedTokensPerSec

    stream = vesting_module.vestingStream(vestingId)
    released_tokens = stream[3]

    assert released_tokens >= min_expected_released_tokens, "Released less tokens than expected"
    assert released_tokens <= max_expected_released_tokens, "Released more tokens than expected"

    protocol_beneficiary_balance_after = ldo_token.balanceOf(protocol_beneficiary)
    assert released_tokens == protocol_beneficiary_balance_after, "Incorrect token amount of beneficiary"

    split_main_module = interface.SplitMain(split_main_address)

    distributor_fee = 0
    distributor_address = unknown_person

    ## check incorrect recipients and percents array length
    with reverts():
        split_main_module.distributeERC20(
            protocol_beneficiary,
            lido_dao_token,
            [unknown_person],
            guild_percents,
            distributor_fee,
            distributor_address,
            { "from": unknown_person})

    ## check incorrect recipients list - the first address was replaced with a fraudulent one
    guild_with_fraud_address = guild_recipients.copy()
    guild_with_fraud_address[0] = unknown_person
    assert guild_recipients != guild_with_fraud_address, "Recipients list are identically"
    with reverts():
        split_main_module.distributeERC20(
            protocol_beneficiary,
            lido_dao_token,
            guild_with_fraud_address,
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

    ## distribute tokens after vesting release
    split_main_module.distributeERC20(protocol_beneficiary,
        lido_dao_token,
        guild_recipients,
        guild_percents,
        distributor_fee,
        distributor_address,
        { "from": unknown_person})

    ## Holders withdrawals
    ##
    for i in range(10):
        holder_balance_before = ldo_token.balanceOf(guild_recipients[i])
        assert holder_balance_before == 0, "Invalid holder amount"

        split_main_module.withdraw(guild_recipients[i], 0, [lido_dao_token], { "from": unknown_person})
        holder_balance_after = ldo_token.balanceOf(guild_recipients[i])

        expected_balance = int(released_tokens * guild_percents[i] / 10000 / 100)
        assert holder_balance_after >= expected_balance-10, "Holder balance delta lower than expected"
        assert holder_balance_after < expected_balance+10, "Holder balance delta higher than expected"


    ## check the 2 claims in a row
    holder_index = 50
    holder_balance_before = ldo_token.balanceOf(guild_recipients[holder_index])

    split_main_module.withdraw(guild_recipients[holder_index], 0, [lido_dao_token], { "from": unknown_person})
    split_main_module.withdraw(guild_recipients[holder_index], 0, [lido_dao_token], { "from": unknown_person})

    holder_balance_after = ldo_token.balanceOf(guild_recipients[holder_index])
    expected_balance = int(released_tokens * guild_percents[holder_index] / 10000 / 100)
    assert holder_balance_after >= holder_balance_before + expected_balance-10, "Holder balance delta lower than expected"
    assert holder_balance_after < holder_balance_before + expected_balance+10, "Holder balance delta higher than expected"

    ##
    ## from the code https://etherscan.io/address/0x2ed6c4b5da6378c7897ac67ba9e43102feb694ee#code
    ## they leave 1 for gas efficiency
    ##
    beneficiary_balance_after_distribute = ldo_token.balanceOf(protocol_beneficiary)
    assert beneficiary_balance_after_distribute - 1 == 0, "Invalid beneficiary balance after"

"""
- Test for the end of vesting in 1 year
- Test for update recipients list via updateSplit method signed with controller (multisig) address and withdrawal of funds
"""
def test_protocol_rewards_hijack(
    helpers, accounts, ldo_holder, dao_voting, unknown_person,
    ldo_token,
    vote_id_from_env
):
    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    vesting_module = interface.VestingModule(protocol_guild_address)

    waitSecondsAndMine(60*60)
    create_timestamp_before = chain.time()
    vesting_module.createVestingStreams([ldo_token], {"from": unknown_person})
    create_timestamp_after = chain.time()

    vesting_streams_count = vesting_module.numVestingStreams()
    assert vesting_streams_count == 4 + 1, "Incorrect Vesting nums"

    ### Create vesting stream
    vestingId = vesting_streams_count - 1
    stream = vesting_module.vestingStream(vestingId)

    assert stream[0] == ldo_token, "Incorrect token"
    assert stream[1] >= create_timestamp_before, "Incorrect timestamp"
    assert stream[1] <= create_timestamp_after, "Incorrect timestamp"
    assert stream[2] == ldo_amount, "Incorrect total amount of tokens for vesting"
    assert stream[3] == 0, "Incorrect released amount of tokens"

    waitSecondsAndMine(60 * 60 * 24 * 365 + 10)
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

    beneficiary_balance_after_distribute = ldo_token.balanceOf(protocol_beneficiary)
    assert beneficiary_balance_after_distribute == 2_000_000 * 10**18


    distributor_fee = 0
    distributor_address = unknown_person

    # distribute tokens to new holders
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

    waitSecondsAndMine(60*60)
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

    waitSecondsAndMine(60 * 60 * 24 * 365 + 10)
    vesting_module.releaseFromVesting([vestingId], {"from": unknown_person})

    multisig = accounts.at('0xF6CBDd6Ea6EC3C4359e33de0Ac823701Cc56C6c4', force=True)

    h6 = '0x4Bfa4639Cc1f4554122aBB930Aa897CDAe90d13b'

    #  MAX_DISTRIBUTOR_FEE = 1e5;
    distributor_fee = 100_000
    distributor_fee_incorrect = 100_000 + 1

    #change split
    split_main_module = interface.SplitMain(split_main_address)

    with reverts():
        split_main_module.updateSplit(protocol_beneficiary, guild_recipients, guild_percents, distributor_fee_incorrect, {"from": multisig})

    split_main_module.updateSplit(protocol_beneficiary, guild_recipients, guild_percents, distributor_fee, {"from": multisig})

    beneficiary_balance_after_distribute = ldo_token.balanceOf(protocol_beneficiary)
    assert beneficiary_balance_after_distribute == 2_000_000 * 10**18

    distributor_address = h6

    # distribute tokens to new holders
    split_main_module.distributeERC20(
        protocol_beneficiary,
        lido_dao_token,
        guild_recipients,
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


"""
- Test for update distribution fee (max 10%) from multisig
"""
def test_protocol_happy_path(
    helpers, accounts, ldo_holder, dao_voting, unknown_person,
    ldo_token,
    vote_id_from_env,
):
    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    vesting_module = interface.VestingModule(protocol_guild_address)

    waitSecondsAndMine(60*60)
    create_timestamp_before = chain.time()
    vesting_module.createVestingStreams([ldo_token], {"from": unknown_person})
    create_timestamp_after = chain.time()

    vesting_streams_count = vesting_module.numVestingStreams()
    assert vesting_streams_count == 4 + 1, "Incorrect Vesting nums"

    ### Create vesting stream
    vestingId = vesting_streams_count - 1
    stream = vesting_module.vestingStream(vestingId)

    assert stream[0] == ldo_token, "Incorrect token"
    assert stream[1] >= create_timestamp_before, "Incorrect timestamp"
    assert stream[1] <= create_timestamp_after, "Incorrect timestamp"
    assert stream[2] == ldo_amount, "Incorrect total amount of tokens for vesting"
    assert stream[3] == 0, "Incorrect released amount of tokens"

    waitSecondsAndMine(60 * 60 * 24 * 365 + 10)
    vesting_module.releaseFromVesting([vestingId], {"from": unknown_person})

    stream_after_released = vesting_module.vestingStream(vestingId)
    released_tokens = stream_after_released[3]

    assert released_tokens == 2_000_000 * 10**18, "Released incorrect amount in stream"

    beneficiary_balance_after_release = ldo_token.balanceOf(protocol_beneficiary)
    assert beneficiary_balance_after_release == 2_000_000 * 10**18

    # distribute tokens to new holders
    split_main_module = interface.SplitMain(split_main_address)

    distributor_fee = 0
    split_main_module.distributeERC20(
        protocol_beneficiary,
        lido_dao_token,
        guild_recipients,
        guild_percents,
        distributor_fee,
        unknown_person,
        { "from": unknown_person})

    beneficiary_balance_after_distribute = ldo_token.balanceOf(protocol_beneficiary)
    assert beneficiary_balance_after_distribute == 1

    released_tokens -= 1
    withdrawal_balance = 0

    split_balance = ldo_token.balanceOf(split_main_address)

    # minus 1 wei on distributeERC20
    assert split_balance == 2_000_000 * 10**18 - 1

    balances = 0
    for i in range(len(guild_recipients)):
        holder_balance_before = split_main_module.getERC20Balance(guild_recipients[i], ldo_token)
        balances += holder_balance_before

        split_main_module.withdraw(guild_recipients[i], 0, [lido_dao_token], { "from": unknown_person})
        holder_balance_after = ldo_token.balanceOf(guild_recipients[i])
        withdrawal_balance += holder_balance_after

        assert holder_balance_before - 1 == holder_balance_after

    # minus 111 wei on distributeERC20, minus 1 wei on each withdraw (111 recipients)
    assert withdrawal_balance == 2_000_000 * 10**18 - (len(guild_recipients) * 1) * 2

