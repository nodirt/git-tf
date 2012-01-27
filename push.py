import re, datetime
from core import *

def _push(cfg, hash, index, total):
  print()
  printLine()
  git('checkout ' + hash)
  print('Pushing [%d/%d] %s...' % (index + 1, total, git(r'log -1 --format="%h \"%s\""')))


  def rawDiff(changeType):
    return git('diff --raw --find-copies-harder HEAD^.. --diff-filter=%s' % changeType)

  def readChanges(changeType, displayChangeType):
    def parse(change):
      file = change[change.index('\t'):].strip()
      file = '"' + file.replace('\t','" "') + '"'
      return file

    files = [parse(change) for change in rawDiff(changeType).splitlines()]
    if files:
      print(displayChangeType + ':')
      indentPrint(files)
      yield files

  unknownChanges = rawDiff('TUX')
  if unknownChanges:
    print('Unexpected file change!!')
    print()
    indentPrint(unknownChanges)
    fail()

  def tfmut(args):
    tf(args, dryRun = cfg.dryRun)

  try:
    for files in readChanges('D', 'Removed'):
      tfmut('rm -recursive ' + ' '.join(files))
    for files in readChanges('M', 'Modified'):
      tfmut('checkout ' + ' '.join(files))
    for files in readChanges('R', 'Renamed'):
      for file in files:
        tfmut('rename ' + file)
    for files in readChanges('CA', 'Added'):
      tfmut('add ' + ' '.join([f.split('\t', 1)[-1] for f in files]))

    print('Checking in...')
    comment = git('log -1 --format=%s%n%b').strip()
    checkin = tf('checkin "-comment:%s" -recursive . ' % comment, output = True, dryRun = cfg.dryRun and 'Changeset #12345')
  except:
    if not cfg.dryRun:
      print('Restoring Git and TFS state...')
      with ReadOnlyWorktree():
        tf('undo -recursive .', allowedExitCodes = [0, 100])
      git('checkout -f tfs')
    raise
  changeSetNumber = re.search(r'^Changeset #(\d+)', checkin, re.M).group(1)

  # add a note about the changeset number
  print('Moving tfs branch HEAD and marking the commit with a "tf" note')
  git('checkout tfs', dryRun = cfg.dryRun)
  git('merge --ff-only %s' % hash, dryRun = cfg.dryRun)
  git('notes add -m "%s" %s' % (changeSetNumber, hash), dryRun = cfg.dryRun)

def push(cfg):
  print('Pushing to TFS')
  lastCommit = git('log -1 --format=%H tfs')
  lastMasterCommit = git('log master --format=%H -1')
  unmergedCommits = git('log %s.. master --oneline' % lastMasterCommit)
  if unmergedCommits:
    print('You have unmerged changes in tfs branch:')
    indentPrint(unmergedCommits)
    fail()

  print('Last synchronized commit:', git('log -1 --format=%h tfs'))
  commits = git('log %s.. --format=%%H master --reverse' % lastCommit).splitlines()
  commits = commits[:cfg.number]
  if not commits:
    print('Nothing to push')
    return

  print('Checking whether there are no unfetched changes on TFS...')
  latestGitChangeset = re.findall(r'^\d+', git('notes show ' + lastCommit), re.M)[-1]
  latestTfChangeset = tf.history('-stopafter:1')[0].id
  if int(latestGitChangeset) < int(latestTfChangeset):
    print('There are unfetched changes on TFS. Fetch and merge them before pushing')
    print('Latest local changeset:', latestGitChangeset)
    print('Latest TFS changeset:', latestTfChangeset)
    fail()


  print('%d commit(s) to be pushed:' % len(commits))

  for i, hash in enumerate(commits):
    _push(cfg, hash, i, len(commits))
