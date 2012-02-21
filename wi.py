#!/usr/bin/env python3
from core import *

noteNamespace = 'tf.wi'

class wi(Command):
    """Associate a commit with a TFS workitem."""

    def __enter__(self):
        self.moveToRootDir()
        pass

    def _initArgParser(self, parser):
        # group = parser.add_mutually_exclusive_group()
        parser.add_argument('-c', '--commit', default='HEAD',
            help='commit to associate with. Defaults to HEAD.')

        parser.add_argument('-d', '--delete', action='store_true',
            help='Remove work item association.')
        parser.add_argument('workitem', type=int, nargs='?',
            help='Workitem number')


    def _run(self):
        args = self.args

        def notes(noteArgs, **kwargs):
            gitArgs = 'notes --ref=%s %s %s' % (noteNamespace, noteArgs, args.commit)
            return git(gitArgs, **kwargs)
        def add(note):
            notes('add -fm "%s"' % note)

        note = notes('show', errorValue='')

        if args.delete:
            if not note: return
            workitem = args.workitem
            if workitem:
                items = note.split(',')
                try:
                    items.remove(str(workitem))
                except ValueError:
                    fail('Workitem %s is not associated with %s' % (workitem, args.commit))
                if items:
                    add(','.join(items))
                    return
            notes('remove')

        elif args.workitem:
            if note:
                note += ','
            add(note + str(args.workitem))
        elif note:
            print(note)

if __name__ == '__main__':
    wi().run()