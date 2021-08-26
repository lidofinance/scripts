try:
    from brownie import interface
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


def set_console_globals(**kwargs):
    global interface
    interface = kwargs['interface']


import time
from brownie.utils import color
from utils.voting import create_vote
from utils.evm_script import encode_call_script
from utils.finance import encode_token_transfer
from utils.node_operators import encode_set_node_operator_staking_limit, encode_add_operator, get_node_operators


from utils.config import (
    ldo_token_address,
    lido_dao_agent_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    get_deployer_account,
    prompt_bool
)


def pp(text, value):
    print(text, color.highlight(str(value)), end='')


def make_fund_ssv_grant_blox_call_script(blox_address, ldo_for_grant_in_wei, finance):
    return encode_token_transfer(
            token_address=ldo_token_address,
            recipient=blox_address,
            amount=ldo_for_grant_in_wei,
            reference=f'LEGO SSV grant: transfer to Blox Staking',
            finance=finance
    )

def make_fund_ssv_grant_obol_call_script(obol_address, ldo_for_grant_in_wei, finance):
    return encode_token_transfer(
            token_address=ldo_token_address,
            recipient=obol_address,
            amount=ldo_for_grant_in_wei,
            reference=f'LEGO SSV grant: transfer to Obol',
            finance=finance
    )

def make_fund_lego_call_script(lego_address, ldo_for_lego_in_wei, finance):
    return encode_token_transfer(
            token_address=ldo_token_address,
            recipient=lego_address,
            amount=ldo_for_lego_in_wei,
            reference=f'LEGO next quarter: transfer to LEGO multisig',
            finance=finance
    )

def encode_nft_transfer(sender, recipient, token_id, mintable_token, agent):
    return (
      agent.address,
      agent.forward.encode_input(
        encode_call_script([(mintable_token.address,
        mintable_token.safeTransferFrom.encode_input(
            sender,
            recipient,
            token_id
        ))])
      )
    )


