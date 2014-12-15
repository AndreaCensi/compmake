.. raw:: html
   :file: index-fork.html

..
    .. container:: twitterbadge

       **Latest news**

       .. raw:: html
          :file: twitter_badge.html

.. include:: definitions.txt

Compmake
=================================================================

.. .. raw:: html
..    :file: index-logo.html


.. container:: maincon

  .. raw:: html

    <div style='float:right; margin-right: 3em'> 
    
    <a style="display: block; float: left; border: 0" href="http://purl.org/censi/compmake-manual">
        <p style='text-align: center'>The Compmake Manual</p>
        <img style="float: left; border: 0; width: 15em" src="https://github.com/AndreaCensi/compmake/raw/master/docs/source/my_static/2015-compmake-v3.png"/>
    </a>
    </div>

  Compmake is a Python library that provides 
  "Make"--like facilities to a Python application, including:

  - Minimal effort **job management** and **parallelization** (multiple CPU on a single host, cluster computing using SGE, and experimental support for cloud computing using Multyvac).
  - **Caching** of temporary results: you can interrupt your program 
    and restart it without losing what was already computed.
  - **Failure tolerance**: if a job fails, other jobs that do
    not depend on it continue to be executed.
  - A **console** for inspecting failures and partial completion,
    with familiar commands such as ``make``, ``clean``, etc.


Screencasts
------------


  .. raw:: html

    <iframe src="http://player.vimeo.com/video/111290574" width="300" height="200" 
            frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>
    <iframe src="http://player.vimeo.com/video/110090252" width="300" height="200" 
            frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>
    <iframe src="http://player.vimeo.com/video/110944533" width="300" height="200" 
                frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>
    <iframe src="http://player.vimeo.com/video/111047404" width="300" height="200" 
                frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>


Installation
------------------

The simplest way to install |compmake| is::

$ pip install -U compmake

You can also `fork the project on GitHub`_.

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

.. image:: _static/initial.png 
   :class: bigpicture

An invocation of the kind: ::
  
    function(param)    

becomes: ::

    context.comp(function, param)

The result of ``comp()`` is a promise that can be reused in
defining other jobs. For example, a program like :::
  
    res = function(param)    
    function2(res)

becomes: ::

    r = context.comp(function, param)
    context.comp(function2, r)


Download `a demo example.py`_ that you can try.

.. _`a demo example.py`: _static/demos/example.py

You would run the modified program using::

    $ python example.py

This gives you a prompt: ::
  
  Compmake 3.3  (27 jobs loaded)
  @:

Run "make" at the prompt: ::
  
  @: make

This will run the jobs serially.


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

.. _`example_fail.py`: _static/demos/example_fail.py


Some visualizations of the jobs graph during execution
-------------------------------------------------------


  .. raw:: html

    <style type='text/css'>
      div#animations { 
      }
      div#animations p { font-style: italic; }
      div#animations img { border: solid 1px black;}
      span { font-weight: normal; font-family: monospace; padding: 5px}
      .DONE { background-color: #00FF00; }
      .FAILED { background-color: red; }
      .INPROGRESS { background-color: yellow; }
      .BLOCKED { background-color: brown; }
      dt, dd { padding: 0; margin: 0}
      dt { float: left; width: 8em; clear:left;}
      dd { margin-left: 8em; }
      div#code { max-width: 25em; margin: 2em; 
        
        padding: 1em; border: dashed 1px gray;}
      div#code p { font-style: italic}
    </style>

    <div id='animations'>
    <p>Robustness to job failure</p>
       
    <img src="http://censi.mit.edu/pub/research/201410-compmake-animations/anim-fail-make-function.gif"/>

    <div id='code'>
       <p>Color code for job states</p>
       <dl>
       <dt><span class="DONE">done</span></dt>
       <dd>Job executed succesfully</dd>

       <dt><span class="INPROGRESS">in&nbsp;progress</span></dt>
       <dd>Job currently executing</dd>

       <dt><span class="FAILED">failed</span></dt>
       <dd>Job failed</dd>

       <dt><span class="BLOCKED">blocked</span></dt>
       <dd>Job blocked because a dependency failed</dd>
       </dl>
    </div>

    <p>Simple dynamic jobs</p>

    <img src="http://censi.mit.edu/pub/research/201410-compmake-animations/anim-dynamic-make-function.gif"/>

    <p>Dynamic jobs and recursive parallel executions</p>

    <img src="http://censi.mit.edu/pub/research/201410-compmake-animations/anim-recursion-parmake16-none.gif"/>
    </div>


Manual
------

For more information, please read 

.. raw:: html
  
  <a style="display: block; float: left; border: 0" href="http://purl.org/censi/compmake-manual">
      <p style='text-align: center'>The Compmake Manual</p>
      <img style="float: left; border: 0; width: 15em" src="https://github.com/AndreaCensi/compmake/raw/master/docs/source/my_static/2015-compmake-v3.png"/>
  </a>

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

.. Documentation
.. -------------

.. Still unsure you need this?  Read :ref:`why`.
.. And check out :ref:`limitations` to see if |compmake| can help you.

.. Still interested? Start with the tutorial :ref:`tutorial_basic`.


.. .. container:: col1

.. 	**Design**

.. 	* :ref:`why`
.. 	* :ref:`limitations`

.. 	**Getting started**
	
.. 	* :ref:`tutorial_basic`
.. 	* :ref:`tutorial_console`
.. 	* :ref:`tutorial_parmake`
.. 	* :ref:`tutorial_embedding`
	
.. .. container:: col2

.. 	.. **Advanced usage**
.. 	.. 
.. 	.. 	* :ref:`tutorial_suspend`
.. 	.. 	* :ref:`tutorial_more`
	
.. 	**Reference**

.. 	* :ref:`commands`
.. 	* :ref:`config`

.. 	**Developement**

.. 	* :ref:`developer`
.. 	* :ref:`extending`
.. 	* :ref:`building_docs`

.. .. raw:: html

..    <div style="clear:left"/>

.. .. 
..    * :ref:`tutorial_cluster`
    
 
.. .. toctree::
..    :hidden:
..    :glob:

..    features*
..    tutorial*
..    config*
..    commands*
..    *



.. * :ref:`search`

