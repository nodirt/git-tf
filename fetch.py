from core import *

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

    def fetch(version, output = True):
        return tf('get -version:%s -recursive .' % version, output = output, dryRun = cfg.dryRun)

    def repair(lastCommit, lastChangeset, changesetToFetch):
        print('But it may mean we have a problem, so let\'s check it.')
        print('Trying to fetch the previous changeset and repeat...')
        fetch(lastChangeset, output = False)

        if gitHasChanges():
            print('git-tf state is corrupted: the commit %s was expected to match changeset %s.' % (lastCommit, lastChangeset))
            print('You can try to "git reset" to a non-corrupted commit and fetch/pull again.')
            unpushed = git('log tfs..master --oneline')
            if unpushed:
                print('You have unpushed commits:')
                indentPrint(unpushed)
                print('Cherry-pick them when you finish repairing.')
            fail()

        print('No, there is no problem. Now fetching %s again...' % changesetToFetch)
        fetch(changesetToFetch, output = False)

    lastSyncedChangeset = lastChangeset
    with ReadOnlyWorktree(cfg.debug):
        try:
            for i, cs in enumerate(history):
                printLine()
                print('Fetching [%d/%d] "%s"...' % (i + 1, len(history), cs.line))
                fetch(cs.id)
                if not gitHasChanges():
                    print('From the Git\'s point of view, there is nothing new to commit in the changeset %s.' % cs.id)
                    print('Sometimes it happens with TFS branching.')
                    if not i:
                        repair(lastCommit, lastChangeset, cs.id)
                    print('An empty commit will be made.')
                print('Committing to Git...')
                comment = cs.comment
                if not comment:
                    print('The comment is empty. Using changeset number as a comment')
                    comment = str(cs.id)
                comment = comment.replace('"', '\\"')
                git('add -A .', dryRun = cfg.dryRun)
                git(r'commit --allow-empty -m "%s" --author="%s <%s@%s>" --date="%s"' % (comment, cs.committer, cs.committer, cfg.domain, cs.dateIso), output = True, dryRun = cfg.dryRun)
                git('notes add -m %s' % cs.id, dryRun = cfg.dryRun)
                lastSyncedChangeset = cs.id
        except:
            if not cfg.dryRun:
                print('Rolling back to the last synchronized changeset: %s' % lastSyncedChangeset)
                fetch(lastSyncedChangeset)
                git('reset --hard')
                git('clean -fd')
            raise
    return True
