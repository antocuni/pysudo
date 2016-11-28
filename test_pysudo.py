import pytest
import sys
import os
from pysudo import AbstractPySudo, SudoError

class FakePySudo(AbstractPySudo):

    def spawn(self, pyfile):
        # don't invoke sudo at all: this is still useful to test the
        # communication with the subprocess
        ret = os.system('%s %s' % (sys.executable, pyfile))
        return ret >> 8


def test_payload(tmpdir):
    pysudo = FakePySudo
    @pysudo
    def foo(a, b):
        return a+b
    #
    assert foo(1, 2) == 3

def test_exit_code(tmpdir):
    pysudo = FakePySudo
    @pysudo
    def foo(a, b):
        import sys
        sys.exit(42)
    #
    with pytest.raises(SudoError) as exc:
        foo(1, 2)
    assert 'return code 42' in str(exc.value)
