#!/usr/bin/python3
from tf import *

def fetch(cfg):
  print('Fetching from TFS')
  lastCommit = git('log -1 --format=%H tfs')

  try:
    lastChangeset = re.findall(r'^\d+', git('notes show $lastCommit'), re.M)[-1]
    print('Last synchronized changeset:', lastChangeset)
  except:
    fail('Last changeset could not determined. Probably the last commit is missing a tf note. Commit: %s' % lastCommit)

  latestCommit = tf.history('-stopAfter:1')[0].id
  print('Latest changeset on TFS:', latestCommit)
  if lastChangeset ==  latestCommit:
    print('Nothing to fetch')
    return False

  print('Requesting tf history %s..%s' % (lastChangeset, latestCommit))
  history = tf.history('-version:C%s~C%s' % (lastChangeset, latestCommit))
  history.reverse()
  history.pop(0)
  history = history[:cfg.number]

  print('%d changeset(s) to fetch' % len(history))

  if cfg.debug:
    print('Making files read-only')
  chmod('.', False)
  chmod('.git', True)
  try:
    for i, cs in enumerate(history):
      printLine()
      print('Fetching [%d/%d] "%s"...' % (i + 1, len(history), cs.line))

      tf('get -version:%s -recursive .' % cs.id, output = True, dryRun = cfg.dryRun)

      comment = cs.comment
      if not comment:
        print('The comment is empty. Using changeset number as a comment')
        comment = str(cs.id)
      print('Committing to Git...')
      git('add -A .', dryRun = cfg.dryRun)
      git(r'commit -m "%s" --author="%s <%s@%s>" --date="%s"' % (comment, cs.committer, cs.committer, cfg.domain, cs.dateIso), output = True, dryRun = cfg.dryRun)
      hash = git('log -1 --format=%H', dryRun = cfg.dryRun and 'abcdef')

      # adding a note
      git('notes add -m %s %s' % (cs.id, hash), dryRun = cfg.dryRun)
  finally:
    chmod('.', True)
  return True
