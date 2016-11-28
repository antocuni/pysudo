import pytest
import sys
import os
from pysudo import PopenPySudo, SudoError

def test_payload():
    pysudo = PopenPySudo
    @pysudo
    def foo(a, b):
        return a+b
    #
    assert foo(1, 2) == 3

def test_exit_code():
    pysudo = PopenPySudo
    @pysudo
    def foo(a, b):
        import sys
        sys.exit(42)
    #
    with pytest.raises(SudoError) as exc:
        foo(1, 2)
    assert 'return code 42' in str(exc.value)

def test_stdout(capsys):
    pysudo = PopenPySudo
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
    pysudo = PopenPySudo
    @pysudo
    def foo():
        def bar():
            0/0
        return bar()
    #
    with pytest.raises(SudoError) as exc:
        foo()
    assert 'ZeroDivisionError' in str(exc.value)

def test_use_stdout_file(tmpdir):
    def foo(a, b):
        print 'hello'
        return a+b
    #
    decorator = PopenPySudo(use_stdout_file=True, tmpdir=tmpdir)
    sudo_foo = decorator(foo)
    assert sudo_foo(1, 2) == 3
    stdout = tmpdir.join('stdout').read()
    assert 'hello' in stdout
    assert '---pysudo return---' in stdout
