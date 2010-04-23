``compmake``
============

__What is compmake?__ ``compmake`` is ``make`` for computational processes.
It is a nonobtrusive module that allows to add:
1) ``make``--like facilities to your computations (``make all``, ``make clean``, ``remake target``)
2) Caching of the computational results.
3) Tracking of the computation status (estimated time to go).
3) **parallelization** using the ``multiprocessing`` module.

### How does it look like?

	from compmake import comp
	
	


The computation gra

Download
------------

Installation
------------

## Installing prerequisites ##

For using the parallel version of compmake, you
should install the Redis server. The python interface to Redis can be installed using::

	$ easy_install redis

Note: we require version

## Installing ``compmake``

	$ python setup 




Limitations
-----------

1) The computational graph should not depend on the result of the computation.

2) Input and ouput should be pickable(). This rules out the use of 
	lambda functions in the argument. 


