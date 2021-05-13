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
