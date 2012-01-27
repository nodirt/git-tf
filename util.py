import subprocess as proc
import os, stat, re, datetime

displayCommands = False
def runner(executable = ''):
  def run(args, errorMsg = None, errorValue = None, output = False, indent = 1, dryRun = None):
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
          print('  ' * indent + line)
        result += line
      elif not p.poll() is None:
        break

    if len(result) > 0 and result[-1] == '\n':
      result = result[:-1]

    if p.returncode:
      if errorValue != None:
        return errorValue
      if errorMsg:
        print(errorMsg)
      print(p.stderr.readall().decode('utf-8'))
      fail('Command "%s" is completed unsuccessfully' % cmd)
    return result
  return run

git = runner('git')

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