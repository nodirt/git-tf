import subprocess as proc
import os
import stat
import datetime
import re
import argparse
import time
import locale
import sys
from itertools import *
import xml.etree.ElementTree as etree

os.environ['GIT_NOTES_REF'] = 'refs/notes/tf'
locale.setlocale(locale.LC_ALL, '')


class GitTfException(Exception):
    pass


def fail(msg=None):
    if msg:
        print(msg)
    raise GitTfException(None)

_curCommand = None


class Runner:
    prefix = ''

    def argsToStr(self, args):
        if type(args) == str:
            return args
        elif type(args) in (tuple, list):
            fmt, *args = args
            fmt = self.argsToStr(fmt)
            args = map(lambda a: a if type(a) == str else self.argsToStr(a), args)
            return fmt.format(*args)
        else:
            return self.argsToStr(str(args))

    def genCommand(self, args):
        cmd = self.prefix
        if args:
            args = self.argsToStr(args).strip()
            if args:
                cmd += ' ' + args
        return cmd

    def start(self, args):
        class Process:
            def __init__(self, pipe):
                self.pipe = pipe

            def readline(self):
                while True:
                    line = self.pipe.stdout.readline()
                    if line != b'':
                        return line.decode('utf-8')[:-1]
                    elif self.pipe.poll() is not None:
                        return None
                    else:
                        time.sleep(0.05)

            def poll(self):
                return self.pipe.poll()

            @property
            def exitCode(self):
                return self.pipe.returncode

            def fail(self, lastMsg=None):
                errorOutput = self.pipe.stderr.readall().decode('utf-8').strip()
                if errorOutput:
                    print(errorOutput)
                print('Command "%s" exited with code %s' % (cmd, self.poll()))
                if lastMsg:
                    print(lastMsg)
                fail()

        cmd = (self.prefix and self.prefix + ' ') + self.argsToStr(args)
        return Process(proc.Popen(cmd, shell=True, stderr=proc.PIPE, stdout=proc.PIPE))

    def __call__(self, args, allowedExitCodes=[0], errorValue=None, output=False, indent=1, dryRun=None, errorMsg=None):
        verbose = _curCommand and _curCommand.args.verbose > 1

        args = self.argsToStr(args)
        if verbose:
            print('$ ' + (self.prefix and self.prefix + ' ') + args)
        if dryRun:
            return dryRun

        process = self.start(args)

        result = ''
        for line in iter(process.readline, None):
            if output or verbose:
                print('  ' * indent + line)
            result = result and result + '\n'
            result += line

        if process.exitCode in allowedExitCodes:
            return result
        elif errorValue is not None:
            return errorValue
        else:
            process.fail(errorMsg)

run = Runner()

#######      GIT       #######


class _git(Runner):
    prefix = 'git'

    def hasChanges(self):
        return self('status -s')

    def getChangesetNumber(self, commit=''):
        note = git('notes show ' + commit, errorValue='')
        return re.findall(r'^\d+', note, re.M)[-1] if note else None

git = _git()
try:
    git('--version', errorMsg='Git not found in the $PATH variable')
except GitTfException:
    exit(1)

#######      TFS       #######


class _tf(Runner):
    prefix = git('config tf.cmd', errorValue='tf')
    paramPrefix = git('config tf.paramPrefix', errorValue='') or '/' if os.name == 'nt' else '-'

    def argsToStr(self, args):
        if type(args) == str and self.paramPrefix != '-':
            args = args.replace('-', self.paramPrefix)
        return Runner.argsToStr(self, args)

    class Changeset(object):
        def __init__(self, node):
            self.id = node.get('id')
            self.comment = node.find('comment')
            self.comment = self.comment is not None and self.comment.text or ''
            self.dateIso = node.get('date')
            self.date = parseXmlDatetime(self.dateIso)
            self.committer = node.get('committer').split('\\', 1)[-1].strip()
            self.line = ' '.join((self.id, self.committer, self.date.ctime(), self.comment))\
                .strip().replace('\n', ' ')[:128]

    def history(self, version=None, stopAfter=None):
        filter = ['']
        if version:
            filter[0] += '-version:C{}~C{}'
            filter += version
        if stopAfter:
            filter[0] += ' -stopafter:{}'
            filter.append(stopAfter)

        args = ('history -recursive -format:xml {} .', filter)
        history = etree.fromstring(self(args))
        return [self.Changeset(cs) for cs in history if cs.tag == 'changeset']

    def getDomain(self):
        domain = git('config tf.domain', errorValue='')
        if domain:
            return domain

        email = git('config user.email')
        if not email:
            print('Email not set. Configure it:')
            fail('$ git config user.email userName@yourTfsServer.com')
        try:
            return email[email.index('@') + 1:]
        except ValueError:
            fail('Could not determine the domain. Your email is: ')

    def get(self, version, **kwargs):
        return self(('get -version:{} -recursive .', version), **kwargs)


