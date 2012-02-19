import subprocess as proc
import os, stat, re, datetime
import xml.etree.ElementTree as etree

displayCommands = False
def runner(executable = ''):
    def run(args, allowedExitCodes = [0], errorMsg = None, errorValue = None, output = False, indent = 1, dryRun = None):
        cmd = args
        if executable:
            cmd = '%s %s' % (executable, cmd)

        if displayCommands:
            print('$ ' + cmd)
        if dryRun:
            return dryRun

        result = ''
        p = proc.Popen(cmd, shell = True, stderr = proc.PIPE, stdout = proc.PIPE)

        while True:
            line = p.stdout.readline()
            if line != b'':
                line = line.decode('utf-8')
                if output or displayCommands:
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

#######      the rest       #######

class GitTfException(Exception):
    pass
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