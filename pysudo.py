import py
import sys
import os
import functools
import textwrap
import cPickle
import inspect
from subprocess import Popen, list2cmdline

class SudoError(Exception):
    pass

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

    def execute(self, fn, *args, **kwargs):
        tmpdir = py.path.local.mkdtemp()
        pyfile = tmpdir.join('pysudo_child.py')
        outfile = tmpdir.join('pysudo.out')
        #
        payload = inspect.getsource(fn)
        payload = textwrap.dedent(payload)
        funcname = fn.__name__
        pickled_args = cPickle.dumps((args, kwargs))
        src = textwrap.dedent("""
        import cPickle
        import sys
        def pysudo(fn):
            return fn

        {payload}

        if __name__ == '__main__':
            with open({outfile.strpath!r}, 'w') as f:
                sys.stdout = f
                sys.stderr = f
                pickled_args = {pickled_args!r}
                args, kwargs = cPickle.loads(pickled_args)
                result = {funcname}(*args, **kwargs)
                print
                print '---pysudo result---'
                cPickle.dump(result, f)
        """)
        src = src.format(**locals())
        pyfile.write(src)
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
                elif line == '---pysudo result---\n':
                    result = cPickle.load(f)
                else:
                    print line,
        return result
