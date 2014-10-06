.. include:: definitions.txt

.. contents::
   :class: pagetoc

.. _tutorial_parmake:

Single-host multiprocessing
===========================


To use single-host multiprocessing, instead of using ``make``, simply use ``parmake``: ::

    @: parmake  [jobs]

Optionally, you can specify the number of processes to spawn: ::

    @: parmake n=11  [jobs]

If you don't specify a number, |compmake| will use the number of detected processors. 
If your jobs are IO-bound_ rather than CPU-bound_, you should specify a larger number. 

What's happening under the hood is that |compmake| spawns ``n`` workers thread using
the :py:mod:`multiprocessing` module. So be aware that each job will run in a different
process.


.. _IO-bound: http://en.wikipedia.org/wiki/I/O_bound

.. _CPU-bound: http://en.wikipedia.org/wiki/CPU_bound 



Troubleshooting problems
------------------------

|compmake| turns your original program into a parallel program. For you, it is almost as easy as it could ever get. However, there might be some issues to be aware about that are documented here.


Some libraries are picky
^^^^^^^^^^^^^^^^^^^^^^^^

Some libraries don't like to run in child processes. For example, ``matplotlib`` on OS X will complain and not work properly. The errors might mention ``exec()``. For example, this is thrown by ``matplotlib``: ::

	The process has forked and you cannot use this CoreFoundation functionality safely. You MUST exec().
	Break on __THE_PROCESS_HAS_FORKED_AND_YOU_CANNOT_USE_THIS_COREFOUNDATION_FUNCTIONALITY___YOU_MUST_EXEC__() to debug.

The solution is to divide your tasks in  processing tasks and visualization tasks. Use ``parmake`` to run the former group, and then run ``make`` for the latter.


Don't use shared state
^^^^^^^^^^^^^^^^^^^^^^

Remember that jobs run on different processes_ -- not threads_. This means that the global state (global module variables, etc.) is not share among the different processes.


.. _processes: http://en.wikipedia.org/wiki/Process_%28computing%29

.. _threads: http://en.wikipedia.org/wiki/Thread_%28computer_science%29


* Go on to the next chapter :ref:`tutorial_embedding`.
