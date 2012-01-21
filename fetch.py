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

  history = tf.history('-stopAfter:1')
  latestCommit = history[0]['id']
  print('Latest changeset on TFS:', latestCommit)
  if lastChangeset ==  latestCommit:
    print('Nothing to fetch')
    return False

  history = tf.history('-version:C%s~C%s' % (lastChangeset, latestCommit), echo = True)
  history.reverse()
  history.pop(0)
  history = history[:cfg.number]

  print('%d changeset(s) to fetch' % len(history))

  print('Making files read-only')
  chmod('.', False)
  chmod('.git', True)
  try:
    for entry in history:
      changeset = entry.get('id')
      comment = entry.find('comment')
      comment = not comment is None and comment.text or ''
      author = entry.get('committer').split('\\')[1].strip()
      date = parseXmlDatetime(entry.get('date')).ctime()
      line = ("%s %s %s %s" % (changeset, author, date, comment or '')).strip()
      print()
      print('Fetching "%s"...' % line)

      tf('get -version:%s -recursive .' % changeset, output = True)

      print('Committing to Git...')
      git('add -A .', dryRun = cfg.dryRun)
      git(r'commit --allow-empty-message -m "%s" --author="%s <%s@%s>"' % (comment, author, author, cfg.domain), output = True, dryRun = cfg.dryRun)
      hash = git('log -1 --format=%H', dryRun = 'abcdef')

      # adding a note
      git('notes add -m %s %s' % (changeset, hash), dryRun = cfg.dryRun)
  finally:
    chmod('.', True)
  return True