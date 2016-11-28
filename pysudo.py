import py
import sys
import os
import functools
import textwrap
import cPickle
import inspect
from subprocess import Popen, list2cmdline

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
        def pysudo(fn):
            return fn

        {payload}

        if __name__ == '__main__':
            pickled_args = {pickled_args!r}
            args, kwargs = cPickle.loads(pickled_args)
            result = {funcname}(*args, **kwargs)
            with open({outfile.strpath!r}, 'w') as f:
                cPickle.dump(result, f)
        """)
        src = src.format(**locals())
        pyfile.write(src)
        ret = self.spawn(pyfile)
        assert ret == 0
        with outfile.open() as f:
            result = cPickle.load(f)
        return result
