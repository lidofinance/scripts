from typing import Tuple
from brownie import ZERO_ADDRESS
from utils.config import (
    contracts,
    LDO_TOKEN,
    LIDO_LIDO,
    WETH_TOKEN,
    DAI_TOKEN,
)


def make_ldo_payout(*not_specified, target_address: str, ldo_in_wei: int, reference: str) -> Tuple[str, str]:
    """Encode LDO payout."""
    if not_specified:
        raise ValueError("Please, specify all arguments with keywords.")

    return _encode_token_transfer(
        token_address=LDO_TOKEN,
        recipient=target_address,
        amount=ldo_in_wei,
        reference=reference,
        finance=contracts.finance,
    )


def make_weth_payout(*not_specified, target_address: str, weth_in_wei: int, reference: str) -> Tuple[str, str]:
    """Encode WETH payout."""
    if not_specified:
        raise ValueError("Please, specify all arguments with keywords.")

    return _encode_token_transfer(
        token_address=WETH_TOKEN,
        recipient=target_address,
        amount=weth_in_wei,
        reference=reference,
        finance=contracts.finance,
    )


def make_steth_payout(*not_specified, target_address: str, steth_in_wei: int, reference: str) -> Tuple[str, str]:
    """Encode stETH payout."""
    if not_specified:
        raise ValueError("Please, specify all arguments with keywords.")

    return _encode_token_transfer(
        token_address=LIDO_LIDO,
        recipient=target_address,
        amount=steth_in_wei,
        reference=reference,
        finance=contracts.finance,
    )


def make_eth_payout(*not_specified, target_address: str, eth_in_wei: int, reference: str) -> Tuple[str, str]:
    """Encode ETH payout."""
    if not_specified:
        raise ValueError("Please, specify all arguments with keywords.")

    return _encode_eth_transfer(
        recipient=target_address, amount=eth_in_wei, reference=reference, finance=contracts.finance
    )


def make_dai_payout(*not_specified, target_address: str, dai_in_wei: int, reference: str) -> Tuple[str, str]:
    """Encode DAI payout."""
    if not_specified:
        raise ValueError("Please, specify all arguments with keywords.")

    return _encode_token_transfer(
        token_address=DAI_TOKEN,
        recipient=target_address,
        amount=dai_in_wei,
        reference=reference,
        finance=contracts.finance,
    )


def _encode_token_transfer(token_address, recipient, amount, reference, finance):
    return (finance.address, finance.newImmediatePayment.encode_input(token_address, recipient, amount, reference))


# aragonOS and aragon-apps rely on address(0) to denote native ETH, in
# contracts where both tokens and ETH are accepted
# from https://github.com/aragon/aragonOS/blob/master/contracts/common/EtherTokenConstant.sol
def _encode_eth_transfer(recipient, amount, reference, finance):
    return (finance.address, finance.newImmediatePayment.encode_input(ZERO_ADDRESS, recipient, amount, reference))
