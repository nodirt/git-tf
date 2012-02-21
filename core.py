import subprocess as proc
import sys, os, stat, re, datetime, getopt
import xml.etree.ElementTree as etree

def runner(executable = ''):
    def run(args, allowedExitCodes = [0], errorMsg = None, errorValue = None, output = False, indent = 1, dryRun = None):
        cmd = args
        if executable:
            cmd = '%s %s' % (executable, cmd)

        if runner.displayCommands:
            print('$ ' + cmd)
        if dryRun:
            return dryRun

        result = ''
        p = proc.Popen(cmd, shell = True, stderr = proc.PIPE, stdout = proc.PIPE)

        while True:
            line = p.stdout.readline()
            if line != b'':
                line = line.decode('utf-8')
                if output or runner.displayCommands:
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
runner.displayCommands = False
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

class App:
    verbose  = True
    debug    = False
    dryRun   = False
    noChecks = False
    number   = None

    def __init__(self):
        self._free = []
        self.args = sys.argv[1:]

    def __enter__(self):
        self.parseArgs(self.args)
        if self.dryRun:
            print('DRY RUN. Nothing is going to be changed.\n')
        runner.displayCommands = self.debug

        root = git('rev-parse --show-toplevel')

        def readCfgValue(name):
            value = git('config tf.%s' % name, errorMsg = 'git tf is not configured. Config value "%s" not found.' % name)
            setattr(self, name, value)

        readCfgValue('domain')
        readCfgValue('username')

        origDir = os.path.abspath('.')
        os.chdir(root)
        self._free.append(lambda : os.chdir(origDir))

        if git('status -s') != '':
            fail('Worktree is dirty. Stash your changes before proceeding.')

        if not self.noChecks:
            print('Checking TFS status. There must be no pending changes...')
            workfold = tf('workfold .')
            if workfold.find(root) == -1:
                print('TF mapped folder does not match git root work folder!')
                print('Expected: %s' % root)
                print('Actual: %s' % workfold.splitlines()[3].split(': ')[1])
                fail()

            if tf('status') != 'There are no matching pending changes.':
                fail('TFS status is dirty!')

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

        os.environ['GIT_NOTES_REF'] = 'refs/notes/tf'

    def __exit__(self, _, __, ___):
        for a in self._free:
            a()

    @staticmethod
    def run(body):
        def _run():
            app = App()
            with app:
                body(app)
        return GitTfException.run(_run)



    def parseArgs(self, args):
        optlist, args = getopt.getopt(args, 'vCn:', 'verbose debug noChecks dry-run number='.split())
        shortToLong = {
            'v': 'verbose',
            'C': 'noChecks',
            'n': 'number'
        }

        for arg, value in optlist:
            if arg[1] != '-':
                long = shortToLong.get(arg[1:])
                if not long: fail('Unknown option ' + arg)
            else:
                long = arg[2:]

            long = toCamelCase(long)
            setattr(self, long, value == '' or value)

        if self.number is not None:
            self.number = int(self.number)

def getCommandPath(name):
    me = sys.argv[0]
    if os.path.islink(me):
        me = os.readlink(me)
    return os.path.join(os.path.dirname(me), 'git-tf-' + name)

#######      the rest       #######

class GitTfException(Exception):
    @staticmethod
    def run(body):
        try:
            return body()
        except GitTfException:
            quit(1)


def fail(msg = None):
    if msg: print(msg)
    raise GitTfException(None)

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