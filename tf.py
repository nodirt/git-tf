from util import *
import xml.etree.ElementTree as etree

git('--version', errorMsg = 'Git not found in $PATH variable')
tf = runner(git('config tf.cmd', errorValue = 'tf'))

def _history(args, echo = False):
  def parse(entry):
    id = entry.get('id')
    comment = entry.find('comment')
    comment = not comment is None and comment.text or ''
    committer = entry.get('committer').split('\\')[1].strip()
    date = parseXmlDatetime(entry.get('date')).ctime()
    line = ('%s %s %s %s' % (id, committer, date, comment)).strip()
    return {
      'id': id,
      'comment': comment,
      'committer': committer,
      'date': date,
      'line': line
    }

  args = 'history -recursive -format:xml %s .' % args
  history = etree.fromstring(tf(args, echo = echo))
  return [parse(changeset) for changeset in history if changeset.tag == 'changeset']

tf.history = _history