ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'


def encode_token_transfer(token_address, recipient, amount, reference, finance):
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
def encode_eth_transfer(recipient, amount, reference, finance):
    return (
        finance.address,
        finance.newImmediatePayment.encode_input(
            ZERO_ADDRESS,
            recipient,
            amount,
            reference
        )
    )
