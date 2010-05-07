
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

Computational graph should be fixed
+++++++++++++++++++++++++++++++++++

The computational graph should not depend on the result of the computation.


All intermediate results are saved to disk/memory
+++++++++++++++++++++++++++++++++++++++++++++++++



Input and ouput should be pickable 
++++++++++++++++++++++++++++++++++

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





