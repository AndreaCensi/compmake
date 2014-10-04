Graph
--------------------

There is a command "graph" that can produce a graphical depiction of the computation.
(to use this feature, you should have installed ``graphviz`` and the ``gvgen`` library)

If you run::

$ compmake my_program diagram

before running ``make`` you will see the following:

.. image:: my_static/example1/graph_before.png
   :width: 100%
   
The color grey means that the job has not started. After running ``make``, the output will be:

.. image:: my_static/example1/graph_after.png
   :width: 100%

Here, green means that the job is done.

After we run 

.. image:: my_static/example1/graph3.png
   :width: 100%

Here, green means that the job is done.

The computation graph... (to write)

