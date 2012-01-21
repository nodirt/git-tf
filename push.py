import re, datetime
from util import *
from tf import tf

def _push(cfg, hash):
  print()
  git('checkout ' + hash)
  print('Pushing "%s" to TFS' % git('log -1 --oneline'))

  def rawDiff(changeType):
    return git('diff --raw --find-copies-harder HEAD^.. --diff-filter=%s' % changeType)

  def readChanges(changeType, displayChangeType, handler):
    def parse(change):
      file = change[change.index('\t'):].strip()
      file = '"' + file.replace('\t','" "') + '"'
      return file

    files = [parse(change) for change in rawDiff(changeType).splitlines()]
    if files:
      print(displayChangeType + ':')
      indentPrint(files)
      handler(files)

  unknownChanges = rawDiff('TUX')
  if unknownChanges:
    print('Unexpected file change!!')
    print()
    indentPrint(unknownChanges)
    fail()

  def tfmut(args):
    tf(args, dryRun = cfg.druRun)
  readChanges('D', 'Removed', lambda files: tfmut('rm -recursive ' + ' '.join(files)))
  readChanges('M', 'Modified', lambda files: tfmut('checkout ' + ' '.join(files)))
  def rename(files):
    for file in files:
      tfmut('rename ' + file)
  readChanges('R', 'Renamed', rename)
  readChanges('CA', 'Added', lambda files: tfmut('add ' + ' '.join([f.split('\t', 1)[0] for f in files])))

  print('Checking in...')
  comment = git('log -1 --format=%s%n%b').strip()

  checkin = tf('checkin "-comment:%s" -recursive . ' % comment, dryRun = cfg.dryRun and 'Changeset #12345')
  changeSetNumber = re.search(r'^Changeset #(\d+)', checkin, re.M).group(1)

  # add a note about the changeset number
  print('Moving TFS head and marking the commit with a note')
  git('checkout tfs', dryRun = cfg.dryRun)
  git('merge --ff-only %s' % hash, dryRun = cfg.dryRun)
  git('notes add -m "%s" %s' % (changeSetNumber, hash), dryRun = cfg.dryRun)

def push(cfg):
  print('Pusing to TFS')
  lastCommit = git('log -1 --format=%H tfs')
  lastMasterCommit = git('log master --format=%H -1')
  unmergedCommits = git('log %s.. master --oneline' % lastMasterCommit)
  if unmergedCommits:
    print('You have unmerged changes in tfs branch:')
    indentPrint(unmergedCommits)
    fail()

  print('Checking whether there are no unfetched changes on TFS...')
  latestGitChangeset = re.findall(r'^\d+', git('notes show ' + lastCommit), re.M)[-1]
  latestTfChangeset = tf.history('-stopafter:1')[0]['id']
  if int(latestGitChangeset) < int(latestTfChangeset):
    print('There are unfetched changes on TFS. Fetch and merge them before pushing')
    print('Latest local changeset:', latestGitChangeset)
    print('Latest TFS changeset:', latestTfChangeset)
    fail()


  print('Pushing commits')
  print('Last synchronized commit:', git('log -1 --format=%h tfs'))
  commits = git('log %s.. --format=%%H master --reverse' % lastCommit).splitlines()
  commits = commits[:cfg.number]
  if not commits:
    print('Nothing to push')
    return

  print('%d commit\(s\) to be pushed:' % len(commits))

  for hash in commits:
    _push(cfg, hash)
