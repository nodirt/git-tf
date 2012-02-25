#!/usr/bin/env python3
from core import *
from fetch import fetch


class pull(fetch):
    """Fetch and merge changes from TFS to Git."""

    def _run(self):
        if fetch._run(self) or git('log master..tfs'):
            print('\nRebasing')
            git('checkout master', output=True)
            try:
                git('rebase tfs', output=True)
            except:
                print('There were errors while rebasing TFS changes on the master.')
                print('Please resolve the conflicts.')
                raise


if __name__ == '__main__':
    pull().run()
