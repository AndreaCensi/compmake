.. include:: definitions.txt

.. contents::
   :class: pagetoc

.. _`extending`:

Extending compmake
======================

|towrite|


How to organize the code
----------------------------

Use --plugin to add/remove plugins: ::

    compmake --plugin +mymodule,-dump

Load your plugin: ::

	from compmake import *


Adding console commands
----------------------------------


Adding configuration switches
----------------------------------


Creating a new visualization / notifier
---------------------------------------

|towrite|

Creating a new DB backend
----------------------------------

|towrite|

Creating a new job scheduler
----------------------------------

|towrite| ::

    def my_scheduler(manager):
        return manager.ready_todo[rand]

    register_job_scheduler(my_scheduler, name='random_scheduler', desc='Random scheduler takes a job at random')

Then run::

	compmake --job_scheduler random_scheduler


Creating a new host scheduler
--------------------------------

|towrite| ::

    def my_scheduler(cluster_manager):
        pass

    register_host_scheduler(my_scheduler, name='random_scheduler', desc='Random scheduler takes a job at random')

Then run::

	compmake --host_scheduler random_scheduler




