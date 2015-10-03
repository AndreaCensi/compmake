Changelog
=========

v3.3 2014-10-04
---------------

Readying public release with an OO interface...

Beta version (1.5) - 2012-03-04
-------------------------------

Lots of changes happened in the last year; compmake became
much more robust, and is almost ready for the public.


Development version (0.9.5)
-------------------------------

* Added confirmation before cleaning and remake jobs.

* Fixed bug in display of "done" jobs.

* Added two new job classes: ``top`` and ``bottom``.

* Also implemented selection by function name. Example: ::

       @> ls  func1()

* Implemented greedy scheduling of jobs. We now try to get
  to the top targets as quickly as possible.

* Implemented two new visualization commands: ``details`` and ``stats``.

* Optimized console performance. Now job enumeration is now done using generators,
  allowing processing at the same time we get data from the DB.

* Removed O(n^2) step inside the "list" command, from the old debugging days.

* Miscellaneous cleanup and more tests.


2010-10-30: Version 0.9.4
-------------------------

* Improved the ``progress()`` function to better handle recursive cases.

* We now try to recover from corrupted cache files.

* Added two new job classes: ``todo`` and ``ready``.

* Fixed a critical bug in the ``reload`` command.

* Improved messages here and there.
