.. include:: definitions.txt

.. contents::
   :class: pagetoc

.. _tutorial_console:

The compmake console
====================

|compmake| can be used both in batch mode (like make) and interactively with a
console. The console allows to inspect the status of the jobs, start/stop jobs,
set configuration, and other related tasks.

To use the batch mode, invoke |compmake| as ``$ compmake [MODULE] [COMMAND]``. 
If you do not specify a command, then you will enter the console mode.
For example, assuming that your module is called ``example.py``, you will
see:

.. literalinclude:: my_static/example1/prompt.txt

The |compmake| console is designed to be friendly. You can use auto-completion 
with ``<tab>``.
In the previous section, we discussed the commands ``make``, ``clean`` and ``list``.
Here we discuss several of the other most useful commands.
The complete list of the console commands is in the  section :ref:`commands`.

The ``help`` command
^^^^^^^^^^^^^^^^^^^^

If you write::

    @> help

you will see a list of all the available commands.
If you write::

    @> help <command>

you will see a description of the specified command. 
This is necessary because many commands can accept optional arguments.

This is the same information that you can find on the page :ref:`commands`.


The ``config`` command
^^^^^^^^^^^^^^^^^^^^^^^

To see all configuration switches, use::

    @> config 

To set a configuration switch, use::

    @> config <name> <value>

For example, the following command suppresses echoing of the 
jobs' stdout to the console::

    @> config echo_stdout False


Advanced console syntax
^^^^^^^^^^^^^^^^^^^^^^^

Most of |compmake|'s commands work on jobs and are invoked as "<command> <list of jobs>".
There are several shortcuts available to specify lists of jobs.

* **Wildcards.** In the previous section, we have seen the use of wildcards::

  	@> ls  *-drawing    # list all jobs that end with "-drawing"
  	@> ls  *            # list all jobs

* **Selection by state.** We can select jobs based on their computational state.
  (see :ref:`job_states` for a complete description of the meaning of these states)::

  	@> ls done         # list all completed jobs
  	@> ls failed       # list all failed jobs
  	@> ls blocked      # list all blocked jobs (dependencies failed)

* **Selection by function name**   ::

  	@> ls f1()        # all jobs that use the function f1()


* **Use of logical operator**. Compmake implements a simple syntax for 
  defining sets of jobs. Some examples The following commands::

 	@> ls not failed in func1()   # list all func1() instances that did not fail
 	@> ls *drawing except *p1=2*  # list those that match *drawing but not *p1=2*
 	@> ls all except job1 job2    # list all except "job1" and "job2"

 There are three keywords: ``in`` (intersection), ``except`` (set difference), and ``not``
 (complement). Their semantics are defined as follows. (Here, ``A`` and ``B`` are
 job lists)::

     [A] except [B]   ==  jobs in A that are not in B
     [A] in [B]       ==  jobs both in A and B
     not [A]          ==  all jobs except those in A 
                          (equivalent to "all except [A]")
     

* Go on to the next chapter :ref:`tutorial_embedding`.







