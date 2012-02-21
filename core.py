import subprocess as proc
import sys, os, stat, re, datetime, argparse
import xml.etree.ElementTree as etree

os.environ['GIT_NOTES_REF'] = 'refs/notes/tf'

_curCommand = None

def runner(executable = ''):
    def run(args, allowedExitCodes = [0], errorMsg = None, errorValue = None, output = False, indent = 1, dryRun = None):
        verbose = _curCommand and _curCommand.args.verbose > 1
        cmd = args
        if executable:
            cmd = '%s %s' % (executable, cmd)

        if verbose:
            print('$ ' + cmd)
        if dryRun:
            return dryRun

        result = ''
        p = proc.Popen(cmd, shell = True, stderr = proc.PIPE, stdout = proc.PIPE)

        while True:
            line = p.stdout.readline()
            if line != b'':
                line = line.decode('utf-8')
                if output or verbose:
                    print('  ' * indent + line, end = '')
                result += line
            elif not p.poll() is None:
                break

        if len(result) > 0 and result[-1] == '\n':
            result = result[:-1]

        if p.returncode not in allowedExitCodes:
            if errorValue != None:
                return errorValue
            if errorMsg:
                print(errorMsg)
            print(p.stderr.readall().decode('utf-8'))
            fail('Command "%s" exited with code %s' % (cmd, p.returncode))
        return result
    return run

#######      GIT       #######

git = runner('git')
git('--version', errorMsg = 'Git not found in $PATH variable')

#######      TFS       #######

tf = runner(git('config tf.cmd', errorValue = 'tf'))

class Changeset(object):
    def __init__(self, node):
        self.id = node.get('id')
        self.comment = node.find('comment')
        self.comment = self.comment is not None and self.comment.text or ''
        self.dateIso = node.get('date')
        self.date = parseXmlDatetime(self.dateIso)
        self.committer = node.get('committer').split('\\', 1)[-1].strip()
        self.line = ('%s %s %s %s' % (self.id, self.committer, self.date.ctime(), self.comment)).strip()

def _history(args):
    args = 'history -recursive -format:xml %s .' % args
    history = etree.fromstring(tf(args))
    return [Changeset(cs) for cs in history if cs.tag == 'changeset']

tf.history = _history

class ReadOnlyWorktree(object):
    def __init__(self, output = False):
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

    def initArgParser(self, parser):
        parser.add_argument('-v', '--verbose', action='count', help='be verbous', default=0)
        parser.add_argument('-C', '--noChecks', action='store_true', help='skip long checks, such as TFS status')
        parser.add_argument('--dryRun', action='store_true', help='do not make any changes')

    def readConfigValue(self, name):
        return git('config tf.%s' % name, errorMsg = 'git tf is not configured. Config value "%s" not found.' % name)

    def moveToRootDir(self):
        root = git('rev-parse --show-toplevel')
        origDir = os.path.abspath('.')
        os.chdir(root)
        self._free.append(lambda : os.chdir(origDir))

    def checkStatus(self, checkTfs=None):
        if git('status -s') != '':
            fail('Worktree is dirty. Stash your changes before proceeding.')

        if checkTfs is True or not self.args.noChecks:
            print('Checking TFS status. There must be no pending changes...')
            if tf('status') != 'There are no matching pending changes.':
                fail('TFS status is dirty!')

    def switchToTfsBranch(self):
        def getCurBranch():
            return [b[2:] for b in git('branch').splitlines() if b.startswith('* ')][0]
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
        self.moveToRootDir()
        self.checkStatus()
        self.switchToTfsBranch()

    def __exit__(self, *rest):
        for a in self._free:
            a()

    def _run(self):
        pass

    def runWithArgs(self, args):
        if args.verbose:
            print('Parsed arguments:')
            indentPrint(str(args))
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
        parser = argparse.ArgumentParser(description=type(self).__doc__)
        self.initArgParser(parser)
        self.runWithArgs(parser.parse_args())


class GitTfException(Exception):
    pass

def fail(msg = None):
    if msg: print(msg)
    raise GitTfException(None)

#######      util       #######

def parseXmlDatetime(str):
    return datetime.datetime.strptime(str, '%Y-%m-%dT%H:%M:%S.%f%z')

def chmod(path, writable, rec = True):
    def update(path):
        mode = os.stat(path).st_mode
        if writable:
            mode = mode | stat.S_IWRITE
        else:
            mode = mode & ~stat.S_IWRITE
        os.chmod(path, mode)
    if not rec:
        update(path)
    else:
        for root, dirnames, filenames in os.walk(path):
            for filename in filenames:
                update(os.path.join(root, filename))

def indentPrint(text, indent = 1):
    if isinstance(text, str):
        lines = text.splitlines()
    else:
        lines = text

    for line in lines:
        print('  ' * indent + line)

def toCamelCase(str):
    return re.sub(r'\-\w', lambda m: m.group()[1].capitalize(), str)

_terminalHeight, _terminalWidth = [int(x) for x in os.popen('stty size', 'r').read().split()] or [24,80]
def printLine():
    print('_' * _terminalWidth)