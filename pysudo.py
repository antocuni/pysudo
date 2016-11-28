import py
import sys
import os
import functools
import textwrap
import cPickle
import inspect
from subprocess import Popen, list2cmdline

class SudoError(Exception):
    def __init__(self, formatted):
        self.formatted = formatted
        Exception.__init__(self)

    def __str__(self):
        return self.formatted

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.formatted)


class AbstractPySudo(object):

    def __new__(cls, fn=None):
        self = super(AbstractPySudo, cls).__new__(cls)
        if fn:
            return self(fn)
        else:
            return self

    def __call__(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            return self.execute(fn, *args, **kwargs)
        return decorated

    def spawn(self, pyfile):
        raise NotImplementedError

    def _write_source(self, fn, *args, **kwargs):
        tmpdir = py.path.local.mkdtemp()
        pyfile = tmpdir.join('pysudo_child.py')
        outfile = tmpdir.join('pysudo.out')
        #
        payload = inspect.getsource(fn)
        payload = textwrap.dedent(payload)
        funcname = fn.__name__
        pickled_args = cPickle.dumps((args, kwargs))
        src = textwrap.dedent("""
        import sys
        import cPickle
        import traceback
        def pysudo(fn):
            return fn

        {payload}
        if __name__ == '__main__':
            with open({outfile.strpath!r}, 'w') as f:
                sys.stdout = f
                sys.stderr = f
                pickled_args = {pickled_args!r}
                args, kwargs = cPickle.loads(pickled_args)
                try:
                    result = {funcname}(*args, **kwargs)
                except Exception:
                    print
                    print '---pysudo exception---'
                    traceback.print_exc()
                else:
                    print
                    print '---pysudo return---'
                    cPickle.dump(result, f)
        """)
        src = src.format(**locals())
        pyfile.write(src)
        return pyfile, outfile

    def execute(self, fn, *args, **kwargs):
        pyfile, outfile = self._write_source(fn, *args, **kwargs)
        ret = self.spawn(pyfile)
        if ret != 0:
            stdout = outfile.read()
            print stdout
            raise SudoError("Error in the child process: return code %s" % ret)
        #
        # process outfile: print stdout and return the result
        result = None
        with outfile.open() as f:
            while True:
                line = f.readline()
                if line == '':
                    break
                elif line == '---pysudo return---\n':
                    result = cPickle.load(f)
                elif line == '---pysudo exception---\n':
                    formatted_tb = f.read()
                    raise SudoError(formatted_tb)
                else:
                    print line,
        return result
