
.. _building_docs:

How to contribute to the documentation
--------------------------------------

These docs are created using sphinx
and are published using the great github pages service.

The following are
instructions to build and publish the documentation.

1. Checkout the compmake repository::

   $ git clone git@github.com:AndreaCensi/compmake.git

2. Go to the docs/ directory, and run the script ``init_website.sh`` .
   This scripts checks out another copy of the repository with the ``gh-pages`` branch.::

   $ cd compmake/docs
   $ ./init_website.sh

3. Edit the ``.rst`` files in the docs/ directory.

4. Run the ``create_website.sh`` script. This runs the sphinx build process.::

   $ ./create_website.sh
   
5. Upload the website using the ``upload.sh`` script::

   $ cd website
   $ ./upload.sh

6. Redo steps 3-5 until the documentation is perfect!
