.. _tutorial1:

The compmake console, more about jobs
=====================================


Using the console
-----------------

Compmake can be used both in batch mode (like make) and interactively with a
console. The console allows to inspect the status of the jobs, manually
add some for execution, and related task.

To use the batch mode, invoke compmake as ``$ compmake [MODULE] [COMMAND]``. 
If you do not specify a command, then you will enter the console mode.
For example, assuming that your module is called ``example.py``, you will
see:

.. literalinclude:: example1/prompt.txt

The compmake console is designed to be friendly. You can use auto-completion 
with ``<tab>``. The complete list of the console commands is in the  section :ref:`commands`.

**``help``**

If you write::

    @> help

you will see a list of all the available commands.

This is the same information in the page :ref:`commands`.

**``make``, ``clean``**



**``list``**

In the console, you can see the status of the computation.
For example, the command "list" shows a list of the jobs with relative status.
If you run it before running ``make``, you will see an output similar to this:

.. literalinclude:: example1/list_before.txt

After running ``make``, the output will be:

.. literalinclude:: example1/list_after.txt



**``config``**

To show all configuration switches, use::

    @> config 

To set a configuration switch, use::

    @> config <name> <value>

For example, the following command suppresses echoing of the 
jobs' stdout to the console::


    @> config <name> <value>



TO WRITE

Advanced console usage
----------------------

