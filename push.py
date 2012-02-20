#!/usr/bin/env python3
from core import *

def _push(app, hash, index, total):
    print()
    printLine()
    git('checkout ' + hash)
    print('Pushing [%d/%d] %s...' % (index + 1, total, git(r'log -1 --format="%h \"%s\""')))


    def rawDiff(changeType):
        return git('diff --raw --find-copies-harder HEAD^.. --diff-filter=%s' % changeType)

    def readChanges(changeType, displayChangeType):
        changes = [change[change.index('\t'):].strip().split('\t') for change in rawDiff(changeType).splitlines()]
        if changes:
            print(displayChangeType + ':')
            indentPrint([' -> '.join(f) for f in changes])
            yield changes

    def joinFiles(files):
        return '"' + '" "'.join(files) + '"'
    def joinChanges(changes):
        return ' '.join(map(joinFiles, changes))

    unknownChanges = rawDiff('TUX')
    if unknownChanges:
        print('Unexpected file change!!')
        print()
        indentPrint(unknownChanges)
        fail()

    def tfmut(args):
        tf(args, dryRun = app.dryRun)

    try:
        for c in readChanges('D', 'Removed'):
            tfmut('rm -recursive ' + joinChanges(c))
        for c in readChanges('M', 'Modified'):
            tfmut('checkout ' + joinChanges(c))
        for changes in readChanges('R', 'Renamed'):
            for files in changes:
                src, dest = files
                if not app.dryRun:
                    os.rename(dest, src)
                try:
                    tfmut('rename ' + joinFiles(files))
                except:
                    if not app.dryRun:
                        os.rename(src, dest)
                    raise
        for c in readChanges('CA', 'Added'):
            tfmut('add ' + joinChanges([files[-1:] for files in c]))

        print('Checking in...')
        comment = git('log -1 --format=%s%n%b').strip()
        checkin = tf('checkin "-comment:%s" -recursive . ' % comment, output = True, dryRun = app.dryRun and 'Changeset #12345')
    except:
        if not app.dryRun:
            print('Restoring Git and TFS state...')
            with ReadOnlyWorktree():
                tf('undo -recursive .', allowedExitCodes = [0, 100])
            git('checkout -f tfs')
        raise
    changeSetNumber = re.search(r'^Changeset #(\d+)', checkin, re.M).group(1)

    # add a note about the changeset number
    print('Moving tfs branch HEAD and marking the commit with a "tf" note')
    git('checkout tfs', dryRun = app.dryRun)
    git('merge --ff-only %s' % hash, dryRun = app.dryRun)
    git('notes add -m "%s" %s' % (changeSetNumber, hash), dryRun = app.dryRun)

def push(app):
    print('Pushing to TFS')
    lastCommit = git('log -1 --format=%H tfs')
    lastMasterCommit = git('log master --format=%H -1')
    unmergedCommits = git('log %s.. master --oneline' % lastMasterCommit)
    if unmergedCommits:
        print('You have unmerged changes in tfs branch:')
        indentPrint(unmergedCommits)
        fail()

    print('Last synchronized commit:', git('log -1 --format=%h tfs'))
    commits = git('log %s.. --format=%%H master --reverse --first-parent' % lastCommit).splitlines()
    commits = commits[:app.number]
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
        _push(app, hash, i, len(commits))

if __name__ == '__main__':
    App.run(push)