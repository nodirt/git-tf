#!/usr/bin/env python3
from core import *


class status(Command):
    """Display commits to be pushed to TFS."""

    def __enter__(self):
        self.moveToRootDir()
        self.switchBranch('master')

    def _run(self):
        commits = git('log tfs.. --format="%h %s" --first-parent').splitlines()
        if not commits:
            print('There are no commits to be pushed to TFS')
            return

        print('%d commit%s to be pushed to TFS:' % (len(commits), 's' if len(commits) > 1 else ''))
        for c in commits:
            printIndented(c)


if __name__ == '__main__':
    status().run()
