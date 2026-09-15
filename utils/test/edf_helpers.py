from brownie import interface, web3  # type: ignore

from utils.balance import set_balance_in_wei
from utils.test.helpers import ETH


def send_as_edf_member(member, contract_fn, *args, call=False):
    """Sends `contract_fn(*args)` from a committee member the same way it happens on mainnet.

    After the EDF vote (LIP-37) oracle members and DSM guardians are DelegationContracts, so the call
    goes through `DelegationContract.execute()` sent by the delegate hot key. An EOA member sends the
    call directly. With `call=True` it is an eth_call instead of a transaction.
    """
    address = getattr(member, "address", member)

    if not web3.eth.get_code(address):
        fn = contract_fn.call if call else contract_fn
        return fn(*args, {"from": address})

    delegation = interface.DelegationContract(address)
    delegate = delegation.getDelegate()
    # the delegate is the hot key that pays for gas on mainnet, so give it some on the fork
    set_balance_in_wei(delegate, ETH(10))
    fn = delegation.execute.call if call else delegation.execute
    return fn(contract_fn._address, contract_fn.encode_input(*args), {"from": delegate})
