README
======
gitreminder.py

A tool that will scan through a filesystem path for git repositories and check
if they have uncommited files or if they have any branches that are not pushed
to the remote server yet.

Author:       Daniel Kurashige-Gollub

Date:         2013-02-07 (February, 7th, 2013)

Version:      0.0.1

Copyright:    Daniel Kurashige-Gollub, 2013

License:      GPLv3

COMMENT
-----
I have no time to finish this little script at the moment, so I just put it 
up on github.com/dgollub/gitreminder for the public. Maybe somebody else
finds it useful and is willing to put more time into it. 2013-03-19 Daniel

TODO/IDEAS
-----
- add ability to do everything automatically or by manually confirm each step
  (like --quiet or --assume-yes)
- add ability to ssh/sftp/scp a zipped version of the repository to a remote
  location
- add better error handling
- support Windows
- support setup.py / pip install / setuptools:
  http://guide.python-distribute.org/
- automated update mechanism for the script itself: updates itself from a
  defined url, comparing the version number and if the downloaded one is
  newer, than update (ask user to update, also present dialog with the
  CHANGES that were made)
- add support for local configuration file in ~/.gitreminder/gitreminder.conf
  (format should be in JSON)
- IMPORTANT: should really check ALL branches, not only the currently active
  one...

Please do not poisen the global namespace with global functions, instead use
a class with static or class functions. Thank you.
