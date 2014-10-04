.. include:: definitions.txt

.. _tutorial_cluster:

Compmake on a cluster
=====================

.. attention: 

   Before starting, check that your setup respects all the assumptions 
   in section :ref:`cluster_assumptions`.


Also note that you have to configure |compmake| to use
Redis_ (and install redis-py_).

.. _Redis: http://code.google.com/p/redis/

.. _redis-py: http://github.com/andymccurdy/redis-py


Configuration
------------------------------------------- 

You have to provide |compmake| with a configuration file describing 
the machines in your cluster. We use the YAML_ format.
Here is an example configuration file::

	hosts:
		nickname_machine1:
			host: 10.0.0.1
			processors: 3
			
		nickname_machine2:
			host: 10.0.0.2
			processors: 8

You can omit the ``host`` attribute, |compmake| will guess that the nickname is the hostname: ::

	hosts:
		10.0.0.1: 
			processors: 3
		
		10.0.0.1:
			processors: 8

The ``processors`` field tells |compmake| how many jobs to spawn on that machine.

By default, |compmake| looks for a file named ``cluster.yaml`` in the current directory. It is possible to specify a different file using the ``--cluster-conf`` option.

.. _YAML: http://www.yaml.org/

.. _nice: http://en.wikipedia.org/wiki/Nice_%28Unix%29

Therefore, a minimal command line for using |compmake|'s cluster capabilities is: ::

	$ compmake --db=redis --cluster_conf my_cluster.yaml  <my module>


The configuration switch ``cluster_nice`` gives the nice_ level to use when spawning processes.


The details of how compmake uses clustering
-------------------------------------------


This is an explanation (for developers) of how 
|compmake| spawns processes on a cluster.

Clustering works by spawning |compmake| processes on other hosts.


What happens is that |compmake| is spawned using a command line similar to this::

    ssh nessa.cds.caltech.edu -R 13005:redisdb:6379 
        nice -n 10 compmake --hostname=nessa.cds.caltech.edu  
                            --db=redis --redis_host=localhost:13005  
                            --save_progress=False 
                            --slave  <namespace>
                    make_single  <job name>

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

* ``... --slave <namespace> ...``

  The ``--slave`` option tells compmake to read the jobs from the DB, instead of running
  the module. The module name here is used only as a namespace.

  SEE: namespaces

* ``... make_single  <job name>``

  Finally, the actual compmake command. ``make_single`` is like ``make`` but without the 
  scheduler. The slave will not look at the job's dependences, and it will throw an error
  if the depenencies are not up to date.



