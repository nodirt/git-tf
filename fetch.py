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
        self.switchBranch()

    def _run(self):
        tf.getDomain()

        print('Fetching from TFS')

        try:
            lastChangeset = git.getChangesetNumber(fail=True)
            print('Last synchronized changeset:', lastChangeset)
        except:
            lastChangeset = None
            git.failNoLastChangeset()

        latestChangeset = tf.history(stopAfter=1)[0].id
        if self.args.verbose:
            print('Latest changeset on TFS:', latestChangeset)
        if lastChangeset == latestChangeset:
            print('Nothing to fetch')
            return False

        print('Requesting tf history %s..%s' % (lastChangeset, latestChangeset))
        history = tf.history(version=(lastChangeset, latestChangeset))
        history.reverse()
        history.pop(0)
        history = history[:self.args.number]

        self.doFetch(history)

    def doFetch(self, history):
        print('%d changeset(s) to fetch' % len(history))
        domain = tf.getDomain()
        dryRun = self.args.dryRun
        verbose = self.args.verbose

        with ReadOnlyWorktree(verbose):
            try:
                for i, cs in enumerate(history):
                    if verbose:
                        printLine()
                    print('Fetching [%d/%d] "%s"...' % (i + 1, len(history), cs.line))
                    tfgetResponse = tf.get(cs.id, dryRun=dryRun, output=verbose).strip()
                    if tfgetResponse == _allFilesUpToDate and not self.args.force:
                        print()
                        print('tf did not fetch anything. Usually it happens when the local folder contents is '
                              'different from what TFS expects.')
                        print('Try to repair tf state by retrieving an old changeset and then returning to this one')
                        print('Or use --force option if you are absolutely sure that the changeset didn\'t actually '
                              'change any files.')
                        fail()

                    if verbose:
                        print('Committing to Git...')
                    comment = cs.comment.strip() if cs.comment else None
                    if not comment:
                        if verbose:
                            print('The comment is empty. Using changeset number as a comment')
                        comment = str(cs.id)
                    comment = comment.replace('"', '\\"')
                    comment = comment.replace('$', '\\$')
                    git('add -A .', dryRun=dryRun)
                    commitArgs = r'commit --allow-empty -m "%s" --author="%s <%s@%s>" --date="%s"' % \
                                 (comment, cs.committer, cs.committer, domain, cs.dateIso)
                    git(commitArgs, output=verbose, dryRun=dryRun)
                    git('notes add -m %s' % cs.id, dryRun=dryRun)
                    if not verbose:
                        print('Commit:', git('log -1 --format=%h'))
            except:
                if not dryRun:
                    lastSyncedChangeset = git.getChangesetNumber()
                    if lastSyncedChangeset:
                        print('Rolling back to the last synchronized changeset: %s' % lastSyncedChangeset)
                        tf.get(lastSyncedChangeset, output=True)
                    git('reset --hard')
                    git('clean -fd')
                raise
        return True


if __name__ == '__main__':
    fetch().run()
