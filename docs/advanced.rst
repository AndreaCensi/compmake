.. _advanced0:

Compmake on a cluster
=====================

.. attention: 

   Before starting, check that your setup respects all the assumptions 
   in section :ref:`cluster_assumptions`.

Clustering works by spawning compmake processes on other hosts.


Configuration
-------------------------------------------

(**VERY IMPORTANT SECTION MISSING**)

The details of how compmake uses clustering
-------------------------------------------

This is an explanation (for developers) of how 
|compmake| spawns processes on a cluster.

What happens is that compmake is spawned using a command line similar to this::

    ssh nessa.cds.caltech.edu -R 13005:redisdb:6379 nice -n 10 compmake --hostname=nessa.cds.caltech.edu  --db=redis --redis_host=localhost:13005  --save_progress=False --slave  pybv_experiments.first_order.go_parallel      make_single more=True v_olfaction180n-fields

This long command line contains several pieces. Let's deconstruct it:

* ``ssh nessa.cds.caltech.edu -R 13005:redisdb:6379 ...``

  This opens a ssh connection to the given host. Moreover, it opens a tunnel for accessing the redis server.
  In this case, port 13005 on the remote host is redirected to the host redisdb (port 6379). 
  You got to have the power to use these redirects

* ``... nice -n 10 ...``

  This selects the nice level (option ``cluster_nice``). Be nice to your fellow users.

* ``... compmake --hostname=nessa.cds.caltech.edu  ...``

  The ``hostname`` option gives a nickname to the slave. This nickname is only used
  for statistics purposes.

* ``... --db=redis --redis_host=localhost:13005 ...``

  This selects redis as the DB backend and uses port 13005 to connect to it.
  
* ``... --save_progress=False ...`` 

  The incremental saving progrees is disabled on remote hosts for network performance purposes.

  CONFIG: progress

* ``... --slave  pybv_experiments.first_order.go_parallel ...``

  The ``--slave`` option tells compmake to read the jobs from the DB, instead of running
  the module. The module name here is used only as a namespace.

  SEE: namespaces

* ``... make_single more=True v_olfaction180n-fields``

  Finally, the actual compmake command. ``make_single`` is like ``make`` but without the 
  scheduler. The slave will not look at the job's dependences, and it will throw an error
  if the depenencies are not up to date.



