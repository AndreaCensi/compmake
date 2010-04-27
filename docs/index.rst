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








Tutorial
==================

Suppose that you have the typical program ``original.py``:

.. literalinclude:: example1/original.py
			
To use ``compmake``, modify each function call of interest by wrapping it with the ``comp()`` function.
It's easy: each fragment of the form::

   result = func1(params1)

becomes::

   result = comp(func1, params1)

In this example, the source code becomes (file ``using_compmake.py``)::

.. literalinclude:: example1/using_compmake1.py
	
This is all you have to do to take advantage of ``compmake``. 
Now, instead of running your program as::

	$ python original.py
	
use the syntax::

	$ compmake [MODULE] [COMMAND]

The following are some examples.

Running the computation (in series)
-----------------------------------

The command "make [jobs]" runs the computation in series::

	$ compmake example make

The command "parmake [jobs]" runs the computation in parallel::

	$ compmake --db=redis example parmake

Note that to use this feature, you should have installed ``redis``.

Diagnostics
-----------

The command "list" shows a list of the jobs with relative status.
If you run ::

	$ compmake example list 

before running ``make``, you will see an output similar to this:

.. literalinclude:: example1/list_before.txt

After running ``make``, the output will be:

.. literalinclude:: example1/list_after.txt


Prettier diagnostics
--------------------

There is a command "graph" that can produce a graphical depiction of the computation.
(to use this feature, you should have installed ``graphviz`` and the ``gvgen`` library)

If you run::

$ compmake my_program diagram

before running ``make`` you will see the following:

.. image:: example1/graph_before.png

The color grey means that the job has not started. After running ``make``, the output will be:

.. image:: example1/graph_after.png

Here, green means that the job is done.

The computation gra

Cleaning up
-----------

Use the command ``clean`` to clean::

	$ compmake my_program clean 




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





