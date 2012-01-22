from util import *
import xml.etree.ElementTree as etree

git('--version', errorMsg = 'Git not found in $PATH variable')
tf = runner(git('config tf.cmd', errorValue = 'tf'))

class Changeset(object):
  def __init__(self, node):
    self.id = node.get('id')
    self.comment = node.find('comment')
    self.comment = self.comment is not None and self.comment.text or ''
    self.dateIso = node.get('date')
    self.date = parseXmlDatetime(self.dateIso)
    self.committer = node.get('committer').split('\\', 1)[-1].strip()
    self.line = ('%s %s %s %s' % (self.id, self.committer, self.date.ctime(), self.comment)).strip()

def _history(args):
  args = 'history -recursive -format:xml %s .' % args
  history = etree.fromstring(tf(args))
  return [Changeset(cs) for cs in history if cs.tag == 'changeset']

tf.history = _history
