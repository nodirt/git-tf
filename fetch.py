#!/usr/bin/env python3
from core import *
import re


class fetch(Command):
    """Fetch changes from TFS to Git without merging."""

    def _initArgParser(self, parser):
        parser.addVerbose()
        parser.addNoChecks()
        parser.addDryRun()
        parser.addNumber('maximum number of changesets to fetch')

    def __enter__(self):
        self.moveToRootDir()
        self.checkStatus()
        self.switchToTfsBranch()

    def _run(self):
        domain = tf.getDomain()
        dryRun = self.args.dryRun

        print('Fetching from TFS')

        try:
            lastChangeset = git.getChangesetNumber()
            print('Last synchronized changeset:', lastChangeset)
        except:
            lastChangeset = None
            fail('Last changeset could not determined. Probably the last commit is missing a tf note. Commit: %s' %
                 git('log -1 --format=%H tfs'))

        latestChangeset = tf.history(stopAfter=1)[0].id
        print('Latest changeset on TFS:', latestChangeset)
        if lastChangeset == latestChangeset:
            print('Nothing to fetch')
            return False

        print('Requesting tf history %s..%s' % (lastChangeset, latestChangeset))
        history = tf.history(version=(lastChangeset, latestChangeset))
        history.reverse()
        history.pop(0)
        history = history[:self.args.number]

        print('%d changeset(s) to fetch' % len(history))

        def repair(changesetToFetch):
            lastCommit, lastChangeset = git('log -1 --format=%h%n%N').strip().splitlines()
            print('But it may mean we have a problem, so let\'s check it.')
            print('Trying to fetch the previous changeset and repeat...')
            tf.get(lastChangeset, dryRun=dryRun)

            if git.hasChanges():
                print('git-tf state is corrupted: the commit %s was expected to match changeset %s.' %
                      (lastCommit, lastChangeset))
                print('You can try to "git reset" to a non-corrupted commit and fetch/pull again.')
                unpushed = git('log tfs..master --oneline')
                if unpushed:
                    print('You have unpushed commits:')
                    printIndented(unpushed)
                    print('Cherry-pick them when you finish repairing.')
                fail()

            print('No, there is no problem. Now fetching %s again...' % changesetToFetch)
            tf.get(changesetToFetch, dryRun=dryRun)

        with ReadOnlyWorktree(self.args.verbose):
            try:
                for i, cs in enumerate(history):
                    printLine()
                    print('Fetching [%d/%d] "%s"...' % (i + 1, len(history), cs.line))
                    tf.get(cs.id, dryRun=dryRun, output=True)
                    if not git.hasChanges():
                        print('From the Git\'s point of view, there is nothing new to commit in the changeset %s.' % \
                              cs.id)
                        print('Sometimes it happens with TFS branching.')
                        if not i:
                            repair(cs.id)
                        print('An empty commit will be made.')
                    print('Committing to Git...')
                    comment = cs.comment
                    if not comment:
                        print('The comment is empty. Using changeset number as a comment')
                        comment = str(cs.id)
                    comment = comment.replace('"', '\\"')
                    git('add -A .', dryRun=dryRun)
                    commitArgs = r'commit --allow-empty -m "%s" --author="%s <%s@%s>" --date="%s"' % \
                                 (comment, cs.committer, cs.committer, domain, cs.dateIso)
                    git(commitArgs, output=True, dryRun=dryRun)
                    git('notes add -m %s' % cs.id, dryRun=dryRun)
            except:
                if not dryRun:
                    lastSyncedChangeset = git.getChangesetNumber()
                    print('Rolling back to the last synchronized changeset: %s' % lastSyncedChangeset)
                    tf.get(lastSyncedChangeset, output=True)
                    git('reset --hard')
                    git('clean -fd')
                raise
        return True


if __name__ == '__main__':
    fetch().run()
