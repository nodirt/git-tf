#!/usr/bin/env python3
from core import *

noteNamespace = 'tf.wi'


class wi(Command):
    """Associate a commit with a TFS workitem."""

    def argParserCtorArgs(self):
        args = Command.argParserCtorArgs(self)
        args['epilog'] = """

Examples:

Associate workitems 123 and 456 with a HEAD commit:
    $ git tf wi 123
    $ git tf wi 456

Show associated workitems:
    $ git tf wi
    123,456

Remove workitem 123 association:
    $ git tf wi -d 123

Remove all workitem associations:
    $ git tf wi -d
        """
        return args

    def _initArgParser(self, parser):
        parser.addVerbose()
        parser.add_argument('-c', '--commit', default='HEAD',
            help='commit to associate with. Defaults to HEAD.')

        parser.add_argument('-d', '--delete', action='store_true',
            help='Remove work item association.')
        parser.add_argument('workitem', type=int, nargs='?',
            help='Workitem ID')

    def _run(self):
        args = self.args

        def notes(noteArgs, **kwargs):
            gitArgs = 'notes --ref=%s %s %s' % (noteNamespace, noteArgs, args.commit)
            return git(gitArgs, **kwargs)

        def add(note):
            notes('add -fm "%s"' % note)

        note = notes('show', errorValue='')

        if args.delete:
            if not note:
                return
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
