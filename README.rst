Compmake is a non-obtrusive module that provides Makefile-like facilities (including parallel processing) for batch Python applications.

See http://andreacensi.github.com/compmake/ for extensive documentation. 

**Quick intro**: To use compmake, you have to minimally modify your Python program, such that it can understand the processing layout and the opportunities for parallelization.

.. image:: http://andreacensi.github.com/compmake/images/initial.png
   :class: bigpicture

Here's a demo ``example.py`` to try out:

    http://andreacensi.github.com/compmake/static/demos/example.py

You would run this program using::

    $ compmake example -c make       # runs serially
    $ compmake example -c parmake    # runs in parallel

See the rest of the tutorial at http://andreacensi.github.com/compmake/ .

