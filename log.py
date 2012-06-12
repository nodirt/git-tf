#!/usr/bin/env python3
from core import *
import datetime


class log(Command):
    """Show changeset log."""

    def _initArgParser(self, parser):
        Command._initArgParser(self, parser)
        parser.add_argument('gitArgs', nargs=argparse.REMAINDER,
            help='Similar to git <since>..<until>. Show only commits between the named two commits.')

    def log(self):
        gitArgs = ', '.join(map(lambda s: '\'' + s + '\'', self.args.gitArgs))

        endMarker = '</git.tf>'
        process = git.start('log {} --first-parent --format="%h\t%an\t%at\t%s%n%N%n{}"'.format(gitArgs, endMarker))
        for line in iter(process.readline, None):
            (commit, author, date, comment) = line.split('\t', 3)
            date = datetime.datetime.fromtimestamp(int(date)).strftime('%x %X')

            changeset = None
            for line in iter(process.readline, endMarker):
                if not changeset:
                    changeset = line.split(' ', 1)[0]

            comment = comment.replace('\n', ' ')
            line = '{:<7} {:<15} {:<23} {}'.format(changeset or commit, author, date, comment)
            maxLen = terminalWidth
            if len(line) > maxLen:
                line = line[:maxLen - 3] + '...'

            yield line

        if process.exitCode:
            process.fail()

    def _run(self):
        printLess(self.log())


if __name__ == '__main__':
    log().run()
