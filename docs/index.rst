compmake
============
 
``compmake`` is ``make`` for batch python processes.

It is a non-obtrusive module that allows to add:

* ``make``--like facilities to your computations (``make all``, ``make clean``, ``remake target``)

* Automatic **caching** of the results.

* **parallelization** using the ``multiprocessing`` module.


Features and limitations
========================

Extended list of features
-------------------------

* Tolerant of failures: if one of the jobs fails, compmake will
  save the error (Exception) for further inspection, but still
  continues to do all the jobs it can complete.

* Two storage backends:
   * Filesystem based.
   * Network-base using Redis. Necessary for using the 
     multiprocessing module.

* (TODO) Tracking of the computation status (estimated time to go).
* (TODO) Curses-based interface

Limitations
-----------

.. attention:: There are some limitations that might limit this module  usefulness. Please read these carefully because it is really hard to work around them, without severely limiting the ``compmake`` experience.

### Computational graph should be fixed

The computational graph should not depend on the result of the computation.


### Input and ouput should be pickable 

All parameters and intermediate results should be pickable (i.e., serializable using the ``pickle`` module).

This rules out the use of lambda functions in the argument. 

For example, this is not supported::

	from compmake import comp
	
	f = lambda param: param * 2
	comp(f, 2)

If you google around, you'll see that this is a fundamental limitation
of the ``pickle`` module. You will have to write your lambda
as a top-level function::

	from compmake import comp

	def x(param): 
	  return param * 2
	
	comp(x, 2)








Simple example
--------------

Suppose that you have the typical program::

	from mycomputations import func1, func2, print_figures
	
	for param1 in [1,2,3,4,5,6]:
	    for param2 in [10,11,12,13,14]:
	        res1 = func1(param1)
	        res2 = func2(res1, param2)
			print_figures(res2)
			
This becomes the following::

	from mycomputations import func1, func2, print_figures
	from compmake import comp
	
	for param1 in [1,2,3,4,5,6]:
		for param2 in [10,11,12,13,14]:
			res1 = comp(func1, param1)
			res2 = comp(func2, res1, param2)
			comp(print_figures, res2)
	
If you run

$ compmake my_program diagram

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





