#!/usr/bin/env python3
from core import *
import re

_allFilesUpToDate = 'All files up to date.'


class fetch(Command):
    """Fetch changes from TFS to Git without merging."""

    def _initArgParser(self, parser):
        parser.addVerbose()
        parser.addNoChecks()
        parser.addForce('make an empty commit when tf responds "%s". Use with caution!' % _allFilesUpToDate)
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

        with ReadOnlyWorktree(self.args.verbose):
            try:
                for i, cs in enumerate(history):
                    printLine()
                    print('Fetching [%d/%d] "%s"...' % (i + 1, len(history), cs.line))
                    tfgetResponse = tf.get(cs.id, dryRun=dryRun, output=True).strip()
                    if tfgetResponse == _allFilesUpToDate and not self.args.force:
                        print()
                        print('tf did not fetch anything. Usually it happens when the local folder contents is '
                              'different from what TFS expects.')
                        print('Try to repair tf state by retrieving an old changeset and then returning to this one')
                        print('Or use --force option if you are absolutely sure that the changeset didn\'t actually '
                              'change any files.')
                        fail()

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
