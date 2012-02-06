git-tf
======

Features
--------

git-tf can do two basic things: fetch and push. In addition it can
pull, but it is just fetch+rebase. These three operations are enough
to work. I use git-tf everyday to do my job, it works reliable for me.
Most of my co-workers even don't know that I use git for work. I still
can enjoy such git features as stash, rebase, local branches, etc.

I didn't implement "git tf clone", so the initial
installation/configuration requires a lot of things to do, 
but once you do it, git-tf is easy to use:

1. You work in the master branch offline as you normally do with a
local git repository.

2. The tfs branch HEAD points to the git commit in the master branch
that is last synchronized with TFS. In some sense "tfs" branch is
analogous to "origin".

3. When you are ready to sync with the server, you first fetch or pull changes

    `$ git tf pull`
    
    This fetches each TFS changeset individually and commits to the tfs.
    Each commit is marked with a changeset it is associated with.

4. Then you push your local changes to TFS

    `$ git tf push`
    
    This pushes each your pending commit to the TFS. The list of pending 
    commits can be displays this way:
    
    `$ git log tfs..master`

git tf fetch, pull and push commands move the "tfs" branch HEAD. Each
git commit synchronized with TFS has a "git note" in the "tf"
namespace. Each note contains a TFS changeset number, a comment, a
user and date (currently git commit dates are different from tfs
changeset dates). To see tfs notes execute

    `$ git log --show-notes=tf`

Note that the commit pointed by "tfs" branch HEAD must always have a
note. Without it git-tf won't be able to sync.

Installation
------------

Download the files and make sure that git-tf is in the $PATH variable.
I usually have only a symbolic link to git-tf in the $PATH variable
and I recommend doing it this way.
Also make sure that git-tf files have the execution permission.

Normally you don't execute none of git-tf files directly. You access
git-tf by calling
    `$ git tf <command>`

### Team Explorer Anywhere installation

I use [.Team Explorer Anywhere](http://www.microsoft.com/download/en/details.aspx?displaylang=en&id=4240) to access TFS from a non-Windows OS (mine
is Ubuntu).

Once it is installed, you have to accept their EULA:
`$ tf eula`

It is a paid product, but you can use it for 180 days:
`$ tf productkey -trial`
The product key is stored at `~/.microsoft/Team Explorer/10.0/`

### TFS Configuration

Skip this section if you have already mapped a TFS server folder to a
local folder.

1. First of all you have to configure a [profile](http://msdn.microsoft.com/en-us/library/gg413276.aspx):

There is an example:

    $ tf profile -new MyProxyProfile \
    -string:serverUrl=http://tfs01.xyz.example.com \
    -string:userName=john \
    -string:userDomain=company \
    -string:password=password \
    -boolean:httpProxyEnabled=true \
    -string:httpProxyUrl=http://proxy01.xyz.example.com \
    -boolean:httpProxyEnableAuth=true \
    -string:httpProxyUsername=john \
    -string:httpProxyPassword=proxy_password \
    -boolean:tfProxyEnabled=true \
    -string:tfProxyUrl=http://tfproxy01.xyz.example.com \
    -boolean:acceptUntrustedCertificates=true

Make sure that acceptUntrustedCertificates is set to true if you have
a secure connection (https). I wasted a lot of time trying to fix it.
Keep in mind that you must scape any character that your shell may
interpret (like a space) in double quotes.

2. Then you should create a [workspace](http://msdn.microsoft.com/en-us/library/y901w7se(v=vs.80).aspx).
Example:
    $ tf workspace -new -collection:http://tfs01.xyz.example.com MyWorkspace

3. Then you finally map a server folder
    $ tf workfold -map -workspace:MyWorkspace $/MyProject/Main ~/projects/myProject

GIT Configuration
-----------------

To start using git-tf you should have a git commit corresponding to a
TFS changeset. The changeset is not required to be latest changeset.
If loosing your git change history, and download it from TFS is
acceptable, then do the following:

1. Download the TFS changeset you would like your git history to start
from. For example, you want to fetch history starting from 12345:
    $ tf get -version:C12345 -recursive .

2. Init a git repository and commit the fetched files
    $ git init
    $ git commit -am "Initial commit"

3. Mark the commit with a note
    $ git notes --ref=tf add -m "12345"

4. Configure git-tf. Example:
    $ git config tf.username john
    $ git config tf.domain mycompany.com
    $ git config tf.winDomain MYCOMPANY

Yes, two domains sounds weird, but that's how TFS works. The first
domain is what is written after @ sign: john@company.com.
The second domain is your full name on TFS: MYCOMPANY\john
Perhaps I'll get rid of the second domain in some future.

There is also a `tf.cmd` config value with which you can override the default
call to the Team Explorer Anywhere executable. This can by usefull to configure
the authentication for your TFS connection.

For example:
    $ git config tf.cmd 'tf -profile:MyProxyProfile'

Details [here.](http://msdn.microsoft.com/en-us/library/hh190726.aspx)

The configuration is complete. Now you can fetch the remaining changesets

    $ git tf fetch

Be patient. TFS works way slower than Git.

### DO NOT MERGE

Never use `git merge tfs` on master if you have called `fetch` instead
of `pull`. You should always rebase:

    # on branch master
    $ git rebase tfs

Rebase is similar to merge, but instead of applying "their" changes on
your changes, it applies your changes on their changes.

If you use merge, you will screw your TFS history up when you push and
your co-workers won't be happy.

Contact me
----------

Feel free to contact me via Gtalk (turakulov@gmail.com) if anything goes wrong.

-Nodir
