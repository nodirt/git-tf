from util import *
from fetch import fetch

def pull(cfg):
  if fetch(cfg):
    print('\nRebasing')
    git('checkout master', output = True)
    git('rebase tfs', output = True)
