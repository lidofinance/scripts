# @version 0.2.15

called: public(bool)

@external
def perform_call():
    assert not self.called
    self.called = True
