git-tf - simple two-way bridge between TFS and Git
==================================================

Features
--------

*   Synchronizes Git commits with TFS changesets and vice versa.
*   One-to-one changeset-commit correspondence.
*   Works transparently. Other TFS users may not even know that you use Git.
*   TFS Workitem support: `git tf wi`.
*   Displays TFS-styled history with changeset numbers instead of commit hashes: `git tf log`.

### Usage workflow

Here is the typical git-tf usage workflow:

1.  You work in the master branch offline as you normally do with a
local git repository. You can stash, rebase, make local branches, bisect, etc. No need to checkout a file before editing.

2.  If a commit is associated with a TFS workitem, you use `wi` command to mark the commit:

        $ git tf wi 1234

    This marks the HEAD commit with the workitem 1234.

3.  When you are ready to sync with the server, you first `fetch` or `pull` changes.
   
        $ git tf pull
   
    This retrieves each TFS changeset individually and commits them into the _tfs_ branch.
    Each commit is marked with a changeset number.

    If you used `fetch`, then `git rebase` your changes instead of merging. It is **important**, see below.

4.  Then you `push` your local changes to TFS
   
        $ git tf push
    
    This sends each of your pending commits to TFS individually. If a commit was associated with workitems,
    then the created changeset is associated with them automatically.

    To see the list of pending commits use `$ git tf status` while you are on _master_ branch.

How it works
------------

The _tfs_ branch points to the git commit in the _master_ branch
that is last synchronized with TFS. In some sense _tfs_ branch is
analogous to _origin_.

Each git commit synchronized with TFS has a [git note](http://schacon.github.com/git/git-notes.html) in the _tf_
namespace. Each note has a TFS changeset number. To see the notes run

    $ git log --show-notes=tf

Associated workitems IDs are stored in the _tf.wi_ note namespace.

The commit pointed by _tfs_ branch must always have a note. Without it git-tf won't be able to sync.

`fetch`, `pull` and `push` commands move the _tfs_ branch.

Installation
------------

Download the files and make sure that git-tf is in the _PATH_ variable.
I usually have only a symbolic link to git-tf in the _PATH_ variable
and I recommend doing it this way.
Also make sure that git-tf files have the execution permission.

Normally you don't execute none of git-tf files directly. You access
git-tf by calling

    $ git tf <command>

### Team Explorer Anywhere installation

[Team Explorer Anywhere](http://www.microsoft.com/download/en/details.aspx?displaylang=en&id=4240) is
a cross-platform client for TFS.

Once it is installed, you have to accept their EULA:

    $ tf eula -accept

It is a paid product, but you can use it for 180 days:

    $ tf productkey -trial

The product key is stored at _~/.microsoft/Team Explorer/10.0/_

TFS Configuration
-----------------

Skip this section if you have already mapped a TFS server folder to a local folder.

1.  Configure a [profile](http://msdn.microsoft.com/en-us/library/gg413276.aspx). 

        $ tf profile -new myProfile \
        -string:serverUrl=http://tfs01.xyz.example.com \
        -string:userName=john \
        -string:userDomain=company \
        -string:password=password \
        -boolean:acceptUntrustedCertificates=true
   
   Make sure that _acceptUntrustedCertificates_ is set to _true_ if you have
   a secure connection (https).

2.  Create a [workspace.][msdnWorkspace]

        $ tf workspace -new -profile:myProfile -collection:http://tfs01.xyz.example.com MyWorkspace

3.  Map a server folder to a local folder:
   
        $ tf workfold -map -workspace:MyWorkspace $/MyProject/Main ~/projects/myProject

Cloning a TFS repository
------------------------

Once you have a local folder mapped to a server folder, you can use `clone`:

    $ git tf clone -e yourName@tfsServer.com --all

This will import the entire change history from TFS to Git.
Be patient. TFS works way slower than Git.

###Changesets to fetch

There are four ways to specify what changesets to fetch:

1. By default only the latest changeset is fetched
2. `--all` option: fetch the entire TFS history
3. `--number` option: fetch a specified number of changesets
4. `--version` option: fetch changesets since the specified version

###Line endings

Since the majority of TFS users are on Windows, the `core.autocrlf` is set to true by default.
To change that set `tf.clone.autocrlf` config value to false globally before cloning:

    $ git config --global tf.clone.autocrlf false

DO NOT MERGE
------------

Never use `git merge tfs` on _master_ if you have used `fetch` instead
of `pull`. You should always `rebase`:

    # on branch master
    $ git rebase tfs

`rebase` is like `merge`, but instead of applying _their_ changes on
your changes, it applies your changes on _their_ changes.

If you use `merge`, you will screw your TFS history up when you `push` and
your team won't be happy.

Mailing list
--------
...is [here](https://groups.google.com/group/git-tf)

[msdnWorkspace]: http://msdn.microsoft.com/en-us/library/y901w7se(v=vs.80).aspx
