# @version 0.3.7

called: public(bool)

@external
def perform_call():
    assert not self.called
    self.called = True
