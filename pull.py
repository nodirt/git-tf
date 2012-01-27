from util import *
from fetch import fetch

def pull(cfg):
  if fetch(cfg) or git('log master..tfs'):
    print('\nRebasing')
    git('checkout master', output = True)
    try:
      git('rebase tfs', output = True)
    except:
      print('There were errors while rebasing TFS changes on the master.')
      print('Please resolve the conflicts.')
      raise