def start_vote(tx_params, silent=False):
    ldo_for_ssv_grant_in_wei = 16_450 * 10**18 # 16 450 LDO
    blox_for_lego_address = '0xb35096b074fdb9bBac63E3AdaE0Bbde512B2E6b6'
    obol_for_lego_address = '0xC62188bDB24d2685AEd8fa491E33eFBa47Db63C2'

    ldo_for_lego_in_wei = 123_250 * 10**18
    lego_multisig_address = '0x12a43b049A7D330cB8aEAB5113032D18AE9a9030'

    rarible_address = '0x60f80121c31a0d46b5279700f9df786054aa5ee5'
    nft_receiver_address = '0x90102a92e8e40561f88be66611e5437feb339e79' # mevalphaleak.eth
    nft_tokenId = 1225266

    rarible = interface.MintableToken(rarible_address)

    finance = interface.Finance(lido_dao_finance_address)
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    agent = interface.Agent(lido_dao_agent_address)

    node_operators = get_node_operators(registry)

    node_operators_limits = {
      0: 4400,
      2: 4500,
      3: 5000,
      5: 5000,
      6: 2880,
      7: 3000,
      8: 5000
    }

    if not silent:
      print()
      pp('Using finance contract at address', lido_dao_finance_address)
      pp('Using voting contract at address', lido_dao_voting_address)
      pp('Using NodeOperatorsRegistry at address', lido_dao_node_operators_registry)
      pp('Using LDO token at address', ldo_token_address)
      pp('Using Rarible at address', rarible_address)
      print()

      print('LEGO SSV grant payout for Blox Staking (LDO):')
      pp('{:<30}'.format(blox_for_lego_address), ldo_for_ssv_grant_in_wei / 10 ** 18)
      print()

      print('LEGO SSV grant payout for Obol (LDO):')
      pp('{:<30}'.format(obol_for_lego_address), ldo_for_ssv_grant_in_wei / 10 ** 18)
      print()

      print('LEGO next quarter top-up (LDO):')
      pp('{:<30}'.format(lego_multisig_address), ldo_for_lego_in_wei / 10 ** 18)
      print()

      print('1 mln stETH NFT transfer:')
      pp('{:<30}'.format(nft_receiver_address), nft_tokenId)
      print()

      print('Set node operators limits:')
      pp('{:<30}'.format(node_operators[0]['name']), node_operators_limits[0])
      pp('{:<30}'.format(node_operators[2]['name']), node_operators_limits[2])
      pp('{:<30}'.format(node_operators[3]['name']), node_operators_limits[3])
      pp('{:<30}'.format(node_operators[5]['name']), node_operators_limits[5])
      pp('{:<30}'.format(node_operators[6]['name']), node_operators_limits[6])
      pp('{:<30}'.format(node_operators[7]['name']), node_operators_limits[7])
      pp('{:<30}'.format(node_operators[8]['name']), node_operators_limits[8])


    lego_blox_call_script = make_fund_ssv_grant_blox_call_script(
        blox_for_lego_address,
        ldo_for_ssv_grant_in_wei,
        finance
    )

    lego_obol_call_script = make_fund_ssv_grant_blox_call_script(
        obol_for_lego_address,
        ldo_for_ssv_grant_in_wei,
        finance
    )

    lego_multisig_call_script = make_fund_lego_call_script(
        lego_multisig_address,
        ldo_for_lego_in_wei,
        finance
    )

    nft_transfer_call_script = encode_nft_transfer(sender=lido_dao_agent_address, recipient=nft_receiver_address, token_id=nft_tokenId, mintable_token=rarible, agent = agent)

    staking_facilities_staking_limit = encode_set_node_operator_staking_limit(
        id=0,
        limit=node_operators_limits[0],
        registry=registry
    )

    p2p_staking_limit = encode_set_node_operator_staking_limit(
        id=2,
        limit=node_operators_limits[2],
        registry=registry
    )

    chorus_staking_limit = encode_set_node_operator_staking_limit(
        id=3,
        limit=node_operators_limits[3],
        registry=registry
    )

    blockscape_staking_limit = encode_set_node_operator_staking_limit(
        id=5,
        limit=node_operators_limits[5],
        registry=registry
    )

    dsrv_staking_limit = encode_set_node_operator_staking_limit(
        id=6,
        limit=node_operators_limits[6],
        registry=registry
    )

    everstake_staking_limit = encode_set_node_operator_staking_limit(
        id=7,
        limit=node_operators_limits[7],
        registry=registry
    )

    skillz_staking_limit = encode_set_node_operator_staking_limit(
        id=8,
        limit=node_operators_limits[8],
        registry=registry
    )

    rockx_add_operator = encode_add_operator(address='0x258cB32B1875168858E57Bb31482054e008d344e', name='RockX', registry=registry)
    figment_add_operator = encode_add_operator(address='0xfE78617EC612ac67bCc9CC145d376400f15a82cb', name='Figment', registry=registry)
    allnodes_add_operator = encode_add_operator(address='0xd8d93E91EA5F24D0E2a328BC242055D40f00bE1A', name='Allnodes', registry=registry)
    anyblock_add_operator = encode_add_operator(address='0x8b90ac446d4360332129e92F857a9d536DB9d7c2', name='Anyblock Analytics', registry=registry)

    call_script = [
        lego_blox_call_script,
        lego_obol_call_script,
        lego_multisig_call_script,
        nft_transfer_call_script,
        staking_facilities_staking_limit,
        p2p_staking_limit,
        chorus_staking_limit,
        blockscape_staking_limit,
        dsrv_staking_limit,
        everstake_staking_limit,
        skillz_staking_limit,
        rockx_add_operator,
        figment_add_operator,
        allnodes_add_operator,
        anyblock_add_operator
    ]

    if not silent:
      print('Callscriptfunds_in_wei')
      for addr, action in call_script:
          pp(addr, action)
      print()

      print('Does it look good?')
      prompt_bool()

    return create_vote(
        voting=interface.Voting(lido_dao_voting_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        vote_desc=(
            f'Omnibus vote: 1) fund SSV grants for Blox Staking & Obol with $100,000 in LDO each, '
            f'2) fund LEGO for the next quarter with 123,250 LDO, '
            f'3) send out 1 mln stETH nft, '
            f'4) increase staking limits for Node Operators, '
            f'5) add RockX Node Operator, '
            f'6) add Figment Node Operator, '
            f'7) add Allnodes Node Operator, '
            f'8) add Anyblock Analytics Node Operator'

        ),
        evm_script=encode_call_script(call_script),
        tx_params=tx_params
    )


def main():
    (vote_id, _) = start_vote({'from': get_deployer_account(), 'gas_price': '50 gwei'})
    print(f'Vote created: {vote_id}')
    time.sleep(5) # hack: waiting thread 2
