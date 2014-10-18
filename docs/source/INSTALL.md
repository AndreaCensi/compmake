
Installation notes for Linux / Ubuntu 14.04
===========================================

Necessary Dependency: readline
------------------------------

The ``readline`` dependency is the only nonobvious one. 

You need to install dependencies:

    sudo apt-get install build-essential libreadline-\* lib\*curses\*

And then use ``pip`` or ``easy_install`` to install the package:

    sudo easy_install readline

At this point this needs to succeed:

    python -c "import readline"

Optional dependency:  Sun Grid Engine
----------------------------------------------

There are some interesting [guides].

[guides]: http://scidom.wordpress.com/tag/parallel/

Important note: **before you install SGE**, make sure that the result of ``hostname`` is a fully qualified hostname:

    $ hostname
    mycomputer      # incorrect
    mycomputer.local # correct

Change permanently in ``/etc/hosts`` and ``/etc/hostname`` and reboot.
If you don't do this, SGE will not be correctly configured.

These are the packages needed in Ubuntu 14.04:

    sudo apt-get install gridengine-master gridengine-client gridengine-common gridengine-qmon gridengine-exec 

Make sure you give correct information when configuration dialogs pop up. 

Need to install xfonts for QMon GUI to work. Just install all xfonts:

    sudo apt-get install xfonts-\*

Add yourself as user:

    sudo qconf -ao andrea
    sudo qconf -am andrea

Add a submit host:

    sudo qconf -as thinkpad14.local
    
Add a queue using this: 

    sudo qconf -aq queue1

Note that you need to add more queues if you want multiple jobs executed.
For example, if you have 8 cores, you might want to add 7 queues.

Here's a simple script ``hello.sh`` to try:

    #!/bin/bash
    echo "Hello world" > /tmp/hello.txt

Try with:
    
    qsub hello.sh


Useful SGE commands
----------------

Look at the queue:

    watch qstat  

Delete all jobs:

    qdel -u <user>
