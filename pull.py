from util import *
from fetch import fetch

def pull(cfg):
  if fetch(cfg) or git('log master..tfs'):
    print('\nRebasing')
    git('checkout master', output = True)
    git('rebase tfs', output = True)
