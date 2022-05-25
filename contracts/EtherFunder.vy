# @version 0.3.1
# @author psirex
# @licence MIT

@payable
@external
def __init__(ether_recipient: address):
    selfdestruct(ether_recipient)
