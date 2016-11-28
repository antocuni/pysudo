import sys
import os
from pysudo import AbstractPySudo

class FakePySudo(AbstractPySudo):

    def spawn(self, pyfile):
        # don't invoke sudo at all: this is still useful to test the
        # communication with the subprocess
        return os.system('%s %s' % (sys.executable, pyfile))


def test_payload(tmpdir):
    pysudo = FakePySudo
    @pysudo
    def foo(a, b):
        return a+b
    #
    assert foo(1, 2) == 3
