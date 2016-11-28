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


def test_payload():
    pysudo = FakePySudo
    @pysudo
    def foo(a, b):
        return a+b
    #
    assert foo(1, 2) == 3

def test_exit_code():
    pysudo = FakePySudo
    @pysudo
    def foo(a, b):
        import sys
        sys.exit(42)
    #
    with pytest.raises(SudoError) as exc:
        foo(1, 2)
    assert 'return code 42' in str(exc.value)

def test_stdout(capsys):
    pysudo = FakePySudo
    @pysudo
    def foo():
        print 'hello'
        print 'world'
        return 42
    #
    assert foo() == 42
    out, err = capsys.readouterr()
    assert out == 'hello\nworld\n\n' # the extra \n is added by pysudo

def test_exception():
    pysudo = FakePySudo
    @pysudo
    def foo():
        def bar():
            0/0
        return bar()
    #
    with pytest.raises(SudoError) as exc:
        foo()
    assert 'ZeroDivisionError' in str(exc.value)
