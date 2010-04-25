``compmake``
============

__What is compmake?__ ``compmake`` is ``make`` for computational processes.
It is a nonobtrusive module that allows to add:
1) ``make``--like facilities to your computations (``make all``, ``make clean``, ``remake target``)
2) Caching of the computational results.
3) **parallelization** using the ``multiprocessing`` module.


Extended list of features
-------------------------
3) Tolerant of failures: if one of the jobs fails, compmake 
3) (TODO) Tracking of the computation status (estimated time to go).
4) (TODO) Curses-based interface
5) Two storage backends:
 * filesystem based
 * Network-base using Redis. Necessar

### How does it look like?

Suppose that you have the typical program::

	from mycomputations import func1, func2, print_figures
	
	for param1 in [1,2,3,4,5,6]:
		for param2 in [10,11,12,13,14]:
			res1 = func1(param1)
			res2 = func2(res1, param2)
			print_figures(res2)
			
This becomes the following::

	from mycomputations import func1, func2, print_figures
	from compmake import comp, interpret_commands
	
	for param1 in [1,2,3,4,5,6]:
		for param2 in [10,11,12,13,14]:
			res1 = comp(func1, param1)
			res2 = comp(func2, res1, param2)
			comp(print_figures, res2)
	
	interpret_commands(sys.argv[1:])
	
If you run

$ python my_program diagram

you will see the following:

.. image:: example1/picture.png



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




