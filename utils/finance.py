from typing import Tuple

from utils.config import (contracts, ldo_token_address, lido_dao_steth_address)

ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'


def make_ldo_payout(
    *not_specified,
    target_address: str,
    ldo_in_wei: int,
    reference: str
) -> Tuple[str, str]:
    """Encode LDO payout."""
    if not_specified:
        raise ValueError(
            'Please, specify all arguments with keywords.'
        )

    return _encode_token_transfer(
        token_address=ldo_token_address,
        recipient=target_address,
        amount=ldo_in_wei,
        reference=reference,
        finance=contracts.finance
    )

def make_steth_payout(
    *not_specified,
    target_address: str,
    steth_in_wei: int,
    reference: str
) -> Tuple[str, str]:
    """Encode stETH payout."""
    if not_specified:
        raise ValueError(
            'Please, specify all arguments with keywords.'
        )

    return _encode_token_transfer(
        token_address=lido_dao_steth_address,
        recipient=target_address,
        amount=steth_in_wei,
        reference=reference,
        finance=contracts.finance
    )

def make_eth_payout(
    *not_specified,
    target_address: str,
    eth_in_wei: int,
    reference: str
) -> Tuple[str, str]:
    """Encode ETH payout."""
    if not_specified:
        raise ValueError(
            'Please, specify all arguments with keywords.'
        )

    return _encode_eth_transfer(
        recipient=target_address,
        amount=eth_in_wei,
        reference=reference,
        finance=contracts.finance
    )


def _encode_token_transfer(token_address, recipient, amount, reference, finance):
    return (
        finance.address,
        finance.newImmediatePayment.encode_input(
            token_address,
            recipient,
            amount,
            reference
        )
    )


# aragonOS and aragon-apps rely on address(0) to denote native ETH, in
# contracts where both tokens and ETH are accepted
# from https://github.com/aragon/aragonOS/blob/master/contracts/common/EtherTokenConstant.sol
def _encode_eth_transfer(recipient, amount, reference, finance):
    return (
        finance.address,
        finance.newImmediatePayment.encode_input(
            ZERO_ADDRESS,
            recipient,
            amount,
            reference
        )
    )
