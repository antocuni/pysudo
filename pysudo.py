import py
import sys
import os
import functools
import textwrap
import cPickle
import inspect
import subprocess
from cStringIO import StringIO

class SudoError(Exception):
    def __init__(self, formatted):
        self.formatted = formatted
        Exception.__init__(self)

    def __str__(self):
        return self.formatted

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.formatted)


class AbstractPySudo(object):

    def __new__(cls, fn=None, **kwargs):
        """
        Either decorate the given function or return a decorator if no function is
        given. This lets you to use both forms:

        @pysudo
        def foo(...)

        @pysudo(my_option='...')
        def foo(...)
        """
        self = super(AbstractPySudo, cls).__new__(cls)
        self.__init__(**kwargs)
        if fn:
            return self(fn)
        else:
            return self

    def __init__(self, use_stdout_file=False, tmpdir=None, fake=False):
        self.use_stdout_file = use_stdout_file
        self.tmpdir = tmpdir
        self.fake = fake

    def __call__(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            return self.execute(fn, *args, **kwargs)
        return decorated

    def spawn(self, pyfile):
        raise NotImplementedError

    def _get_source(self, fn, *args, **kwargs):
        payload = inspect.getsource(fn)
        payload = textwrap.dedent(payload)
        #
        # remove the @pysudo decorator (and any other)
        lines = []
        for line in payload.splitlines():
            if line.startswith('@'):
                continue
            lines.append(line)
        payload = '\n'.join(lines)
        #
        funcname = fn.__name__
        pickled_args = cPickle.dumps((args, kwargs))
        src = textwrap.dedent(
        """
        import sys
        import cPickle
        import traceback
        {payload}

        class SetupStreams(object):

            def __init__(self, outfile):
                self.outfile = outfile

            def __enter__(self):
                if self.outfile:
                    sys.stdout = open(self.outfile, 'w')
                sys.stderr = sys.stdout

            def __exit__(self, etype, evalue, tb):
                if self.outfile:
                    sys.stdout.close()

        if __name__ == '__main__':
            outfile = None
            if len(sys.argv) == 2:
                outfile = sys.argv[1]
            pickled_args = {pickled_args!r}
            args, kwargs = cPickle.loads(pickled_args)
            with SetupStreams(outfile):
                try:
                    result = {funcname}(*args, **kwargs)
                except Exception:
                    print
                    print '---pysudo exception---'
                    traceback.print_exc()
                else:
                    print
                    print '---pysudo return---'
                    cPickle.dump(result, sys.stdout)
        """)
        src = src.format(**locals())
        return src

    def execute(self, fn, *args, **kwargs):
        tmpdir = self.tmpdir or py.path.local.mkdtemp()
        pyfile = tmpdir.join('pysudo_child.py')
        src = self._get_source(fn, *args, **kwargs)
        pyfile.write(src)
        #
        ret, stdout = self.spawn(pyfile)
        if ret != 0:
            print stdout
            raise SudoError("Error in the child process: return code %s" % ret)
        #
        # process outfile: print stdout and return the result
        result = None
        f = StringIO(stdout)
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


class PopenPySudo(AbstractPySudo):

    @staticmethod
    def is_root():
        return os.getuid() == 0

    def sudoargs(self, args):
        if self.fake:
            return args
        return ['sudo'] + args

    def spawn(self, pyfile):
        args = self.sudoargs([sys.executable, str(pyfile)])
        if self.use_stdout_file:
            stdout_file = pyfile.dirpath('stdout')
            args.append(str(stdout_file))
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = proc.communicate()
        if self.use_stdout_file:
            stdout = stdout_file.read()
        return proc.returncode, stdout


class Win32PySudo(AbstractPySudo):

    @staticmethod
    def is_root():
        import win32com.shell.shell as shell
        return shell.IsUserAnAdmin()

    def spawn(self, pyfile):
        import win32api
        import win32event
        import win32process
        import win32com.shell.shell as shell
        SEE_MASK_NOASYNC = 0x00000100
        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        #
        exe = sys.executable
        stdout_file = pyfile.dirpath('stdout')
        params = [str(pyfile), str(stdout_file)]
        params = subprocess.list2cmdline(params)
        #
        if self.fake:
            verb = 'open'
        else:
            verb = 'runas'
        #
        try:
            ret = shell.ShellExecuteEx(
                fMask=SEE_MASK_NOASYNC+SEE_MASK_NOCLOSEPROCESS,
                lpVerb=verb,
                lpFile=exe,
                lpParameters=params)
        except win32api.error as e:
            msg = "Cannot execute child process: %s [%s]" % (e.strerror, e.winerror)
            raise SudoError(msg)
        #
        proc_handle = ret['hProcess']
        win32event.WaitForSingleObject(proc_handle, -1)
        returncode = win32process.GetExitCodeProcess(proc_handle)
        stdout = stdout_file.read()
        return returncode, stdout


if sys.platform == 'win32':
    pysudo = Win32PySudo
else:
    pysudo = PopenPySudo

is_root = pysudo.is_root
