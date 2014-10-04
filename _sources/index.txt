.. raw:: html
   :file: index-fork.html

..
    .. container:: twitterbadge

       **Latest news**

       .. raw:: html
          :file: twitter_badge.html

.. include:: definitions.txt

Compmake: keep calm and carry on
================================

.. raw:: html
   :file: index-logo.html

.. container:: intro

  |compmake| is a non-obtrusive module that provides Makefile--like facilities to your Python computations, including:

  * **Familiar commands** such as ``make``, ``clean``, etc.

  * Zero-effort **parallelization**.

  * **Caching** of temporary results: you can interrupt your program (CTRL-C), and restart it without losing what was already computed.

  * A **console** for inspecting failures and partial completion.

  |compmake| has been designed primarily for handling long computational-intensive
  batch processes. 
  You can use |compmake| to gain considerable peace of mind. Read :ref:`why`.


Installation
------------------

The simplest way to install |compmake| is::

$ easy_install compmake

or, alternatively, using ``pip install compmake``. You can also `fork the project on GitHub`_.

.. _`fork the project on GitHub`: http://github.com/AndreaCensi/compmake

.. 
  .. raw:: html
     :file: download.html

.. 
    This will allow you to run |compmake| on a single host.
    However, there are also separate dependencies to install for some
    advanced features such as multiprocessing. See :ref:`install` for more information.

Basic usage
------------

To use |compmake|, you have to minimally modify your Python program,
such that it can understand the processing layout and
the opportunities for parallelization.

.. image:: my_static/initial.png 
   :class: bigpicture

Download `a demo example.py`_ that you can try.

.. _`a demo example.py`: static/demos/example.py

You would run the modified program using::

    $ python example 

This gives you a prompt: ::
  
  compmake 3.2   ``Keep calm and carry on,,
  Welcome to the compmake console. (write 'help' for a list of commands)
  27 jobs loaded.
  @:

Run "parmake" at the prompt: ::
  
  @: make


**Parallel execution**: To run jobs in parallel, use the ``parmake`` command::

  @: parmake n=6  # runs at most 6 in parallel

.. There are all sorts of configuration options for being nice to other
.. users of the machine; for example, Compmake can be instructed  
.. not to start other jobs if the CPU or memory usage is already above a certain 
.. percentage
..     $ compmake --max_cpu_load=50 --max_mem_load=50 example -c "clean; parmake"

..

**Selective re-make**: You can selectively remake part of the computations. For example,
suppose that you modify the ``draw()`` function, and you want to
rerun only the last step. You can achieve that by::

    @: remake draw*

|compmake| will reuse part of the computations (``func1`` and ``func2``)
but it will redo the last step.

**Failure tolerance**: 
If some of the jobs fail (e.g., they throw an exception),
compmake will go forward with the rest. 

To try this behavior, download the file `example_fail.py`_. If you run::

    $ python example_fail.py "parmake n=4"

you will see how compmake completes all jobs that can be completed. If you run again::

    $ python example_fail.py "make"

Compmake will try again to run the jobs that failed.

.. _`example_fail.py`: static/demos/example_fail.py


Feedback
---------

Please use the `issue tracker on github`_ for bugs and feature requests.

.. _`issue tracker on github`: http://github.com/AndreaCensi/compmake/issues

.. _`Andrea Censi`: http://purl.org/censi/web


.. **Note**: |compmake| is currently a **beta release**:
.. while most of the functionality is there,
.. the documentation is not complete,
.. it is a bit rough around the edges,
.. and some minor aspects of the API could change in the future.
.. If you feel adventorous, this is a perfect time to
.. get support and influence |compmake|'s evolution!

Documentation
-------------

Still unsure you need this?  Read :ref:`why`.
And check out :ref:`limitations` to see if |compmake| can help you.

Still interested? Start with the tutorial :ref:`tutorial_basic`.


.. container:: col1

	**Design**

	* :ref:`why`
	* :ref:`limitations`

	**Getting started**
	
	* :ref:`tutorial_basic`
	* :ref:`tutorial_console`
	* :ref:`tutorial_parmake`
	* :ref:`tutorial_embedding`
	
.. container:: col2

	.. **Advanced usage**
	.. 
	.. 	* :ref:`tutorial_suspend`
	.. 	* :ref:`tutorial_more`
	
	**Reference**

	* :ref:`commands`
	* :ref:`config`

	**Developement**

	* :ref:`developer`
	* :ref:`extending`
	* :ref:`building_docs`

.. raw:: html

   <div style="clear:left"/>

.. 
   * :ref:`tutorial_cluster`
    
 
.. toctree::
   :hidden:
   :glob:

   features*
   tutorial*
   config*
   commands*
   *



* :ref:`search`

