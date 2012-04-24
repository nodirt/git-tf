#!/usr/bin/env python3
import os
import re
from core import *
from fetch import fetch
import shutil

emailRgx = r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b'


class clone(Command):
    """Clone a TFS repository."""

    def __init__(self):
        self.fetch = fetch()
        Command.__init__(self)

    def _initArgParser(self, parser):
        parser.addVerbose()
        parser.addNoChecks()

        ver = parser.add_mutually_exclusive_group()
        ver.add_argument('-V', '--version', default='',
            help='first changeset. Defaults to the latest.')
        ver.add_argument('-A', '--all', action='store_true',
            help='Fetch the entire history. Slow.')

        parser.add_argument('-e', '--email',
            help='email for TFS')

    def _run(self):
        if git('status -s', errorValue='', allowedExitCodes=[1]):
            print('A Git repository already exists')
            if git.getChangesetNumber():
                print('If you tried to clone but it failed, try to continue by calling pull or fetch')
                printIndented('$ git tf pull')
            fail()

        print('Determining the TFS workspace and folder mapping...')
        workfold = tf('workfold .')

#        def getSetting(name):
#            rgx = r'^{}:\s+(\S.+)$'.format(name)
#            m = re.search(rgx, workfold, re.M)
#            if not m:
#                print('Could not determine ' + name)
#                print('"tf workfold ." command output:')
#                printIndented(workfold)
#                fail()
#            return m.groups()
#        workspace = getSetting('Workspace')
#        collection = getSetting('Collection')
        pwd = os.path.abspath('.')
        folderMaps = re.findall('^\s*(\$[^:]+): (\S+)$', workfold, re.M)
        serverRoot, localRoot = [(s, l) for s, l in folderMaps if os.path.commonprefix((l, pwd)) == l][0]
        if localRoot != pwd:
            print('You must be in the mapped local folder to use "git tf clone":')
            printIndented(localRoot)
            fail()

        self.checkStatus(checkGit=False)

        git('init')
        git('config core.autocrlf true')

        try:
            # Email
            def checkEmail(email):
                if not re.match(emailRgx, email, flags=re.I):
                    fail('Malformed email: ' + email)

            email = self.args.email
            if email:
                checkEmail(email)
                git('config user.email ' + email)
                git('config user.name ' + email.split('@', 1)[0])
            else:
                email = git('config user.email', errorMsg='Email is not specified')
                checkEmail(email)
                if self.args.verbose:
                    print('Email is not specified, so using ', email)

            # Branches
            git('commit --allow-empty -m root-commit')
            git('branch -f tfs')
            git('branch --set-upstream master tfs')
            git('checkout tfs')

            # History
            if self.args.all:
                print('Requesting for the entire TFS history...')
                history = tf.history()
            else:
                print('Determining the latest version...')
                history = tf.history(stopAfter=1)
                if history:
                    latest = history[0]
                    version = self.args.version
                    if version:
                        print('Requesting for TFS history since', version)
                        history = tf.history(version=(version, latest.id))
                    else:
                        print('Version is not specified, so using the latest version...')
                        history = [latest]

            if not history:
                print('Nothing to fetch')
            else:
                history.reverse()

                # Fetch
                try:
                    self.args.force = True
                    self.fetch.args = self.args
                    self.fetch.doFetch(history)
                finally:
                    git('checkout master')
                    git('reset --hard tfs')
        except:
            if git('notes show', errorValue=False) is False:
                shutil.rmtree('.git')
            raise

        print()
        print('Cloning is completed. Try "git tf log" to see the change history.')

if __name__ == '__main__':
    clone().run()
