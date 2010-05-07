Compmake
=========

.. raw:: html
   :file: fork.html

.. image:: workers.jpg
   :align: right

``compmake`` is ``make`` for batch python processes. 
It is a non-obtrusive module that provides:

* ``make``--like facilities to your computations (``make``, ``clean``, etc.),
  including caching of temporary results. That is you can do a CTRL+C, play your
  videogame, and then restart compmake without losing data.
* **Single-host parallelization** using the ``multiprocessing`` module.
* **Multiple-host parallelization** using ssh-spawned slaves.


Interested? Please read along:

.. toctree::
   :maxdepth: 1

   tutorial.rst
   features.rst
   install.rst
   parallel.rst
   commandline.rst
   developer.rst
   advanced.rst
   commands.rst
   config.rst


Quick installation
------------------

The quick install is::

$ easy_install compmake

This will allow you to run ``compmake`` on a single host.
However, there are also separate dependencies to install for some
advanced features. See install.rst__ for more information.


Source download
---------------

.. raw:: html
   :file: download.html



Feedback
---------

Compmake is currently developed by Andrea Censi. Contributors are most welcome.

Please use the issue_tracker_on_github_ for bugs and requested features.

:: _issue_tracker_on_github: https://github.com/AndreaCensi/compmake/issues

