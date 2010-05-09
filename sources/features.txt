.. _features:

Features and limitations
========================

Extended list of features
-------------------------

* Tolerant of failures: if one of the jobs fails, compmake will
  save the error (Exception) for further inspection, but still
  continues to do all the jobs it can complete.

* Two storage backends:
   * Filesystem based.
   * Network-base using Redis. Necessary for using the 
     multiprocessing module.

* (TODO) Tracking of the computation status (estimated time to go).
* (TODO) Curses-based interface

.. _limitations:


