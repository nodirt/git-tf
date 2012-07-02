#!/usr/bin/env python3
from core import *
import shutil
import re
import repair
import wi
import tempfile


class push(Command):
    """Push pending commits to TFS."""

    def _initArgParser(self, parser):
        parser.addVerbose()
        parser.addNoChecks()
        parser.addDryRun()
        parser.addNumber('maximum number of changesets to push')

    def __enter__(self):
        self.moveToRootDir()
        self.checkStatus()
        self.switchBranch()

    def _push(self, hash, index, total):
        dryRun = self.args.dryRun
        verbose = self.args.verbose

        git('checkout ' + hash)

        if verbose:
            print()
            printLine()
        print('Pushing [%d/%d] %s...' % (index + 1, total, git(r'log -1 --format="%h \"%s\""')))

        def rawDiff(changeType):
            return git('diff --raw --find-copies-harder HEAD^.. --diff-filter=%s' % changeType)

        def readChanges(changeType, displayChangeType):
            changes = [change[change.index('\t'):].strip().split('\t') for change in rawDiff(changeType).splitlines()]
            if changes:
                if verbose:
                    print(displayChangeType + ':')
                    printIndented([' -> '.join(f) for f in changes])
                yield changes

        def joinFiles(files):
            return '"' + '" "'.join(files) + '"'

        def joinChanges(changes):
            return ' '.join(map(joinFiles, changes))

        unknownChanges = rawDiff('TUX')
        if unknownChanges:
            print('Unexpected file change!!')
            print()
            printIndented(unknownChanges)
            fail()

        def tfmut(*args):
            tf(args, dryRun=dryRun)

        try:
            for c in readChanges('D', 'Removed'):
                tfmut('rm -recursive {}', joinChanges(c))
            for c in readChanges('M', 'Modified'):
                tfmut('checkout {}', joinChanges(c))
            for changes in readChanges('R', 'Renamed'):
                for files in changes:
                    src, dest = files
                    destDir = createDestDir = None
                    try:
                        if not dryRun:
                            destDir = os.path.dirname(src)
                            createDestDir = not os.path.exists(destDir)
                            if createDestDir:
                                mkdir(destDir, True)
                            os.rename(dest, src)
                        try:
                            tfmut('rename {}', joinFiles(files))
                            tfmut('checkout {}', files[1])
                        except:
                            if not dryRun:
                                os.rename(src, dest)
                            raise
                    finally:
                        if createDestDir:
                            shutil.rmtree(destDir)
            for c in readChanges('CA', 'Added'):
                tfmut('add {}', joinChanges([files[-1:] for files in c]))

            if verbose:
                print('Checking in...')
            comment = git('log -1 --format=%s%n%b').strip()
            workitems = git('notes --ref=%s show %s' % (wi.noteNamespace, hash), errorValue='')
            if workitems:
                workitems = '"-associate:%s"' % workitems
            with tempfile.NamedTemporaryFile('w') as tempFile:
                tempFile.file.write(comment)
                tempFile.file.close()
                checkin = tf(('checkin "-comment:@{}" -recursive {} .', tempFile.name, workitems),
                    allowedExitCodes=[0, 1],
                    output=verbose,
                    dryRun=dryRun and 'Changeset #12345')
            changeSetNumber = re.search(r'^Changeset #(\d+)', checkin, re.M)
            if not changeSetNumber:
                fail('Check in failed.')
            changeSetNumber = changeSetNumber.group(1)
            if not verbose:
                print('Changeset number:', changeSetNumber)
        except:
            if not dryRun:
                repairer = repair()
                repairer.checkoutBranch = 'tfs'
                repairer._run()
            raise

        # add a note about the changeset number
        if verbose:
            print('Moving tfs branch HEAD and marking the commit with a "tf" note')
        git('checkout tfs', dryRun=dryRun)
        git('merge --ff-only %s' % hash, dryRun=dryRun)
        git('notes add -m "%s" %s' % (changeSetNumber, hash), dryRun=dryRun)

    def _run(self):
        print('Pushing to TFS')
        lastCommit = git('log -1 --format=%H tfs')
        lastMasterCommit = git('log master --format=%H -1')
        unmergedCommits = git('log %s.. master --oneline' % lastMasterCommit)
        if unmergedCommits:
            print('You have unmerged changes in tfs branch:')
            printIndented(unmergedCommits)
            fail()

        if self.args.verbose:
            print('Last synchronized commit:', git('log -1 --format=%h tfs'))
        commits = git('log %s.. --format=%%H master --reverse --first-parent' % lastCommit).splitlines()
        commits = commits[:self.args.number]
        if not commits:
            print('Nothing to push')
            return

        print('Checking whether there are no unfetched changes on TFS...')
        ourLatestChangeset = git.getChangesetNumber(lastCommit, fail=True)
        theirLatestChangeset = tf.history(stopAfter=1)[0].id
        if int(ourLatestChangeset) < int(theirLatestChangeset):
            print('There are unfetched changes on TFS. Fetch and merge them before pushing')
            print('Latest local changeset:', ourLatestChangeset)
            print('Latest TFS changeset:', theirLatestChangeset)
            fail()

        print('%d commit(s) to be pushed:' % len(commits))

        for i, hash in enumerate(commits):
            self._push(hash, i, len(commits))


if __name__ == '__main__':
    push().run()
