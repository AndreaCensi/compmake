.. _install:

Installation notes
==================

## Installing ``compmake``

	$ python setup.py install


The following are notes for the prerequisites:

## Installing prerequisites ##

Dependencies for parallel computation support
----------------------------------------------

For using the parallel version of compmake, you
should install the Redis server. 

The python interface to Redis can be installed using::

	$ easy_install redis

Note: we require version

``readline``

Other non-strictly necessary dependencies
------------------------------------------

The following Python packages are used if they are found, but they 
are not necessary.

* ``termcolor`` allows ``compmake`` to use colors. Do install it, it
  makes life more fun.::

  $ easy_install termcolor

* ``setproctitle`` will change the name of the process to a string 
  describing the current computation status. Useful to monitor 
  compmake using ``top``. (in Linux, press ``c`` to see the full command name.)::

  $ easy_install setproctitle


Software to generate dependency graphs
--------------------------------------

The command ``graph`` allows you to 

You have to have installed the python package ``gvgen`` from 
http://software.inl.fr/trac/wiki/GvGen

Moreover, you have to have installed ``graphviz``
http://www.graphviz.org/