tf = _tf()


class ReadOnlyWorktree(object):
    def __init__(self, output=False):
        self.output = output

    def __enter__(self):
        if self.output:
            print('Making files read-only')
        chmod('.', False)
        chmod('.git', True)

    def __exit__(self, _, __, ___):
        if self.output:
            print('Making files writable')
        chmod('.', True)

######       App           #######


class Command:
    def __init__(self):
        self._free = []

    def argParserCtorArgs(self):
        return dict(
            description=type(self).__doc__,
            formatter_class=argparse.RawTextHelpFormatter,
            prog='git-tf-' + type(self).__name__)

    def initArgParser(self, parser):
        parser.set_defaults(cmd=self, dryRun=False, verbose=0)
        self._initArgParser(parser)

    def _initArgParser(self, parser):
        pass

    def moveToRootDir(self):
        root = git('rev-parse --show-toplevel')
        origDir = os.path.abspath('.')
        os.chdir(root)
        self._free.append(lambda: os.chdir(origDir))

    def checkStatus(self, checkTfs=None, checkGit=True):
        if checkGit and git('status -s') != '':
            fail('Worktree is dirty. Stash your changes before proceeding.')

        if checkTfs is True or not self.args.noChecks:
            print('Checking TFS status. There must be no pending changes...')
            if tf('status') != 'There are no matching pending changes.':
                fail('TFS status is dirty!')

    def switchToTfsBranch(self):
        def getCurBranch():
            branches = git('branch').splitlines()
            return [b[2:] for b in branches if b.startswith('* ')][0]

        noBranch = '(no branch)'

        def checkoutBranch(branch):
            curBranch = getCurBranch()
            if curBranch != branch and curBranch != noBranch:
                git('checkout ' + branch)
        origBranch = getCurBranch()
        if origBranch == noBranch:
            fail('Not currently on any branch')
        checkoutBranch('tfs')
        self._free.append(lambda: checkoutBranch(origBranch))

    def __enter__(self):
        pass

    def __exit__(self, *rest):
        for a in self._free:
            a()

    def _run(self):
        pass

    def runWithArgs(self, args):
        if args.verbose:
            print('Parsed arguments:')
            printIndented(str(args))
            print()

        if args.dryRun:
            print('DRY RUN. Nothing is going to be changed.\n')
        self.args = args

        global _curCommand
        if _curCommand:
            raise AssertionError('Only one Command can run at a time')
        _curCommand = self
        try:
            with self:
                self._run()
        except GitTfException:
            quit(1)
        finally:
            _curCommand = None

    def run(self):
        parser = argparse.ArgumentParser(**self.argParserCtorArgs())
        self.initArgParser(parser)
        self.runWithArgs(parser.parse_args())

#######      util       #######


class ArgParser(argparse.ArgumentParser):
    def addVerbose(self):
        self.add_argument('-v', '--verbose', action='count', default=0,
            help='be verbous')

    def addNoChecks(self):
        self.add_argument('-C', '--noChecks', action='store_true',
            help='skip long checks, such as TFS status')

    def addDryRun(self):
        self.add_argument('--dryRun', action='store_true',
            help='do not make any changes')

    def addNumber(self, help):
        self.add_argument('--number', type=int, default=None, help=help)

    def addForce(self, help):
        self.add_argument('-f', '--force', action='store_true', help=help)


def parseXmlDatetime(text):
    return datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%S.%f%z')


def chmod(path, writable, rec=True):
    def update(path):
        mode = os.stat(path).st_mode
        if writable:
            mode |= stat.S_IWRITE
        else:
            mode &= ~stat.S_IWRITE
        os.chmod(path, mode)
    if not rec:
        update(path)
    else:
        for root, dirnames, filenames in os.walk(path):
            for filename in filenames:
                update(os.path.join(root, filename))


def printIndented(text, indent=1):
    if isinstance(text, str):
        lines = text.splitlines()
    else:
        lines = text

    for line in lines:
        print('  ' * indent + line)


_terminalHeight, terminalWidth = [int(x) for x in os.popen('stty size', 'r').read().split()] or [24, 80]


def printLine():
    print('_' * terminalWidth)


def printLess(lines):
    if not sys.stdout.isatty():
        for line in lines:
            print(line)
        return

    (forPrint, forLess) = tee(lines, 2)
    doLess = False
    for i, line in enumerate(forPrint):
        print(line)
        if i >= _terminalHeight - 2:
            doLess = True
            break

    if doLess:
        less = proc.Popen(['less', '-'], stdin=proc.PIPE)
        try:
            for line in forLess:
                if less.poll() is not None:
                    break
                less.stdin.write(bytes(line + '\n', 'utf-8'))
        finally:
            less.communicate()
