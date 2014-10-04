
.. contents::
   :class: pagetoc

.. _`limitations`:

Limitations and assumptions
---------------------------

The goal of compmake is to be a friendly, compact, simple assistant
for batch operations. To keep simplicity and maintanability high,
you have to define very well the features that you want to have.

Therefore, there are some limitations that might limit compmake's usefulness to you. 
Please read these carefully, because it is hard to work around them.

If any of these really bother you, please discuss it on the mailing list
or the `issue tracker`_.

.. _`issue tracker`: http://github.com/AndreaCensi/compmake/issues


The computational layout is  fixed
+++++++++++++++++++++++++++++++++++

The computational layout should not depend on the result of the computation.
Compmake is organized on the basic idea that all the jobs are described at 
the beginning, loaded into memory, and then processed.

* If you need to conditionally add new jobs, compmake is not for you.
* If you have to process an infinite amount of jobs coming from outside, compmake is not for you.

However, you could probably dig into the internals and use (undocumented) functions
for adding and removing jobs.


All intermediate results are saved to disk/memory
+++++++++++++++++++++++++++++++++++++++++++++++++

* If you do not have enough disk space, compmake is not for you.

(this might be lifted in the future)


Input and ouput should be pickable 
++++++++++++++++++++++++++++++++++

All jobs' parameters and intermediate results should be "pickable", that is, serializable using the `pickle module`_.

This is not a problem in general; however, it rules out the use of lambda functions in the argument. 
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

.. _`pickle module`: http://docs.python.org/library/pickle.html


Assumptions for cluster operation
+++++++++++++++++++++++++++++++++

We assume the following:

* You know the IPs of the servers.
* You can do passwordless ssh logins on the server.
* You have installed compmake on the slaves.
* You have installed your software on the slaves in the system path.
* You got to have the power to use these redirects


