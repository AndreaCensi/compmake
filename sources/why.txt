.. include:: definitions.txt

.. contents::
   :class: pagetoc

.. _why:

Why using  compmake
-------------------------

This section explains why you would want to use |compmake|. If you already know why, skip ahead to
:ref:`preparing`.

Suppose that you are working on this simple program:

.. literalinclude:: my_static/example1/original.py

This is a very simple program. Suppose, however, that the functions ``func1()``, ``func2()`` are very computational expensive. If that's the case, you encounter several problems that slow down your progress.

* Suppose you want to improve the function ``draw()``. You find yourself running and running
  the computation again, even though ``func1`` and ``func2`` did not change. 
  It's obvious that some caching mechanism is needed. Yes, you can easily dump the intermediate
  results to file using the `pickle module`_. Or you can use `memoization`_: you google
  for the right Python decorator, maybe you add a persistent cache.
  But now the 5 lines program has become a (buggy) 30 lines program. 
  
  **You wonder whether there's an easy way to do caching.**

  .. _`pickle module`: http://docs.python.org/library/pickle.html
  .. _`memoization`: http://en.wikipedia.org/wiki/Memoization

* Suppose you want to try out another value for parameter ``param1``. Because you don't want to do the 
  other computations again, you comment out one line, writing ``param1 = [42]``. Later on, 
  you wonder whether you did try all combinations of ``param1`` and ``param2``. 

  **You wonder whether there is an easy way to run selectively part of the computation**.

* Ooops! You left the computation running for the night. When you check it out in the morning you
  discover that there is one combination of ``param1`` and ``param2`` that makes ``func2`` throw
  an exception. Your program terminated and you have to start again from the beginning.

  **You wonder whether there's an easy way to work around the failing of part of your computations.**

* What about parallelization? Yes, the `multiprocessing module`_ seem quite easy to use.
  You just need to add a few lines of code. But wait, there is a nested loop. You probably
  have to write different functions... and, where exactly can you parallelize?

  **You wonder why Python cannot discover the parallelizable structure in your code.** 

  .. _`multiprocessing module`: http://docs.python.org/library/multiprocessing.html

* No, really, what you want is running your computation on the big server down the hall. No problem,
  you can log in there. But wait, you can only run ``draw()`` on your desktop because the server
  does not have the required libraries.

  **You wonder whether there's a way to easily share the computation across machines.**

In short, writing computationally intensive batch processes, (especially simulations), presents
some common problems. In isolation, each of them could be overcome by writing ad hoc code.
|compmake|  **helps you** by solving each of these problems (and more) in a robust way, once and for all.
The price you have to pay is a slight modification of the source code, as explained in the following section.


* Interested in using |compmake|? Read the first part of the tutorial: :ref:`tutorial_basic`.

