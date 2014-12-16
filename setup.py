import os
from setuptools import setup, find_packages

version = "3.5.1"

setup(
    name='compmake',
    author="Andrea Censi",
    url='http://compmake.org',
    version=version,

    description="Compmake is a non-obtrusive module that provides "
        "'make'-like facilities to your Python applications,"
        "including caching of results, robustness to jobs failure, "
        "and multiprocessing/multihost parallel processing.",

    long_description="""
        Compmake is a non-obtrusive module that provides 
        'make'-like facilities to your Python applications,
        including caching of results, robustness to jobs failure,
        and multiprocessing/multihost parallel processing.

        Please see for docs: http://compmake.org 
        and get the manual PDF at: http://purl.org/censi/compmake-manual
    """,

    keywords="parallel processing, make, cmake, manager, recovery",
    license="LGPL",

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Hardware :: Symmetric Multi-processing',
        'License :: OSI Approved :: GNU Library or '
        'Lesser General Public License (LGPL)',
    ],

    package_dir={'':'src'},
    packages=find_packages('src'),
    entry_points={
     'console_scripts': [
       'compmake = compmake.scripts.master:main',
       #'compmake_slave = compmake.jobs.manager_ssh_cluster:compmake_slave'
      ]
    },
    install_requires=[
        'PyContracts',
        'termcolor',
        'setproctitle',
        'PyYaml',
        'psutil',
        'decorator', 
        'SystemCmd',
        #'pyreadline',
    ],

    tests_require=['nose'],
)

