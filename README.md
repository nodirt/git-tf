git-tf - basic two-way bridge between TFS and Git
=================================================

Features
--------

git-tf can do two basic things: `fetch`/`pull` and `push`. These  operations are enough to work. 

git-tf works transparently. Other TFS users may not even know, that you use Git. 

Here is the typical git-tf usage workflow:

1. You work in the master branch offline as you normally do with a
local git repository. You can stash, rebase, make local branches, etc.

3. When you are ready to sync with the server, you first `fetch` or `pull` changes.
   
        $ git tf pull
   
    This retrieves each TFS changeset individually and commits them into the _tfs_ branch.
    Each commit is marked with a changeset number.

    If you used `fetch`, then `git rebase` your changes instead of merging. It is **important**, see below.

4. Then you `push` your local changes to TFS
   
        $ git tf push
    
    This sends each of your pending commits to the TFS individually. To see the list of pending
    commits use `$ git log tfs..` while you are on _master_ branch,

`clone` is not implemented yet, so the initial installation/configuration is manual.

How it works
------------

The _tfs_ branch HEAD points to the git commit in the _master_ branch
that is last synchronized with TFS. In some sense _tfs_ branch is
analogous to _origin_.

Each git commit synchronized with TFS has a [git note](http://schacon.github.com/git/git-notes.html) in the _tf_
namespace. Each note has a TFS changeset number. To see the notes execute

    $ git log --show-notes=tf

The commit pointed by _tfs_ branch HEAD must always have a note. Without it git-tf won't be able to sync.

`fetch`, `pull` and `push` commands move the _tfs_ branch.

Installation
------------

Download the files and make sure that git-tf is in the $PATH variable.
I usually have only a symbolic link to git-tf in the $PATH variable
and I recommend doing it this way.
Also make sure that git-tf files have the execution permission.

Normally you don't execute none of git-tf files directly. You access
git-tf by calling

    $ git tf <command>

### Team Explorer Anywhere installation

[Team Explorer Anywhere](http://www.microsoft.com/download/en/details.aspx?displaylang=en&id=4240) is
a cross-platform client for TFS.

Once it is installed, you have to accept their EULA:

    $ tf eula

It is a paid product, but you can use it for 180 days:

    $ tf productkey -trial

The product key is stored at _~/.microsoft/Team Explorer/10.0/_

### TFS Configuration

Skip this section if you have already mapped a TFS server folder to a local folder.

1. Configure a [profile](http://msdn.microsoft.com/en-us/library/gg413276.aspx):
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
   
   Make sure that _acceptUntrustedCertificates_ is set to _true_ if you have
   a secure connection (https). Keep in mind that you must escape any character that your shell may
   interpret (like space) in double quotes.

2. Create a [workspace.][msdnWorkspace]

        $ tf workspace -new -collection:http://tfs01.xyz.example.com MyWorkspace

3. Map a server folder to a local folder:
   
        $ tf workfold -map -workspace:MyWorkspace $/MyProject/Main ~/projects/myProject

GIT Configuration
-----------------

To start using git-tf you should have a git commit corresponding to a
TFS changeset. The changeset is not required to be latest changeset.
If loosing your git change history, and downloading it from TFS is
acceptable, then do the following:

1. Get the version from TFS that you would like your git history to start
from. For example, you want to fetch history starting from 12345:
   
        $ tf get -version:C12345 -recursive .

2. Init a git repository and commit the fetched files
   
        $ git init
        $ git commit -am "Initial commit"

3. Mark the commit with a note
   
        $ git notes --ref=tf add -m "12345"

4. Configure git-tf. Example:
   
        $ git config tf.domain mycompany.com

5. Set _tfs_ branch as an upstream branch for _master_.

        $ git branch --set-upstream master tfs

There is also a _tf.cmd_ config value with which you can override the default
call to the Team Explorer Anywhere executable. This can by usefull to configure
the authentication for your TFS connection.

For example:

    $ git config tf.cmd 'tf -profile:MyProxyProfile'

Details are [here](http://msdn.microsoft.com/en-us/library/hh190726.aspx).

The configuration is complete. Now you can fetch the remaining changesets

    $ git tf fetch

Be patient. TFS works way slower than Git.

DO NOT MERGE
------------

Never use `git merge tfs` on master if you have called `fetch` instead
of `pull`. You should always rebase:

    # on branch master
    $ git rebase tfs

Rebase is similar to merge, but instead of applying _their_ changes on
your changes, it applies your changes on _their_ changes.

If you use merge, you will screw your TFS history up when you push and
your team won't be happy.

[msdnWorkspace]: http://msdn.microsoft.com/en-us/library/y901w7se(v=vs.80).aspx
