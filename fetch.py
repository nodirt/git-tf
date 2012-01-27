from tf import *

def fetch(cfg):
  print('Fetching from TFS')
  lastCommit = git('log -1 --format=%H tfs')

  try:
    lastChangeset = re.findall(r'^\d+', git('notes show'), re.M)[-1]
    print('Last synchronized changeset:', lastChangeset)
  except:
    lastChangeset = None
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

  def gitHasChanges():
    return git('status -s')

  def fetch(version):
    return tf('get -version:%s -recursive .' % version, output = True, dryRun = cfg.dryRun)

  if cfg.debug:
    print('Making files read-only')
  chmod('.', False)
  chmod('.git', True)
  lastSyncedChangeset = lastChangeset
  try:
    for i, cs in enumerate(history):
      printLine()
      print('Fetching [%d/%d] "%s"...' % (i + 1, len(history), cs.line))
      fetch(cs.id)
      if not gitHasChanges():
        print('Nothing new is fetched. TFS thinks that it is up to date.')
        if i:
          fail('Please, try it again with --debug option and report the output to the developer.')
        print('Trying to fetch the previous changeset and repeat.')
        fetch(lastChangeset)

        def didNotHelp():
          fail('It did not help. The problem is that TFS thinks that it is up to date,' +
            'but it is not according to Git. Try to fetch an older version from TFS and fetch/pull again.' +
            ('Alternatively try to fetch version %s completely:' % lastChangeset) +
             'tf get -version:%s -force -overwrite -all' % lastChangeset
          )

        if gitHasChanges(): didNotHelp()
        print('Now fetching %s again...' % cs.id)
        fetch(cs.id)
        if not gitHasChanges(): didNotHelp()

      print('Committing to Git...')
      comment = cs.comment
      if not comment:
        print('The comment is empty. Using changeset number as a comment')
        comment = str(cs.id)
      git('add -A .', dryRun = cfg.dryRun)
      git(r'commit -m "%s" --author="%s <%s@%s>" --date="%s"' % (comment, cs.committer, cs.committer, cfg.domain, cs.dateIso), output = True, dryRun = cfg.dryRun)
      git('notes add -m %s' % cs.id, dryRun = cfg.dryRun)
      lastSyncedChangeset = cs.id
  except:
    print('Rolling back to the last synchronized changeset: %s' % lastSyncedChangeset)
    fetch(lastSyncedChangeset)
    git('reset --hard')
    git('clean -fd')
    raise
  finally:
    chmod('.', True)
  return True
