import pytest
import sys
import os
from pysudo import PopenPySudo, Win32PySudo, SudoError

interactive = pytest.mark.skipif(
    not pytest.config.getoption("--interactive"),
    reason="need --interactive option to run"
)

@pytest.fixture(params=['popen', 'win32'])
def pysudo(request):
    if request.param == 'popen':
        return PopenPySudo
    elif request.param == 'win32':
        if sys.platform == 'win32':
            return Win32PySudo
        else:
            pytest.skip('win32-only test')

def fakesudo(*args, **kwargs):
    kwargs['fake'] = True
    return PopenPySudo(*args, **kwargs)

class TestPySudo:

    def test_payload(self, pysudo):
        @pysudo(fake=True)
        def foo(a, b):
            return a+b
        #
        assert foo(1, 2) == 3

    def test_exit_code(self):
        @fakesudo
        def foo(a, b):
            import sys
            sys.exit(42)
        #
        with pytest.raises(SudoError) as exc:
            foo(1, 2)
        assert 'return code 42' in str(exc.value)

    def test_stdout(self, capsys):
        @fakesudo
        def foo():
            print 'hello'
            print 'world'
            return 42
        #
        assert foo() == 42
        out, err = capsys.readouterr()
        assert out == 'hello\nworld\n\n' # the extra \n is added by pysudo

    def test_exception(self):
        @fakesudo
        def foo():
            def bar():
                0/0
            return bar()
        #
        with pytest.raises(SudoError) as exc:
            foo()
        assert 'ZeroDivisionError' in str(exc.value)

    def test_use_stdout_file(self, tmpdir):
        @fakesudo(use_stdout_file=True, tmpdir=tmpdir)
        def foo(a, b):
            print 'hello'
            return a+b
        #
        assert foo(1, 2) == 3
        stdout = tmpdir.join('stdout').read()
        assert 'hello' in stdout
        assert '---pysudo return---' in stdout

    @interactive
    def test_nofake(self):
        @PopenPySudo
        def foo():
            import os
            return os.getuid()
        #
        assert foo() == 0
