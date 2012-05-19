#!/usr/bin/env python3
from core import *


class repair(Command):
    """Repair local TFS state, synchronize it with Git."""
    checkoutBranch = 'master'

    def initArgParser(self, parser):
        Command.initArgParser(self, parser)
        parser.addVerbose()

    def __enter__(self):
        self.switchBranch('master', True)
        self.checkStatus(checkGit=True, checkTfs=False)
        self.moveToRootDir()

    def _run(self):
        print('Restoring Git and TFS state...')
        if not tf.hasPendingChanges():
            print('It\'s OK')
            return
        with ReadOnlyWorktree():
            print('Clearing TFS pending changes...')
            tf('undo -recursive .', allowedExitCodes=[0, 100])
        git('checkout -f ' + self.checkoutBranch)


if __name__ == '__main__':
    repair().run()
